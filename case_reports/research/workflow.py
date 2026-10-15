"""The approved scientific tree, composed through one generic method_loop."""

from dataclasses import replace

from ...method_loop import Context, EpisodeGoal
from ...task_executors._http import ProviderError
from ...task_executors.scenario_metrics.catalog import METRICS, metric_catalog_record
from ...task_executors.scenario_metrics.dependencies import input_fields
from ...task_executors.scenario_metrics.evaluate import CONDITIONS, DEFAULT_METRICS, UNITS
from .acquisition import StrategySource
from .admission import extract_and_admit
from .assumptions import RUBRIC, assess_assumption, assumption_candidate, candidate_response_schema, frame_scenario, text, unassessed_assumption
from .engine import CONSISTENCY, ResearchLimits, ResearchProviders, ResearchRun, ResearchSource, selected_choice
from .goal_state import GLOBAL_GOAL_PROGRESS
from .modeling import DERIVATIONS, review_model, select_facts
from .records import Ledger, ResearchResult, assumption_model_view, evidence_summary, identity
from .report import ResearchReport, scientific_progress
from .scenarios import initial_scenarios, load_scenarios
from .tools import TOOLS, TOOL_METRICS, bind_reference_inputs, execute_tool, input_options, tool_options
from .verification import CALIBRATION_PROGRESS


OBJECTIVE = (
    "Derive evidence-supported conditional indoor transmission safety estimates in the sense of "
    "Bazant and Bush for the requested scenarios. Justify the physical and infectiousness assumptions; "
    "report allowable room time, risk-based safe distance, and R_in only, with their exposure "
    "conditions and regimes. Intermediate quantities serve these outputs, not additional report goals. "
    "Use one risk model per named parameterization and background regime: fix distance to solve time, "
    "fix time to solve distance, and fix both to evaluate R_in. "
    "Resolve uncertainty through evidence for assumptions, not comparison or matching to published "
    "answers. A jet/background concentration crossover is not the requested safe distance."
)


def admit_scopes(run, proposal, inherited, context):
    ledger = Ledger(inherited)
    scenarios = proposal.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("Scenario proposals must be a list of named descriptions, not numeric dictionaries")
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("Scenario descriptions must be objects")
        if run.fixed_scenarios:
            if (scenario.get("role") != "calibration" or scenario.get("subject") in ledger.scenarios
                    or scenario.get("subject") not in calibration_subjects(ledger)):
                raise ValueError("Target cases are fixed. Only a distinct calibration context identified by admitted source observations may be registered; existing scopes cannot be replaced")
        framed = frame_scenario(run.complete, scenario, ledger, context)
        if not framed.scenarios:
            raise ValueError(f"Scenario {scenario.get('subject')!r} was not admitted: "
                             + "; ".join(framed.findings))
        ledger.merge(framed)
    return ledger


def calibration_subjects(ledger):
    observed = {f.subject for f in ledger.facts.values() if f.kind == "source_observation" and f.source}
    observed.update(e["subject"] for e in ledger.evidence.values()
                    if e.get("kind") == "source_evidence" and e.get("evidence_role") == "observation" and e.get("source"))
    return sorted(observed - ledger.scenarios.keys())


def calculation_leaf(source, proposal, staged, context):
    """One reviewed deterministic-tool path for root and hypothesis owners."""
    action = proposal["action"]

    def calculate():
        calculation_action = bind_reference_inputs(proposal, staged, source.run.metrics)
        if action == "compare_predictions_with_observations":
            observation = proposal.get("observation")
            if observation not in staged.options():
                raise ValueError("Comparison requires an admitted observation option")
            facts = (staged.options()[observation],)
        else:
            facts = select_facts(calculation_action, input_options(staged))
        model_context = {**context, "calculation_options": tool_options(staged)}
        review_failure = None
        try:
            review = review_model(source.run.complete, calculation_action, facts, model_context)
        except (ProviderError, ValueError, TypeError, KeyError, OSError) as exc:
            review_failure = source.failure_result(exc, "model_support_assessment")
            review = {"admit": False, "completed": False, "reason": "Model support assessment did not complete",
                      "limitations": list(review_failure.issues)}
        result = execute_tool(calculation_action, staged, source.run.metrics, review=review)
        if review_failure is not None:
            result = replace(result, issues=(*result.issues, *review_failure.issues),
                             diagnostics=(*result.diagnostics, *review_failure.diagnostics))
        staged.merge(result)
        return staged.result(evaluated=result.evaluated)

    return source.leaf(calculate, action)


