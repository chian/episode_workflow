"""The approved scientific tree, composed through one generic method_loop."""

from dataclasses import replace

from ...method_loop import Context, EpisodeGoal
from ...task_executors._http import ProviderError
from ...task_executors.scenario_metrics.catalog import METRICS, required_inputs
from ...task_executors.scenario_metrics.evaluate import CONDITIONS, DEFAULT_METRICS, UNITS, metric_conditions
from .acquisition import StrategySource
from .admission import extract_and_admit
from .assumptions import RUBRIC, assess_assumption, assumption_candidate, candidate_response_schema, frame_scenario, text
from .engine import BudgetExceeded, CONSISTENCY, ResearchLimits, ResearchProviders, ResearchRun, ResearchSource, selected_choice, child_model_allowance
from .modeling import DERIVATIONS, review_model, select_facts
from .records import Ledger, ResearchResult, identity
from .report import ResearchReport, scientific_progress
from .tools import TOOLS, execute_tool, tool_options


OBJECTIVE = (
    "Derive evidence-supported conditional indoor transmission safety estimates in the sense of "
    "Bazant and Bush for the requested scenarios. Justify the physical and infectiousness assumptions; "
    "calculate risk, duration, occupancy, clean-air requirements and applicable distance scales. "
    "Resolve consequential uncertainty and disagreement. Separate calibration consistency from "
    "independent validation, and critical distance from risk-threshold separation."
)


def admit_scopes(run, proposal, inherited, context):
    ledger = Ledger(inherited)
    scenarios = proposal.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("Scenario proposals must be a list of named descriptions, not numeric dictionaries")
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("Scenario descriptions must be objects")
        framed = frame_scenario(run.agent, scenario, ledger, context)
        if not framed.scenarios:
            raise ValueError(f"Scenario {scenario.get('subject')!r} was not admitted: "
                             + "; ".join(framed.findings))
        ledger.merge(framed)
    return ledger


