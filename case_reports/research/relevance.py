"""Source-event grouping and target-relative acquisition credit."""

from collections import defaultdict
from collections.abc import Mapping

from .progress import ADDITIONAL_SUPPORT, evidence_key, parameter_support
from .records import Credit, ResearchResult, identity


RELEVANCE_LEVELS = (0, 0.25, 0.5, 0.75, 1)
CONTEXT_VARIABLES = ("disease_context", "respiratory_activity", "population", "physical_setting")
RELATIONS = ("match", "partial", "mismatch", "unknown", "not_applicable")
TARGET_RELEVANCE_CREDIT_MEANING = (
    "Evidence-filled inputs earn up to one point each within a related source-event type, plus 0.1 "
    "for distinct corroboration of the same source-event subject. Each field uses its strongest current "
    "event-to-target relevance and comparison coverage; only the strongest type contributes for that target. "
    "Original observations retain their event identity. This is learning credit, not "
    "permission to transfer a numeric value without a reviewed assumption."
)


def source_profiles(result, requirements):
    profiles = defaultdict(lambda: {"contexts": set(), "fields": set(), "kinds": set(), "facts": []})
    for fact in result.facts:
        if fact.kind not in {"source_observation", "source_model_parameter"} or fact.field not in requirements:
            continue
        row = profiles[(fact.source, fact.subject)]
        row["contexts"].add(fact.context)
        row["fields"].add(fact.field)
        row["kinds"].add(fact.kind)
        row["facts"].append({"field": fact.field, "value": fact.value, "unit": fact.unit,
                             "kind": fact.kind, "quote": fact.quote,
                             "source_version": fact.source_version})
    for evidence in result.evidence:
        if (evidence.get("kind") != "source_evidence"
                or evidence.get("evidence_role") != "observation"
                or not requirements.intersection(evidence.get("fields", ()))):
            continue
        key = (evidence.get("source"), evidence.get("subject"))
        row = profiles[key]
        row["contexts"].add(evidence.get("context", ""))
        row["fields"].update(requirements.intersection(evidence.get("fields", ())))
        row["kinds"].add("source_observation_context")
    return {key: {name: sorted(values, key=lambda item: str(item)) for name, values in row.items()}
            for key, row in profiles.items()}


def comparison_variables(profile, target):
    """Compare context plus numeric fields known on both sides of this application."""
    target_fields = set(target.get("fixed_parameters", {})) | set(target.get("recorded_hypotheses", {}))
    return (*CONTEXT_VARIABLES, *sorted(set(profile["fields"]) & target_fields))


def _plain_value(value):
    """Copy closed contract mappings into JSON-compatible assessment context."""
    if isinstance(value, Mapping):
        return {key: _plain_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain_value(item) for item in value]
    return value


def target_comparison_context(definition, assumptions):
    """Target givens and distinct recorded hypotheses, with their review states."""
    target = {name: _plain_value(definition.get(name, {} if name != "assumption_needs" else []))
              for name in ("description", "fixed_parameters", "fixed_conditions", "assumption_needs")}
    hypotheses = {}
    for assumption in assumptions:
        if (assumption.get("subject") == definition.get("subject")
                and assumption.get("role") not in {"scenario_constraint", "request_constraint"}
                and assumption.get("review", {}).get("verdict") != "contradicted"):
            row = {
                "value": assumption["value"], "unit": assumption["unit"],
                "statement": assumption["statement"],
                "review_verdict": assumption.get("review", {}).get("verdict", "unassessed")}
            hypotheses.setdefault(assumption["field"], {})[identity(row)] = row
    target["recorded_hypotheses"] = {field: [rows[key] for key in sorted(rows)]
                                      for field, rows in hypotheses.items()}
    return target


