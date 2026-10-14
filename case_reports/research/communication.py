"""Processed decision context, with the full evidence and failures left in audit."""

from .records import condensed_diagnostics


def merged_ranges(ranges):
    result = []
    for start, end in sorted(ranges):
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def reading_coverage(attempts):
    """Execution coverage, not evidence of absence or a scientific judgment."""
    groups = {}
    for attempt in attempts:
        key = (attempt["source"], attempt["source_version"])
        group = groups.setdefault(key, {
            "source": key[0], "source_version": key[1], "document_characters": attempt["document_characters"],
            "attempts": 0, "outcomes": {}, "examined_ranges": [], "reviewed_ranges": [], "questions": []})
        group["attempts"] += 1
        status = attempt["status"]
        group["outcomes"][status] = group["outcomes"].get(status, 0) + 1
        if status != "not_started":
            group["examined_ranges"].extend(attempt["ranges"])
        if status == "completed":
            group["reviewed_ranges"].extend(attempt["ranges"])
        if attempt["question"] not in group["questions"]:
            group["questions"].append(attempt["question"])
    for group in groups.values():
        for name in ("examined_ranges", "reviewed_ranges"):
            group[name] = merged_ranges(group[name])
        unread, position = [], 0
        for start, end in group["examined_ranges"]:
            if position < start:
                unread.append([position, start])
            position = end
        if position < group["document_characters"]:
            unread.append([position, group["document_characters"]])
        group["unexamined_ranges"] = unread
        group["interpretation"] = (
            "Half-open character offsets in this source version. Examined means supplied to an extraction attempt; "
            "reviewed means extraction/admission completed, not that every claim was accepted or the question resolved. "
            "Different questions may need rereading. Unexamined text cannot support an absence claim.")
    return list(groups.values())


def summary_schema(diagnostics):
    prose = {"type": "string", "minLength": 1}
    texts = {"type": "array", "items": prose}
    return {"type": "object", "additionalProperties": False,
        "required": ["findings", "uncertainties", "failures"], "properties": {
            "findings": {**texts, "description": "Condensed conclusions, their evidential basis and affected invoking-parent quantities; not a source inventory, copied table, or the root's entire task repeated at every scope."},
            "uncertainties": {**texts, "description": "Current scientific uncertainty only. Distinguish evidence gaps, missing scenario inputs, applicability and kernel fidelity; name affected quantities."},
            "failures": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["references", "meaning", "not_established"], "properties": {
                    "references": {"type": "array", "minItems": 1, "uniqueItems": True,
                        "items": {"type": "string", "enum": list(diagnostics)} if diagnostics else False},
                    "meaning": {**prose, "description": "What this failure or rejection reveals for the parent's decision, with known cause distinguished from speculation."},
                    "not_established": {**prose, "description": "Limits of the inference: what was not learned; failed retrieval is not scientific disproof."}}}}}}


def validate_summary(value, diagnostics):
    if not isinstance(value, dict) or set(value) != {"findings", "uncertainties", "failures"}:
        raise ValueError("Decision summary requires findings, uncertainties and failures")
    for name in ("findings", "uncertainties"):
        if not isinstance(value[name], list) or any(not isinstance(v, str) or not v.strip() for v in value[name]):
            raise ValueError("Decision summary requires nonempty text lists")
    if not isinstance(value["failures"], list):
        raise ValueError("Failure implications must be a list")
    failures = []
    covered = set()
    for item in value["failures"]:
        if not isinstance(item, dict) or set(item) != {"references", "meaning", "not_established"}:
            raise ValueError("Failure implications require references, meaning and inference limits")
        refs = item["references"]
        if (not isinstance(refs, list) or not refs or any(not isinstance(k, str) or k not in diagnostics for k in refs)
                or len(set(refs)) != len(refs)):
            raise ValueError("Failure implication must reference supplied diagnostics")
        for name in ("meaning", "not_established"):
            if not isinstance(item[name], str) or not item[name].strip():
                raise ValueError("Failure implications require an explanation and inference limits")
        covered.update(refs)
        failures.append({"meaning": item["meaning"], "not_established": item["not_established"],
                         "basis": [{k: v for k, v in diagnostics[ref].items()
                                    if k in {"stage", "category", "source", "subject", "field", "candidate", "received_fields",
                                             "requested_fields", "question", "query", "assessment_state", "extraction_state",
                                             "why", "completion"}}
                                   for ref in dict.fromkeys(refs)]})
    return {**value, "failures": failures}


def diagnostic_options(diagnostics, retained=()):
    # Carry the original small records, not nested summaries of summaries.
    records = [*diagnostics, *(record for failure in retained for record in failure["basis"])]
    unique = []
    for record in records:
        if record not in unique:
            unique.append(record)
    return {f"failure:{i}": record for i, record in enumerate(condensed_diagnostics(unique), 1)}


def decision_diagnostics(diagnostics):
    return (d for d in diagnostics if not (
        d.get("stage") == "assumption_assessment" and d.get("category") in {"supported", "provisional"}))


def compact_assumption(assessment):
    return {k: assessment[k] for k in ("subject", "field", "value", "statement", "reasonableness")}