class GuidelineSource(ResearchSource):
    def __init__(self, run):
        super().__init__(run)
        self.request_read = False
        self.request_evidence = ResearchResult()

    def proposal_schema(self):
        prose = {"type": "string", "minLength": 1}
        def strings(description, choices=None, minimum=0):
            item = prose if choices is None else ({"type": "string", "enum": list(choices)} if choices else False)
            return {"type": "array", "minItems": minimum, "uniqueItems": True,
                    "items": item, "description": description}
        return {"type": "object", "additionalProperties": False, "required": ["action", "objective"],
            "properties": {
                "action": {"type": "string", "enum": ["investigate", *TOOLS]},
                "objective": {**prose, "description": "Scientific information need or purpose of the calculation"},
                "child_model_calls": self.child_budget_schema(),
                "focus": strings("Canonical information needs; requested outputs expand to their input dependencies",
                                 sorted(set(UNITS) | set(CONDITIONS) | set(METRICS)), minimum=1),
                "subjects": strings("Existing or newly proposed scenario names whose uncertainty the investigation should resolve"),
                "scenarios": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "required": ["subject", "description", "basis", "role"], "properties": {
                        "subject": prose, "description": {**prose, "description": "A case or conditional experiment, not a calculation topic or numeric parameter records"},
                        "basis": {**prose, "description": "Alignment with the original request"},
                        "role": {"type": "string", "enum": ["target", "calibration", "validation"]}}}},
                "subject": {**prose, "description": "Reviewed scenario for the selected tool"},
                "facts": strings("Select existing admitted fact keys, one value per field", self.ledger.options(), minimum=1),
                "conditions": {"type": "object", "additionalProperties": False,
                    "properties": {name: {**prose, "description": "Exact current assessed statement"} for name in CONDITIONS}},
                "basis": {**prose, "description": "Named parameterization or comparison rationale"},
                "parameterization": {**prose, "description": "Stable model-alternative name, reused across tools sharing assumptions"},
                "metrics": strings("Output names belonging to the selected tool", sorted(set(METRICS) | {"removal_rate_s"})),
                "operator": {"type": "string", "enum": list(DERIVATIONS)},
                "prediction": {**prose, "description": "Existing calculation option for comparison"},
                "observation": {**prose, "description": "Existing observed fact option for comparison"},
                "metric": {"type": "string", "enum": sorted(METRICS)},
            }, "allOf": [
                {"if": {"properties": {"action": {"enum": [name for name in TOOLS if name != "compare_predictions_with_observations"]}}},
                 "then": {"required": ["subject", "facts", "basis"]}},
                {"if": {"properties": {"action": {"const": "calibrate_infectiousness"}}},
                 "then": {"required": ["operator"]}},
                {"if": {"properties": {"action": {"const": "compare_predictions_with_observations"}}},
                 "then": {"required": ["prediction", "observation", "metric", "basis"]}},
            ]}

    def propose(self, view):
        proposal = self.run.agent(self.inputs(view, operation="propose_guideline_action",
            allowed_actions=["investigate", *TOOLS], tools=TOOLS,
            metric_catalog={k: m.as_record() for k, m in METRICS.items()},
            canonical_fields=UNITS, model_conditions=CONDITIONS, derivations=DERIVATIONS,
            calculations=tool_options(self.ledger),
            scientific_progress=scientific_progress(self.ledger.result(), self.run.metrics),
            instruction=(
                "Choose one useful action toward the original request, informed by prior results. "
                "This run performs the scientific investigation using the existing workflow and "
                "calculation kernels; an implementation plan or input glossary is not its result. "
                "No fixed task or case sequence, no stop/report/assessment action. Propose scenario "
                "descriptions when needed; numeric parameters must be acquired or justified in investigate. "
                "The scenarios list is only for new definitions. Reference existing scenarios by their "
                "subject names; do not redeclare or paraphrase their definitions. A materially different "
                "scope requires a distinct subject and fresh justification. "
                "Investigate unresolved assumptions, conflicting evidence, or prediction discrepancies. "
                "Calculations select existing fact options and assessed condition statements; never invent "
                "parameter values. Recalculate when assumptions change. "
                "A target scenario identifies the case or conditional experiment receiving estimates. "
                "A model extension or unresolved equation is an investigation focus for a case, not a "
                "separate target requiring its own complete report. When the request leaves cases open, "
                "explicitly scoped study cases may instantiate that open scope; do not substitute them "
                "for specified cases or claim they establish results for every possible case. "
                "Distinguish requester constraints from unresolved scientific assumptions and named "
                "conditional study choices. An unspecified input is not automatically something only "
                "the requester can supply: the investigation branch may propose and justify bounded "
                "assumptions where appropriate. Such choices are neither universal defaults nor facts "
                "about an unspecified real room. Preserve all requested outputs and case constraints. "
                "General applicability does not mean one universal set of parameter values. Named "
                "conditional parameterizations can instantiate a target scope, with every numerical "
                "choice justified and distinguished from requester givens and source observations. "
                "scientific_progress reports the same current output coverage used at closure. "
                "The registered equations are already executable kernels; verifying their scientific "
                "basis may resolve uncertainty, but transcribing them is not itself a prerequisite "
                "for tool availability or a numerical safety conclusion. "
                "The requested output quantities are model outputs, not facts to search for verbatim. "
                "Return an instance of the JSON Schema; omit fields not used by the selected action."
            ),
            response_contract=self.proposal_schema()))
        self.last_proposal = proposal
        action = selected_choice(proposal.get("action"), ["investigate", *TOOLS], "action")
        objective = text(proposal.get("objective"), "objective")
        if action == "investigate":
            child_model_allowance(proposal)
        staged = admit_scopes(self.run, proposal, self.ledger.result(), self.context())
        context = {**self.context(), "defined_scenarios": dict(staged.scenarios)}
        if not self.request_read:
            self.request_evidence = extract_and_admit(self.run.agent, text=self.run.research_request, source="request",
                focus=self.focus, objective=OBJECTIVE, context=context,
                question="Admit only explicit requester-defined constraints. Questions asking for unknown scientific quantities are not evidence of their answers.")
            self.request_read = True
        staged.merge(self.request_evidence)
        if action == "investigate":
            focus = proposal.get("focus", [f for f in self.focus if f in UNITS or f in CONDITIONS])
            allowed = set(UNITS) | set(CONDITIONS) | set(METRICS)
            if not isinstance(focus, list) or not focus or any(not isinstance(f, str) or f not in allowed for f in focus):
                invalid = [f for f in focus if not isinstance(f, str) or f not in allowed] if isinstance(focus, list) and focus else focus
                raise ValueError(f"Investigation focus must be a nonempty list of canonical field keys; invalid selection: {invalid!r}. "
                                 "Use the exact names enumerated in response_contract.properties.focus.items.enum.")
            focus = tuple(dict.fromkeys(focus))
            fields = set()
            for name in focus:
                if name in UNITS or name in CONDITIONS:
                    fields.add(name)
                else:
                    fields.update(required_inputs((name,)))
                    fields.update(metric_conditions(name))
            focus = tuple(sorted(fields))
            source = InvestigationSource(self.run, staged.result())
            subjects = proposal.get("subjects", list(staged.scenarios))
            if not isinstance(subjects, list) or any(s not in staged.scenarios for s in subjects):
                raise ValueError("Investigation subjects must be reviewed scenarios")
            source.credit_subjects = tuple(subjects) or None
            return self.edge(self.run.child(view, source, "investigate", objective, focus,
                proposal=proposal, contract=self.contract(
                    f"Decide which assumptions/model choices or calculations to revisit: {objective}", focus,
                    subjects=subjects, meaning="Evidence-linked assumption resolution for the requested subjects: "
                    "supported or provisional parameter values and conditions, refutations, uncertainty, and missing information. "
                    "A dependency name or source glossary alone does not resolve a target assumption.")))

        def calculate():
            if action == "compare_predictions_with_observations":
                observation = proposal.get("observation")
                if observation not in staged.options():
                    raise ValueError("Comparison requires an admitted observation option")
                facts = (staged.options()[observation],)
            else:
                facts = select_facts(proposal, staged.options())
            model_context = {**context, "calculation_options": tool_options(staged)}
            review = review_model(self.run.agent, proposal, facts, model_context)
            result = execute_tool(proposal, staged, self.run.metrics, review=review)
            staged.merge(result)
            return staged.result(evaluated=result.evaluated)
        return self.leaf(calculate, action)