def assess_source_types_with_jev(agent, jev_assess, source, profiles, targets,
                                 known_groups, disease=None, *, parameter=None):
    """Group observed events, then score each source/target pair with a Noul."""
    subjects = sorted(subject for locator, subject in profiles if locator == source)
    if not subjects:
        return [], []
    existing = sorted(known_groups)
    response = agent({
        "operation": "classify_source_event_types",
        "source": source,
        "source_subjects": {subject: profiles[(source, subject)] for subject in subjects},
        "disease_of_interest": disease,
        "known_types": {key: {name: group[name] for name in ("description", "basis")}
                        for key, group in known_groups.items()},
        "instruction": (
            "Group source subjects by the actual exposure event or modeled source context. "
            "Keep distinct events separate; reuse a known type only for comparable disease, "
            "activity, population, and physical setting. This classifies source identity only. "
            "Target-scenario applicability is measured separately by Jev."
        ),
        "response_contract": {"type": "object", "additionalProperties": False,
            "required": ["groups"], "properties": {"groups": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["type_id", "description", "subjects", "basis"],
                "properties": {"type_id": {"type": "string", "enum": [*existing, "new"]},
                    "description": {"type": "string", "minLength": 1},
                    "subjects": {"type": "array", "minItems": 1, "uniqueItems": True,
                                 "items": {"type": "string", "enum": subjects}},
                    "basis": {"type": "string", "minLength": 1}}}}}},
    })
    groups = response.get("groups")
    if not isinstance(groups, list) or any(not isinstance(group, dict)
            or not isinstance(group.get("subjects"), list) for group in groups):
        raise ValueError("Source-event classification requires groups with subjects")
    if sorted(subject for group in groups for subject in group["subjects"]) != subjects:
        raise ValueError("Source-event groups must partition source subjects exactly")
    reused = [group.get("type_id") for group in groups if group.get("type_id") != "new"]
    if (len(set(reused)) != len(reused)
            or any(group.get("type_id") not in {*existing, "new"}
                   or not isinstance(group.get("description"), str) or not group["description"].strip()
                   or not isinstance(group.get("basis"), str) or not group["basis"].strip()
                   for group in groups)):
        raise ValueError("Source-event classification has an invalid type or basis")

    relationships = []
    scores = {}
    for subject in subjects:
        profile = profiles[(source, subject)]
        probabilities = jev_assess({"source": source, "source_subject": subject,
            "source_profile": profile, "target_scenarios": targets,
            "disease_of_interest": disease, "parameter": parameter})
        if not isinstance(probabilities, Mapping) or set(probabilities) != set(targets):
            raise ValueError("Jev source-target assessment must cover selected targets")
        for target_subject, target in targets.items():
            probability = probabilities[target_subject]
            if (isinstance(probability, bool) or not isinstance(probability, (int, float))
                    or not 0 <= probability <= 1):
                raise ValueError("Jev source-target probability must be between zero and one")
            score = float(probability)
            scores[(subject, target_subject)] = score
            relationships.append({"source": source, "source_subject": subject,
                "target_subject": target_subject, "parameter": parameter,
                "target_version": identity(target),
                "source_profile_version": identity(profile),
                "score": score, "jev_probability": score,
                "assessment_method": "jev_noul",
                "basis": "Jev Noul probability that this source event is applicable to this selected target for the assigned parameter.",
                "source_role": sorted(profile["kinds"]),
                "source_contexts": list(profile["contexts"]),
                "target_description": target.get("description", ""),
                "target_fixed_conditions": target.get("fixed_conditions", {}),
                "comparisons": [{"field": "source_target_applicability",
                    "relation": "jev_noul", "basis": "Source and target contexts were submitted together as one Noul question.",
                    "source_values": profile["facts"],
                    "target_value": {"fixed_parameters": target.get("fixed_parameters", {}),
                        "fixed_conditions": target.get("fixed_conditions", {}),
                        "recorded_hypotheses": target.get("recorded_hypotheses", {})}}],
                "known": 1, "considered": 1})
    return [{**group, "target_relevance": {target: max(scores[(subject, target)]
            for subject in group["subjects"]) for target in targets}} for group in groups], relationships


