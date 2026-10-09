"""Deterministic quotation/unit checks and a separate applicability review."""

from __future__ import annotations

import math
import hashlib
import re

from ...task_executors.scenario_metrics.evaluate import CONDITIONS, UNITS, validate_parameter
from ...task_executors.scenario_metrics.catalog import METRICS
from ...task_executors.unit_conversion.units import METERS_PER_FOOT, SECONDS_PER_DAY
from .records import Fact, ResearchResult, diagnostic_value, finite
from .assumptions import text as required_text


CONVERSIONS = {
    ("m3/h", "m3/s"): 1/3600, ("L/s", "m3/s"): 0.001,
    ("L/min", "m3/s"): 1/60000, ("h", "s"): 3600, ("min", "s"): 60,
    ("1/h", "1/s"): 1/3600, ("ACH", "1/s"): 1/3600,
    ("um", "m"): 1e-6, ("cm2", "m2"): 1e-4, ("mL", "m3"): 1e-6,
    ("m/h", "m/s"): 1/3600, ("cm/s", "m/s"): 0.01, ("%", "fraction"): 0.01,
    ("quanta/h", "quanta/s"): 1/3600, ("count", "person"): 1,
    ("uPa*s", "Pa*s"): 1e-6,
    ("ft", "m"): METERS_PER_FOOT, ("ft2", "m2"): METERS_PER_FOOT**2,
    ("ft3", "m3"): METERS_PER_FOOT**3, ("cfm", "m3/s"): METERS_PER_FOOT**3 / 60,
    ("cm", "m"): .01, ("mm", "m"): .001, ("cm3", "m3"): 1e-6, ("L", "m3"): .001,
    ("day", "s"): SECONDS_PER_DAY, ("1/day", "1/s"): 1 / SECONDS_PER_DAY,
    ("dimensionless", "scalar"): 1, ("dimensionless", "fraction"): 1,
    ("%", "scalar"): .01, ("um3/cm3", "fraction"): (1e-6 / .01)**3,
}


EVIDENCE_FIELDS = frozenset(UNITS) | frozenset(CONDITIONS) | frozenset(METRICS)


def extraction_response_schema(source):
    """Use the same field vocabulary as admission, with explicit JSON types."""
    text = {"type": "string", "minLength": 1}
    shared = {name: dict(text) for name in ("subject", "quote", "context", "basis")}
    shared["subject"]["description"] = "Actual source event or population, not the target unless directly applicable."
    shared["quote"]["description"] = "One exact contiguous original source span, preserving qualifiers."
    shared["context"]["description"] = "Disease, strain, population, activity and event identity."
    shared["basis"]["description"] = "What this supports, constrains or contradicts, and what it does not establish."
    facts = {**shared, "field": {"type": "string", "enum": sorted(UNITS)},
             "value": {"type": "number", "description":
                       "Finite scalar number explicitly printed in the source, not a quoted numeric string. "
                       "Do not put a range, bound, expression or null here. Preserve those in evidence instead."},
             "unit": {**text, "description": "Unit of the printed number; preserve it before conversion."},
             "kind": {"type": "string", "enum": ["request_constraint"] if source == "request" else
                      ["source_observation", "source_model_parameter"]}}
    evidence = {**shared, "claim": {**text, "description":
               "Source-supported qualitative claim, range, bound, equation or applicability condition."},
                "fields": {"type": "array", "minItems": 1,
                           "items": {"type": "string", "enum": sorted(EVIDENCE_FIELDS)}}}
    return {"type": "object", "additionalProperties": False,
            "required": ["facts", "evidence", "findings"], "properties": {
                "facts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                          "required": list(facts), "properties": facts}},
                "evidence": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                             "required": list(evidence), "properties": evidence}},
                "findings": {"type": "array", "items": {"type": "string"},
                             "description": "Limitations, contradictions and remaining information needs; not new evidence."}}}


