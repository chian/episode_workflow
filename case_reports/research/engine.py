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
from ...task_executors.scenario_metrics.catalog import METRICS, PAPER
from .records import (Ledger, ResearchMessage, ResearchResult, diagnostic_value, condensed_diagnostics,
                      cited_assessment_evidence, evidence_summary, evidence_inventory)


TREE = {
    "evaluate_safety_guideline": ("investigate",),
    "investigate": ("strategy",),
    "strategy": ("search",),
    "search": ("page",),
    "page": ("source_table", "report", "lexical_probe"),
    "source_table": (), "report": (), "lexical_probe": (),
}
SCIENTIFIC = {"evaluate_safety_guideline", "investigate"}
CONSISTENCY = "evidence_consistency"


@dataclass(frozen=True)
class ResearchLimits:
    max_model_calls: int = 240
    max_units_per_episode: int = 24
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


class BudgetExceeded(RuntimeError):
    pass


def selected_choice(value, options, field):
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"{field} must be one exact declared key {list(options)!r}; received {value!r}")
    return value


def child_model_allowance(proposal):
    if "child_model_calls" not in proposal:
        return None
    value = proposal["child_model_calls"]
    if type(value) is not int or value <= 0:
        raise ValueError("child_model_calls must be a positive integer operational allowance")
    return value


