"""Closed scientific records; source evidence is distinct from model choices."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
import hashlib
import json
import math
from typing import Any, Mapping

from ...method_loop import ClosedRecord


def identity(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def diagnostic_value(value):
    """Retain malformed provider proposals without emitting invalid audit JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, Mapping):
        return {str(k): diagnostic_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [diagnostic_value(v) for v in value]
    return value


def condensed_diagnostics(diagnostics):
    """Describe failure patterns without replaying rejected prose as context."""
    groups = {}
    for diagnostic in diagnostics:
        summary = {k: v for k, v in diagnostic.items()
                   if k not in {"proposal", "diagnostic_id", "model_call"}}
        proposal = diagnostic.get("proposal")
        if isinstance(proposal, Mapping):
            summary["received_fields"] = sorted(proposal)
            summary["candidate"] = {k: proposal[k] for k in ("subject", "field", "value", "unit", "kind")
                                    if k in proposal}
        key = identity(summary)
        if key not in groups:
            groups[key] = {**summary, "retained_records": 0, "model_calls": []}
        groups[key]["retained_records"] += 1
        if "model_call" in diagnostic and diagnostic["model_call"] not in groups[key]["model_calls"]:
            groups[key]["model_calls"].append(diagnostic["model_call"])
    return list(groups.values())


def cited_assessment_evidence(assessment):
    """Distinguish the judgment's cited basis from all material it considered."""
    references = {key for criterion in assessment["review"]["criteria"].values()
                  for key in criterion["evidence"]}
    constraint = assessment["review"].get("request_constraint")
    if constraint is not None:
        references.update(constraint["evidence"])
    return {key: item for key, item in assessment["evidence"].items() if key in references}


def assessment_summary(assessment):
    return {**{k: v for k, v in assessment.items() if k not in {"key", "evidence", "assessment_basis_version"}},
            "evidence": cited_assessment_evidence(assessment),
            "considered_evidence_count": len(assessment["evidence"])}


def evidence_summary(evidence):
    """A decision view, not a replacement for the provenance-bearing record."""
    return {key: value for key, value in evidence.items() if key not in {"quote", "source_version"}}


def evidence_inventory(numeric, qualitative):
    """Index changed subjects/fields/sources without resending their whole bodies."""
    groups = {}
    for form, records in (("numeric", numeric), ("qualitative", qualitative)):
        for record in records:
            key = (record["subject"], record.get("source", ""), record.get("kind", "source_evidence"), form)
            group = groups.setdefault(key, {"subject": key[0], "source": key[1], "kind": key[2],
                                           "form": form, "fields": set(), "records": 0})
            group["fields"].update([record["field"]] if "field" in record else record.get("fields", ()))
            group["records"] += 1
    return [{**group, "fields": sorted(group["fields"])} for group in groups.values()]


@dataclass(frozen=True)
class Fact(ClosedRecord):
    subject: str
    field: str
    value: float
    unit: str
    kind: str
    basis: str
    source: str = ""
    quote: str = ""
    context: str = ""
    parents: tuple[str, ...] = ()
    source_version: str = ""

    def __post_init__(self):
        for name in ("subject", "field", "unit", "basis"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Fact.{name} is required")
        object.__setattr__(self, "value", finite(self.value, self.field))
        if self.kind not in {"user_assumption", "request_constraint", "source_observation", "source_model_parameter", "model_assumption", "derived"}:
            raise ValueError("Unknown fact kind")
        if any(not isinstance(getattr(self, name), str) for name in ("source", "quote", "context")):
            raise ValueError("Fact source, quote and context must be text")
        if self.kind.startswith("source_") and not (self.source and self.quote and self.context):
            raise ValueError("Source facts require an exact quote and applicability context")

    @property
    def key(self):
        return identity(self.as_record())

    @property
    def credit_key(self):
        # Mirrors, paraphrases and repeated quotations do not manufacture yield.
        return identity([self.subject, self.field, self.value, self.unit])

    def as_record(self):
        return {"subject": self.subject, "field": self.field, "value": self.value,
                "unit": self.unit, "kind": self.kind, "basis": self.basis,
                "source": self.source, "quote": self.quote, "context": self.context,
                "parents": list(self.parents), "source_version": self.source_version}

    def semantic_record(self):
        return {k: v for k, v in self.as_record().items() if k != "parents"}


@dataclass(frozen=True)
class ResearchMessage(ClosedRecord):
    objective: str
    focus: tuple[str, ...]
    subjects: tuple[str, ...]
    proposal: Mapping[str, Any] = dataclass_field(default_factory=dict)

    def as_record(self):
        return {"objective": self.objective, "focus": list(self.focus), "subjects": list(self.subjects),
                "proposal": dict(self.proposal)}


@dataclass(frozen=True)
class Credit(ClosedRecord):
    identities: tuple[tuple[str, str], ...] = ()
    evaluated: bool = True
    qualities: tuple[tuple[str, str, float], ...] = ()

    def as_record(self):
        return {"identities": [list(pair) for pair in self.identities], "evaluated": self.evaluated,
                "qualities": [list(row) for row in self.qualities]}


@dataclass(frozen=True)
class ResearchResult(ClosedRecord):
    facts: tuple[Fact, ...] = ()
    estimates: tuple[Mapping[str, Any], ...] = ()
    findings: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    evaluated: bool = True
    stop_reason: str = ""
    evidence: tuple[Mapping[str, Any], ...] = ()
    assumptions: tuple[Mapping[str, Any], ...] = ()
    scenarios: tuple[Mapping[str, Any], ...] = ()
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    calculations: tuple[Mapping[str, Any], ...] = ()

    def as_record(self):
        return {"facts": [f.as_record() for f in self.facts],
                "estimates": list(self.estimates), "findings": list(self.findings),
                "issues": list(self.issues), "evaluated": self.evaluated,
                "stop_reason": self.stop_reason, "evidence": list(self.evidence),
                "assumptions": list(self.assumptions), "scenarios": list(self.scenarios),
                "diagnostics": list(self.diagnostics), "calculations": list(self.calculations)}

    def audit_identifiers(self):
        return tuple(f.key for f in self.facts)

    def credit(self, focus, *, scientific=False, subjects=None):
        if scientific:
            from .assumptions import scientific_credit
            return scientific_credit(self, focus, subjects=subjects)
        pairs = {(f.field, f.credit_key) for f in self.facts if f.field in focus}
        pairs.update((field, identity([e["subject"], field, " ".join(e["quote"].split())]))
                     for e in self.evidence for field in e.get("fields", ()) if field in focus)
        for estimate in self.estimates:
            for name, output in estimate["metrics"].items():
                column = f"{estimate['subject']}::{name}"
                column = column if column in focus else name
                if column in focus and output["status"] == "calculated":
                    pairs.add((column, identity([estimate["subject"], name, output["value"], output["limit"]])))
            for name, output in estimate.get("derived_parameters", {}).items():
                if name in focus:
                    pairs.add((name, identity([estimate["subject"], name, output["value"]])))
        return Credit(tuple(sorted(pairs)), self.evaluated)

    def synthesis(self):
        return {"evidence": [f.semantic_record() for f in self.facts],
                "estimates": [{"subject": e["subject"], "label": e["label"],
                               "metrics": e["metrics"], "issues": e["issues"]} for e in self.estimates],
                "findings": list(self.findings), "unresolved": list(self.issues),
                "completion": self.stop_reason, "assumptions": [{k: v for k, v in a.items() if k != "key"} for a in self.assumptions],
                "qualitative_evidence": list(self.evidence), "scenarios": list(self.scenarios),
                "diagnostics": list(self.diagnostics)}


class Ledger:
    """Episode-owned admitted knowledge, updated only after a numeric verdict."""

    def __init__(self, facts=()):
        inherited = facts if isinstance(facts, ResearchResult) else ResearchResult(tuple(facts))
        self.facts = {}
        self.estimates = {}
        self.findings = []
        self.issues = []
        self.evidence = {}
        self.assumptions = {}
        self.scenarios = {}
        self.diagnostics = []
        self.calculations = {}
        self.merge(inherited)

    def merge(self, result):
        self.facts.update((f.key, f) for f in result.facts)
        for estimate in result.estimates:
            model = estimate.get("parameterization")
            if model:
                for previous_key, previous in tuple(self.estimates.items()):
                    if previous.get("parameterization") == model and previous["subject"] == estimate["subject"]:
                        combined = compatible_estimates(previous, estimate)
                        if combined is not None:
                            estimate = combined
                            del self.estimates[previous_key]
                            break
            key = identity([estimate["subject"], estimate["parameters"], estimate["conditions"],
                            estimate.get("assumption_versions", {}), model])
            previous = self.estimates.get(key)
            if previous:
                estimate = {**previous, **estimate, "metrics": {**previous["metrics"], **estimate["metrics"]},
                    "calculation_versions": list(dict.fromkeys([*previous.get("calculation_versions", ()),
                                                                *estimate.get("calculation_versions", ())]))}
            self.estimates[key] = estimate
        self.findings.extend(v for v in result.findings if v not in self.findings)
        self.issues.extend(v for v in result.issues if v not in self.issues)
        self.evidence.update((identity(e), e) for e in result.evidence)
        self.assumptions.update((a["key"], a) for a in result.assumptions)
        self.scenarios.update((s["subject"], s) for s in result.scenarios)
        self.diagnostics.extend(d for d in result.diagnostics if d not in self.diagnostics)
        self.calculations.update((c["version"], c) for c in result.calculations)

    def options(self):
        return {f"fact:{i}": f for i, f in enumerate(self.facts.values(), 1)}

    def evidence_options(self):
        records = [f.semantic_record() for f in self.facts.values()
                   if f.kind in {"source_observation", "source_model_parameter", "request_constraint"}]
        return {f"evidence:{i}": e for i, e in enumerate([*records, *self.evidence.values()], 1)}

    def assumption_options(self):
        return {f"assumption:{i}": assessment_summary(a)
                for i, a in enumerate(self.assumptions.values(), 1)}

    def calculation_options(self):
        return {f"calculation:{i}": c for i, c in enumerate(self.calculations.values(), 1)}

    def result(self, **kwargs):
        return ResearchResult(tuple(self.facts.values()), tuple(self.estimates.values()),
                              tuple(self.findings), tuple(self.issues), evidence=tuple(self.evidence.values()),
                              assumptions=tuple(self.assumptions.values()), scenarios=tuple(self.scenarios.values()),
                              diagnostics=tuple(self.diagnostics), calculations=tuple(self.calculations.values()), **kwargs)


def compatible_estimates(left, right):
    """Join tool outputs only within an explicitly named, compatible model."""
    for name in ("parameters", "conditions", "assumption_versions"):
        if any(left.get(name, {})[k] != value for k, value in right.get(name, {}).items()
               if k in left.get(name, {})):
            return None
    parameters = {**left["parameters"], **right["parameters"]}
    conditions = {**left["conditions"], **right["conditions"]}
    from ...task_executors.scenario_metrics.evaluate import evaluate_parameters
    check = evaluate_parameters(parameters, conditions, (), subject=left["subject"], label=left["label"])
    if check["issues"]:
        return None
    support = {a["key"]: a for a in (*left.get("assumption_support", ()), *right.get("assumption_support", ()))}
    return {**left, **right, "parameters": parameters, "conditions": conditions,
            "metrics": {**left["metrics"], **right["metrics"]},
            "input_provenance": {**left.get("input_provenance", {}), **right.get("input_provenance", {})},
            "derived_parameters": {**left.get("derived_parameters", {}), **right.get("derived_parameters", {})},
            "assumption_versions": {**left.get("assumption_versions", {}), **right.get("assumption_versions", {})},
            "assumption_keys": list(dict.fromkeys([*left.get("assumption_keys", ()), *right.get("assumption_keys", ())])),
            "assumption_support": list(support.values()),
            "reasonableness": min(left.get("reasonableness", 0), right.get("reasonableness", 0)),
            "calculation_versions": list(dict.fromkeys([*left.get("calculation_versions", ()), *right.get("calculation_versions", ())])),
            "issues": list(dict.fromkeys([*left.get("issues", ()), *right.get("issues", ())]))}
