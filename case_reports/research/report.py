"""Report projections from admitted episode results, never hand-filled values."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from ...method_loop import ClosedRecord
from ...task_executors.scenario_metrics.catalog import METRICS, PAPER
from ...task_executors.scenario_metrics.evaluate import output_is_resolved
from .records import cited_assessment_evidence


def scenario_results(result, metrics):
    """Project current coverage without executing a calculation or changing state."""
    scenarios = {}
    definitions = {s["subject"]: s for s in result.scenarios if s.get("role", "target") == "target"}
    complete = bool(definitions)
    assessments = {a["key"]: a for a in result.assumptions}
    for subject in definitions:
        alternatives = [e for e in result.estimates if e["subject"] == subject]
        alternatives = [{**e, "current_reasonableness": min((assessments.get(k, {}).get("reasonableness", 0)
                         if k not in e.get("assumption_versions", {}) or assessments.get(k, {}).get("version") == e["assumption_versions"][k] else 0
                         for k in e.get("assumption_keys", ())), default=0)} for e in alternatives]
        coverage = {}
        for name in metrics:
            rows = [e["metrics"].get(name, {"status": "not_evaluated"}) for e in alternatives]
            current_rows = [e["metrics"].get(name, {"status": "not_evaluated"}) for e in alternatives
                            if e["current_reasonableness"] > 0]
            calculated = [r for r in current_rows if r["status"] == "calculated"]
            excluded = [r for r in current_rows if r["status"] == "inapplicable" and output_is_resolved(r)]
            historical = any(r["status"] == "calculated" for r in rows)
            historical_exclusion = any(r["status"] == "inapplicable" for r in rows)
            coverage[name] = {
                "status": "calculated" if calculated else "inapplicable" if excluded else (
                    "unsupported_calculation" if historical else "unsupported_applicability" if historical_exclusion else
                    ((current_rows or rows)[-1]["status"] if rows else "not_evaluated")),
                "missing": [] if calculated or excluded else sorted({v for r in (current_rows or rows) for v in r.get("missing", [])}),
                "applicability": [r["applicability"] for r in excluded],
            }
        coherent = any(e["current_reasonableness"] > 0 and
                       all(output_is_resolved(e["metrics"].get(name, {})) for name in metrics)
                       for e in alternatives)
        complete = complete and coherent
        comparisons = {}
        for name in metrics:
            rows = [{"label": e["label"], **e["metrics"][name]} for e in alternatives
                    if e["current_reasonableness"] > 0 and e["metrics"].get(name, {}).get("status") == "calculated"]
            finite = [r["value"] for r in rows if r["limit"] == "finite"]
            if len(rows) > 1:
                comparisons[name] = {
                    "alternatives": [{k: r[k] for k in ("label", "value", "limit")} for r in rows],
                    "finite_min": min(finite) if finite else None,
                    "finite_max": max(finite) if finite else None,
                    "interpretation": "Sensitivity across named parameterizations, not independent validation or a statistical confidence interval.",
                }
        scenarios[subject] = {"definition": definitions[subject], "coverage": coverage,
                              "alternatives": alternatives, "comparisons": comparisons,
                              "complete_parameterization_available": coherent}
    return scenarios, complete


def scientific_progress(result, metrics):
    """Give the scientific parent the same current-coverage view as closure."""
    scenarios, _ = scenario_results(result, metrics)
    targets = {}
    for subject, scenario in scenarios.items():
        active = [a for a in result.assumptions if a["subject"] == subject and a["reasonableness"] > 0]
        targets[subject] = {
            "coverage": scenario["coverage"],
            "complete_parameterization_available": scenario["complete_parameterization_available"],
            "assessed_numeric_fields": sorted({a["field"] for a in active if a["value"] is not None}),
            "assessed_condition_fields": sorted({a["field"] for a in active if a["value"] is None}),
            "evaluated_parameterizations": len(scenario["alternatives"]),
        }
    return {"targets": targets, "requested_quantities_per_target": list(metrics),
            "calculated_quantities": sum(row["status"] == "calculated" for scenario in scenarios.values()
                                         for row in scenario["coverage"].values()),
            "interpretation": "Current supported conclusions, not source counts or equation inventories. "
            "Assessed fields do not by themselves establish a coherent executable parameterization. "
            "No calculations, candidate selection, or evidence admission occur in this projection."}


@dataclass(frozen=True)
class ResearchReport(ClosedRecord):
    passed: bool
    data: dict

    @classmethod
    def from_result(cls, result, record, run):
        failures = Counter((a["operation"], a["diagnostic"]["category"])
                           for a in run.model_attempts if a["status"] == "response_failed")
        scenarios, complete = scenario_results(result, run.metrics)
        assessments = {a["key"]: a for a in result.assumptions}
        numerical = any(row["status"] == "calculated" for scenario in scenarios.values() for row in scenario["coverage"].values())
        data = {
            "objective": record.goal.as_record()["objective"], "reference": PAPER,
            "status": ("conditional_estimates_available" if numerical else "requested_model_inapplicable") if complete else "incomplete",
            "scenarios": scenarios,
            "evidence_and_assumptions": [f.as_record() for f in result.facts],
            "assumption_assessments": list(result.assumptions),
            "qualitative_evidence": list(result.evidence), "attempt_diagnostics": list(result.diagnostics),
            "calculations": list(result.calculations),
            "observation_comparisons": [{**c["output"], "subject": c["subject"],
                "support_status": "current" if c["assumption_versions"] and all(
                    assessments.get(k, {}).get("version") == version and assessments.get(k, {}).get("reasonableness", 0) > 0
                    for k, version in c["assumption_versions"].items()) else "stale_or_unsupported"}
                for c in result.calculations if c["tool"] == "compare_predictions_with_observations"],
            "research_request": run.research_request,
            "model_attempts": list(run.model_attempts),
            "model_response_failures": [{"operation": operation, "category": category, "count": count}
                                        for (operation, category), count in sorted(failures.items())],
            "implementation_sha256_at_start": dict(run.implementation),
            "source_documents": dict(run.documents),
            "episode_tree": {parent.name: [child.name for child in children]
                             for parent, children in run.tree.children.items()},
            "findings": list(result.findings), "unresolved": list(result.issues),
            "control": {"ended_by": record.ended_by, "reason": result.stop_reason,
                        "credit_history": list(record.controller_state.history),
                        "rarefaction": record.controller_state.rarefaction,
                        "model_calls": run.model_calls, "total_units": run.total_units,
                        "limits": vars(run.limits),
                        "method": "Evidence-linked assumption resolution, supported outputs, and evidence-consistency checks are separately weighted. Parent recomputes credit; rolling marginal yield controls continuation. Operational heuristic, not calibrated confidence.",
                        "input_boundary": "Original prompt only; no preloaded scenario parameters or seeded evidence."},
            "validation": {
                "status": "not_independently_validated",
                "calibration": "Solving Cq from an outbreak and predicting that same outbreak is a consistency check by construction.",
                "independent_validation_requires": "A held-out observation and independently justified transferable assumptions, with no tuning to its outcomes.",
            },
            "paper_coverage": {
                "implemented_metrics": [m.as_record() for m in METRICS.values()],
                "scope": "Constant-source, single-effective-radius, well-mixed model and the unmasked continuous-jet extension.",
                "not_implemented": [
                    "Size-resolved aerosol distributions and their weighted effective radius (SI Eq. S7).",
                    "Direct integration of activity-dependent aerosol size spectra (scalar volume-fraction rescaling is available).",
                    "An independent held-out validation experiment selected and evaluated by the research loop.",
                ],
            },
            "interpretation": "Conditional research estimates, not a guarantee of safety. Critical distance is a jet/background crossover, not a universal safe separation.",
        }
        return cls(complete, data)

    def as_record(self):
        return {"passed": self.passed, **self.data}

    def markdown(self):
        def cell(value):
            return str(value).replace("|", "\\|").replace("\n", " ")

        def quantity(row):
            if row.get("status") == "inapplicable":
                return "not applicable"
            return "unbounded" if row.get("limit") == "unbounded" else (
                f"{row['value']:.8g}" if row.get("value") is not None else "unknown")

        lines = ["# Conditional Indoor Transmission Estimates", "", self.data["objective"], "",
                 f"Status: {self.data['status']}", "", self.data["interpretation"], ""]
        for subject, scenario in self.data["scenarios"].items():
            lines.extend([f"## {subject}", "", scenario["definition"].get("description", ""), "",
                          "| Requested Quantity | Current Status | Missing Information or Applicability |",
                          "| --- | --- | --- |"])
            for name, coverage in scenario["coverage"].items():
                notes = [*coverage["missing"], *(a["reason"] for a in coverage.get("applicability", []))]
                lines.append(f"| {cell(name)} | {coverage['status']} | {cell('; '.join(notes))} |")
            lines.append("")
            if not scenario["alternatives"]:
                lines.append("No admitted parameterization was evaluated.")
            for alternative in scenario["alternatives"]:
                lines.extend([f"### {alternative['label']}", "", "| Quantity | Value | Unit | Status | Limitations |",
                              "| --- | ---: | --- | --- | --- |"])
                for name, row in alternative["metrics"].items():
                    notes = [*row.get("missing", []), row.get("applicability_warning", ""),
                             row.get("applicability", {}).get("reason", "")]
                    lines.append(f"| {cell(name)} | {quantity(row)} | {cell(row.get('unit', ''))} | {row['status']} | {cell('; '.join(n for n in notes if n))} |")
                current = alternative["current_reasonableness"]
                lines.extend(["", f"Current assumption support: {'withdrawn' if not current else 'supported' if current == 1 else 'provisional'}.",
                              "", "Named model assumptions:", ""])
                lines.extend(f"- {name}: {basis}" for name, basis in alternative["conditions"].items())
                lines.extend(["", "Input evidence and assumptions:", ""])
                for name, fact in alternative["input_provenance"].items():
                    citation = f" [Source]({fact['source']})" if fact["source"] and fact["source"] != "request" else ""
                    lines.append(f"- {name} = {fact['value']:.8g} {fact['unit']} ({fact['kind']}): {fact['basis']}{citation}")
                lines.append("")
            if scenario["comparisons"]:
                lines.extend(["### Sensitivity Across Supported Alternatives", "",
                              "These are conditional model alternatives, not independent validation or confidence intervals.", ""])
                for name, comparison in scenario["comparisons"].items():
                    values = "; ".join(f"{row['label']}: {quantity(row)}" for row in comparison["alternatives"])
                    lines.append(f"- {name}: {values}")
                lines.append("")
        lines.extend(["## Assumption Support", "", "Ordinal review judgments, not probabilities or independent validation.", ""])
        for assumption in self.data["assumption_assessments"]:
            review = assumption["review"]
            lines.extend([f"### {assumption['subject']}: {assumption['field']}", "",
                          assumption["statement"], "", f"Assessment: {review['verdict']}. {review['explanation']}", ""])
            lines.extend(f"- {name} ({row['grade']}/2): {row['reason']}" for name, row in review["criteria"].items())
            for name in ("limitations", "alternatives", "missing_evidence"):
                lines.extend(f"- {name}: {item}" for item in review[name])
            for evidence in cited_assessment_evidence(assumption).values():
                source = evidence["source"]
                citation = "Original request" if source == "request" else f"[Source]({source})"
                lines.append(f"- {citation}: {evidence['basis']}")
            lines.append("")
        if self.data["observation_comparisons"]:
            lines.extend(["## Prediction and Observation Checks", "",
                          "| Scenario | Metric | Predicted | Observed | Residual | Comparison Role | Support |",
                          "| --- | --- | ---: | ---: | ---: | --- | --- |"])
            for comparison in self.data["observation_comparisons"]:
                lines.append(f"| {cell(comparison['subject'])} | {cell(comparison['metric'])} | "
                             f"{comparison['predicted']:.8g} | {comparison['observed']:.8g} | {comparison['residual']:.8g} | "
                             f"{comparison['category']} | {comparison['support_status']} |")
            lines.append("")
        lines.extend(["## Unresolved Questions", ""])
        lines.extend(f"- {item}" for item in self.data["unresolved"])
        lines.extend(["", "## Validation", "", self.data["validation"]["calibration"], "",
                      "Independent validation: not performed.", "", "## Remaining Scope", ""])
        lines.extend(f"- {item}" for item in self.data["paper_coverage"]["not_implemented"])
        lines.extend(["", "## Episode Control", "",
                      f"Ended: {self.data['control']['reason']}. {self.data['control']['method']}", ""])
        return "\n".join(lines)
