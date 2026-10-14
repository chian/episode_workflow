"""Composition and mandatory lifecycle shared by the approved episode bindings."""

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Callable, Mapping

from ...credit_assignment.research import ResearchController
from ...method_loop import (
    ChildEpisodeUnit, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree,
    Grain, Leaf, ReportContract, SourceEnd,
)
from ...task_executors._http import ProviderError
from ...task_executors.evidence_extraction.argo import ModelOutputError
from ...task_executors.outbreak_search.queries import search_results_from_provider, source_locator, source_text
from ...task_executors.scenario_metrics.catalog import METRICS, PAPER, metric_catalog_record, metric_routes
from ...task_executors.scenario_metrics.evaluate import metric_conditions
from ...task_executors.scenario_metrics.dependencies import PARAMETER_DERIVATIONS
from ...task_executors.scenario_metrics.conditional import CONDITIONAL_INPUTS, conditional_inputs
from .communication import decision_diagnostics, reading_coverage
from .goal_state import GLOBAL_GOAL_PROGRESS, GLOBAL_SCORE_WEIGHTS, ScientificGoalState
from .model_tiers import ModelTier, tier_for_operation
from .progress import PARAMETER_EVIDENCE, parameter_requirements, parameter_support, progress_credit
from .records import (Credit, Ledger, ResearchMessage, ResearchResult, diagnostic_value, condensed_diagnostics,
                      identity, scenario_relation_key)
from .tools import TOOLS, tool_options


TREE = {
    "evaluate_airborne_safety_guideline": ("investigate",),
    "investigate": ("strategy",),
    "strategy": ("search",),
    "search": ("page",),
    "page": ("source_table", "report", "lexical_probe"),
    "source_table": (), "report": (), "lexical_probe": (),
}
SCIENTIFIC = {"evaluate_airborne_safety_guideline", "investigate"}
CONSISTENCY = "evidence_consistency"


@dataclass(frozen=True)
class ResearchLimits:
    max_model_calls: int = 240
    max_total_units: int = 240
    search_limit: int = 8
    text_window_chars: int = 12000
    yield_window: int = 4

    def __post_init__(self):
        for name, value in vars(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.yield_window < 2 or self.search_limit > 100 or self.text_window_chars < 100:
            raise ValueError("Invalid research control limits")


@dataclass(frozen=True)
class ResearchProviders:
    agent: Callable[[Mapping], Mapping]
    search: Callable
    retrieve: Callable
    event: Callable | None = None
    trace_event: Callable | None = None
    page_assessor: object | None = None
    agent_for_tier: Callable[[Mapping, ModelTier], Mapping] | None = None
    model_route: Callable[[str, ModelTier], Mapping[str, str]] | None = None
    relation_event: Callable | None = None
    source_target_assessor: Callable[[Mapping], Mapping[str, float]] | None = None
    scenario_parameter_assessor: Callable[[Mapping], Mapping] | None = None
    preflight_attempts: list[Mapping] | None = None


class BudgetExceeded(RuntimeError):
    pass


def selected_choice(value, options, field):
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"{field} must be one exact declared key {list(options)!r}; received {value!r}")
    return value