class GuidelineSource(ResearchSource):
    def __init__(self, run):
        super().__init__(run, run.initial or ())
        self.request_read = False
        self.request_evidence = ResearchResult()
        self.output_fields = run.metrics

    def proposal_schema(self, *, ledger=None, actions=None, focus=None):
        ledger = self.ledger if ledger is None else ledger
        actions = ["investigate", *self.run.tools] if actions is None else actions
        focus = self.focus if focus is None else focus
        prose = {"type": "string", "minLength": 1}
        options = input_options(ledger)
        def strings(description, choices=None, minimum=0):
            item = prose if choices is None else ({"type": "string", "enum": list(choices)} if choices else False)
            return {"type": "array", "minItems": minimum, "uniqueItems": True,
                    "items": item, "description": description}
        schema = {"type": "object", "additionalProperties": False, "required": ["action"],
            "properties": {
                "action": {"type": "string", "enum": actions},
                "objective": {**prose, "description": "Required information need for an investigation child; optional for a calculation whose rationale belongs in basis"},
                "parameter": {"type": "string", "enum": sorted(set(focus) & (UNITS.keys() | CONDITIONS.keys())),
                    "description": "For investigation: the calculation parameter or model condition this branch serves. Its scoring scope is fixed by executable dependencies, not by search wording."},
                "deliverable": {"type": "string", "enum": ["source_findings", "assumption_hypotheses"],
                    "description": "For investigation: source_findings requests observations, bounds or applicability evidence; assumption_hypotheses requests recorded, independently assessed parameter or condition hypotheses for the named subjects."},
                "subjects": strings("Existing or newly proposed scenario names whose uncertainty the investigation should resolve"),
                "scenarios": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "required": ["subject", "description", "basis", "role"], "properties": {
                        "subject": prose, "description": {**prose, "description": "A case or conditional experiment, not a calculation topic or numeric parameter records"},
                        "basis": {**prose, "description": "Alignment with the original request"},
                        "role": {"type": "string", "enum": ["target", "calibration", "validation"]}}}},
                "subject": {**prose, "description": "Reviewed scenario for the selected tool"},
                "facts": strings("Select references from calculation_inputs.numeric_options only, one value per field; condition statements belong in conditions, never facts",
                                 options, minimum=1),
                "conditions": {"type": "object", "additionalProperties": False,
                    "properties": {name: {**prose, "description": "Named condition hypothesis, including unassessed conditions; reuse an assessed statement exactly when that is the intended assumption"} for name in CONDITIONS}},
                "basis": {**prose, "description": "Named parameterization or comparison rationale"},
                "parameterization": {**prose, "description": "Stable model-alternative name, reused across tools sharing assumptions"},
                "metrics": strings("Omit to use this tool's requested outputs, or choose only names permitted by its action-specific schema below. Geometry-derived input parameters are emitted automatically, not selected here.",
                                   sorted(set(METRICS) | {"removal_rate_s"})),
                "operator": {"type": "string", "enum": list(DERIVATIONS)},
                "prediction": {**prose, "description": "Existing calculation option for comparison"},
                "observation": {**prose, "description": "Existing observed fact option for comparison"},
                "metric": {"type": "string", "enum": sorted(METRICS)},
            }, "allOf": [
                {"if": {"properties": {"action": {"const": "investigate"}}},
                 "then": {"required": ["objective", "subjects", "deliverable", "parameter"]}},
                {"if": {"properties": {"action": {"enum": [name for name in TOOLS if name != "compare_predictions_with_observations"]}}},
                 "then": {"required": ["subject", "facts", "basis"]}},
                {"if": {"properties": {"action": {"const": "calibrate_infectiousness"}}},
                 "then": {"required": ["operator"]}},
                {"if": {"properties": {"action": {"const": "compare_predictions_with_observations"}}},
                 "then": {"required": ["prediction", "observation", "metric", "basis"]}},
                *({"if": {"properties": {"action": {"const": tool}}},
                   "then": {"required": ["parameterization"], "properties": {"metrics": strings("Output names executable by this selected tool",
                       sorted(choices), minimum=0 if tool == "calculate_geometry_and_removal" else 1)}}}
                  for tool, choices in TOOL_METRICS.items()),
            ]}
        if self.run.fixed_scenarios:
            properties = schema["properties"]
            for name in ("prediction", "observation", "metric"):
                properties.pop(name)
            events = calibration_subjects(ledger)
            scopes = [*ledger.scenarios, *events]
            properties["scenarios"]["description"] = "Only register a distinct calibration event already identified by admitted observations. Never redefine target cases."
            properties["scenarios"]["items"]["properties"]["role"] = {"const": "calibration"}
            properties["scenarios"]["items"]["properties"]["subject"] = {"enum": events} if events else False
            properties["subject"] = {"type": "string", "enum": scopes}
            properties["subjects"] = strings("Existing cases or observed calibration events registered in this proposal",
                                            scopes)
            properties["basis"]["description"] = "Named conditional parameterization and its rationale"
            schema["allOf"] = [row for row in schema["allOf"] if row["if"]["properties"]["action"].get("const")
                               != "compare_predictions_with_observations"]
            schema["allOf"].extend({
                "if": {"required": ["subject"], "properties": {"subject": {"const": subject}},
                       "not": {"required": ["operator"], "properties": {"operator": {"const": "transfer_parameter"}}}},
                "then": {"properties": {
                    "facts": strings("Inputs belonging to this selected case; cross-case transfer must be explicit",
                                     [key for key, fact in options.items() if fact.subject == subject], minimum=1),
                    "conditions": {"properties": {name: {"const": statement}
                        for name, statement in definition.get("fixed_conditions", {}).items()}}}}}
                for subject, definition in ledger.scenarios.items())
        return schema

    def propose(self, view):
        assumptions = self.ledger.assumption_options()
        proposal = self.run.agent(self.inputs(view, operation="propose_guideline_action",
            allowed_actions=["investigate", *self.run.tools], tools=self.run.tools,
            assumption_options={key: value for key, value in assumptions.items() if value["value"] is not None},
            calculation_inputs={
                "numeric_options": {key: {name: value for name, value in fact.semantic_record().items()
                                          if name in {"subject", "field", "value", "unit", "kind"}}
                                    for key, fact in input_options(self.ledger).items()},
                "condition_hypotheses": [value for value in assumptions.values() if value["value"] is None],
                "selection_contract": "facts selects numeric_options references. conditions maps canonical condition fields to their statement text; condition hypotheses are not numeric options.",
            },
            metric_catalog={k: metric_catalog_record(k) for k in METRICS},
            canonical_fields=UNITS, model_conditions=CONDITIONS, derivations=DERIVATIONS,
            calculations=tool_options(self.ledger),
            scientific_progress=scientific_progress(self.ledger.result(), self.run.metrics),
            instruction=(
                "Choose one useful action toward the original request, informed by prior results. "
                "At each root decision, try a requested calculation as soon as selected numeric "
                "facts or recorded hypotheses and physically applicable conditions make it executable. "
                "Prefer a new provisional calculation to another investigation when it would fill a "
                "missing requested output or expose a consequential sensitivity; weak evidence lowers "
                "support, not the value of learning that consequence. If a calculation lacks a specific "
                "physical input, request a narrowly scoped assumption_hypotheses investigation to "
                "propose a qualified value, then reconsider calculation when it returns. Do not spend "
                "another source_findings branch collecting every possible context detail first. "
                "This run performs the scientific investigation using the existing workflow and "
                "calculation kernels; an implementation plan or input glossary is not its result. "
                "No fixed action sequence, no stop/report/assessment action. If context.fixed_scenarios "
                "is true, the caller has selected and defined every TARGET case. Do not discover, propose, "
                "replace or alter target scenarios. Their fixed_parameters and fixed_conditions define scope, "
                "not empirical evidence; use the supplied options without reassessing those givens. "
                "Investigate the remaining assumptions. Read each case's output_contracts. "
                "Name the calculation parameter served by each investigation in parameter. Its "
                "existing executable dependencies determine eligible evidence elements; strategies "
                "cannot add requirements by naming more settings, sources or topics. Search choices "
                "remain yours. Credit measures filled parameters and distinct corroboration, not "
                "completion of a literature survey or a partially answered question. "
                "The caller's target cases were compared before research and equivalent parameter "
                "needs were grouped as independent unknowns. A numeric_option shared from another "
                "case belongs to the selected target's group; select it directly when useful instead "
                "of requesting a duplicate hypothesis for that group. "
                "Give each investigation a specific question and only the context necessary to answer it. "
                "Name only the target subjects involved; use [] for source discovery without a target assignment. "
                "The child contract retains the full caller-defined target set, including fixed inputs "
                "and conditions, while subjects marks this episode's local investigation. This lets "
                "source discovery assess applicability across the requested cases even with subjects=[]. "
                "Do not pass your whole requirement list to a child. Its return is a brief synthesis of "
                "trends, changed understanding and limitations that help you choose the next action. "
                "Specify deliverable=source_findings when you need observed events, bounds or "
                "applicability evidence without a new target hypothesis. Specify assumption_hypotheses "
                "when you need recorded parameter values or condition hypotheses and their independent "
                "reasonableness assessments. Evidence discovery and hypothesis justification have "
                "different completion contracts; neither is an instruction to execute your tools. "
                "An evidence-based outbreak calibration is also required. Acquire observed outbreak counts, "
                "duration and context through investigate's search children. Source observations "
                "retain their actual event subject. Register a separate calibration context in scenarios "
                "using that exact admitted subject and role=calibration; this does not add a target case. "
                "Investigate missing event assumptions, then use calibrate_infectiousness with "
                "cq_from_steady_outbreak or cq_from_transient_outbreak. That tool contains the "
                "calibrate_cq_from_outbreak subtask. Carry its derived Cq through explicit transfer_parameter "
                "and, where justified, cq_activity_rescaling to the target; select the derived facts in "
                "subsequent calculations so calibration lineage is retained. Assess transfer compatibility, "
                "including the runtime disease/variant and activity, without double scaling. A source's "
                "published Cq is not an outbreak inversion performed by this workflow. "
                "Provisional calculations can proceed before calibration, but do not complete that requirement. "
                "scientific_progress.targets reports calibration_linkage for each parameterization. "
                "A supported solution and a calibrated solution in different parameterizations do not "
                "complete the goal. Performing an inversion is distinct from using its derived value "
                "in each target's three calculations; those contributions are credited separately. "
                "calculate_conditional_limits exposes solve_time through allowable_room_time_s "
                "and transient_allowable_room_time_s: FIX neighbor_distance_m and SOLVE duration. "
                "Its solve_distance operation uses safe_distance_m and transient_safe_distance_m: "
                "FIX exposure_time_s and SOLVE separation. calculate_transmission_metrics exposes "
                "evaluate_R_in through scenario_reproductive_number and transient_scenario_reproductive_number: "
                "FIX BOTH exposure_time_s and neighbor_distance_m. All three operations use the "
                "same risk model and assumptions within a background regime. Background-only legacy "
                "outputs and the concentration crossover do not substitute for these requested answers. "
                "The tool binds caller-supplied reference inputs before model review and execution; "
                "it does not choose scientific assumptions. These reference inputs are not the "
                "unknown being solved for and are not discoveries to research or reassess. Never "
                "copy the reference separation as a calculated safe distance or replace it with "
                "random spacing. Omitted target-case reference inputs are filled by the scenario "
                "loader using the declared reference defaults, not selected by the agent. These "
                "defaults never supply an outbreak's exposure duration. calculation_variables remain free variables "
                "for explicitly requested legacy relationships, not scalar safety answers. "
                "In particular, do not invent an exposure duration to fill a risk "
                "or distance output. This restriction applies to declared calculation variables, not "
                "to proposing reasoned physical hypotheses. A source range need not choose a scalar "
                "for the investigator: choosing and qualifying that hypothesis is its responsibility. "
                "Calibration contexts must be grounded in acquired observations, not invented outbreaks. "
                "Reference existing subjects without "
                "redeclaring or paraphrasing their definitions. "
                "Investigate unresolved assumptions, conflicting evidence, or prediction discrepancies. "
                "Calculations select existing fact options or numeric assumption options, including "
                "unsupported guesses; use named condition statements. calculation_inputs separates "
                "numeric references from condition hypotheses. Never place a condition reference in facts. "
                "Numeric hypotheses originate in "
                "investigate, not as hidden literals in a tool call. Evidence quality affects credit and "
                "conclusion support, not permission to compute. Calculating a guess can reveal sensitivity "
                "or a discrepancy without validating it. Recalculate when input values or model claims change. "
                "Develop provisional numerical results and iteratively strengthen their assumptions or "
                "revise their consequences. Numerical coverage and evidential support are concurrent needs, "
                "not phases where every missing output must be filled before any weak result is revisited. "
                "Do not wait for all assumptions to be "
                "well supported before using the calculation tools. This is a scientific objective, not a fixed action order. "
                "A calculation for a scoped case can reveal concrete gaps relevant to the other fixed cases; "
                "resolving every uncertainty across all cases is not a prerequisite to that calculation. "
                "Use one stable parameterization name for compatible input assumptions across tools; a tool "
                "or output-family name is not a different physical case. Distinguish steady, transient and "
                "near-field regimes explicitly without fragmenting an otherwise shared parameterization. "
                "A new review of an unchanged claim changes its support, not its computed consequence. "
                "Read per-quantity coverage and metric_support: weak evidence for one input does not "
                "invalidate outputs that do not use it. "
                "Each calculation tool owns the output names in its action-specific metrics schema. "
                "Omit metrics to use that tool's requested outputs. Geometry/removal derivations also "
                "emit available input parameters automatically; do not put those input names in metrics. "
                "The same parameter derivations run inside the limit and transmission tools, so a separate "
                "geometry step is not required when the selected inputs suffice. input_requirements shows "
                "executable routes and their missing inputs/conditions, not a requirement to search for an "
                "already implemented equation. An absent removal term requires an explicit hypothesis, "
                "including when the proposed term is zero; it is never silently zero. "
                "Routes also declare parameter_constraints enforced by execution. If the selected case "
                "falls outside every implemented route, identify that capability gap explicitly. "
                "A differently worded condition or another supporting source cannot register a new kernel "
                "or override those constraints. Evidence can inform a needed extension without making "
                "it executable in this run. Such a gap does not resolve the requested quantity, but it "
                "is not a prerequisite to strengthening other still-uncertain conclusions. "
                "For all three operations, inspect the alternative routes and their physical hypotheses. The "
                "negligible_near_field condition explicitly selects a spatially uniform risk model for "
                "time, distance AND R_in; "
                "mask penetration alone does not justify or select it. A well-mixed background does "
                "not establish negligible local exposure. Do not assume away local risk merely to fill "
                "coverage. A zero minimum under that approximation means no positive separation is "
                "imposed by the model, not that contact is safe. Retain the hypothesis and its uncertainty. "
                "The transient continuous-jet route additionally requires an explicit "
                "quasi_steady_local_plume hypothesis. It adds an immediately established local jet "
                "to the time-evolving background; it is not a resolved transient-flow simulation. "
                "That hypothesis may be provisionally calculated before evidence is strong, just "
                "like other assumptions. Keep its uncertainty visible to the investigation. "
                "A duration formula alone does not satisfy a requested scalar output contract. "
                "A target scenario identifies the case or conditional experiment receiving estimates. "
                "A model extension or unresolved equation is an investigation focus for a case, not a "
                "separate target requiring its own complete report. Only when cases are not fixed and the request leaves them open, "
                "explicitly scoped study cases may instantiate that open scope; do not substitute them "
                "for specified cases or claim they establish results for every possible case. "
                "Distinguish requester constraints from unresolved scientific assumptions and named "
                "conditional study choices. An unspecified input is not automatically something only "
                "the requester can supply: the investigation branch may propose and justify bounded "
                "assumptions where appropriate. Such choices are neither universal defaults nor facts "
                "about an unspecified real room. Preserve all requested outputs and case constraints. "
                "General applicability does not mean one universal set of parameter values. Named "
                "conditional parameterizations can instantiate a target scope, with every numerical "
                "choice given a rationale and its current support distinguished from requester givens "
                "and source observations. Missing justification remains a research need, not an execution gate. "
                "scientific_progress separates computed quantities, evidence-supported quantities and "
                "coherent parameterization coverage, using the same projection as closure. Its figures "
                "retain named assumptions; assumption_support_needs links weaker premises to affected outputs. "
                "quantity_coverage exposes an output still absent across the cases. Progress on other "
                "quantities does not resolve it or make it optional. Use the child's explanation to "
                "distinguish missing proposed inputs, uncertain evidence and actual model inapplicability; "
                "generic evidence alone is not a reason that a provisional hypothesis cannot be formed. "
                "computed_but_unsupported_subjects remains part of the scientific goal, even when "
                "another output lacks an executable route. Judge new investigations by the uncertainty "
                "they can change, including support for existing results, not by empty-field count alone. "
                "Improving a review can strengthen existing results without repeating the arithmetic. "
                "A current result at the required fixed inputs earns provisional computation credit; "
                "evidence strengthens it further. Copying a reference input, computing a legacy metric, "
                "repeating arithmetic, or excluding a kernel does not answer a missing requested operation. "
                "There is no fixed action order; apply the newly executable calculation "
                "preference above at each root decision. "
                "The registered equations are already executable kernels; verifying their scientific "
                "basis may resolve uncertainty, but transcribing them is not itself a prerequisite "
                "for tool availability or a numerical safety conclusion. "
                "The requested output quantities are model outputs, not facts to search for verbatim. "
                "Return an instance of the JSON Schema; omit fields not used by the selected action."
            ),
            response_contract=self.proposal_schema()))
        self.last_proposal = proposal
        action = selected_choice(proposal.get("action"), ["investigate", *self.run.tools], "action")
        objective = text(proposal.get("objective"), "objective") if action == "investigate" or "objective" in proposal else None
        staged = admit_scopes(self.run, proposal, self.ledger.result(), self.context())
        context = {**self.context(), "defined_scenarios": dict(staged.scenarios)}
        if not self.request_read:
            self.request_evidence = extract_and_admit(self.run.agent, text=self.run.research_request, source="request",
                objective=OBJECTIVE, context=context,
                question="Admit only explicit requester-defined constraints. Questions asking for unknown scientific quantities are not evidence of their answers.")
            self.request_read = True
        staged.merge(self.request_evidence)
        if action == "investigate":
            parameter = selected_choice(proposal.get("parameter"),
                set(self.focus) & (UNITS.keys() | CONDITIONS.keys()), "parameter")
            deliverable = selected_choice(proposal.get("deliverable"),
                ("source_findings", "assumption_hypotheses"), "deliverable")
            source = InvestigationSource(self.run, staged.result())
            subjects = proposal.get("subjects")
            if not isinstance(subjects, list) or any(s not in staged.scenarios for s in subjects):
                raise ValueError("Investigation subjects must be reviewed scenarios")
            source.credit_subjects = tuple(subjects) or None
            if deliverable == "assumption_hypotheses" and not subjects:
                raise ValueError("An assumption investigation must name its assigned scenario subjects")
            targets = {name: definition for name, definition in staged.scenarios.items()
                       if definition.get("role") == "target"}
            target_scenarios = {name: {
                "description": targets[name]["description"],
                "fixed_parameters": targets[name].get("fixed_parameters", {}),
                "fixed_conditions": targets[name].get("fixed_conditions", {}),
                "assumption_needs": targets[name].get("assumption_needs", ()),
            } for name in targets}
            return self.edge(self.run.child(view, source, "investigate", objective,
                proposal=proposal, contract=self.contract(
                    f"Decide which assumptions/model choices or calculations to revisit: {objective}",
                    subjects=subjects, deliverable=deliverable,
                    meaning=objective, parameter=parameter, target_scenarios=target_scenarios)))

        return calculation_leaf(self, proposal, staged, context)


