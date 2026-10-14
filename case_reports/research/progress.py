"""Fixed parameter-evidence credit, independent of generated search objectives."""

from urllib.parse import urlsplit, urlunsplit

from ...task_executors.scenario_metrics.dependencies import input_fields
from ...task_executors.scenario_metrics.evaluate import CONDITIONS, UNITS
from .modeling import DERIVATIONS, derivation_inputs
from .records import Credit, identity


PARAMETER_EVIDENCE = "parameter_evidence"
ADDITIONAL_SUPPORT = 0.1


def parameter_requirements(parameter):
    """Use executable dependencies, never a search-generated checklist."""
    if parameter not in UNITS and parameter not in CONDITIONS:
        raise ValueError("Investigation parameter must be a declared calculation input")
    names = {parameter}
    if parameter == "quanta_concentration_exhaled_m3":
        for operator in DERIVATIONS:
            if operator != "transfer_parameter":
                names.update(derivation_inputs(operator, {}))
                names.update(derivation_inputs(operator, {"attack_probability": 0}))
    return frozenset(input_fields(names, parameters=UNITS) & (UNITS.keys() | CONDITIONS.keys()))


def _source(record):
    source, quote = record.get("source", ""), record.get("quote", "")
    if not source or not quote or source == "request":
        return None
    if record.get("kind") not in {"source_observation", "source_model_parameter", "source_evidence"}:
        return None
    parts = urlsplit(source)
    locator = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
    return locator, " ".join(quote.split())


def evidence_key(record):
    return identity({k: record.get(k) for k in (
        "subject", "field", "fields", "value", "unit", "kind", "source", "quote")})


def _distinct_sources(records):
    grouped = {}
    for record in records:
        support = _source(record)
        if support:
            source, quote = support
            grouped.setdefault(source, set()).add(quote)
    sources, seen_quotes = [], set()
    for source, quotes in grouped.items():
        if not seen_quotes.intersection(quotes):
            sources.append(source)
        seen_quotes.update(quotes)
    return sources


def parameter_support(result, requirements, *, hypotheses_only=False, subjects=()):
    """Count filled elements, retaining alternatives rather than selecting a value."""
    values = {field: {} for field in requirements}
    learning = {field: {} for field in requirements}
    invalid = {evidence_key(record) for assessment in result.assumptions
               for record in assessment.get("invalidated_evidence", ())}

    def add(field, subject, value, unit, records, *, relation="supports", reviewed=False):
        if field not in values:
            return
        key = identity([subject, field, value, unit])
        bucket = values[field].setdefault(key, {"subject": subject, "value": value,
            "unit": unit, "supports": [], "contradicts": []})
        for record in records:
            if evidence_key(record) not in invalid and _source(record):
                bucket[relation].append(record)
                if reviewed:
                    learning[field].setdefault(subject, []).append(record)

    if not hypotheses_only:
        for fact in result.facts:
            if fact.kind in {"source_observation", "source_model_parameter"}:
                add(fact.field, fact.subject, fact.value, fact.unit, (fact.semantic_record(),), reviewed=True)
    for assessment in result.assumptions:
        if subjects and assessment["subject"] not in subjects:
            continue
        if assessment.get("role") == "request_constraint":
            continue
        for row in assessment.get("learning_evidence", ()):
            add(assessment["field"], assessment["subject"],
                assessment["value"] if assessment["value"] is not None else assessment["statement"],
                assessment["unit"], (row["evidence"],), relation=row["relation"], reviewed=True)

    rows = []
    for field, candidates in sorted(values.items()):
        alternatives, corroboration = [], set()
        for key, candidate in sorted(candidates.items()):
            sources = _distinct_sources(candidate["supports"])
            contrary = _distinct_sources(candidate["contradicts"])
            if not sources and not contrary:
                continue
            alternatives.append({"subject": candidate["subject"], "value": candidate["value"],
                                 "unit": candidate["unit"], "supporting_sources": sources,
                                 "contradicting_sources": contrary})
        for records in learning[field].values():
            corroboration.update(_distinct_sources(records)[1:])
        if any(row["supporting_sources"] for row in alternatives):
            rows.append({"field": field, "alternatives": alternatives,
                         "points": round(1 + ADDITIONAL_SUPPORT * len(corroboration), 10)})
    return rows


def progress_credit(rows, *, evaluated):
    return Credit(evaluated=evaluated, quality_resolution=ADDITIONAL_SUPPORT,
                  qualities=tuple((PARAMETER_EVIDENCE, row["field"], row["points"]) for row in rows))
