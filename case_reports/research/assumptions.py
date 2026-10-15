"""Evidence-linked reasonableness assessments, distinct from source extraction.

Ordinal review grades are operational judgments, not calibrated probabilities.
The proposer cannot set its own credit or turn a conditional claim into evidence.
"""

from ...task_executors.scenario_metrics.evaluate import CONDITIONS, UNITS, validate_parameter
from ...task_executors.scenario_metrics.catalog import METRICS
from .records import Credit, Fact, ResearchResult, identity, assessment_summary, assumption_claim, current_support
from .scenarios import check_case_inputs
from .progress import parameter_support, found_parameter_progress
from .verification import CALIBRATION_PROGRESS, calibration_progress, target_calibration_progress
from .model_defaults import retained_defaults


RUBRIC = {
    "support": "0: no relevant admitted evidence; 1: indirect evidence with an explicit inference; 2: direct applicable evidence resolving the claim, for or against, or an explicit request constraint.",
    "applicability": "0: context unexamined; 1: bounded context comparison with stated limitations; 2: scenario, activity and population match or mismatch established.",
    "physical_consistency": "0: consistency unexamined; 1: plausible mechanism with unresolved checks; 2: relevant checks establish physical consistency or a contradiction.",
    "uncertainty": "0: uncertainty ignored; 1: consequential limitations identified; 2: alternatives or bounds examined and remaining limitations explained.",
}