class InvestigationSource(ResearchSource):
    def __init__(self, run, inherited):
        super().__init__(run, inherited)
        self.candidates = {}
        self.staged = Ledger(inherited)
        self.output_fields = ()

    def uses_scientific_credit(self):
        # The child answers its assignment; the root projects scientific credit.
        return False

    @staticmethod
    def candidate_key(candidate):
        return identity([candidate.get("subject"), candidate.get("field"), candidate.get("value"),
                         candidate.get("statement") if candidate.get("field") in CONDITIONS else None])

    def inference_options(self):
        """Inputs retain native fields; the assignment constrains inferred outputs."""
        return self.ledger.evidence_options(), input_options(self.ledger)

    def proposal_schema(self):
        prose = {"type": "string", "minLength": 1}
        evidence, numeric = self.inference_options()
        schema = GuidelineSource.proposal_schema(self, ledger=self.ledger,
            actions=["evidence_strategy", *self.run.tools], focus=())
        schema.pop("required")
        schema["anyOf"] = [{"required": ["action"]},
                           {"required": ["candidates"], "properties": {"candidates": {"minItems": 1}}}]
        for condition in schema["allOf"]:
            if "action" in condition["if"].get("properties", {}):
                condition["if"]["required"] = ["action"]
        schema["properties"].update({
            "approach": {**prose, "description": "Evidence strategy and its rationale"},
            "objective": {**prose, "description": "Information this strategy must resolve for the parent"},
            "candidates": {"type": "array", "description": "Your proposed target-case hypotheses for mandatory assessment. Omit action and supply nonempty candidates to assess in this iteration using accumulated evidence, without another search. With evidence_strategy, assessment follows that child. An empty array proposes no new hypotheses.",
                "items": candidate_response_schema(
                    scenarios={name: self.ledger.scenarios[name] for name in self.requested_subjects}
                              if self.run.fixed_scenarios else None, evidence=evidence, numeric_inputs=numeric)},
        })
        schema["allOf"].append({"if": {"required": ["action"], "properties": {"action": {"const": "evidence_strategy"}}},
                                 "then": {"required": ["approach", "objective", "candidates"]}})
        return schema

    def propose(self, view):
        self.staged = Ledger(self.ledger.result())
        evidence, numeric = self.inference_options()
        proposal = self.run.agent(self.inputs(view, operation="propose_investigation_strategy",
            candidates=[assumption_model_view(candidate, evidence_options=evidence, numeric_options=numeric)
                        for candidate in self.candidates.values()],
            canonical_fields=UNITS, model_conditions=CONDITIONS,
            allowed_actions=["evidence_strategy", *self.run.tools], tools=self.run.tools,
            inference_inputs={
                "evidence_options": {key: {**evidence_summary(record),
                                           "source_version": record.get("source_version", "")}
                                     for key, record in evidence.items()},
                "numeric_options": {key: (fact.semantic_record() if fact.kind == "derived" else fact.as_record())
                                    for key, fact in numeric.items()},
                "selection_contract": "Candidate source_refs select these evidence_options; input_refs select these numeric_options. These references identify existing records, not new evidence or permission to relabel a measurement.",
            },
            calculation_inputs={
                "numeric_options": {key: {name: value for name, value in fact.semantic_record().items()
                                          if name in {"subject", "field", "value", "unit", "kind"}}
                                    for key, fact in input_options(self.ledger).items()},
                "condition_hypotheses": [value for value in self.ledger.assumption_options().values()
                                         if value["value"] is None],
                "selection_contract": "facts selects numeric_options references; conditions maps canonical condition fields to statements.",
            },
            calculations=tool_options(self.ledger),
            reasonableness_rubric=RUBRIC,
            episode_responsibilities={
                "this_investigation": "Meet the parent's information contract through assessed hypotheses from accumulated evidence and chosen evidence strategies. When existing inputs permit a requested calculation, execute its deterministic tool here and share that progress with the whole Goal.",
                "strategy_child": "Acquire and synthesize source evidence relevant to the hypotheses and unresolved question. It cannot propose or admit target-case assumptions for this investigation.",
                "scientific_parent": "Use shared calculation and evidence progress to select the next investigation or calculation.",
            },
            instruction=(
                "You are the investigation episode, responsible for connecting source evidence to the "
                "parent's scientific Goal. Use the information you already have to infer missing "
                "parameters: recognize related quantity names, convert units, recast measurements, "
                "or calculate an estimate from other quantities when the physical reasoning permits it. "
                "Record each inferred numeric candidate as entry_type=best_guess, with its own "
                "canonical value and unit, source_refs and input_refs from inference_inputs, the "
                "reasoning and arithmetic in basis, and any added_assumptions. Preserve the native "
                "meaning of each source measurement; your inference is a separate parameter claim. "
                "To submit candidates using accumulated evidence now, omit action and return a "
                "nonempty candidates array. The normal mandatory assessment follows immediately; "
                "no new search, tool or child is required. Empty references honestly declare an "
                "unsupported guess; they do not manufacture evidence. Choose evidence_strategy "
                "when you need additional evidence, or choose an available calculation tool when selected existing inputs and physically "
                "applicable conditions can produce a new requested result. A tool choice uses existing "
                "numeric_options and condition statements; do not put a new hypothesis in tool literals. "
                "Prefer a newly executable provisional calculation to another long evidence strategy "
                "when it advances the shared Goal. A calculation here retains its source and assumption "
                "lineage and returns to the parent with your other findings. For evidence_strategy, "
                "choose candidate hypotheses and an evidence-acquisition approach "
                "for this parent's scientific uncertainty. Put hypotheses you propose in this response's "
                "candidates array. Read the parent's deliverable: source_findings needs source-grounded "
                "answers, bounds and applicability limits and does not require inventing a target "
                "hypothesis; assumption_hypotheses needs actual recorded proposals and mandatory "
                "reasonableness assessment. Under either contract, any hypotheses you choose to propose "
                "must be recorded in the "
                "candidates array. Asking the strategy child to construct a parameterization, choose "
                "values or independently assess assumptions does not perform that work: its contract "
                "returns source evidence, not target-case hypotheses. Mandatory reasonableness review assesses "
                "only candidates actually recorded by this investigation. "
                "Admitted source values and ranges can inform your own conditional choices with an "
                "explicit applicability rationale; they need not already be labeled with the target "
                "subject. A source range may support a provisional scalar hypothesis without selecting "
                "one for you. Identify which uncertainty would change that choice or its support. "
                "The prohibition on arbitrary exposure durations or scenario replacement does not prohibit "
                "physical-parameter estimation within a fixed case. Distinguish the case's declared "
                "calculation_variables from missing physical inputs. For the latter, reason from available "
                "ranges, transferable measurements, dimensional constraints or clearly labeled guesses; "
                "name the applicability premise and what could overturn it. A range can motivate one "
                "qualified hypothesis or distinct sensitivity hypotheses without constituting a direct "
                "measurement. Do not defer a whole requested output merely because the source did not "
                "select a scalar for you. If a proposed approximation would contradict the fixed case "
                "or the available model, explain that specific conflict rather than inventing a compatible case. "
                "Model constraints conveyed by the parent are execution limits, not evidence grades. "
                "A new hypothesis can supply a missing parameter or qualify an applicable regime, but "
                "cannot add a kernel or override its enforced constraints. Distinguish evidence that "
                "would inform a model extension from an input the parent can calculate with now. "
                "An empty candidates array is appropriate when this iteration is acquiring information "
                "without proposing a new hypothesis, but it leaves target inputs unresolved unless "
                "existing candidates already cover them. "
                "Use previous failures to understand what remains unknown. You may propose or revise "
                "named candidate assumptions and alternatives, but cannot mark them supported or assign credit. "
                "A candidate statement describes a physical/scenario claim, not a research instruction or "
                "a rule to use a model only after evidence is found. For an unchanged claim, preserve its "
                "existing statement exactly; put new rationale in basis and evidence qualifications in the "
                "mandatory review. Changing a statement changes claim identity and can invalidate calculations. "
                "Source extraction and assumption inference have different contracts: extracted "
                "numeric facts must be printed in a source, whereas a candidate may be an inferred "
                "conditional value with a named rationale to test against numeric or qualitative "
                "evidence. A formula inventory alone is not a justified target parameterization. "
                "When a final parameter is not directly reported, consider measurements of its "
                "ingredients, related systems, geometric or physical constraints, and explicit "
                "approximations. Explain the inference, differences in context and uncertainty. "
                "A guess can be proposed before justification exists; its assessment and credit must "
                "reflect that weakness, but the parent can still calculate its consequences. "
                "Do not restrict all evidence searches to a reference paper merely because it defines "
                "the model. Choose the approach from the information needed and prior search outcomes. "
                "A numeric candidate needs a finite JSON number, not a string or null. If a parameter has "
                "no proposed value yet, omit that numeric candidate rather than using null. Explain in "
                "approach which requested quantity remains unresolved and what reasoning or evidence "
                "is needed to form a hypothesis; missing direct measurement alone does not prohibit "
                "an inferred choice. Null is only for nonnumeric model conditions. "
                "Mandatory assessment follows every candidate-bearing iteration or returned strategy "
                "and considers accumulated supporting and contrary evidence, including inherited evidence. "
                "The system has already compared the selected cases and grouped parameter needs "
                "that can use one value. Propose one candidate for an independent group; do not "
                "duplicate it across that group's cases. "
                "A candidate is a hypothesis, never reported evidence. When context.fixed_scenarios is true, "
                "use the caller's existing cases, do not define or alter scenarios, and do not propose their "
                "fixed_parameters or fixed_conditions as new assumptions. Source evidence retains its actual "
                "event identity; explain its applicability to the selected target cases. Only an unfixed "
                "internal task may define additional source/calibration scenarios. No stopping or separate assessment action."
                " A scenario is a case or conditional experiment, not an equation or investigation topic."
                " Every candidate subject must match a reviewed case. Source-event labels alone do not "
                "establish a scope; source evidence retains its original identity and applicability must "
                "be assessed for the target. Fixed-mode contracts do not accept scenario definitions. "
                " The parent's information contract and requested subjects are in context. Source or "
                "calibration subjects can supply evidence, but new templates do not substitute for "
                "resolving assumptions for the requested subjects. Explain applicability to those subjects. "
                "Propose hypotheses only for your assigned question and subjects. "
                "The parent-assigned parameter fixes this branch's scoring scope. Strategies may "
                "vary, but additional source settings or broader questions are not extra requirements. "
                "Retain competing parameter values with their evidence and conditions; do not select "
                "a value by evidence count. Mandatory reasonableness review judges applicability "
                "and contradictions. "
                "Give the strategy child a specific evidence question and the necessary hypothesis "
                "context in objective, not your whole assignment or a field checklist. Its short "
                "synthesis should help you decide whether this approach is informing the assumption. "
                "Return an instance of the JSON Schema."
            ), response_contract=self.proposal_schema()))
        self.last_proposal = proposal
        action = (selected_choice(proposal["action"], ["evidence_strategy", *self.run.tools], "action")
                  if "action" in proposal else None)
        if action is not None and action != "evidence_strategy":
            if proposal.get("candidates"):
                raise ValueError("A calculation may select only previously recorded hypotheses")
            self.staged = admit_scopes(self.run, proposal, self.ledger.result(), self.context())
            context = {**self.context(), "defined_scenarios": dict(self.staged.scenarios)}
            return calculation_leaf(self, proposal, self.staged, context)
        self.staged = admit_scopes(self.run, proposal, self.ledger.result(), self.context())
        if "candidates" not in proposal:
            raise ValueError("Investigation proposals require a candidates array. Put this episode's hypotheses there; instructions asking its evidence-acquisition child to propose them do not register hypotheses. Use [] when none are proposed.")
        candidates = proposal["candidates"]
        if not isinstance(candidates, list) or (action is None and not candidates):
            raise ValueError("Candidate assumptions must be a list, nonempty when no action is selected")
        for candidate in candidates:
            if (isinstance(candidate, dict) and candidate.get("field") in UNITS
                    and candidate.get("entry_type") != "best_guess"):
                raise ValueError("An inferred numeric candidate must declare entry_type=best_guess")
            if isinstance(candidate, dict) and candidate.get("entry_type") == "best_guess":
                if "derivation" in candidate:
                    raise ValueError("New candidate provenance must select the supplied source_refs and input_refs")
                for name, options in (("source_refs", evidence), ("input_refs", numeric)):
                    refs = candidate.get(name)
                    if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in options for ref in refs):
                        raise ValueError(f"Candidate {name} must select this investigation's inference_inputs")
        validated = [assumption_candidate(candidate, self.staged) for candidate in candidates]
        if any(c["field"] not in self.parameter_requirements for c in validated):
            raise ValueError("Candidate assumptions must serve the assigned parameter or its executable dependencies")
        if self.run.fixed_scenarios and any(c["subject"] not in self.requested_subjects for c in validated):
            raise ValueError("Candidate assumptions must belong to this investigation's assigned subjects")
        changed_candidates = [candidate for candidate in validated
                              if self.candidates.get(self.candidate_key(candidate)) != candidate]
        self.candidates.update((self.candidate_key(candidate), candidate) for candidate in validated)
        for candidate in changed_candidates:
            self.run.emit_trace("target_input_candidate", status="proposed_not_admitted",
                episode_id=self.goal.goal_id, investigated_target_subjects=list(self.requested_subjects),
                subject=candidate["subject"], field=candidate["field"], value=candidate["value"],
                unit=candidate["unit"], statement=candidate["statement"],
                entry_type=candidate.get("entry_type"), derivation=candidate.get("derivation"),
                model_calls=self.run.model_calls)
        if action is None:
            return self.leaf(lambda: self.staged.result(), "inferred_parameters")
        approach, objective = text(proposal.get("approach"), "approach"), text(proposal.get("objective"), "objective")
        source = StrategySource(self.run, self.staged.result(), approach=approach)
        return self.edge(self.run.child(view, source, "strategy", objective,
            proposal=proposal, contract=self.contract(
                f"Judge whether evidence supports, bounds or contradicts candidate assumptions: {objective}",
                subjects=self.requested_subjects,
                target_scenarios=self.parent_contract.measurements.get("target_scenarios"))))

    def assess(self, result):
        """Always run before this episode's credit projection, never as an action."""
        working = Ledger(self.staged.result())
        working.merge(result)
        failed = False
        assessed = 0
        for key, candidate in self.candidates.items():
            field = candidate["field"]
            options = working.evidence_options()
            current = working.assumptions.get(key)
            # Cross-field physical evidence can support or contradict a hypothesis.
            # The reviewer, not a field-name filter or proposer, judges relevance.
            relevant = options
            basis_version = identity([candidate, list(relevant.values()), working.scenarios.get(candidate["subject"])])
            if current and current.get("assessment_basis_version") == basis_version:
                continue
            try:
                assessment = assess_assumption(self.run.complete, {**candidate, "evidence": list(relevant)}, working,
                    self.context())
                assessment.assumptions[0]["assessment_basis_version"] = basis_version
                working.merge(assessment)
                assessed += 1
            except (ProviderError, ValueError, TypeError, KeyError, OSError) as exc:
                failed = True
                failure = self.failure_result(exc, "mandatory_reasonableness_assessment")
                # An unfinished review is not a new scientific judgment.
                completed = current and current.get("review", {}).get("completed", True)
                if current is None:
                    try:
                        hypothesis = unassessed_assumption(candidate, working)
                    except (ValueError, TypeError, KeyError):
                        hypothesis = None
                    if hypothesis is not None:
                        working.merge(ResearchResult(assumptions=(hypothesis,)))
                state = {
                    "retained_version": current.get("version") if completed else None,
                    "retained_basis_version": current.get("assessment_basis_version") if completed else None,
                    "unassessed_basis_version": basis_version,
                    "hypothesis_available": key in working.assumptions,
                    "meaning": ("Prior completed judgment and credit retained; new material or rationale was not reassessed. "
                                "The failed attempt establishes neither new support nor an invalidation."
                                if completed else "No completed judgment exists. Any valid recorded candidate remains an unassessed "
                                "hypothesis usable for conditional calculations, with no evidence or assessment credit."),
                }
                working.merge(replace(failure, diagnostics=tuple({**d,
                    "subject": candidate["subject"], "field": field, "proposal": candidate,
                    "assessment_state": state}
                    for d in failure.diagnostics)))
        reviewed = working.result(evaluated=assessed > 0 or (result.evaluated and not failed), stop_reason=result.stop_reason)
        return super().assess(reviewed)