def assess_source_types(agent, source, profiles, targets, known_groups, disease=None, *, parameter=None):
    """Classify one source's observed subjects against reusable event types."""
    subjects = sorted(subject for locator, subject in profiles if locator == source)
    if not subjects:
        return []
    existing = sorted(known_groups)
    expected = {(subject, target) for subject in subjects for target in targets}
    variables = {(subject, target): comparison_variables(profiles[(source, subject)], targets[target])
                 for subject, target in expected}
    response = agent({
        "operation": "assess_source_event_types",
        "source": source,
        "source_subjects": {subject: profiles[(source, subject)] for subject in subjects},
        "target_scenarios": targets,
        "disease_of_interest": disease,
        "assigned_parameter": parameter,
        "comparison_variables": {subject: {target: list(variables[(subject, target)]) for target in targets}
                                 for subject in subjects},
        "known_types": {key: {name: group[name] for name in ("description", "target_relevance", "basis")}
                        for key, group in known_groups.items()},
        "instruction": (
            "Group the supplied source subjects by the kind of exposure event or modeled source context, "
            "reusing a known type only when its disease context, activity, population and physical setting are comparable. "
            "The same actual event may have several source subject labels; retain their separate records. "
            "Do not merge distinct events into one observation or treat a model sensitivity case as a measured outbreak. "
            "For each type, assess how relevant its context is to each target scenario. Also assess "
            "each actual source subject against every target for the assigned parameter. For each "
            "pair, compare exactly its declared comparison_variables. Use match, partial, mismatch, "
            "unknown or not_applicable and explain each comparison from the supplied source and "
            "target context. Unknown is not a mismatch. Do not invent values or treat target inputs "
            "as source observations. Source facts, target givens, and recorded target hypotheses "
            "with review status are supplied separately. "
            "Relevance is a multiplier for learning from these sources, not a claim of scientific confidence "
            "or permission to copy numerical values. Use 0 for unrelated contexts, 0.25 for a remote analogy, "
            "0.5 for a related mechanism with major transfer differences, 0.75 for a close but qualified match, "
            "and 1 only for a directly matching context. A related type remains available even at low relevance; "
            "an explicit, reviewed transfer is still needed before target calculations use its values. "
            "Return every supplied subject exactly once in a group and every source-subject/target "
            "pair exactly once in relationships."
        ),
        "response_contract": {"type": "object", "additionalProperties": False,
            "required": ["groups", "relationships"], "properties": {"groups": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["type_id", "description", "subjects", "target_relevance", "basis"],
                "properties": {
                    "type_id": {"type": "string", "enum": [*existing, "new"]},
                    "description": {"type": "string", "minLength": 1},
                    "subjects": {"type": "array", "minItems": 1, "uniqueItems": True,
                                 "items": {"type": "string", "enum": subjects}},
                    "target_relevance": {"type": "object", "additionalProperties": False,
                        "required": list(targets), "properties": {
                            target: {"type": "number", "enum": list(RELEVANCE_LEVELS)} for target in targets}},
                    "basis": {"type": "string", "minLength": 1},
                }}}, "relationships": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["source_subject", "target_subject", "score", "basis", "comparisons"],
                    "properties": {
                        "source_subject": {"type": "string", "enum": subjects},
                        "target_subject": {"type": "string", "enum": list(targets)},
                        "score": {"type": "number", "enum": list(RELEVANCE_LEVELS)},
                        "basis": {"type": "string", "minLength": 1},
                        "comparisons": {"type": "array", "items": {"type": "object",
                            "additionalProperties": False, "required": ["field", "relation", "basis"],
                            "properties": {"field": {"type": "string"},
                                           "relation": {"type": "string", "enum": list(RELATIONS)},
                                           "basis": {"type": "string", "minLength": 1}}}},
                    }} }},
            },
    })
    groups = response.get("groups")
    if not isinstance(groups, list):
        raise ValueError("Source-event assessment requires groups")
    if any(not isinstance(group, dict) or not isinstance(group.get("subjects"), list)
           for group in groups):
        raise ValueError("Source-event groups must contain subject lists")
    assigned = [subject for group in groups for subject in group["subjects"]]
    if sorted(assigned) != subjects:
        raise ValueError("Source-event groups must partition the source subjects exactly")
    reused = [group["type_id"] for group in groups if group.get("type_id") != "new"]
    if len(set(reused)) != len(reused):
        raise ValueError("A known source-event type may appear only once per assessment")
    for group in groups:
        if group.get("type_id") not in {*existing, "new"}:
            raise ValueError("Source-event group references an unknown type")
        if not isinstance(group.get("description"), str) or not group["description"].strip():
            raise ValueError("Source-event type requires a description")
        if not isinstance(group.get("basis"), str) or not group["basis"].strip():
            raise ValueError("Source-event relevance requires a basis")
        relevance = group.get("target_relevance")
        if not isinstance(relevance, dict) or set(relevance) != set(targets):
            raise ValueError("Source-event relevance must cover every selected target")
        if any(type(value) not in (int, float) or value not in RELEVANCE_LEVELS
               for value in relevance.values()):
            raise ValueError("Source-event relevance must use a declared multiplier")
    relationships = response.get("relationships")
    if not isinstance(relationships, list) or len(relationships) != len(expected):
        raise ValueError("Source-event relationships must cover every source/target pair")
    seen = set()
    admitted = []
    for row in relationships:
        if not isinstance(row, dict):
            raise ValueError("Source-event relationship must be an object")
        key = (row.get("source_subject"), row.get("target_subject"))
        if key not in expected or key in seen:
            raise ValueError("Source-event relationships must be unique declared pairs")
        seen.add(key)
        if type(row.get("score")) not in (int, float) or row["score"] not in RELEVANCE_LEVELS:
            raise ValueError("Source-event relationship score must use a declared level")
        if not isinstance(row.get("basis"), str) or not row["basis"].strip():
            raise ValueError("Source-event relationship needs a basis")
        comparisons = row.get("comparisons")
        if not isinstance(comparisons, list) or {item.get("field") for item in comparisons
                if isinstance(item, dict)} != set(variables[key]) or len(comparisons) != len(variables[key]):
            raise ValueError("Source-event comparisons must cover the declared variables exactly")
        enriched = []
        profile = profiles[(source, key[0])]
        target = targets[key[1]]
        for item in comparisons:
            if (not isinstance(item, dict) or item.get("relation") not in RELATIONS
                    or not isinstance(item.get("basis"), str) or not item["basis"].strip()):
                raise ValueError("Source-event comparison needs a relation and basis")
            field = item["field"]
            source_values = [{k: fact[k] for k in ("value", "unit", "kind", "quote", "source_version")}
                             for fact in profile["facts"] if fact["field"] == field]
            target_value = (target.get("fixed_parameters", {}).get(field)
                            or target.get("recorded_hypotheses", {}).get(field))
            enriched.append({**item, "source_values": source_values,
                             "target_value": target_value})
        considered = sum(item["relation"] != "not_applicable" for item in enriched)
        known = sum(item["relation"] in {"match", "partial", "mismatch"} for item in enriched)
        admitted.append({"source": source, "source_subject": key[0], "target_subject": key[1],
                         "parameter": parameter, "target_version": identity(target),
                         "source_profile_version": identity(profile),
                         "score": row["score"], "basis": row["basis"],
                         "source_role": sorted(profile["kinds"]),
                         "source_contexts": list(profile["contexts"]),
                         "target_description": target.get("description", ""),
                         "target_fixed_conditions": target.get("fixed_conditions", {}),
                         "comparisons": enriched,
                         "known": known, "considered": considered})
    return groups, admitted