def canonical_notation(unit):
    if isinstance(unit, str):
        unit = unit.strip().replace("\u2212", "-")
        power = re.fullmatch(r"(m|cm|ft)\s*\^?\s*([23\u00b2\u00b3])", unit)
        if power:
            return power[1] + power[2].translate(str.maketrans("\u00b2\u00b3", "23"))
        inverse = re.fullmatch(r"(h|s|day)\s*(?:\^\s*)?-\s*1", unit)
        if inverse:
            return "1/" + inverse[1]
        parts = unit.split("/")
        if len(parts) == 2 and all(part.strip() for part in parts):
            unit = "/".join("1" if part.strip() == "1" else canonical_notation(part) for part in parts)
    if isinstance(unit, str) and re.fullmatch(r"[u\u03bc\u00b5]\s*Pa\s*[*\u00b7]\s*s", unit):
        return "uPa*s"
    if isinstance(unit, str) and (re.fullmatch(r"\([u\u03bc\u00b5]m/cm\)(?:\^?3|\u00b3)", unit)
                                 or re.fullmatch(r"[u\u03bc\u00b5]m(?:\^?3|\u00b3)/cm(?:\^?3|\u00b3)", unit)):
        return "um3/cm3"
    aliases = {"quanta/m^3": "quanta/m3", "quanta/m\u00b3": "quanta/m3",
               "infection quanta/m3 exhaled air": "quanta/m3",
               "q/m3": "quanta/m3", "q/m^3": "quanta/m3", "q/m\u00b3": "quanta/m3",
               "q/h": "quanta/h", "q/s": "quanta/s",
               "people": "person", "persons": "person",
               "unitless": "dimensionless", "1": "dimensionless",
               "foot": "ft", "feet": "ft", "ft^2": "ft2", "ft\u00b2": "ft2",
               "ft^3": "ft3", "ft\u00b3": "ft3", "ft3/min": "cfm", "ft^3/min": "cfm",
               "m^3": "m3", "m\u00b3": "m3", "cm^3": "cm3", "cm\u00b3": "cm3",
               "cm^2": "cm2", "m\u00b2/s": "m2/s", "m^2/s": "m2/s",
               "days": "day", "d": "day", "/day": "1/day", "day-1": "1/day", "day^-1": "1/day",
               "quanta m^-3": "quanta/m3", "quanta m\u207b\u00b3": "quanta/m3",
               "m\u00b3/s": "m3/s", "m\u00b3/h": "m3/h", "m^3/s": "m3/s", "m^3/h": "m3/h",
               "m\u00b2": "m2", "cm\u00b2": "cm2", "\u03bcm": "um", "\u00b5m": "um",
               "h^-1": "1/h", "h-1": "1/h", "h\u207b\u00b9": "1/h", "/h": "1/h",
               "s^-1": "1/s", "s-1": "1/s"}
    return aliases.get(unit, unit)


def exact_span(quote, source):
    if isinstance(quote, str) and quote.strip() and quote not in source:
        match = re.search(r"\s+".join(re.escape(token) for token in quote.split()), source)
        if match:
            quote = match.group(0)
    if not isinstance(quote, str) or not quote.strip() or quote not in source:
        raise ValueError("Evidence quote is not an exact source span")
    return quote