def run_guideline_research(*, disease, providers, research_request="", metrics=DEFAULT_METRICS, limits=None, scenario="bazant-bush"):
    """Caller-defined cases; evidence and scientific answers start empty."""
    disease = text(disease, "disease of interest")
    if not isinstance(research_request, str):
        raise ValueError("Additional research instructions must be text")
    metrics = tuple(dict.fromkeys(metrics))
    if set(metrics) != set(DEFAULT_METRICS):
        raise ValueError("The safety-guideline workflow requires allowable time, safe distance and R_in "
                         "in both steady and initially clean-room regimes. Omit --metric to use the "
                         "complete output contract; scenario selection does not reduce these quantities.")
    request = (f"Disease of interest: {disease}. Estimate allowable room time, risk-based safe distance, "
               "and R_in for the caller-selected fixed scenarios. Fix separation to solve time; "
               "fix duration to solve separation; fix both to evaluate R_in under the same model. "
               "Use the scenario's reference inputs for these calculations. Investigate evidence for the "
               "disease-dependent assumptions; the scenario catalog provides no infectiousness answers. "
               "Do not discover or replace scenarios, assign arbitrary exposure durations, or target "
               "published numerical answers. " + research_request).strip()
    from .scenario_sharing import initialize_parameter_scope
    initial = initialize_parameter_scope(initial_scenarios(load_scenarios(scenario)),
        providers.scenario_parameter_assessor, disease=disease)
    return _run_research(research_request=request, providers=providers, metrics=DEFAULT_METRICS,
                         limits=limits, initial=initial, disease=disease,
                         scenario_selection=scenario)