def target_relevance_credit(result, requirements, groups, targets, *, parameter=None):
    """Credit the strongest related event type per target, never a field pool across types."""
    assessments = []
    invalid = {evidence_key(evidence) for assessment in result.assumptions
               for evidence in assessment.get("invalidated_evidence", ())}
    relationships = {(row["source"], row["source_subject"], row["target_subject"], row["parameter"]): row
                     for row in result.source_target_relationships}
    profiles = source_profiles(result, requirements) if relationships else {}
    for target in targets:
        choices = []
        for type_id, group in groups.items():
            if not group["members"]:
                continue
            members = {tuple(member) for member in group["members"]}
            assessed_members = [relationships[(source, subject, target, parameter)] for source, subject in members
                                if (source, subject, target, parameter) in relationships]
            if assessed_members:
                target_context = target_comparison_context({**targets[target], "subject": target}, result.assumptions)
                field_points = {}
                multipliers = []
                for source, subject in members:
                    relation = relationships.get((source, subject, target, parameter))
                    profile = profiles.get((source, subject))
                    if (relation is None or profile is None
                            or relation.get("target_version") != identity(target_context)
                            or relation.get("source_profile_version") != identity(profile)):
                        continue
                    multiplier = relation["score"] * (relation["known"] / relation["considered"]
                                                      if relation["considered"] else 0)
                    multipliers.append(multiplier)
                    facts = tuple(fact for fact in result.facts if (fact.source, fact.subject) == (source, subject)
                                  and evidence_key(fact.semantic_record()) not in invalid)
                    for row in parameter_support(ResearchResult(facts=facts), requirements):
                        field_points[row["field"]] = max(field_points.get(row["field"], 0),
                                                         multiplier * row["points"])
                rows = [{"field": field, "points": round(value, 10)} for field, value in sorted(field_points.items())]
                multiplier = max(multipliers, default=0)
                points = round(sum(field_points.values()), 10)
            else:
                facts = tuple(fact for fact in result.facts if (fact.source, fact.subject) in members
                              and evidence_key(fact.semantic_record()) not in invalid)
                rows = parameter_support(ResearchResult(facts=facts), requirements)
                multiplier = group["target_relevance"].get(target, 0)
                points = round(multiplier * sum(row["points"] for row in rows), 10)
                rows = [{"field": row["field"], "points": round(multiplier * row["points"], 10)}
                        for row in rows]
            choices.append({"target": target, "type_id": type_id,
                            "description": group["description"], "relevance": multiplier,
                            "points": points,
                            "fields": rows,
                            "member_count": len(group["members"]),
                            "basis": group["basis"]})
        if choices:
            assessments.append(max(choices, key=lambda row: (row["points"], row["relevance"])))
    credit = Credit(evaluated=result.evaluated, quality_resolution=ADDITIONAL_SUPPORT / 4,
                    qualities=tuple(("parameter_evidence", row["target"], row["points"])
                                    for row in assessments))
    return assessments, credit
