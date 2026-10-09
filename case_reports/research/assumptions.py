"""Evidence-linked reasonableness assessments, distinct from source extraction.

Ordinal review grades are operational judgments, not calibrated probabilities.
The proposer cannot set its own credit or turn a conditional claim into evidence.
"""

from ...task_executors.scenario_metrics.evaluate import CONDITIONS, UNITS, validate_parameter, output_is_resolved
from ...task_executors.scenario_metrics.catalog import METRICS
from .records import Credit, Fact, ResearchResult, identity, assessment_summary


RUBRIC = {
    "support": "0: no relevant admitted evidence; 1: indirect evidence with an explicit inference; 2: direct applicable evidence resolving the claim, for or against, or an explicit request constraint.",
    "applicability": "0: context unexamined; 1: bounded context comparison with stated limitations; 2: scenario, activity and population match or mismatch established.",
    "physical_consistency": "0: consistency unexamined; 1: plausible mechanism with unresolved checks; 2: relevant checks establish physical consistency or a contradiction.",
    "uncertainty": "0: uncertainty ignored; 1: consequential limitations identified; 2: alternatives or bounds examined and remaining limitations explained.",
}


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def texts(value, name):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{name} must be a list of nonempty text")
    return value


def reasonableness_response_schema(evidence, request_evidence=()):
    nonempty_text = {"type": "string", "minLength": 1}
    text_list = {"type": "array", "items": nonempty_text}
    evidence_item = {"type": "string", "enum": list(evidence)} if evidence else False
    criterion = {"type": "object", "additionalProperties": False,
        "required": ["grade", "reason", "evidence"], "properties": {
            "grade": {"type": "integer", "enum": [0, 1, 2]}, "reason": nonempty_text,
            "evidence": {"type": "array", "items": evidence_item}},
        "allOf": [{"if": {"properties": {"grade": {"enum": [1, 2]}}},
                   "then": {"properties": {"evidence": {"minItems": 1}}}}]}
    return {"type": "object", "additionalProperties": False,
        "required": ["verdict", "criteria", "limitations", "alternatives", "missing_evidence", "explanation", "request_constraint"],
        "properties": {
            "verdict": {"type": "string", "enum": ["supported", "provisional", "unsupported", "contradicted"]},
            "criteria": {"type": "object", "additionalProperties": False, "required": list(RUBRIC),
                         "properties": {name: criterion for name in RUBRIC}},
            "limitations": text_list, "alternatives": text_list, "missing_evidence": text_list,
            "explanation": nonempty_text,
            "request_constraint": {"type": ["object", "null"], "additionalProperties": False,
                "description": "Explicit requester condition instantiated by this candidate, or null for a scientific hypothesis. This is scope classification, not empirical support.",
                "required": ["evidence", "reason"], "properties": {
                    "evidence": {"type": "array", "minItems": 1, "uniqueItems": True,
                        "items": {"type": "string", "enum": list(request_evidence)} if request_evidence else False},
                    "reason": {**nonempty_text, "description": "Why the quoted requester condition applies to this candidate's specific scenario, including any difference in subject labels"}}}},
        "allOf": [
            {"if": {"properties": {"verdict": {"const": "supported"}}},
             "then": {"properties": {"criteria": {"properties": {
                 name: {"properties": {"grade": {"const": 2}}} for name in RUBRIC}}}}},
            {"if": {"properties": {"verdict": {"const": "provisional"}}},
             "then": {"properties": {"limitations": {"minItems": 1}}}},
        ]}