def _run_research(*, research_request, providers, metrics=DEFAULT_METRICS, limits=None, initial=None,
                  disease=None, scenario_selection=None):
    """Shared method_loop composition; unfixed mode is used by synthetic fixtures."""
    if not isinstance(research_request, str) or not research_request.strip():
        raise ValueError("research_request must be a nonempty natural-language prompt")
    metrics = tuple(dict.fromkeys(metrics))
    if not metrics or any(m not in METRICS and m != "removal_rate_s" for m in metrics):
        raise ValueError("Unknown requested metric")
    run = ResearchRun(providers, limits or ResearchLimits(), research_request, metrics,
                      initial=initial, scenario_selection=scenario_selection)
    if disease is not None:
        run.context["disease_of_interest"] = disease
    variables = (set.intersection(*(set(s.get("calculation_variables", ())) for s in initial.scenarios))
                 if initial and initial.scenarios else set())
    focus = tuple(sorted((input_fields(metrics, parameters=UNITS) - variables) | set(metrics) |
                         {CALIBRATION_PROGRESS, GLOBAL_GOAL_PROGRESS} |
                         (set() if run.fixed_scenarios else {CONSISTENCY})))
    goal = EpisodeGoal.root(objective=f"{OBJECTIVE}\n\nResearch request: {research_request}",
        result_contract={"metrics": list(metrics), "provisional_outputs": True,
            "scenario_output_contracts": {s["subject"]: s.get("output_contracts", {})
                                          for s in initial.scenarios} if initial else {},
            "evidence_support_reported_separately": True,
            "input_roles": "Requester constraints, source observations, source-model choices and named hypotheses remain distinct; "
                           "evidence claims require retained provenance, while hypotheses may be calculated before support exists."},
        task_context=run.context)
    source = GuidelineSource(run)
    episode = run.episode("evaluate_airborne_safety_guideline", source, goal=goal, focus=focus)
    record = episode.run(Context(tree=run.tree))
    return record, ResearchReport.from_result(source.build_result(record), record, run)