class ResearchRun:
    def __init__(self, providers, limits, research_request, metrics, *, initial=None, scenario_selection=None):
        self.providers, self.limits = providers, limits
        self.research_request, self.metrics = research_request, metrics
        self.initial = initial
        self.global_goal = ScientificGoalState(metrics, initial)
        self.fixed_scenarios = initial is not None
        self.tools = {k: v for k, v in TOOLS.items()
                      if not self.fixed_scenarios or k != "compare_predictions_with_observations"}
        self.documents = {}
        self.model_attempts = list(providers.preflight_attempts or ())
        self.provider_events = []
        self.provider_unavailable = None
        self.model_calls = len(self.model_attempts)
        self.total_units = self.sequence = 0
        self.diagnostic_sequence = 0
        self.controller_specs = {}
        self.sources = {}
        self.root_source = self.root_key = None
        root = Path(__file__).resolve().parents[2]
        paths = list(root.glob("*.py"))
        for folder in ("case_reports", "credit_assignment", "method_loop", "task_executors"):
            paths.extend((root / folder).rglob("*.py"))
        self.implementation = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted(paths)}
        self.context = {"research_request": research_request, "reference_model": PAPER,
                        "scenario_selection": scenario_selection,
                        "requested_metrics": list(metrics), "fixed_scenarios": self.fixed_scenarios}
        units = {
            "evaluate_airborne_safety_guideline": "a selected calculation tool or completed investigation",
            "investigate": "a completed evidence strategy with mandatory candidate assessment",
            "strategy": "a completed search for a proposed query within this approach",
            "search": "a completed source episode selected from this query's results",
            "page": "a completed reading episode selected from physically available material",
            "source_table": "a table query execution with mandatory evidence admission",
            "report": "a document-order reading window with retained context",
            "lexical_probe": "a ranked unprocessed source chunk",
        }
        self.grains = {name: Grain(name, unit, "contracted findings and admitted scientific state", self.controller)
                       for name, unit in units.items()}
        self.tree = EpisodeTree(self.grains["evaluate_airborne_safety_guideline"], {
            self.grains[parent]: tuple(self.grains[name] for name in children)
            for parent, children in TREE.items() if children
        })
        self.emit_trace("run_started", research_request=research_request, metrics=list(metrics),
                        scenario_selection=scenario_selection,
                        target_set=[row["subject"] for row in initial.scenarios
                                    if row.get("role", "target") == "target"] if initial else [],
                        target_fixed_inputs={row["subject"]: {
                            "fixed_parameters": row.get("fixed_parameters", {}),
                            "fixed_conditions": row.get("fixed_conditions", {})}
                            for row in initial.scenarios if row.get("role", "target") == "target"}
                            if initial else {},
                        implementation_sha256=dict(self.implementation))
        if initial is not None:
            scope = self.global_goal.preview()
            self.emit_trace("scenario_parameter_scope_initialized", model_calls=self.model_calls,
                independent_values_needed=scope["recorded_target_inputs"]["required"],
                scenario_parameter_relations=list(initial.scenario_parameter_relations),
                score_weights=scope["score_weights"])

    def emit_trace(self, kind, **payload):
        if self.providers.trace_event:
            self.providers.trace_event(diagnostic_value({"event": kind, **payload}))

    def search(self, query, limit):
        event = {"operation": "search", "query": query, "limit": limit, "status": "started"}
        self.provider_events.append(event)
        try:
            results = search_results_from_provider(self.providers.search(query, limit))
        except (ProviderError, OSError, ValueError) as exc:
            event.update(status="failed", why=str(exc))
            self.emit_trace("provider_event", provider_event=event)
            raise
        event.update(status="completed", sources=[source_locator(row) for row in results])
        self.emit_trace("provider_event", provider_event=event)
        return results

    def retrieve(self, candidate):
        event = {"operation": "retrieve", "source": source_locator(candidate), "status": "started"}
        self.provider_events.append(event)
        try:
            result = self.providers.retrieve(candidate)
            body = result if isinstance(result, str) else source_text(result or {})
            if not isinstance(body, str) or not body.strip():
                raise ValueError("Retrieval returned no source text")
        except (ProviderError, OSError, ValueError) as exc:
            event.update(status="failed", why=str(exc))
            self.emit_trace("provider_event", provider_event=event)
            raise
        event.update(status="completed", characters=len(body), sha256_utf8=hashlib.sha256(body.encode()).hexdigest())
        self.emit_trace("provider_event", provider_event=event)
        return result

    def controller(self, path):
        focus, initial, scientific, outputs = self.controller_specs[path[-1][1]]
        outputs = set(METRICS) if outputs is None else set(outputs)
        groups = tuple(g for g in (tuple(f for f in focus if f not in outputs and f not in {CONSISTENCY, GLOBAL_GOAL_PROGRESS}),
                                   tuple(f for f in focus if f in outputs),
                                   tuple(f for f in focus if f == CONSISTENCY),
                                   tuple(f for f in focus if f == GLOBAL_GOAL_PROGRESS)) if g) if scientific else None
        return ResearchController(focus, window=self.limits.yield_window, initial=initial,
                                  capacity=1 if scientific else 2, groups=groups, sum_qualities=scientific,
                                  point_scores=not scientific)

    def root_credit_projection(self):
        """Read-only root score from the shared admitted ledger, including nested child work."""
        if self.root_key is None:
            return None
        credit = self.root_source.credit(self.global_goal.ledger.result())
        controller = self.controller((("root", self.root_key),))
        return controller.observe("shared_goal_projection", credit, is_root=True).score

    def agent(self, request, *, completing=False, tier=None):
        if self.provider_unavailable is not None:
            exc = ProviderError(self.provider_unavailable["why"])
            exc.model_call_diagnostic = dict(self.provider_unavailable)
            raise exc
        if self.model_calls >= self.limits.max_model_calls:
            raise BudgetExceeded("model_call_budget_exhausted")
        self.model_calls += 1
        operation = request.get("operation", "")
        tier = tier or tier_for_operation(operation)
        route = dict(self.providers.model_route(operation, tier)) if self.providers.model_route else {}
        attempt = {"call": self.model_calls, "operation": request.get("operation", ""),
                   "phase": "mandatory_completion" if completing else "work",
                   "model_tier": tier.value, **route,
                   "request": diagnostic_value(request)}
        self.model_attempts.append(attempt)
        try:
            result = (self.providers.agent_for_tier(request, tier)
                      if self.providers.agent_for_tier else self.providers.agent(request))
            attempt["response"] = diagnostic_value(result)
            if not isinstance(result, Mapping):
                raise ValueError("Research agent must return a JSON object")
        except (ProviderError, OSError, ValueError) as exc:
            diagnostic = {**self.model_diagnostic(exc), "model_call": self.model_calls,
                          "operation": attempt["operation"]}
            exc.model_call_diagnostic = diagnostic
            attempt.update(status="response_failed", diagnostic=diagnostic)
            if diagnostic.get("category") == "provider_usage_limit":
                self.provider_unavailable = dict(diagnostic)
            if isinstance(exc, ModelOutputError):
                exc.diagnostic.update(model_call=self.model_calls, operation=attempt["operation"])
                attempt["raw_response"] = diagnostic_value(exc.raw_response)
            self.emit_trace("model_attempt", attempt=attempt)
            raise
        attempt["status"] = "json_object_received_not_yet_admitted"
        self.emit_trace("model_attempt", attempt=attempt)
        return result

    def complete(self, request, *, tier=None):
        """Record mandatory processing under the caller's global cap."""
        return self.agent(request, completing=True, tier=tier)

    def model_diagnostic(self, exc):
        if hasattr(exc, "model_call_diagnostic"):
            return dict(exc.model_call_diagnostic)
        if isinstance(exc, BudgetExceeded):
            return {"category": "operational_limit", "why": str(exc)}
        details = dict(exc.diagnostic) if isinstance(exc, ModelOutputError) else {
            "category": "provider_failure" if isinstance(exc, (ProviderError, OSError)) else "invalid_action_contract",
            "why": str(exc)}
        return details

    def identify_diagnostic(self, diagnostic):
        if "diagnostic_id" in diagnostic:
            self.diagnostic_sequence = max(self.diagnostic_sequence, diagnostic["diagnostic_id"])
            return diagnostic
        self.diagnostic_sequence += 1
        return {**diagnostic, "diagnostic_id": self.diagnostic_sequence}

    def episode(self, grain, source, *, goal, focus, contract=None, proposal=None):
        self.sequence += 1
        key = f"{grain}:{self.sequence}"
        source.focus = tuple(focus) if contract is None else (PARAMETER_EVIDENCE, GLOBAL_GOAL_PROGRESS)
        source.scientific = grain in SCIENTIFIC
        source.goal = goal
        self.sources[goal.goal_id] = source
        source.parent_contract = contract
        source.requested_subjects = tuple(contract.measurements.get("subjects", ())) if contract else ()
        if contract is not None:
            source.parameter = contract.measurements.get("parameter")
            source.parameter_requirements = parameter_requirements(source.parameter)
        self.controller_specs[key] = (source.focus, source.credit(source.ledger.result()), source.uses_scientific_credit(), source.output_fields)
        if grain == "evaluate_airborne_safety_guideline":
            self.root_source, self.root_key = source, key
        return Episode(self.grains[grain], key, source, EpisodeRequest(
            goal, ResearchMessage(str(goal.objective), source.requested_subjects,
                                  diagnostic_value(proposal or {})), contract),
            source.build_result, on_unit=source.after_verdict)

    def child(self, parent, source, grain, objective, *, contract, proposal):
        parent_source = self.sources[parent.goal.goal_id]
        if (parent_source.parameter is not None
                and contract.measurements.get("parameter") != parent_source.parameter):
            raise ValueError("A search branch cannot change its assigned calculation parameter")
        goal = EpisodeGoal.child(parent.goal, objective=objective,
                                 result_contract={"information": contract.as_record()})
        return self.episode(grain, source, goal=goal, focus=(),
                            contract=contract, proposal=proposal)