def assumption_candidate(action, ledger):
    """Validate a hypothesis before acquisition and again before assessment."""
    if not isinstance(action, dict):
        raise ValueError("Candidate assumption must be an object")
    subject, field = text(action.get("subject"), "subject"), action.get("field")
    if subject not in ledger.scenarios:
        raise ValueError(f"Assumption subject {subject!r} has no reviewed scenario definition. "
                         f"Existing subjects: {list(ledger.scenarios)!r}. Use an exact existing subject "
                         "or define the new scope in this proposal's scenarios list. "
                         "Source-evidence labels do not automatically define model scenarios.")
    if field not in UNITS and field not in CONDITIONS:
        raise ValueError("Unknown assumption field or model condition")
    value = action.get("value")
    if field in UNITS:
        if value is None:
            raise ValueError(f"{field} is a numeric parameter, not a model condition. Supply a finite "
                             "candidate value or keep it as an unresolved information need; omit the "
                             "candidate until a value can be proposed.")
        validate_parameter(field, value, action.get("unit"))
        if any(f.subject == subject and f.field == field and f.kind == "request_constraint" and f.value != value
               for f in ledger.facts.values()):
            raise ValueError("An assumption cannot override an admitted requester constraint")
    elif value is not None:
        raise ValueError("Model conditions use a statement, not a numeric value")
    return {"subject": subject, "field": field, "value": value,
             "unit": UNITS.get(field, "condition"),
             "statement": text(action.get("statement"), "statement"),
             "basis": text(action.get("basis"), "basis")}


def candidate_response_schema():
    prose = {"type": "string", "minLength": 1}
    properties = {name: prose for name in ("subject", "statement", "basis")}
    properties["subject"] = {**prose, "description": "Exact subject from context.defined_scenarios, "
        "or a new definition in this proposal's scenarios list. A source-evidence subject or "
        "colon-suffixed activity label alone is not a reviewed scenario."}
    return {"oneOf": [
        {"type": "object", "additionalProperties": False,
         "required": [*properties, "field", "value", "unit"], "properties": {**properties,
             "field": {"type": "string", "enum": sorted(UNITS)},
             "value": {"type": "number", "description": "Finite scalar hypothesis, not an unresolved dependency"},
             "unit": {"type": "string", "enum": sorted(set(UNITS.values())),
                      "description": "The canonical unit for this field in canonical_fields"}}},
        {"type": "object", "additionalProperties": False,
         "required": [*properties, "field", "value", "unit"], "properties": {**properties,
             "field": {"type": "string", "enum": sorted(CONDITIONS)},
             "value": {"type": "null"}, "unit": {"const": "condition"}}},
    ]}