def extract_and_admit(agent, *, text, source, focus, objective, context, question, feedback=(), source_spans=None,
                      source_version=None):
    spans = source_spans or {"current": text}
    source_version = source_version or hashlib.sha256(text.encode()).hexdigest()

    def quote_span(quote):
        for span in spans.values():
            try:
                return exact_span(quote, span)
            except ValueError:
                pass
        raise ValueError("Evidence quote is not an exact source span")
    response = agent({
        "operation": "extract_research_evidence", "objective": objective,
        "question": question, "focus": list(focus), "context": context,
        "previous_attempt_findings": list(feedback),
        "canonical_units": UNITS, "model_conditions": CONDITIONS, "source": source, "source_text": text,
        "response_contract": extraction_response_schema(source),
        "instruction": (
            "Return an instance of response_contract, which is a JSON Schema, not an output template. "
            "Numeric facts require finite JSON numbers, never strings. Put reported ranges, inequalities "
            "and equations in evidence with their exact quotes and qualifiers. If OCR or flattened "
            "typesetting makes a number ambiguous, retain the expression as qualitative evidence and "
            "explain the ambiguity instead of silently repairing it. Never choose a midpoint "
            "or endpoint to manufacture a scalar. Evidence can concern declared parameters, conditions "
            "or calculated outputs, but a quoted equation or range is not itself a computed output or "
            "supported target assumption. Use empty arrays when nothing qualifies. For source=request, "
            "only explicit requester-defined conditions are evidence; requested unknown answers and "
            "workflow requirements are not scientific evidence."
        ),
    })
    candidates, issues, diagnostics = [], [], []
    rows = response.get("facts", [])
    if not isinstance(rows, list):
        raise ValueError("Extraction facts must be a list")
    for raw in rows:
        try:
            field = raw["field"]
            if field not in UNITS:
                raise ValueError("Unknown field")
            quote = quote_span(raw["quote"])
            unit = UNITS[field]
            if not isinstance(raw["value"], (int, float)) or isinstance(raw["value"], bool):
                raise ValueError(f"{field} must be a finite JSON number, not {type(raw['value']).__name__}; "
                                 "preserve ranges, bounds and expressions in qualitative evidence")
            value = finite(raw["value"], field)
            printed_numbers = re.findall(r"(?<![\w.])[-+]?(?:\d[\d,]*(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", quote)
            if not any(math.isclose(value, float(n.replace(",", "")), rel_tol=1e-12, abs_tol=0)
                       for n in printed_numbers):
                raise ValueError("The proposed printed number does not occur in the evidence quote")
            printed_unit = canonical_notation(raw["unit"])
            factor = 1 if printed_unit == unit else CONVERSIONS.get((printed_unit, unit))
            if factor is None:
                raise ValueError(f"Unsupported unit conversion from {raw['unit']!r} to {unit!r}")
            value *= factor
            validate_parameter(field, value, unit)
            kinds = {"request_constraint"} if source == "request" else {"source_observation", "source_model_parameter"}
            if raw["kind"] not in kinds:
                raise ValueError("An extraction cannot create an assumed or derived fact")
            fact = Fact(raw["subject"], field, value, unit, raw["kind"], raw["basis"],
                        source, quote, raw["context"], source_version=source_version)
            candidates.append((raw, fact))
        except (KeyError, TypeError, ValueError) as exc:
            field = raw.get("field", "unknown") if isinstance(raw, dict) else "unknown"
            issues.append(f"Rejected extraction of {field}: {exc}")
            diagnostics.append({"stage": "extraction", "category": "invalid_candidate", "source": source,
                                "field": field, "why": str(exc), "proposal": raw})
    qualitative = response.get("evidence", [])
    if not isinstance(qualitative, list):
        raise ValueError("Qualitative evidence must be a list")
    for raw in qualitative:
        try:
            item = {name: required_text(raw[name], name) for name in ("subject", "claim", "context", "basis")}
            fields = raw.get("fields")
            if not isinstance(fields, list) or not fields:
                raise ValueError("Qualitative evidence requires a nonempty list of declared parameter, condition or output names")
            invalid = [f for f in fields if not isinstance(f, str) or f not in EVIDENCE_FIELDS]
            if invalid:
                raise ValueError(f"Unknown evidence fields {invalid!r}; use names declared in response_contract")
            item["fields"] = list(dict.fromkeys(fields))
            item.update(source=source, quote=quote_span(raw["quote"]),
                        source_version=source_version,
                        kind="request_constraint" if source == "request" else "source_evidence")
            candidates.append((raw, item))
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"Rejected qualitative evidence: {exc}")
            diagnostics.append({"stage": "extraction", "category": "invalid_candidate", "source": source,
                                "why": str(exc), "proposal": raw})
    admitted, evidence = [], []
    if candidates:
        review = agent({
            "operation": "review_research_evidence", "objective": objective,
            "context": context, "source": source, "source_text": text,
            "available_source_spans": spans,
            "candidates": [{"option": i, "raw": raw, "normalized": fact.semantic_record() if isinstance(fact, Fact) else fact,
                            **({"unit_conversion": {"printed_value": raw["value"], "printed_unit": raw["unit"],
                                "canonical_unit": fact.unit,
                                "factor": 1 if canonical_notation(raw["unit"]) == fact.unit else
                                          CONVERSIONS[(canonical_notation(raw["unit"]), fact.unit)]}}
                               if isinstance(fact, Fact) else {})}
                           for i, (raw, fact) in enumerate(candidates)],
            "instruction": (
                "Independently verify each numerical value and unit against its quote and source. "
                "The raw candidate records the printed number and unit; normalized records use canonical "
                "units after the explicit unit_conversion. Check that conversion rather than requiring "
                "the canonical number to occur verbatim in the source. Raw basis text refers to the "
                "printed representation, not a claim that normalization did not happen. "
                "Check event identity, disease/strain/population/activity, whether it is observation, "
                "a fitted parameter or a hypothetical scenario. Reject incompatible assignment to the "
                "target, ventilation mistaken for total loss, RNA copies mistaken for quanta, and "
                "unsupported extrapolation. A quote match alone does not establish applicability."
                " Qualitative claims must be entailed by the quoted passage. For source=request, admit "
                "only conditions the requester explicitly defines, not scientific answers they ask you to discover."
            ),
            "response_contract": {"type": "object", "additionalProperties": False,
                "required": ["decisions"], "properties": {
                    "decisions": {"type": "array", "minItems": len(candidates), "maxItems": len(candidates),
                        "description": "Exactly one independent decision for each candidate option, without repeats",
                        "items": {"type": "object", "additionalProperties": False,
                            "required": ["option", "admit", "reason"], "properties": {
                                "option": {"type": "integer", "enum": list(range(len(candidates)))},
                                "admit": {"type": "boolean"},
                                "reason": {"type": "string", "minLength": 1}}}}}},
        })
        decisions = review.get("decisions")
        if not isinstance(decisions, list) or len(decisions) != len(candidates):
            raise ValueError("Applicability review must decide every candidate")
        seen = set()
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ValueError("Each evidence review decision must be an object")
            index = decision.get("option")
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(candidates) or index in seen:
                raise ValueError("Invalid or repeated review option")
            seen.add(index)
            if type(decision.get("admit")) is not bool or not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
                raise ValueError("Review requires boolean admit and a reason")
            if decision["admit"]:
                item = candidates[index][1]
                if isinstance(item, Fact):
                    admitted.append(item)
                else:
                    evidence.append(item)
            else:
                item = candidates[index][1]
                field = item.field if isinstance(item, Fact) else item["claim"]
                issues.append(f"Applicability rejected {field}: {decision['reason']}")
                diagnostics.append({"stage": "applicability_review", "category": "rejected_evidence",
                                    "source": source, "claim": field, "why": decision["reason"],
                                    "proposal": candidates[index][0]})
    findings = response.get("findings", [])
    if not isinstance(findings, list) or any(not isinstance(v, str) for v in findings):
        raise ValueError("Findings must be a list of text")
    if not rows and not qualitative:
        diagnostics.append({"stage": "extraction", "category": "no_relevant_evidence", "source": source,
                            "why": "The reading returned no relevant evidence", "findings": findings})
    return ResearchResult(tuple(admitted), findings=tuple(findings), issues=tuple(issues),
                          evidence=tuple(evidence), diagnostics=tuple(diagnostic_value(d) for d in diagnostics),
                          evaluated=not (rows or qualitative) or bool(candidates))