class ResearchSource:
    def __init__(self, run, inherited=()):
        if isinstance(inherited, ResearchResult):
            inherited = replace(inherited, diagnostics=tuple(run.identify_diagnostic(d) for d in inherited.diagnostics))
        self.run, self.ledger = run, Ledger(inherited)
        self.initial = self.ledger.result()
        self.focus, self.scientific = (), False
        self.goal = None
        self.parent_contract = None
        self.requested_subjects = ()
        self.parameter = None
        self.parameter_requirements = frozenset()
        self.credit_subjects = None
        self.output_fields = None
        self.pending = None
        self.failure = ""
        self.completion_diagnostic = None
        self.evaluated_units = 0
        self.last_proposal = None
        self.information_assessment = []
        self.evidence_handoff_baseline = None
        self.decision_summary = {"findings": [], "uncertainties": [], "failures": []}
        self.communicated = {"findings": set(self.initial.findings), "issues": set(self.initial.issues),
                             "diagnostics": {identity(d) for d in self.initial.diagnostics}}

    def contract(self, decision, *, subjects=(), meaning=None, deliverable="source_findings", parameter=None,
                 target_scenarios=None):
        """The invoking binding supplies a decision and its required measurements."""
        measurements = {"question": meaning or decision,
                        "deliverable": deliverable, "subjects": list(subjects),
                        "parameter": self.parameter if parameter is None else parameter}
        if target_scenarios is not None:
            measurements["target_scenarios"] = target_scenarios
        return ReportContract(decision=decision,
            measurements=measurements,
            information={
                "findings": f"A brief synthesis for this decision: {decision}. Return only consequential trends, changed understanding, and uncertainty or failure implications needed to steer the next action. No evidence inventory, field checklist, transcript or raw diagnostics.",
            })

    def build_result(self, record):
        reason = self.failure or (record.controller_state.reason if record.ended_by == "yield_stop" else record.ended_by)
        if self.failure and self.completion_diagnostic is None:
            self.completion_diagnostic = self.run.identify_diagnostic({
                "stage": "episode_completion",
                "category": ("provider_usage_limit" if "provider_usage_limit" in reason else
                             "operational_limit" if "budget_exhausted" in reason else "source_termination"),
                "why": reason,
                "requested_fields": list(self.focus),
                "question": str(self.goal.objective),
                "completion": {"ended_by": record.ended_by, "reason": reason,
                               "units_consumed": record.units_consumed,
                               "evaluated_units": self.evaluated_units},
            })
            self.ledger.diagnostics.append(self.completion_diagnostic)
        evaluated = bool(self.evaluated_units) or (
            record.units_consumed == 0 and not self.failure and record.ended_by == "exhausted")
        return self.ledger.result(evaluated=evaluated, stop_reason=reason)

    def after_verdict(self, unit, contribution, view):
        self.run.total_units += 1
        if contribution.episode_update is not None:
            self.decision_summary["findings"].append(
                contribution.episode_update.report.as_record()["findings"])
        if self.pending is not None:
            new_issues = [v for v in self.pending.issues if v not in self.ledger.issues]
            new_diagnostics = [d for d in self.pending.diagnostics if d not in self.ledger.diagnostics]
            self.ledger.merge(self.pending)
            before_goal = self.run.global_goal.preview()
            previous_relations = dict(self.run.global_goal.ledger.source_target_relationships)
            previous_parameter_relations = dict(self.run.global_goal.ledger.scenario_parameter_relations)
            previous_assumptions = dict(self.run.global_goal.ledger.assumptions)
            previous_estimates = set(self.run.global_goal.ledger.estimates)
            global_status = self.run.global_goal.commit(self.pending)
            changed_relations = [row for key, row in self.run.global_goal.ledger.source_target_relationships.items()
                                 if previous_relations.get(key) != row]
            changed_parameter_relations = [row for key, row in self.run.global_goal.ledger.scenario_parameter_relations.items()
                                           if previous_parameter_relations.get(key) != row]
            for row in changed_parameter_relations:
                self.run.emit_trace("scenario_parameter_compared", episode_type=type(self).__name__,
                    model_calls=self.run.model_calls, relationship=row)
            for row in changed_relations:
                self.run.emit_trace("source_target_relationship_assessed", status="assessed",
                    episode_type=type(self).__name__, model_calls=self.run.model_calls,
                    investigated_target_subjects=list(self.requested_subjects),
                    source_event={"locator": row["source"], "subject": row["source_subject"],
                                  "roles": row["source_role"]},
                    target_scenario=row["target_subject"], assigned_parameter=row["parameter"],
                    relationship=row)
                if self.run.providers.relation_event:
                    self.run.providers.relation_event({
                        "investigated_target_subjects": list(self.requested_subjects),
                        "source": row["source"], "source_subject": row["source_subject"],
                        "source_roles": row["source_role"], "target_subject": row["target_subject"],
                        "parameter": row["parameter"], "score": row["score"],
                        "known": row["known"], "considered": row["considered"]})
            for key, row in self.run.global_goal.ledger.assumptions.items():
                if (previous_assumptions.get(key) == row
                        or row.get("role") in {"scenario_constraint", "request_constraint"}
                        or row.get("subject") not in global_status["target_inputs"]):
                    continue
                verdict = row.get("review", {}).get("verdict")
                self.run.emit_trace("target_input_status",
                    status=("reviewed_usable" if verdict in {"supported", "provisional"} else
                            "recorded_unassessed" if verdict == "unassessed" else
                            "recorded_unsupported" if verdict == "unsupported" else "contradicted"),
                    episode_type=type(self).__name__, model_calls=self.run.model_calls,
                    subject=row.get("subject"), field=row.get("field"), value=row.get("value"),
                    unit=row.get("unit"), review_verdict=verdict, assumption_key=key)
            for key, row in self.run.global_goal.ledger.estimates.items():
                if key in previous_estimates:
                    continue
                scenario = self.run.global_goal.ledger.scenarios.get(row.get("subject"), {})
                self.run.emit_trace("calculation_inputs_selected", episode_type=type(self).__name__,
                    model_calls=self.run.model_calls, scenario_subject=row.get("subject"),
                    scenario_role=scenario.get("role", "unregistered_source_context"),
                    parameterization=row.get("label"), parameters=row.get("parameters"),
                    assumption_versions=row.get("assumption_versions", {}),
                    calculated_outputs=[name for name, output in row.get("metrics", {}).items()
                                        if output.get("status") == "calculated"])
            root_projection = self.run.root_credit_projection()
            if (global_status["scores"] != before_goal["scores"]
                    or global_status["target_inputs"] != before_goal["target_inputs"]
                    or changed_relations or changed_parameter_relations):
                self.run.emit_trace("global_goal_progress", episode_type=type(self).__name__,
                    unit=unit.label, model_calls=self.run.model_calls,
                    scores=global_status["scores"],
                    score_weights=global_status["score_weights"],
                    weighted_score=global_status["weighted_score"],
                    root_credit_projection=root_projection,
                    values_found=global_status["recorded_target_inputs"]["recorded"],
                    values_needed=global_status["recorded_target_inputs"]["required"],
                    target_routes={name: row["best_route"] for name, row in global_status["target_routes"].items()},
                    target_assumptions=global_status["target_assumptions"],
                    recorded_target_inputs=global_status["recorded_target_inputs"],
                    independent_target_values=global_status["independent_target_values"],
                    target_inputs=global_status["target_inputs"],
                    source_target_learning=global_status["source_target_learning"],
                    calibration=global_status["calibration"],
                    computed_outputs=global_status["computed_outputs"],
                    requested_outputs=global_status["requested_outputs"])
            self.evaluated_units += int(self.pending.evaluated)
            if self.run.providers.event:
                self.run.providers.event({"unit": unit.label, "evaluated": self.pending.evaluated,
                    "admitted_facts": len(self.pending.facts), "estimates": len(self.pending.estimates),
                    "issues": new_issues, "gain": view.controller_step.gain,
                    "stop": view.controller_step.stop, "model_calls": self.run.model_calls,
                    "model_call_limit": self.run.limits.max_model_calls,
                    "global_goal_score": global_status["weighted_score"],
                    "root_credit_projection": root_projection,
                    "target_assumptions": global_status["target_assumptions"],
                    "recorded_target_inputs": global_status["recorded_target_inputs"],
                    "source_target_learning": global_status["source_target_learning"],
                    "computed_outputs": global_status["computed_outputs"],
                    "requested_outputs": global_status["requested_outputs"]})
            self.run.emit_trace("credit_verdict", episode_id=self.goal.goal_id,
                episode_type=type(self).__name__, question=str(self.goal.objective), focus=list(self.focus),
                contract=self.parent_contract.as_record() if self.parent_contract else None,
                unit=unit.label, evaluated=self.pending.evaluated, gain=view.controller_step.gain,
                score=view.controller_step.score, stop=view.controller_step.stop,
                parameter=self.parameter, parameter_evidence=self.information_assessment,
                model_calls=self.run.model_calls, issues=new_issues, diagnostics=new_diagnostics)
            self.pending = None

    def assess(self, result):
        """Source admission and investigation reasonableness remain mandatory."""
        return result

    def project(self, result):
        self.pending = self.assess(result)
        self.pending = replace(self.pending, diagnostics=tuple(
            self.run.identify_diagnostic(d) for d in self.pending.diagnostics))
        accumulated = Ledger(self.ledger.result())
        accumulated.merge(self.pending)
        return self.credit(accumulated.result(evaluated=self.pending.evaluated))

    def uses_scientific_credit(self):
        return self.scientific

    def credit(self, result):
        if self.uses_scientific_credit():
            local = result.credit(tuple(field for field in self.focus if field != GLOBAL_GOAL_PROGRESS),
                                  scientific=True, subjects=self.credit_subjects, outputs=self.output_fields)
            return self.global_credit(local, result) if GLOBAL_GOAL_PROGRESS in self.focus else local
        if (self.parent_contract is not None
                and self.parent_contract.measurements.get("deliverable") == "source_findings"
                and self.parent_contract.measurements.get("target_scenarios") is not None):
            from .relevance import TARGET_RELEVANCE_CREDIT_MEANING, target_relevance_credit
            all_targets = self.parent_contract.measurements["target_scenarios"]
            targets = {name: all_targets[name] for name in self.requested_subjects if name in all_targets} or all_targets
            groups = {row["type_id"]: row for row in result.source_event_types}
            self.credit_meaning_override = TARGET_RELEVANCE_CREDIT_MEANING
            self.information_assessment, credit = target_relevance_credit(
                result, self.parameter_requirements, groups, targets, parameter=self.parameter)
            return self.global_credit(credit, result)
        self.information_assessment = parameter_support(result, self.parameter_requirements,
            hypotheses_only=self.parent_contract.measurements.get("deliverable") == "assumption_hypotheses",
            subjects=self.requested_subjects)
        return self.global_credit(progress_credit(self.information_assessment, evaluated=result.evaluated), result)

    def global_credit(self, local, result):
        status = self.run.global_goal.preview(result)
        qualities = (*local.qualities, *((GLOBAL_GOAL_PROGRESS, name, value * GLOBAL_SCORE_WEIGHTS[name])
                                        for name, value in status["scores"].items()))
        return Credit(identities=local.identities, evaluated=local.evaluated, qualities=qualities,
                      quality_resolution=min(local.quality_resolution or 1.0, 0.001))

    def evidence_handoff_ready(self):
        """Return new parameter evidence promptly for a higher-level scientific decision."""
        points = sum(float(row.get("points", 0)) for row in self.information_assessment)
        if self.evidence_handoff_baseline is None:
            self.evidence_handoff_baseline = points
            return False
        return self.evaluated_units > 0 and points > self.evidence_handoff_baseline + 1e-9

    def receive(self, result, completion, request):
        if not isinstance(result, ResearchResult):
            raise TypeError("Unexpected scientific child result")
        return self.project(result)

    def edge(self, child):
        return ChildEpisodeUnit(child, self.receive, self.synthesize)

    def synthesize(self, result, completion, request):
        # Detailed child state is input to synthesis, never the parent's return.
        child_source = self.run.sources[request.goal.goal_id]
        changes = {
            "facts": [f.semantic_record() for f in result.facts if f.key not in self.ledger.facts],
            "evidence": [e for e in result.evidence if e not in self.ledger.evidence.values()],
            "assumptions": [a for a in result.assumptions
                            if self.ledger.assumptions.get(a["key"]) != a],
            "findings": [f for f in result.findings if f not in self.ledger.findings],
            "diagnostics": condensed_diagnostics(
                d for d in result.diagnostics if d not in self.ledger.diagnostics),
            "reading_coverage": reading_coverage(a for a in result.reading_attempts
                if identity(a) not in self.ledger.reading_attempts),
            "source_event_types": [row for row in result.source_event_types
                                   if self.ledger.source_event_types.get(row["type_id"]) != row],
            "source_target_relationships": [row for row in result.source_target_relationships
                if self.ledger.source_target_relationships.get((row["source"], row["source_subject"],
                    row["target_subject"], row["parameter"])) != row],
            "scenario_parameter_relations": [row for row in result.scenario_parameter_relations
                if self.ledger.scenario_parameter_relations.get(scenario_relation_key(row)) != row],
        }
        try:
            report = self.run.complete({
                "operation": "synthesize_research_findings",
                "parent_contract": request.report_contract.as_record(),
                "child_objective": str(request.goal.objective),
                "child_parameter_evidence": child_source.information_assessment,
                "child_findings": child_source.communication_context()["findings"],
                "changes": changes, "completion_reason": result.stop_reason,
                "instruction": (
                    "Return one brief paragraph answering the parent's reporting contract. "
                    "Synthesize trends and consequential changes in understanding that help the parent "
                    "choose its next action. Mention uncertainty, contradictions or a failure's meaning "
                    "only when they affect that decision. Explain what an unsuccessful route taught; "
                    "do not equate failed extraction with absence of evidence. Distinguish unexamined "
                    "material from examined but uninformative material. Do not reproduce facts, tables, "
                    "field lists, provenance indexes, audit identifiers, reading offsets, raw errors or the child's history. "
                    "Detailed evidence stays in the scientific records for calculation and credit. "
                    "Preserve consequential disagreements between parameter values and distinguish "
                    "different conditions from conflicting evidence for the same claim. Evidence points "
                    "do not choose a value or establish scientific confidence. "
                    "Do not restate the parent's whole task, prescribe its next action, assign credit "
                    "or declare the overall goal achieved. Your only return field is findings."),
                "response_contract": {"type": "object", "additionalProperties": False,
                    "required": ["findings"], "properties": {
                        "findings": {"type": "string", "minLength": 1,
                                     "description": request.report_contract.information["findings"]}}}})
            if (set(report) != {"findings"} or not isinstance(report["findings"], str)
                    or not report["findings"].strip()):
                raise ValueError("Child synthesis must contain only a brief findings paragraph")
        except (BudgetExceeded, ProviderError, ValueError, TypeError, KeyError, OSError) as exc:
            diagnostic = self.run.identify_diagnostic({"stage": "synthesis", **self.run.model_diagnostic(exc)})
            if self.pending is not None:
                self.pending = replace(self.pending, diagnostics=(*self.pending.diagnostics, diagnostic))
            report = {"findings": "The child returned, but its steering synthesis could not be completed. "
                      "Admitted scientific records are retained; no conclusion about the evidence follows "
                      "from this communication failure."}
        for state in (self.ledger.result(), result):
            self.communicated["findings"].update(state.findings)
            self.communicated["issues"].update(state.issues)
            self.communicated["diagnostics"].update(identity(d) for d in state.diagnostics)
        return report

    def context(self):
        if self.parent_contract is not None:
            context = {"disease_of_interest": self.run.context.get("disease_of_interest"),
                       "parent_information_contract": self.parent_contract.as_record()}
            if "target_scenarios" in self.parent_contract.measurements:
                context["target_scenario_use"] = (
                    "The contract's target_scenarios describe the caller's intended application, "
                    "not observed source events or evidence. Use their activity, population and "
                    "conditions to guide evidence relevance for the assigned parameter, including "
                    "Cq applicability. Related settings and indirect evidence remain useful when "
                    "their transfer assumptions and differences are identified. Retain each "
                    "source event's actual conditions; never substitute target-case inputs for "
                    "outbreak observations or add scoring requirements from these descriptions.")
            if self.scientific:
                context.update(fixed_scenarios=self.run.fixed_scenarios,
                    defined_scenarios={name: self.ledger.scenarios[name] for name in self.requested_subjects
                                       if name in self.ledger.scenarios})
            return context
        return {**self.run.context, "defined_scenarios": dict(self.ledger.scenarios),
                "known_source_subjects": sorted(
                    {f.subject for f in self.ledger.facts.values() if f.kind.startswith("source_")}
                    | {e["subject"] for e in self.ledger.evidence.values() if e.get("kind") == "source_evidence"}),
                "input_roles": {
                    "fixed_case_conditions": "Caller-owned givens; preserve them, do not rediscover or replace them.",
                    "calculation_variables": "Retain or solve the variables declared by the case. Do not assign arbitrary point values merely to fill an output.",
                    "missing_physical_inputs": "The investigation may propose named, qualified hypotheses using bounds, indirect evidence, physical reasoning or explicit guesses. Lack of direct evidence lowers support; it is not a prohibition on proposing or calculating a hypothesis. These are not new scenarios or caller givens.",
                },
                "calculated_model_behavior": tool_options(self.ledger),
                "requested_subjects": list(self.requested_subjects),
                "implemented_model": {
                    "tools": self.run.tools,
                    "parameter_derivations": [d.as_record() for d in PARAMETER_DERIVATIONS],
                    "duration_relationships": {name: {"variable": "exposure_time_s",
                        "routes": [{"regime": route.regime,
                                    "bound_inputs": list(conditional_inputs(name, regime=route.regime)),
                                    "conditions": sorted(metric_conditions(name, regime=route.regime))}
                                   for route in metric_routes(name)]}
                        for name in CONDITIONAL_INPUTS},
                    "quantities": {name: metric_catalog_record(name) for name in METRICS},
                    "interpretation": "Executable repository kernels, not retrieved evidence or independent validation. "
                        "Calculations can explore recorded guesses; evidence support affects credit and "
                        "conclusions, not execution. Calculated behavior is not empirical evidence. Missing source equations "
                        "do not imply a missing kernel; investigate fidelity when consequential. "
                        "An existing kernel may still have no applicable route for a selected case. Parameter constraints "
                        "are enforced by execution, not evidence-quality gates. Condition prose cannot override them or "
                        "introduce a new kernel. Unsupported hypotheses remain usable within the declared model domain. "
                        "This catalog grants no child permission to call the root's tools.",
                },
                "parent_information_contract": self.parent_contract.as_record() if self.parent_contract else None}

    def communication_context(self):
        return {"findings": list(dict.fromkeys([*self.decision_summary["findings"],
                    *(f for f in self.ledger.findings if f not in self.communicated["findings"])])),
                "uncertainties": list(dict.fromkeys([*self.decision_summary["uncertainties"],
                    *(v for v in self.ledger.issues if v not in self.communicated["issues"])])),
                "failures": self.decision_summary["failures"],
                "unprocessed_diagnostics": condensed_diagnostics(decision_diagnostics(
                    d for d in self.ledger.diagnostics if identity(d) not in self.communicated["diagnostics"]))}

    def failure_result(self, exc, stage):
        if isinstance(exc, BudgetExceeded):
            self.failure = str(exc)
        issue = f"{stage} failed: {type(exc).__name__}: {exc}"
        return ResearchResult(issues=(issue,), evaluated=False, diagnostics=({
            "stage": stage, **self.run.model_diagnostic(exc),
            "requested_fields": list(self.focus),
            "question": self.parent_contract.decision if self.parent_contract else str(self.goal.objective) if self.goal else "",
            "proposal": diagnostic_value(self.last_proposal),
            **({"extraction_state": exc.extraction_state,
                "unreviewed_candidates": exc.unreviewed_candidates}
               if hasattr(exc, "extraction_state") else {})},))

    def leaf(self, function, label):
        def execute(_):
            try:
                return function()
            except (BudgetExceeded, ProviderError, ValueError, TypeError, KeyError,
                    ZeroDivisionError, OverflowError, OSError) as exc:
                return self.failure_result(exc, label)
        return Leaf(None, execute, lambda _, result: self.project(result), label)

    def next(self, view):
        if self.run.provider_unavailable is not None:
            self.failure = "provider_usage_limit_not_scientific_convergence"
            if self.failure not in self.ledger.issues:
                self.ledger.issues.append(self.failure)
            return SourceEnd("source_failed")
        if self.failure:
            return SourceEnd("source_failed")
        if (self.run.total_units >= self.run.limits.max_total_units
                or self.run.model_calls >= self.run.limits.max_model_calls):
            self.failure = "operational_budget_exhausted_not_scientific_convergence"
            self.ledger.issues.append(self.failure)
            return SourceEnd("source_failed")
        try:
            self.last_proposal = None
            return self.propose(view)
        except (BudgetExceeded, ProviderError, ValueError, TypeError, KeyError, OSError) as exc:
            result = self.failure_result(exc, "proposal")
            return self.leaf(lambda: result, f"proposal_failure:{view.units_consumed}")

    def inputs(self, view, **kwargs):
        communication = self.communication_context()
        global_status = self.run.global_goal.preview(self.ledger.result())
        return view.model_inputs({
            "objective": str(view.goal.objective), "context": self.context(),
            "global_scientific_goal": {
                "scores": global_status["scores"],
                "score_weights": global_status["score_weights"],
                "weighted_score": global_status["weighted_score"],
                "target_routes": {name: row["best_route"] for name, row in global_status["target_routes"].items()},
                "target_assumptions": global_status["target_assumptions"],
                "recorded_target_inputs": global_status["recorded_target_inputs"],
                "independent_target_values": global_status["independent_target_values"],
                "target_inputs": global_status["target_inputs"],
                "source_target_learning": global_status["source_target_learning"],
                "calibration": global_status["calibration"],
                "computed_outputs": global_status["computed_outputs"],
                "requested_outputs": global_status["requested_outputs"],
                "meaning": "Shared admitted Goal projection. Recorded target values include conditional hypotheses before independent review; target_assumptions counts supported or provisional reviews. Route counts use reviewed inputs and conditions, not completed calculations. The numerical controller credits only new progress above inherited state."},
            "own_findings": [f for f in self.ledger.findings if f not in self.communicated["findings"]],
            "own_unresolved": communication["uncertainties"],
            "failure_implications": communication["failures"],
            "attempt_diagnostics": communication["unprocessed_diagnostics"],
            "parameter_progress": [{"field": row["field"], "points": row["points"],
                                    "alternative_values": len(row["alternatives"])}
                                   for row in self.information_assessment if "field" in row],
            "source_event_type_progress": [row for row in self.information_assessment if "type_id" in row],
            "numeric_yield": {"history": list(view.controller_state.history), "reason": view.controller_state.reason,
                "score_meaning": getattr(self, "credit_meaning_override", None) or ("Accumulated evidence-linked parameter learning and computed-output progress across scoped scenarios, with fixed requirement-group weights; "
                    "not a completion fraction. New empty scenarios earn zero and do not dilute prior progress. "
                    "A current numerical consequence earns a small progress floor even with zero evidence support; "
                    "outbreak inversion and its use in target outputs have distinct, deduplicated contributions; "
                    "repetition earns no gain. Genuine contrary evidence can advance learning while current "
                    "support or calculation validity falls; an identified evidence-record error retracts its credit. "
                    "Evidence strength and report coverage are separate." if self.uses_scientific_credit() else
                    "One point per filled calculation input within the assigned parameter's fixed dependencies, "
                    "plus 0.1 for distinct corroboration or independently reviewed refinement/correction. "
                    "Previously justified learning survives genuine contradiction, but invalid evidence does not. "
                    "Alternative values or events do not "
                    "create new scored elements. Inherited evidence is the initial baseline, not new gain. "
                    "Queries, objectives and source breadth cannot change the scoring criteria. "
                    "Points are not confidence or a judgment that a question is partially answered.")},
            **kwargs,
        }, reports=view.child_reports)