def assess_assumption(agent, action, ledger, context):
    claim = assumption_candidate(action, ledger)
    subject, field, value = claim["subject"], claim["field"], claim["value"]
    options = ledger.evidence_options()
    keys = action.get("evidence", [])
    if not isinstance(keys, list) or any(not isinstance(k, str) or k not in options for k in keys):
        raise ValueError("Assumption evidence must reference the admitted evidence catalog")
    evidence = {k: options[k] for k in dict.fromkeys(keys)}
    request_evidence = {k: e for k, e in evidence.items() if e.get("kind") == "request_constraint"
        and ((field in UNITS and e.get("field") == field and e.get("value") == value)
             or (field in CONDITIONS and field in e.get("fields", ())))}
    review = agent({
        "operation": "assess_assumption_reasonableness", "candidate": claim,
        "evidence": evidence, "context": context, "rubric": RUBRIC,
        "previous_assessments": [assessment_summary(a) for a in ledger.assumptions.values()
                                 if a["subject"] == subject and a["field"] == field],
        "instruction": (
            "Assess this candidate independently of its proposer's confidence. Evidence may support, "
            "constrain or contradict it. An inferred value need not appear verbatim in a source; explain "
            "the inference and its bounds. Separate physical plausibility from empirical applicability. "
            "Do not treat source model choices as observations or request constraints as empirical proof. "
            "Cite only supplied evidence options. Unsupported candidates remain hypotheses, not facts. "
            "Return an instance of the JSON Schema. A supported verdict requires grade 2 in every "
            "criterion. When support is bounded or indirect, use provisional with explicit limitations "
            "if warranted; do not inflate grades to fit a verdict. Every positive grade requires "
            "admitted evidence references. The weakest grade limits the numerical credit. "
            "Classify whether this candidate instantiates an explicit requester condition. If so, "
            "return request_constraint with its admitted request evidence and explain applicability "
            "to this target even when the request evidence names a broader scenario class. Otherwise "
            "return null. A source-model choice or a condition for a different case is not a requester "
            "condition for this target. Interpreting a requester condition earns no discovery credit. "
            "Explain why a rejection matters, without prescribing the parent's next action."
        ),
        "response_contract": reasonableness_response_schema(evidence, request_evidence),
    })
    verdict = review.get("verdict")
    if verdict not in {"supported", "provisional", "unsupported", "contradicted"}:
        raise ValueError("Unknown reasonableness verdict")
    criteria = review.get("criteria")
    if not isinstance(criteria, dict) or set(criteria) != set(RUBRIC):
        raise ValueError("Reasonableness review must assess every rubric dimension")
    for name, row in criteria.items():
        if not isinstance(row, dict):
            raise ValueError("Each reasonableness criterion must be an object")
        grade = row.get("grade")
        if type(grade) is not int or grade not in (0, 1, 2):
            raise ValueError("Reasonableness grades must be integers from 0 to 2")
        text(row.get("reason"), name)
        refs = texts(row.get("evidence"), "criterion evidence")
        if any(k not in evidence for k in refs):
            raise ValueError("Review cited evidence outside the admitted selection")
        if grade and not refs:
            raise ValueError("Positive reasonableness grades require admitted evidence references")
    for name in ("limitations", "alternatives", "missing_evidence"):
        texts(review.get(name), name)
    text(review.get("explanation"), "explanation")
    if "request_constraint" not in review:
        raise ValueError("Reasonableness review must classify request_constraint as evidence-linked scope or null")
    constraint = review["request_constraint"]
    if constraint is not None:
        if not isinstance(constraint, dict):
            raise ValueError("request_constraint must be evidence-linked scope or null")
        refs = texts(constraint.get("evidence"), "request constraint evidence")
        if not refs or any(k not in request_evidence for k in refs):
            raise ValueError("Request classification must cite admitted requester evidence for this field and candidate value")
        text(constraint.get("reason"), "request constraint scope reason")
    # A bottleneck prevents impressive prose in one dimension hiding a missing one.
    resolution = min(row["grade"] for row in criteria.values()) / 2
    if verdict == "supported" and resolution < 1:
        incomplete = {name: row["grade"] for name, row in criteria.items() if row["grade"] < 2}
        raise ValueError(f"Supported verdict requires all rubric criteria to have grade 2; received {incomplete!r}. "
                         "Keep evidence-justified grades; use a compatible verdict and explicit limitations.")
    if verdict == "provisional" and not review["limitations"]:
        raise ValueError("Provisional assumptions require explicit limitations")
    quality = resolution if verdict in {"supported", "provisional"} else 0.0
    if verdict == "unsupported":
        resolution = 0.0
    declared = any(
        e.get("kind") == "request_constraint" and e.get("subject") == subject
        and ((field in UNITS and e.get("field") == field and e.get("value") == value)
             or (field in CONDITIONS and field in e.get("fields", ()))) for e in evidence.values())
    declared = declared or constraint is not None
    if declared:
        # Interpreting a supplied number is not new scientific justification.
        resolution = 0.0
    key = identity([subject, field, value, claim["statement"] if field in CONDITIONS else None])
    assessment = {**claim, "key": key, "review": review, "evidence": evidence,
                  "reasonableness": quality, "resolution_credit": resolution,
                  "role": "request_constraint" if declared else "inferred_assumption"}
    assessment["version"] = identity(assessment)
    facts = ()
    if field in UNITS and quality > 0:
        facts = (Fact(subject, field, value, UNITS[field], "model_assumption", claim["basis"],
                      context=claim["statement"], parents=(key,)),)
    return ResearchResult(facts=facts, assumptions=(assessment,),
                          findings=(review["explanation"],),
                          diagnostics=({"stage": "assumption_assessment", "category": verdict,
                                        "subject": subject, "field": field, "why": review["explanation"],
                                        "limitations": review["limitations"], "missing_evidence": review["missing_evidence"]},))