# One rubric increment for a new usable computation; this is not evidence quality.
PROVISIONAL_OUTPUT_CREDIT = 1 / (2 * len(RUBRIC))


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
        "required": ["verdict", "criteria", "limitations", "alternatives", "missing_evidence", "explanation", "request_constraint",
                     "supporting_evidence", "contradicting_evidence", "invalid_evidence"],
        "properties": {
            "verdict": {"type": "string", "enum": ["supported", "provisional", "unsupported", "contradicted"]},
            "criteria": {"type": "object", "additionalProperties": False, "required": list(RUBRIC),
                         "properties": {name: criterion for name in RUBRIC}},
            "limitations": text_list, "alternatives": text_list, "missing_evidence": text_list,
            "explanation": nonempty_text,
            "supporting_evidence": {"type": "array", "uniqueItems": True, "items": evidence_item,
                "description": "Admitted evidence supporting this exact parameter value or condition in its stated context, including justified indirect support. Background and contrary evidence do not belong here."},
            "contradicting_evidence": {"type": "array", "uniqueItems": True, "items": evidence_item,
                "description": "Admitted evidence opposing this claim in comparable conditions. Different contexts or values are not automatically contradictions; explain applicability in the review."},
            "invalid_evidence": {"type": "array", "uniqueItems": True, "items": evidence_item,
                "description": "Evidence records with an identified extraction or attribution error, explained in the review. A valid observation disagreeing with the hypothesis is contrary evidence, not invalid evidence."},
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
        scope_instruction = ("Use an exact caller-defined subject; fixed cases cannot be introduced or replaced. "
                             if any(s.get("scope_locked") for s in ledger.scenarios.values()) else
                             "Use an exact existing subject or define the new scope in this proposal's scenarios list. ")
        raise ValueError(f"Assumption subject {subject!r} has no reviewed scenario definition. "
                         f"Existing subjects: {list(ledger.scenarios)!r}. " + scope_instruction +
                         "Source-evidence labels do not automatically define model scenarios.")
    if field not in UNITS and field not in CONDITIONS:
        raise ValueError("Unknown assumption field or model condition")
    definition = ledger.scenarios[subject]
    if field in retained_defaults(definition):
        raise ValueError(f"{field} is a retained model default; the constants judge must promote it before a scenario-specific value is proposed")
    check_case_inputs(definition, {field: action.get("value")} if field in UNITS else {},
                      {field: action.get("statement")} if field in CONDITIONS else {})
    if field in definition.get("fixed_parameters", {}) or field in definition.get("fixed_conditions", {}):
        raise ValueError(f"{field} is already a fixed scenario condition, not an assumption to propose or reassess")
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
    claim = {"subject": subject, "field": field, "value": value,
             "unit": UNITS.get(field, "condition"),
             "statement": text(action.get("statement"), "statement"),
             "basis": text(action.get("basis"), "basis")}
    if action.get("entry_type") is not None:
        if action["entry_type"] != "best_guess" or field not in UNITS:
            raise ValueError("best_guess entries are inferred numeric parameters")
        claim.update(entry_type="best_guess", derivation=_candidate_derivation(action, claim, ledger))
    elif any(name in action for name in ("source_refs", "input_refs", "added_assumptions", "derivation")):
        raise ValueError("Inference provenance requires entry_type=best_guess")
    return claim


def _candidate_derivation(action, claim, ledger):
    from .records import numeric_references

    evidence = ledger.evidence_options()
    numeric = numeric_references(ledger)
    evidence_ids = {identity(row) for row in evidence.values()}
    numeric_keys = {fact.key: fact for fact in numeric.values()}
    if "derivation" in action:
        derivation = action["derivation"]
        if not isinstance(derivation, dict) or set(derivation) != {
                "source_evidence_ids", "input_fact_keys", "added_assumptions",
                "input_assumption_versions", "input_assumption_claims"}:
            raise ValueError("Invalid retained best-guess derivation")
        sources = texts(derivation["source_evidence_ids"], "source_evidence_ids")
        inputs = texts(derivation["input_fact_keys"], "input_fact_keys")
        added = texts(derivation["added_assumptions"], "added_assumptions")
    else:
        sources = texts(action.get("source_refs"), "source_refs")
        inputs = texts(action.get("input_refs"), "input_refs")
        added = texts(action.get("added_assumptions"), "added_assumptions")
        if any(ref not in evidence for ref in sources) or any(ref not in numeric for ref in inputs):
            raise ValueError("Best-guess references must select this episode's admitted evidence or numeric inputs")
        # Positional option names can move when a child adds source facts.
        sources = [identity(evidence[ref]) for ref in sources]
        inputs = [numeric[ref].key for ref in inputs]
    if any(key not in evidence_ids for key in sources) or any(key not in numeric_keys for key in inputs):
        raise ValueError("Best-guess provenance no longer identifies available evidence or numeric inputs")
    claim_key = identity([claim["subject"], claim["field"], claim["value"], None])
    versions, claims = {}, {}

    def check_lineage(key, path):
        if key == claim_key or key in path:
            raise ValueError("A best guess cannot depend on itself or cyclic input lineage")
        fact = numeric_keys.get(key)
        assumption = ledger.assumptions.get(key)
        if assumption is not None:
            versions[key] = assumption["version"]
            claims[key] = assumption_claim(assumption)
        if fact is not None and fact.kind == "model_assumption" and fact.parents:
            current = ledger.assumptions.get(fact.parents[0])
            if current is not None:
                expected_context = (current["statement"] if fact.subject == current["subject"] else
                                    f"Shared from {current['subject']}: {current['statement']}")
                if (fact.field != current["field"] or fact.value != current["value"]
                        or fact.unit != current["unit"] or fact.context != expected_context):
                    raise ValueError("Best-guess input refers to a changed assumption claim")
        parents = (fact.parents if fact is not None else
                   assumption.get("derivation", {}).get("input_fact_keys", ()) if assumption else ())
        for parent in parents:
            check_lineage(parent, {*path, key})

    for key in inputs:
        check_lineage(key, set())
    if "derivation" in action:
        prior_versions, prior_claims = derivation["input_assumption_versions"], derivation["input_assumption_claims"]
        if (not isinstance(prior_versions, dict) or not isinstance(prior_claims, dict)
                or set(prior_versions) != set(versions) or prior_claims != claims
                or any(not isinstance(value, str) or not value for value in prior_versions.values())):
            raise ValueError("Best-guess input assumption lineage is stale or invalid")
        # Evidence-only reviews may change a version without changing the input claim.
        versions = prior_versions
    return {"source_evidence_ids": list(dict.fromkeys(sources)),
            "input_fact_keys": list(dict.fromkeys(inputs)), "added_assumptions": added,
            "input_assumption_versions": versions, "input_assumption_claims": claims}


def candidate_response_schema(*, scenarios=None, evidence=None, numeric_inputs=None):
    prose = {"type": "string", "minLength": 1}
    properties = {name: prose for name in ("subject", "statement", "basis")}
    properties["subject"] = {**prose, "description": "Exact subject from context.defined_scenarios, "
        "or a new definition in this proposal's scenarios list. A source-evidence subject or "
        "colon-suffixed activity label alone is not a reviewed scenario."}
    if scenarios is not None:
        properties["subject"] = {"type": "string", "enum": list(scenarios),
                                 "description": "Exact reviewed target or calibration context; no new scope or replacement is allowed"}
    def references(options, description):
        item = {"type": "string"} if options is None else (
            {"type": "string", "enum": list(options)} if options else False)
        return {"type": "array", "uniqueItems": True, "items": item, "description": description}
    inferred = {
        "entry_type": {"const": "best_guess", "description": "An LLM-inferred parameter, not a directly reported source fact"},
        "source_refs": references(evidence, "Admitted evidence used in this inference; [] honestly declares no source support yet"),
        "input_refs": references(numeric_inputs, "Existing numeric inputs used in the recasting or calculation; preserve their native meaning"),
        "added_assumptions": {"type": "array", "items": prose,
                              "description": "Explicit approximations or transfer assumptions added by this inference"},
    }
    schema = {"oneOf": [
        {"type": "object", "additionalProperties": False,
         "required": [*properties, "field", "value", "unit", *inferred], "properties": {**properties, **inferred,
             "field": {"type": "string", "enum": sorted(UNITS)},
             "value": {"type": "number", "description": "Finite scalar hypothesis, not an unresolved dependency"},
             "unit": {"type": "string", "enum": sorted(set(UNITS.values())),
                      "description": "The canonical unit for this field in canonical_fields"}}},
        {"type": "object", "additionalProperties": False,
         "required": [*properties, "field", "value", "unit"], "properties": {**properties,
             "field": {"type": "string", "enum": sorted(CONDITIONS)},
             "value": {"type": "null"}, "unit": {"const": "condition"}}},
    ]}
    if scenarios is not None:
        for branch in schema["oneOf"]:
            fields = branch["properties"]["field"]["enum"]
            branch["allOf"] = []
            for subject, definition in scenarios.items():
                choices = [f for f in fields
                    if f not in definition.get("fixed_parameters", {})
                    and f not in definition.get("fixed_conditions", {})
                    and f not in retained_defaults(definition)
                    and f not in definition.get("calculation_variables", ())]
                branch["allOf"].append({"if": {"properties": {"subject": {"const": subject}}},
                    "then": {"properties": {"field": {"enum": choices} if choices else False}}})
    return schema


def unassessed_assumption(candidate, ledger):
    """Retain a validated hypothesis, without inventing an independent judgment."""
    claim = assumption_candidate(candidate, ledger)
    key = identity([claim["subject"], claim["field"], claim["value"],
                    claim["statement"] if claim["field"] in CONDITIONS else None])
    assessment = {**claim, "key": key, "reasonableness": 0.0,
        "role": "inferred_assumption", "evidence": {}, "review": {
            "completed": False, "verdict": "unassessed", "criteria": {}, "request_constraint": None,
            "explanation": "No independent reasonableness judgment completed. This remains a proposed hypothesis, not evidence.",
            "limitations": ["Conditional calculations may use this hypothesis, but no evidential support is established."],
            "alternatives": [], "missing_evidence": ["Independent reasonableness assessment is incomplete."]}}
    assessment["version"] = identity(assessment)
    return assessment


def candidate_review_scope(candidate, ledger):
    """The physical cases and sharing decision to which a claim applies."""
    from .scenario_sharing import group_for

    group = group_for(ledger, candidate["subject"], candidate["field"]) or {}
    subjects = group.get("subjects", (candidate["subject"],))
    return {"scenarios": {name: ledger.scenarios.get(name) for name in subjects}, "group": group}


def register_candidate(candidate, ledger):
    """Retain a validated hypothesis before the common value and review processing.

    A registered statement and its input provenance define the claim. Rewriting
    explanatory prose cannot replace its physical premises without changing that
    statement or the identified provenance.
    """
    claim = assumption_candidate(candidate, ledger)
    key = identity([claim["subject"], claim["field"], claim["value"],
                    claim["statement"] if claim["field"] in CONDITIONS else None])
    current = ledger.assumptions.get(key)
    scope_version = identity(candidate_review_scope(claim, ledger))
    provenance_fields = ("source_evidence_ids", "input_fact_keys", "input_assumption_claims")

    def provenance(row):
        derivation = row.get("derivation", {})
        return {name: sorted(derivation.get(name, ())) if name != "input_assumption_claims"
                else derivation.get(name, {}) for name in provenance_fields}

    same_claim = (current is not None and assumption_claim(current) == assumption_claim(claim)
        and provenance(current) == provenance(claim)
        and current.get("candidate_scope_version", scope_version) == scope_version)
    if same_claim:
        changed_prose = (current["basis"] != claim["basis"] or
            current.get("derivation", {}).get("added_assumptions", ()) !=
            claim.get("derivation", {}).get("added_assumptions", ()))
        diagnostics = ({"stage": "candidate_registration", "category": "registered_claim_retained",
            "subject": claim["subject"], "field": claim["field"], "value": claim["value"],
            "why": "The existing claim, provenance and scope are unchanged. Its registered basis and added assumptions were retained; the proposed rationale rewrite was not applied. A material premise revision must change the claim statement or identified input/source provenance.",
            "proposed_basis": claim["basis"],
            "proposed_added_assumptions": claim.get("derivation", {}).get("added_assumptions", [])},) if changed_prose else ()
        return ResearchResult(assumptions=(current,), diagnostics=diagnostics)
    registered = unassessed_assumption(claim, ledger)
    registered["candidate_scope_version"] = scope_version
    registered.pop("version", None)
    registered["version"] = identity(registered)
    return ResearchResult(assumptions=(registered,))


def candidate_review_identity(candidate, ledger):
    """One review cache identity for every origin; relevance is separate."""
    return identity({"claim": assumption_claim(candidate), "basis": candidate["basis"],
        "derivation": candidate.get("derivation", {}),
        "evidence": sorted(identity(row) for row in ledger.evidence_options().values()),
        **candidate_review_scope(candidate, ledger)})


def assess_assumption(agent, action, ledger, context, *, source_candidate_key=None):
    claim = assumption_candidate(action, ledger)
    automatic = None
    if source_candidate_key is not None:
        automatic = ledger.assumptions[source_candidate_key]
        if (automatic.get("entry_type") != "source_candidate"
                or automatic.get("source_candidate_unavailable")
                or any(claim[name] != automatic[name] for name in claim)):
            raise ValueError("Automatic support review must preserve the selected available claim")
        claim.update(entry_type="source_candidate", derivation=automatic["derivation"],
                     source_applicability=automatic["source_applicability"])
    subject, field, value = claim["subject"], claim["field"], claim["value"]
    options = ledger.evidence_options()
    keys = action.get("evidence", [])
    if not isinstance(keys, list) or any(not isinstance(k, str) or k not in options for k in keys):
        raise ValueError("Assumption evidence must reference the admitted evidence catalog")
    evidence = {k: options[k] for k in dict.fromkeys(keys)}
    inference = {}
    if claim.get("entry_type") in {"best_guess", "source_candidate"}:
        from .records import numeric_provenance
        numeric = numeric_provenance(ledger)
        derivation = claim["derivation"]
        inference = {
            "proposed_source_refs": [key for key, row in evidence.items()
                                     if identity(row) in derivation["source_evidence_ids"]],
            "derivation_inputs": {key: numeric[key].as_record() for key in derivation["input_fact_keys"]},
        }
    request_evidence = {k: e for k, e in evidence.items() if e.get("kind") == "request_constraint"
        and ((field in UNITS and e.get("field") == field and e.get("value") == value)
             or (field in CONDITIONS and field in e.get("fields", ())))}
    review = agent({
        "operation": "assess_assumption_reasonableness", "candidate": claim,
        "evidence": evidence, "context": context, "rubric": RUBRIC, **inference,
        "previous_assessments": [assessment_summary(a) for a in ledger.assumptions.values()
                                 if a["subject"] == subject and a["field"] == field],
        "instruction": (
            "Assess this candidate independently of its proposer's confidence. Evidence may support, "
            "constrain or contradict it. An inferred value need not appear verbatim in a source; explain "
            "the inference and its bounds. Evidence may concern ingredients, related systems or extremes "
            "rather than the final parameter. Assess the approximation or analogy explicitly; an extreme "
            "observation is not a representative measurement, but may anchor a bounded heuristic. "
            "For a best_guess entry, check the recasting, arithmetic, dimensional meaning and added "
            "assumptions stated in basis and derivation against derivation_inputs and the source evidence. "
            "A source_candidate is an automatically recorded conditional transfer of a native source "
            "value to a target parameter group, preserving quantity and unit. Assess that transfer's "
            "scientific support and limitations; its automatic origin is not a reason to reject it. "
            "source_applicability is a separate relevance judgment, not established physical support. "
            "proposed_source_refs records the proposer's claimed support, not your admission decision; "
            "select supporting_evidence independently. The inferred value has its own record and need "
            "not be printed in its source. Never turn a source's native quantity into a different "
            "measurement by relabeling it. Empty proposed references do not provide support; judge "
            "any support you independently identify only from the admitted evidence catalog. "
            "Separate physical plausibility from empirical applicability. "
            "Do not treat source model choices as observations or request constraints as empirical proof. "
            "Cite only supplied evidence options. Unsupported candidates remain hypotheses, not facts. "
            "Separate supporting_evidence from contradicting_evidence for this exact claim and its "
            "conditions. Do not count a different value in a different setting as a contradiction "
            "without an applicability argument. Retain unresolved alternatives and explain genuine "
            "conflicts; never choose a value by majority vote or number of sources. Evidence cited "
            "to explain a limitation is not automatically corroboration. Each reference may appear "
            "in at most one of these two lists. "
            "Use invalid_evidence only for identified errors in extraction or attribution, not "
            "because valid evidence disagrees with a hypothesis. Explain the specific error. "
            "Valid contradictory evidence advances understanding even when current support falls. "
            "Previously acquired learning is distinct from the latest claim's current support. "
            "Return an instance of the JSON Schema. A supported verdict requires grade 2 in every "
            "criterion. When support is bounded or indirect, use provisional with explicit limitations "
            "if warranted; do not inflate grades to fit a verdict. Every positive grade requires "
            "admitted evidence references. Grade established understanding, not the amount of prose: "
            "naming a limitation is not the same as bounding it with applicable evidence. "
            "The weakest grade limits current conclusion support, not permission to calculate a hypothesis. "
            "Recording a numerical target hypothesis fills one independent parameter need and earns "
            "its discovery point regardless of this review's grades. Evidence learning separately "
            "records distinct evidence that strengthens, refines or overturns supported claims. "
            "Neither is a rubric grade or a measure of how completely a question was answered. "
            "Repeating an assessment or adding alternatives for an already filled need does not "
            "earn another discovery point. "
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
    for name in ("supporting_evidence", "contradicting_evidence", "invalid_evidence"):
        refs = texts(review.get(name), name)
        if any(k not in evidence for k in refs) or len(set(refs)) != len(refs):
            raise ValueError(f"{name} must contain distinct admitted evidence references")
    if set(review["supporting_evidence"]) & set(review["contradicting_evidence"]):
        raise ValueError("The same evidence cannot both support and contradict the same claim")
    if set(review["invalid_evidence"]) & (set(review["supporting_evidence"]) | set(review["contradicting_evidence"])):
        raise ValueError("An invalid evidence record cannot support or contradict a claim")
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
    usable = min(row["grade"] for row in criteria.values()) / 2
    if verdict == "supported" and usable < 1:
        incomplete = {name: row["grade"] for name, row in criteria.items() if row["grade"] < 2}
        raise ValueError(f"Supported verdict requires all rubric criteria to have grade 2; received {incomplete!r}. "
                         "Keep evidence-justified grades; use a compatible verdict and explicit limitations.")
    if verdict == "provisional" and not review["limitations"]:
        raise ValueError("Provisional assumptions require explicit limitations")
    quality = usable if verdict in {"supported", "provisional"} else 0.0
    declared = any(
        e.get("kind") == "request_constraint" and e.get("subject") == subject
        and ((field in UNITS and e.get("field") == field and e.get("value") == value)
             or (field in CONDITIONS and field in e.get("fields", ()))) for e in evidence.values())
    declared = declared or constraint is not None
    if verdict in {"supported", "provisional"} and not declared and not review["supporting_evidence"]:
        raise ValueError("A supported or provisional scientific claim requires supporting evidence")
    key = source_candidate_key or identity([subject, field, value, claim["statement"] if field in CONDITIONS else None])
    previous = ledger.assumptions.get(key, {})
    learning = list(previous.get("learning_evidence", ()))
    invalid = list(previous.get("invalidated_evidence", ()))
    invalid.extend(evidence[ref] for ref in review["invalid_evidence"] if evidence[ref] not in invalid)
    if not declared:
        if verdict in {"supported", "provisional"}:
            learning.extend({"relation": "supports", "evidence": evidence[ref]}
                            for ref in review["supporting_evidence"])
        # Refuting a newly invented, never-supported guess is not manufactured progress.
        if any(row["relation"] == "supports" for row in previous.get("learning_evidence", ())):
            learning.extend({"relation": "contradicts", "evidence": evidence[ref]}
                            for ref in review["contradicting_evidence"])
    learning = list({identity(row): row for row in learning}.values())
    assessment = {**previous, **claim, "key": key, "review": review, "evidence": evidence,
                  "reasonableness": quality,
                  "role": "request_constraint" if declared else "inferred_assumption",
                  "learning_evidence": learning, "invalidated_evidence": invalid}
    assessment.pop("version", None)
    assessment["version"] = identity(assessment)
    facts = ()
    if field in UNITS and quality > 0 and automatic is None:
        facts = (Fact(subject, field, value, UNITS[field], "model_assumption", claim["basis"],
                      context=claim["statement"], parents=(key,)),)
    return ResearchResult(facts=facts, assumptions=(assessment,),
                          findings=(review["explanation"],),
                          diagnostics=({"stage": "assumption_assessment", "category": verdict,
                                        "subject": subject, "field": field, "why": review["explanation"],
                                        "limitations": review["limitations"], "missing_evidence": review["missing_evidence"]},))


def assess_registered_candidates(agent, ledger, keys, context, on_failure, *,
                                 stage="candidate_reasonableness_assessment"):
    """Reuse or update one review for registered claims of every origin."""
    from dataclasses import replace
    from ...task_executors._http import ProviderError
    from .records import Ledger

    working = Ledger(ledger.result())
    updates, facts, findings, diagnostics = [], [], [], []
    for key in dict.fromkeys(keys):
        candidate = working.assumptions.get(key)
        if (candidate is None or candidate.get("source_candidate_unavailable")
                or candidate.get("role") in {"scenario_constraint", "request_constraint", "model_default"}):
            continue
        evidence = working.evidence_options()
        basis_version = candidate_review_identity(candidate, working)
        action = {name: candidate[name] for name in ("subject", "field", "value", "unit", "statement", "basis")}
        automatic = candidate.get("entry_type") == "source_candidate"
        if not automatic and candidate.get("entry_type") == "best_guess":
            action.update(entry_type="best_guess", derivation=candidate["derivation"])
        review = candidate.get("review", {})
        old_manual_basis = identity([action, list(evidence.values()), working.scenarios.get(candidate["subject"])])
        old_automatic_basis = identity({"claim": assumption_claim(candidate),
            "derivation": candidate.get("derivation"),
            "evidence": sorted(identity(row) for row in evidence.values()),
            **candidate_review_scope(candidate, working)})
        reusable = (review.get("completed", True) and review.get("verdict") != "unassessed" and (
            review.get("assessment_basis_version") == basis_version
            or (automatic and review.get("assessment_basis_version") == old_automatic_basis)
            or (not automatic and candidate.get("assessment_basis_version") == old_manual_basis)))
        if reusable:
            if (review.get("completed") is not True or review.get("assessment_basis_version") != basis_version
                    or "assessment_basis_version" in candidate):
                retained = {**candidate, "review": {**review, "completed": True,
                    "assessment_basis_version": basis_version}}
                retained.pop("assessment_basis_version", None)
                retained.pop("version", None)
                retained["version"] = identity(retained)
                working.merge(ResearchResult(assumptions=(retained,)))
                updates.append(retained)
            continue
        try:
            reviewed = assess_assumption(agent, {**action, "evidence": list(evidence)}, working,
                context, source_candidate_key=key if automatic else None)
            assessment = reviewed.assumptions[0]
            assessment["review"] = {**assessment["review"], "completed": True,
                                    "assessment_basis_version": basis_version}
            assessment.pop("assessment_basis_version", None)
            assessment.pop("version", None)
            assessment["version"] = identity(assessment)
            working.merge(reviewed)
            updates.extend(reviewed.assumptions)
            facts.extend(reviewed.facts)
        except (ProviderError, ValueError, TypeError, KeyError, OSError) as exc:
            reviewed = on_failure(exc, stage)
            reviewed = replace(reviewed, diagnostics=tuple({**row, "subject": candidate["subject"],
                "field": candidate["field"], "assumption_key": key,
                "hypothesis_available": True} for row in reviewed.diagnostics))
        findings.extend(reviewed.findings)
        diagnostics.extend(reviewed.diagnostics)
    return ResearchResult(facts=tuple(facts), assumptions=tuple(updates), findings=tuple(findings),
                          diagnostics=tuple(diagnostics))


def assess_selected_source_candidates(agent, ledger, facts, conditions, subject, context, on_failure):
    """Use the common review cache for the actual selected premises of any origin."""
    from .tools import support_for

    selected, _, _ = support_for(ledger, facts, conditions, subject)
    keys = [key for key, row in selected.items()
            if row.get("entry_type") in {"best_guess", "source_candidate"}
            or row.get("review", {}).get("assessment_basis_version")]
    return assess_registered_candidates(agent, ledger, keys, context, on_failure,
                                         stage="selected_input_reasonableness_assessment")


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
                    "source_evidence": [f.semantic_record() for f in ledger.facts.values()
                                        if f.subject == scenario["subject"] and f.kind.startswith("source_")]
                        + [e for e in ledger.evidence.values() if e["subject"] == scenario["subject"]
                           and e.get("kind") == "source_evidence"],
                    "instruction": (
                        "Check alignment with the original request. A scenario identifies a case or "
                        "conditional experiment, not an equation, model extension or research topic. "
                        "A target receives the requested safety estimates; calibration and validation "
                        "scenarios identify distinct evidential cases. Reject topic-only scopes rather "
                        "than an observed outbreak context: a fixed target scenario set still permits "
                        "separate source-grounded calibration contexts, but no new target cases. Check "
                        "the proposed event identity against source_evidence. Reject invented events rather "
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


def scientific_credit(result, focus, *, subjects=None, outputs=None):
    """Project independent target discoveries and separately qualified computations."""
    rows = []
    subjects = (set(subjects) if subjects is not None else
                {s["subject"] for s in result.scenarios if s.get("role", "target") == "target"})
    current = {a["key"]: a for a in result.assumptions}
    from .records import Ledger
    ledger = Ledger(result)
    from .scenario_sharing import independent_groups, needed_fields
    from .calculation_steps import calculation_step_status
    from ...task_executors.scenario_metrics.dependencies import CALCULATED_PARAMETER_FIELDS
    scoped_groups = independent_groups(ledger) if any(row.get("kind") == "group"
        for row in result.scenario_parameter_relations) else ()
    found = found_parameter_progress(result, ledger=ledger)
    outputs = set(METRICS) if outputs is None else set(outputs)
    calculation_fields = set(focus).intersection(outputs | CALCULATED_PARAMETER_FIELDS)
    steps = calculation_step_status(result, sorted(outputs), subjects=subjects) if calculation_fields else {"steps": []}
    step_scores = {(row["subject"], row["field"]): row["points"] for row in steps["steps"]}
    calibration = calibration_progress(result) if CALIBRATION_PROGRESS in focus else None
    linked_targets = target_calibration_progress(result, sorted(outputs), calibration=calibration) if calibration else {}
    for field in focus:
        if field == CALIBRATION_PROGRESS:
            score = max((max(PROVISIONAL_OUTPUT_CREDIT, row["support"])
                for row in calibration["calibrations"] if row["outbreak_evidence_acquired"] and row["current"]), default=0)
            rows.append((field, "workflow:outbreak_inversion", score))
            for subject in sorted(subjects):
                alternatives = linked_targets.get(subject, {}).get("alternatives", ())
                score = max((sum(max(PROVISIONAL_OUTPUT_CREDIT, alternative["calibrated_support_by_quantity"].get(name, 0))
                                 if alternative["calibrated_inputs_by_quantity"].get(name) else 0
                                 for name in outputs) / len(outputs)
                             for alternative in alternatives if alternative["coherent"] and outputs), default=0)
                rows.append((field, "target:" + subject, score))
            continue
        if field in calculation_fields:
            rows.extend((field, subject, step_scores.get((subject, field), 0.0)) for subject in sorted(subjects))
            continue
        if field in UNITS:
            groups = [row for row in found if row["parameter"] == field
                      and set(row["subjects"]).intersection(subjects)]
            rows.extend((field, "group:" + row["group_id"], row["points"]) for row in groups)
            if not groups:
                rows.extend((field, subject, 0.0) for subject in sorted(subjects))
            continue
        if field not in outputs and field != "evidence_consistency":
            groups = [group for group in scoped_groups if group["parameter"] == field
                      and set(group["subjects"]).intersection(subjects)]
            if groups:
                for group in groups:
                    learning = parameter_support(result, (field,), hypotheses_only=True,
                                                 subjects=group["subjects"])
                    rows.append((field, "group:" + group["group_id"],
                                 learning[0]["points"] if learning else 0.0))
                continue
        for subject in sorted(subjects):
            if field == "evidence_consistency":
                # Establishing a discrepancy is learning too; a smaller residual is not credit.
                score = max((current_support(c, current, ledger=ledger) for c in result.calculations
                    if c["subject"] == subject and c["tool"] == "compare_predictions_with_observations"
                    and c["output"]["category"] != "calibration_consistency"), default=0)
            else:
                scenario = ledger.scenarios.get(subject, {})
                if (field in retained_defaults(scenario) or field in CALCULATED_PARAMETER_FIELDS
                        or (scoped_groups and field not in needed_fields(scenario))):
                    rows.append((field, subject, 0.0))
                    continue
                learning = parameter_support(result, (field,), hypotheses_only=True, subjects=(subject,))
                score = learning[0]["points"] if learning else 0.0
            rows.append((field, subject, score))
    return Credit(evaluated=result.evaluated, qualities=tuple(rows),
                  quality_resolution=PROVISIONAL_OUTPUT_CREDIT / (max(1, len(outputs)) if calibration else 1))