class ResearchRun:
    def __init__(self, providers, limits, research_request, metrics):
        self.providers, self.limits = providers, limits
        self.research_request, self.metrics = research_request, metrics
        self.documents = {}
        self.model_attempts = []
        self.model_calls = self.total_units = self.sequence = 0
        self.diagnostic_sequence = 0
        self.controller_specs = {}
        self.sources = {}
        root = Path(__file__).resolve().parents[2]
        paths = list(root.glob("*.py"))
        for folder in ("case_reports", "credit_assignment", "method_loop", "task_executors"):
            paths.extend((root / folder).rglob("*.py"))
        self.implementation = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted(paths)}
        self.context = {"research_request": research_request, "reference_model": PAPER,
                        "requested_metrics": list(metrics)}
        units = {
            "evaluate_safety_guideline": "a selected calculation tool or completed investigation",
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
        self.tree = EpisodeTree(self.grains["evaluate_safety_guideline"], {
            self.grains[parent]: tuple(self.grains[name] for name in children)
            for parent, children in TREE.items() if children
        })

    def controller(self, path):
        focus, initial, scientific = self.controller_specs[path[-1][1]]
        groups = tuple(g for g in (tuple(f for f in focus if f not in METRICS and f != CONSISTENCY),
                                   tuple(f for f in focus if f in METRICS),
                                   tuple(f for f in focus if f == CONSISTENCY)) if g) if scientific else None
        return ResearchController(focus, window=self.limits.yield_window, initial=initial,
                                  capacity=1 if scientific else 2, groups=groups)

    def agent(self, request):
        if self.model_calls >= self.limits.max_model_calls:
            raise BudgetExceeded("model_call_budget_exhausted")
        deadline = request.get("context", {}).get("operational_resources", {}).get("model_call_deadline", self.limits.max_model_calls)
        if self.model_calls >= deadline:
            raise BudgetExceeded("episode_model_call_budget_exhausted_not_scientific_convergence")
        self.model_calls += 1
        attempt = {"call": self.model_calls, "operation": request.get("operation", ""),
                   "request": diagnostic_value(request)}
        self.model_attempts.append(attempt)
        try:
            result = self.providers.agent(request)
            attempt["response"] = diagnostic_value(result)
            if not isinstance(result, Mapping):
                raise ValueError("Research agent must return a JSON object")
        except (ProviderError, OSError, ValueError) as exc:
            diagnostic = {**self.model_diagnostic(exc), "model_call": self.model_calls,
                          "operation": attempt["operation"]}
            exc.model_call_diagnostic = diagnostic
            attempt.update(status="response_failed", diagnostic=diagnostic)
            if isinstance(exc, ModelOutputError):
                exc.diagnostic.update(model_call=self.model_calls, operation=attempt["operation"])
                attempt["raw_response"] = diagnostic_value(exc.raw_response)
            raise
        attempt["status"] = "json_object_received_not_yet_admitted"
        return result

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

    def episode(self, grain, source, *, goal, focus, contract=None, proposal=None, model_call_deadline=None):
        self.sequence += 1
        key = f"{grain}:{self.sequence}"
        source.focus, source.scientific = tuple(focus), grain in SCIENTIFIC
        source.goal = goal
        source.model_calls_start = self.model_calls
        source.model_call_deadline = self.limits.max_model_calls if model_call_deadline is None else model_call_deadline
        self.sources[goal.goal_id] = source
        source.parent_contract = contract
        source.requested_subjects = tuple(contract.measurements.get("subjects", ())) if contract else ()
        self.controller_specs[key] = (source.focus, source.credit(source.ledger.result()), source.scientific)
        return Episode(self.grains[grain], key, source, EpisodeRequest(
            goal, ResearchMessage(str(goal.objective), source.focus, source.requested_subjects,
                                  diagnostic_value(proposal or {})), contract),
            source.build_result, on_unit=source.after_verdict)

    def child(self, parent, source, grain, objective, focus, *, contract, proposal):
        owner = self.sources[parent.goal.goal_id]
        allowance = child_model_allowance(proposal)
        deadline = owner.model_call_deadline
        if allowance is not None:
            deadline = min(deadline, self.model_calls + allowance)
        allocation = {"model_call_allowance": max(0, deadline - self.model_calls),
                      "requested_model_calls": allowance,
                      "interpretation": "Operational ceiling for the entire child subtree, not scientific convergence"}
        goal = EpisodeGoal.child(parent.goal, objective=objective,
                                 result_contract={"fields": list(focus), "information": contract.as_record(),
                                                  "operational_limits": allocation})
        return self.episode(grain, source, goal=goal, focus=focus,
                            contract=contract, proposal=proposal, model_call_deadline=deadline)


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
        self.credit_subjects = None
        self.pending = None
        self.failure = ""
        self.evaluated_units = 0
        self.last_proposal = None
        self.model_calls_start = run.model_calls
        self.model_calls_end = None
        self.model_call_deadline = run.limits.max_model_calls

    def resource_usage(self):
        end = self.run.model_calls if self.model_calls_end is None else self.model_calls_end
        return {"model_calls_used": end - self.model_calls_start,
                "model_calls_remaining": max(0, self.model_call_deadline - end),
                "model_call_deadline": self.model_call_deadline,
                "run_model_calls_used": self.run.model_calls,
                "run_model_calls_remaining": max(0, self.run.limits.max_model_calls - self.run.model_calls)}

    def child_budget_schema(self):
        return {"type": "integer", "minimum": 1,
                "description": "Optional model-call ceiling for the next child and all its descendants. "
                "Omitting it inherits the remaining parent allowance. Enclosing limits still apply. "
                "Calls are not child iterations: nested proposals, extraction, independent review "
                "and return synthesis all consume calls. A reading unit returning candidates alone "
                "requires both an extraction call and an evidence-review call. "
                "Consider resources needed for your own mandatory assessment, synthesis and later decisions. "
                "Each new or changed candidate in investigate needs a reasonableness-review call after the child returns. "
                "This limits work; it does not declare scientific convergence."}

    def contract(self, decision, focus, *, subjects=None, meaning=None):
        """The invoking binding supplies a decision and its required measurements."""
        return ReportContract(decision=decision,
            measurements={"needed_fields": list(focus),
                          "subjects": list(self.requested_subjects if subjects is None else subjects),
                          "meaning": meaning or "Relevant, nonduplicated admitted evidence; the parent assesses its scientific implications"},
            information={
                "findings": "Condensed implications for this parent's stated decision, without new evidence.",
                "changes": "Index of changed subjects, fields and sources, plus changed assumption judgments; implications belong in findings. Full evidence is retained in the shared scientific state, not repeated here.",
                "unresolved": "Unanswered questions and limitations relevant to the requested fields.",
                "diagnostics": "What failed or was rejected, and why; not instructions for a recovery sequence.",
                "completion": "Numerical saturation, finite exhaustion, or operational failure; never conflate them.",
            })

    def build_result(self, record):
        if self.model_calls_end is None:
            self.model_calls_end = self.run.model_calls
        reason = self.failure or (record.controller_state.reason if record.ended_by == "yield_stop" else record.ended_by)
        evaluated = bool(self.evaluated_units) or (
            record.units_consumed == 0 and not self.failure and record.ended_by == "exhausted")
        return self.ledger.result(evaluated=evaluated, stop_reason=reason)

    def after_verdict(self, unit, contribution, view):
        self.run.total_units += 1
        if self.pending is not None:
            new_issues = [v for v in self.pending.issues if v not in self.ledger.issues]
            self.ledger.merge(self.pending)
            self.evaluated_units += int(self.pending.evaluated)
            if self.run.providers.event:
                self.run.providers.event({"unit": unit.label, "evaluated": self.pending.evaluated,
                    "admitted_facts": len(self.pending.facts), "estimates": len(self.pending.estimates),
                    "issues": new_issues, "gain": view.controller_step.gain,
                    "stop": view.controller_step.stop, "model_calls": self.run.model_calls,
                    "model_call_limit": self.run.limits.max_model_calls,
                    "episode_calls_remaining": self.resource_usage()["model_calls_remaining"]})
            self.pending = None

    def assess(self, result):
        """Binding-owned mandatory assessment before numerical projection."""
        return result

    def project(self, result):
        self.pending = self.assess(result)
        self.pending = replace(self.pending, diagnostics=tuple(
            self.run.identify_diagnostic(d) for d in self.pending.diagnostics))
        accumulated = Ledger(self.ledger.result())
        accumulated.merge(self.pending)
        return self.credit(accumulated.result(evaluated=self.pending.evaluated))

    def credit(self, result):
        return result.credit(self.focus, scientific=self.scientific, subjects=self.credit_subjects)

    def receive(self, result, completion, request):
        if not isinstance(result, ResearchResult):
            raise TypeError("Unexpected scientific child result")
        return self.project(result)

    def edge(self, child):
        return ChildEpisodeUnit(child, self.receive, self.synthesize)

    def synthesize(self, result, completion, request):
        # Compression is communication, not a second evidence-admission path.
        changes = {
            "evidence": [{k: v for k, v in f.semantic_record().items() if k not in {"quote", "context"}}
                         for f in result.facts if f.key not in self.ledger.facts],
            "qualitative_evidence": [{k: v for k, v in e.items() if k not in {"quote", "context"}}
                                     for e in result.evidence if e not in self.ledger.evidence.values()],
            "assumptions": [{"subject": a["subject"], "field": a["field"], "value": a["value"],
                             "statement": a["statement"], "verdict": a["review"]["verdict"],
                             "reasonableness": a["reasonableness"], "why": a["review"]["explanation"],
                             "limitations": a["review"]["limitations"],
                             "sources": sorted({e["source"] for e in cited_assessment_evidence(a).values()})}
                            for a in result.assumptions if self.ledger.assumptions.get(a["key"]) != a],
        }
        report = {"findings": [f for f in result.findings if f not in self.ledger.findings], "changes": changes,
                  "unresolved": [v for v in result.issues if v not in self.ledger.issues],
                  "diagnostics": condensed_diagnostics(d for d in result.diagnostics if d not in self.ledger.diagnostics),
                  "completion": {**completion.as_record(), "reason": result.stop_reason,
                                 "resources": self.run.sources[request.goal.goal_id].resource_usage()}}
        try:
            response = self.run.agent({"operation": "synthesize_research_findings",
                "context": self.context(),
                "parent_contract": request.report_contract.as_record(),
                "child_objective": request.goal.as_record()["objective"], "admitted_result": report,
                "instruction": "Condense decision-relevant findings and failure implications. Prefer plain-text mathematical notation in this synthesis; JSON-escape any retained backslashes. Do not invent evidence, numbers, diagnoses, instructions, or a stopping decision. This synthesis cannot earn credit or alter admitted state.",
                "response_contract": {"type": "object", "additionalProperties": False,
                    "required": ["findings", "uncertainties"], "properties": {
                        "findings": {"type": "array", "items": {"type": "string"},
                                     "description": "Concise evidence-grounded implications for the parent"},
                        "uncertainties": {"type": "array", "items": {"type": "string"},
                                          "description": "Remaining uncertainty relevant to the parent contract"}}}})
            for name in ("findings", "uncertainties"):
                if not isinstance(response.get(name), list) or any(not isinstance(v, str) for v in response[name]):
                    raise ValueError("Synthesis requires text lists")
            report["findings"] = response["findings"]
            report["unresolved"] = list(dict.fromkeys([*report["unresolved"], *response["uncertainties"]]))
        except (BudgetExceeded, ProviderError, ValueError, OSError) as exc:
            issue = f"Synthesis unavailable ({type(exc).__name__}); admitted findings retained"
            diagnostic = self.run.identify_diagnostic({"stage": "synthesis", **self.run.model_diagnostic(exc)})
            report["unresolved"].append(issue)
            report["diagnostics"].extend(condensed_diagnostics([diagnostic]))
            if self.pending is not None:
                self.pending = replace(self.pending, issues=(*self.pending.issues, issue),
                                       diagnostics=(*self.pending.diagnostics, diagnostic))
        return {**report, "changes": {
            "evidence_index": evidence_inventory(changes["evidence"], changes["qualitative_evidence"]),
            "assumptions": changes["assumptions"],
            "interpretation": "Change index only. The parent retains all admitted records separately; counts are not scientific credit."}}

    def context(self):
        return {**self.run.context, "defined_scenarios": dict(self.ledger.scenarios),
                "requested_subjects": list(self.requested_subjects),
                "operational_resources": self.resource_usage(),
                "model_call_costs": {
                    "proposal": "One call per agent-selected action/query/source/reading scope/table query.",
                    "new_scenario": "One scope-review call for each new scenario definition.",
                    "reading_unit": "One extraction call plus one mandatory evidence-review call when candidates are returned.",
                    "child_return": "One synthesis call per completed child edge, charged to the invoking parent.",
                    "investigation_assessment": "One reasonableness-review call per new or changed candidate/evidence basis, after strategy return.",
                    "calculation": "One model-admission review call after tool selection; the kernel itself uses no model calls.",
                    "interpretation": "These costs compound through the ownership tree. A subtree allowance is not a number of searches or reading units. No call count guarantees useful evidence.",
                },
                "parent_information_contract": self.parent_contract.as_record() if self.parent_contract else None}

    def failure_result(self, exc, stage):
        if isinstance(exc, BudgetExceeded):
            self.failure = str(exc)
        issue = f"{stage} failed: {type(exc).__name__}: {exc}"
        return ResearchResult(issues=(issue,), evaluated=False, diagnostics=({
            "stage": stage, **self.run.model_diagnostic(exc),
            "proposal": diagnostic_value(self.last_proposal)},))

    def leaf(self, function, label):
        def execute(_):
            try:
                return function()
            except (BudgetExceeded, ProviderError, ValueError, TypeError, KeyError,
                    ZeroDivisionError, OverflowError, OSError) as exc:
                return self.failure_result(exc, label)
        return Leaf(None, execute, lambda _, result: self.project(result), label)

    def next(self, view):
        if self.failure:
            return SourceEnd("source_failed")
        if self.run.model_calls >= self.model_call_deadline < self.run.limits.max_model_calls:
            self.failure = "episode_model_call_budget_exhausted_not_scientific_convergence"
            self.ledger.issues.append(self.failure)
            return SourceEnd("source_failed")
        if (view.units_consumed >= self.run.limits.max_units_per_episode
                or self.run.total_units >= self.run.limits.max_total_units
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
        knowledge = ({"evidence_options": {k: evidence_summary(e) for k, e in self.ledger.evidence_options().items()}}
                     if self.scientific else {"evidence_inventory": evidence_inventory(
                         [f.semantic_record() for f in self.ledger.facts.values()], self.ledger.evidence.values())})
        return view.model_inputs({
            "objective": view.goal.as_record()["objective"], "context": self.context(),
            "focus": list(self.focus),
            "admitted_facts": {k: evidence_summary(f.semantic_record()) for k, f in self.ledger.options().items()},
            **knowledge,
            "evidence_view": "Acquisition choices receive a source/field inventory; scientific proposals receive evidence summaries. Independent evidence and assumption reviews retain the full original records.",
            "assumption_options": self.ledger.assumption_options(),
            "own_findings": self.ledger.findings, "own_unresolved": self.ledger.issues,
            "attempt_diagnostics": condensed_diagnostics(self.ledger.diagnostics),
            "numeric_yield": {"history": list(view.controller_state.history), "reason": view.controller_state.reason},
            **kwargs,
        }, reports=view.child_reports)