def frame_scenario(agent, action, ledger, context):
    scenario = {"subject": text(action.get("subject"), "subject"),
                "description": text(action.get("description"), "description"),
                "basis": text(action.get("basis"), "basis"),
                "role": action.get("role", "target")}
    if scenario["role"] not in {"target", "calibration", "validation"}:
        raise ValueError("Scenario role must be target, calibration, or validation")
    if "parameters" in action:
        raise ValueError("Scenario framing cannot inject numeric parameter records")
    existing = ledger.scenarios.get(scenario["subject"])
    if existing:
        changed = [name for name in ("description", "role")
                   if existing.get(name, "target" if name == "role" else None) != scenario[name]]
        if changed:
            raise ValueError(f"Scenario {scenario['subject']!r} is already defined; changed fields: {changed}. "
                             "To reference it, use its existing subject and omit it from scenarios. "
                             "A changed scope needs a new subject; previous assessments cannot silently transfer")
        return ResearchResult(scenarios=(existing,))
    review = agent({"operation": "review_scenario_scope", "proposal": scenario, "context": context,
                    "existing_scenarios": list(ledger.scenarios.values()),
                    "instruction": (
                        "Check alignment with the original request. A scenario identifies a case or "
                        "conditional experiment, not an equation, model extension or research topic. "
                        "A target receives the requested safety estimates; calibration and validation "
                        "scenarios identify distinct evidential cases. Reject topic-only scopes rather "
                        "than treating them as additional target cases. Distinguish requester conditions "
                        "from agent-proposed study conditions. When cases are left open, an explicitly "
                        "conditional study case may instantiate that scope without claiming universality. "
                        "Do not replace specified cases or add numerical givens. Framing does not admit "
                        "parameters or evidence; every proposed input still requires acquisition or "
                        "evidence-linked assumption assessment. Explain a rejection so the parent can "
                        "understand which scope requirement was not met."),
                    "response_contract": {"type": "object", "additionalProperties": False,
                        "required": ["admit", "reason"], "properties": {
                            "admit": {"type": "boolean"}, "reason": {"type": "string", "minLength": 1}}}})
    if type(review.get("admit")) is not bool:
        raise ValueError("Scenario review requires a boolean decision")
    text(review.get("reason"), "scenario review reason")
    if not review["admit"]:
        return ResearchResult(findings=(review["reason"],))
    scenario["scope_review"] = review["reason"]
    return ResearchResult(scenarios=(scenario,))


def scientific_credit(result, focus, *, subjects=None):
    """Project reviewed learning, not field presence or children's numeric scores."""
    rows = []
    subjects = (set(subjects) if subjects is not None else
                {s["subject"] for s in result.scenarios if s.get("role", "target") == "target"})
    current = {a["key"]: a for a in result.assumptions}
    for field in focus:
        assessments = [a for a in result.assumptions if a["field"] == field]
        score = 0.0
        if field == "evidence_consistency" and subjects:
            def checked(calculation):
                if calculation["tool"] != "compare_predictions_with_observations":
                    return 0.0
                if calculation["output"]["category"] == "calibration_consistency":
                    return 0.0
                versions = calculation["assumption_versions"]
                return min((current.get(k, {}).get("reasonableness", 0)
                            if current.get(k, {}).get("version") == version else 0
                            for k, version in versions.items()), default=0)
            # Establishing a discrepancy is learning too; a smaller residual is not credit.
            score = sum(max((checked(c) for c in result.calculations if c["subject"] == subject), default=0)
                        for subject in subjects) / len(subjects)
        elif field in METRICS and subjects:
            def supported(estimate):
                if not output_is_resolved(estimate["metrics"].get(field, {})):
                    return 0.0
                refs = estimate.get("assumption_keys", ())
                versions = estimate.get("assumption_versions", {})
                return min((current.get(k, {}).get("reasonableness", 0)
                            if k not in versions or current.get(k, {}).get("version") == versions[k] else 0
                            for k in refs), default=0)
            score = sum(max((supported(e) for e in result.estimates if e["subject"] == subject), default=0)
                        for subject in subjects) / len(subjects)
        elif subjects:
            score = sum(max((a["resolution_credit"] for a in assessments if a["subject"] == subject), default=0)
                        for subject in subjects) / len(subjects)
        rows.append((field, "reviewed_resolution", score))
    return Credit(evaluated=result.evaluated, qualities=tuple(rows))