class InvestigationSource(ResearchSource):
    def __init__(self, run, inherited):
        super().__init__(run, inherited)
        self.candidates = {}
        self.staged = Ledger(inherited)

    def adopt_inherited_candidates(self):
        # Inherited knowledge is not an instruction to reassess every other scope.
        for assumption in self.initial.assumptions:
            if assumption["field"] not in self.focus or (
                    self.requested_subjects and assumption["subject"] not in self.requested_subjects):
                continue
            candidate = {k: assumption[k] for k in ("subject", "field", "value", "unit", "statement", "basis")}
            self.candidates.setdefault(self.candidate_key(candidate), candidate)

    @staticmethod
    def candidate_key(candidate):
        return identity([candidate.get("subject"), candidate.get("field"), candidate.get("value"),
                         candidate.get("statement") if candidate.get("field") in CONDITIONS else None])

    def propose(self, view):
        self.adopt_inherited_candidates()
        self.staged = Ledger(self.ledger.result())
        prose = {"type": "string", "minLength": 1}
        proposal = self.run.agent(self.inputs(view, operation="propose_investigation_strategy",
            candidates=list(self.candidates.values()), canonical_fields=UNITS, model_conditions=CONDITIONS,
            reasonableness_rubric=RUBRIC,
            instruction=(
                "Choose an evidence-acquisition approach for this parent's scientific uncertainty. "
                "Use previous failures to understand what remains unknown. You may propose or revise "
                "named candidate assumptions and alternatives, but cannot mark them supported or assign credit. "
                "Source extraction and assumption inference have different contracts: extracted "
                "numeric facts must be printed in a source, whereas a candidate may be an inferred "
                "conditional value with a named rationale to test against numeric or qualitative "
                "evidence. A formula inventory alone is not a justified target parameterization. "
                "A numeric candidate needs a finite JSON number, not a string or null. If a parameter has "
                "no proposed value yet, keep it in the strategy's information need and omit that candidate; "
                "null is only for nonnumeric model conditions. "
                "Mandatory assessment follows every returned strategy and considers supporting and contrary evidence. "
                "A candidate is a hypothesis, never reported evidence. Define source/calibration scenarios "
                "when needed without injecting parameter records. No stopping or separate assessment action."
                " A scenario is a case or conditional experiment, not an equation or investigation topic."
                " Every candidate subject must match an existing reviewed scenario or a new definition "
                "in this proposal's scenarios list; source-event labels alone do not establish a scope."
                " Reference existing scenarios by subject and omit them from scenarios; do not redeclare "
                "or paraphrase their definitions. Use scenarios only for genuinely new definitions."
                " The parent's information contract and requested subjects are in context. Source or "
                "calibration subjects can supply evidence, but new templates do not substitute for "
                "resolving assumptions for the requested subjects. Explain applicability to those subjects. "
                "Inherited candidates are scoped to the parent's requested fields and subjects; "
                "propose related hypotheses explicitly when needed to resolve this uncertainty. "
                "Choose focus fields appropriate to this evidence approach; they may include intermediate "
                "quantities needed to resolve the parent's uncertainty. This scopes the child's search and "
                "local evidence credit without changing your own scientific goal. "
                "Return an instance of the JSON Schema."
            ), response_contract={"type": "object", "additionalProperties": False,
                "required": ["approach", "objective"], "properties": {
                    "approach": {**prose, "description": "Evidence strategy and its rationale"},
                    "objective": {**prose, "description": "Information this strategy must resolve for the parent"},
                    "child_model_calls": self.child_budget_schema(),
                    "focus": {"type": "array", "minItems": 1, "uniqueItems": True,
                              "items": {"type": "string", "enum": sorted(set(UNITS) | set(CONDITIONS) | set(METRICS))},
                              "description": "Evidence fields needed by this strategy; omitted means inherit the parent focus"},
                    "candidates": {"type": "array", "items": candidate_response_schema()},
                    "scenarios": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                        "required": ["subject", "description", "basis", "role"], "properties": {
                            "subject": prose, "description": prose, "basis": prose,
                            "role": {"type": "string", "enum": ["target", "calibration", "validation"]}}}},
                },
            }))
        self.last_proposal = proposal
        approach, objective = text(proposal.get("approach"), "approach"), text(proposal.get("objective"), "objective")
        child_model_allowance(proposal)
        focus = proposal.get("focus", list(self.focus))
        allowed = set(UNITS) | set(CONDITIONS) | set(METRICS)
        if not isinstance(focus, list) or not focus or any(not isinstance(f, str) or f not in allowed for f in focus):
            raise ValueError("A strategy focus needs a nonempty list of declared evidence fields")
        focus = tuple(dict.fromkeys(focus))
        self.staged = admit_scopes(self.run, proposal, self.ledger.result(), self.context())
        candidates = proposal.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("Candidate assumptions must be a list")
        validated = [assumption_candidate(candidate, self.staged) for candidate in candidates]
        self.candidates.update((self.candidate_key(candidate), candidate) for candidate in validated)
        source = StrategySource(self.run, self.staged.result(), approach=approach)
        return self.edge(self.run.child(view, source, "strategy", objective, focus,
            proposal=proposal, contract=self.contract(
                f"Judge whether evidence supports, bounds or contradicts candidate assumptions: {objective}", focus)))

    def assess(self, result):
        """Always run before this episode's credit projection, never as an action."""
        self.adopt_inherited_candidates()
        working = Ledger(self.staged.result())
        working.merge(result)
        failed = False
        assessed = 0
        for key, candidate in self.candidates.items():
            field = candidate["field"]
            options = working.evidence_options()
            # Cross-field physical evidence can support or contradict a hypothesis.
            # The reviewer, not a field-name filter or proposer, judges relevance.
            relevant = options
            basis_version = identity([candidate, list(relevant.values()), working.scenarios.get(candidate["subject"])])
            current = working.assumptions.get(key)
            if current and current.get("assessment_basis_version") == basis_version:
                continue
            try:
                assessment = assess_assumption(self.run.agent, {**candidate, "evidence": list(relevant)}, working,
                    {**self.context(), "defined_scenarios": dict(working.scenarios)})
                assessment.assumptions[0]["assessment_basis_version"] = basis_version
                working.merge(assessment)
                assessed += 1
            except (BudgetExceeded, ProviderError, ValueError, TypeError, KeyError, OSError) as exc:
                failed = True
                failure = self.failure_result(exc, "mandatory_reasonableness_assessment")
                working.merge(replace(failure, diagnostics=tuple({**d,
                    "subject": candidate["subject"], "field": field, "proposal": candidate}
                    for d in failure.diagnostics)))
                if current:
                    withdrawn = {**current, "reasonableness": 0, "resolution_credit": 0,
                                 "assessment_error": str(exc)}
                    withdrawn["version"] = identity(withdrawn)
                    working.merge(ResearchResult(assumptions=(withdrawn,)))
        return working.result(evaluated=assessed > 0 or (result.evaluated and not failed), stop_reason=result.stop_reason)


def run_guideline_research(*, research_request, providers, metrics=DEFAULT_METRICS, limits=None):
    """Only the original prompt enters externally; all knowledge starts empty."""
    if not isinstance(research_request, str) or not research_request.strip():
        raise ValueError("research_request must be a nonempty natural-language prompt")
    metrics = tuple(dict.fromkeys(metrics))
    if not metrics or any(m not in METRICS and m != "removal_rate_s" for m in metrics):
        raise ValueError("Unknown requested metric")
    run = ResearchRun(providers, limits or ResearchLimits(), research_request, metrics)
    conditions = set().union(*(metric_conditions(name) for name in metrics))
    focus = tuple(sorted(set(required_inputs(metrics)) | set(metrics) | conditions | {CONSISTENCY}))
    goal = EpisodeGoal.root(objective=f"{OBJECTIVE}\n\nResearch request: {research_request}",
        result_contract={"metrics": list(metrics), "source_grounded_inputs": True}, task_context=run.context)
    source = GuidelineSource(run)
    episode = run.episode("evaluate_safety_guideline", source, goal=goal, focus=focus)
    record = episode.run(Context(tree=run.tree))
    return record, ResearchReport.from_result(source.build_result(record), record, run)
