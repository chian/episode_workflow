"""Report projections from admitted episode results, never hand-filled values."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from ...method_loop import ClosedRecord
from ...task_executors.scenario_metrics.catalog import METRICS, PAPER, metric_catalog_record, metric_routes
from ...task_executors.scenario_metrics.evaluate import CONDITIONS, UNITS, output_has_exclusion, output_meets_contract, exposure_outputs_agree
from ...task_executors.scenario_metrics.dependencies import input_requirements
from .records import cited_assessment_evidence, current_support, assumption_matches, identity, Ledger
from .communication import decision_records, reading_coverage
from .verification import calibration_progress, live_acceptance, target_calibration_progress
from .calculation_steps import calculation_is_up_to_date, calculation_step_status


def scenario_results(result, metrics):
    """Project current coverage without executing a calculation or changing state."""
    scenarios = {}
    definitions = {s["subject"]: s for s in result.scenarios if s.get("role", "target") == "target"}
    complete = bool(definitions)
    assessments = {a["key"]: a for a in result.assumptions}
    ledger = Ledger(result)
    steps = {(row["subject"], row["field"]): row
             for row in calculation_step_status(result, metrics)["steps"]}
    for subject in definitions:
        contracts = definitions[subject].get("output_contracts", {})
        alternatives = [e for e in result.estimates if e["subject"] == subject]
        alternatives = [{**e, "metrics": {name: row for name, row in e["metrics"].items() if name in metrics}}
                        for e in alternatives]
        alternatives = [{**e, "current_reasonableness": current_support(e, assessments, ledger=ledger),
                         "current_computed_metrics": [m for m in e["metrics"]
                             if calculation_is_up_to_date(e, m, ledger)],
                         "current_metric_support": {m: current_support(e, assessments, metric=m, ledger=ledger) for m in e["metrics"]}}
                        for e in alternatives]
        coverage = {}
        for name in metrics:
            step = steps[(subject, name)]
            rows = [e["metrics"].get(name, {"status": "not_evaluated"}) for e in alternatives]
            current_rows = [e["metrics"].get(name, {"status": "not_evaluated"}) for e in alternatives
                            if e["current_metric_support"].get(name, 0) > 0]
            calculated = [e["metrics"][name] for e in alternatives if name in e["current_computed_metrics"]
                          and e["current_metric_support"].get(name, 0) > 0]
            excluded = [r for r in current_rows if output_has_exclusion(r)]
            historical = any(r["status"] == "calculated" for r in rows)
            mismatched = any(r["status"] == "calculated" and not output_meets_contract(r, contracts.get(name))
                             for r in rows)
            historical_exclusion = any(r["status"] == "inapplicable" for r in rows)
            figures = [{"parameterization": e["label"],
                        **{k: e["metrics"][name][k] for k in ("value", "unit", "limit", "function", "regime", "interpretation",
                            "operation", "background", "near_field", "fixed_inputs", "model_id", "risk_threshold",
                            "distance_outcome", "applicability_warning")
                           if k in e["metrics"][name]},
                        "support": e["current_metric_support"].get(name, 0)}
                       for e in alternatives if name in e["current_computed_metrics"]]
            coverage[name] = {
                "computed": step["status"] == "calculated_up_to_date",
                "recorded_computation": step["status"] != "not_calculated",
                "calculation_status": step["status"],
                "output_contract": contracts.get(name),
                "figures": sorted(figures, key=lambda f: f["support"], reverse=True),
                "status": "calculated" if calculated else "inapplicable" if excluded else (
                    "output_contract_mismatch" if mismatched and not figures else
                    "unsupported_calculation" if historical else "unsupported_applicability" if historical_exclusion else
                    ((current_rows or rows)[-1]["status"] if rows else "not_evaluated")),
                "missing": [] if calculated or excluded else sorted({v for r in (current_rows or rows) for v in r.get("missing", [])}
                    | ({"A calculation at the requested fixed inputs and for the requested operation is still needed"}
                       if mismatched and not figures else set())),
                "applicability": [r["applicability"] for r in excluded],
            }
        coherent = any(exposure_outputs_agree(e["metrics"]) and
                       all(e["current_metric_support"].get(name, 0) > 0 and
                           name in e["current_computed_metrics"] for name in metrics)
                       for e in alternatives)
        provisional = any(exposure_outputs_agree(e["metrics"]) and
                          all(name in e["current_computed_metrics"] for name in metrics) for e in alternatives)
        complete = complete and coherent
        comparisons = {}
        for name in metrics:
            rows = [{"label": e["label"], **e["metrics"][name]} for e in alternatives
                    if e["current_metric_support"].get(name, 0) > 0 and name in e["current_computed_metrics"]]
            finite = [r["value"] for r in rows if r["limit"] == "finite"]
            if len(rows) > 1:
                comparisons[name] = {
                    "alternatives": [{k: r[k] for k in ("label", "value", "limit", "function", "regime", "interpretation") if k in r} for r in rows],
                    "finite_min": min(finite) if finite else None,
                    "finite_max": max(finite) if finite else None,
                    "interpretation": "Sensitivity across named parameterizations, not independent validation or a statistical confidence interval.",
                }
        scenarios[subject] = {"definition": definitions[subject], "coverage": coverage,
                              "alternatives": alternatives, "comparisons": comparisons,
                              "provisional_parameterization_available": provisional,
                              "complete_parameterization_available": coherent}
    return scenarios, complete


def scientific_progress(result, metrics, *, decision_view=False):
    """Give the scientific parent the same current-coverage view as closure."""
    scenarios, _ = scenario_results(result, metrics)
    calibration = calibration_progress(result)
    calibration_targets = target_calibration_progress(result, metrics, calibration=calibration)
    assessments = {a["key"]: a for a in result.assumptions}
    ledger = Ledger(result)
    if decision_view:
        records = decision_records(ledger, target_subjects=scenarios)
        subject_refs = records["subjects"]
        parameterizations = {estimate["label"]: "parameterization:" + identity(estimate["label"])[:12]
                             for estimate in result.estimates}
        parameterizations.update(records["parameterizations"])
        assumption_rows = {key: records["assumptions"].get(f"assumption:{index}")
                           for index, key in enumerate(ledger.assumptions, 1)}
        declared_fields = set(UNITS) | set(CONDITIONS) | set(METRICS)
        # Describe calculated source values without exposing a target-input selector.
        outputs = {fact.key: {"subject": subject_refs[fact.subject], "field": fact.field,
                            "value": fact.value, "unit": fact.unit}
                   for fact in ledger.facts.values() if fact.field in UNITS}

        def referenced(keys):
            return [outputs.get(key, {"available": False}) for key in keys]

        calibration = {**calibration,
            "observed_event_fields": {subject_refs[subject]: fields
                                      for subject, fields in calibration["observed_event_fields"].items()},
            "calibrations": [{
                **{key: row[key] for key in ("subtask", "operator", "observed_fields", "outbreak_evidence_acquired",
                                           "duration_observation_available", "current", "support")},
                "subject": subject_refs[row["subject"]],
                "source_count": len(row["source_refs"]),
                "outbreak_observations_missing": bool(row["missing_observations"]),
                "outputs": referenced(row.get("output_fact_keys", ())),
            } for row in calibration["calibrations"]]}
        calibration_targets = {subject: {**target, "alternatives": [
            {**alternative, "parameterization": parameterizations[alternative["parameterization"]],
             "calibrated_inputs_by_quantity": {
                name: referenced(keys) for name, keys in
                alternative["calibrated_inputs_by_quantity"].items()}}
            for alternative in target["alternatives"]]}
            for subject, target in calibration_targets.items()}
    from .scenario_sharing import applicable_assumptions
    from .tools import main_calculation_inputs
    targets = {}
    for subject, scenario in scenarios.items():
        scoped = [a for a, _relation in applicable_assumptions(ledger, subject)]
        active = [a for a in scoped if a["reasonableness"] > 0]
        main_inputs = main_calculation_inputs(ledger, subject)
        needs = {}
        recalculation = []
        for alternative in scenario["alternatives"]:
            for metric in metrics:
                dependency = alternative.get("metric_support", {}).get(metric, {})
                if (alternative["metrics"].get(metric, {}).get("status") == "calculated"
                        and metric not in alternative["current_computed_metrics"]):
                    contract_met = output_meets_contract(alternative["metrics"][metric],
                        scenario["definition"].get("output_contracts", {}).get(metric))
                    changed = []
                    previous = {a["key"]: a for a in alternative.get("assumption_support", [])}
                    for key in dependency.get("assumption_versions", {}):
                        current = assessments.get(key)
                        if not assumption_matches(dependency, key, current) or current.get("review", {}).get("verdict") == "contradicted":
                            if decision_view:
                                before = previous.get(key, {})
                                typed = assumption_rows.get(key)
                                changed.append({"field": (current or before).get("field"),
                                    "previous_value": before.get("value") if type(before.get("value")) in (int, float) else None,
                                    "current_value": typed.get("value") if typed else None,
                                    "current_review": typed["review"] if typed else None,
                                    "condition_changed": bool((current or before).get("field") in CONDITIONS and
                                        before.get("statement") != (current or {}).get("statement")),
                                    "current_condition_ref": typed.get("condition_ref") if typed else None})
                            else:
                                changed.append({"assumption_key": key, "field": (current or previous.get(key, {})).get("field"),
                                    "previous_statement": previous.get(key, {}).get("statement"),
                                    "current_statement": current.get("statement") if current else None,
                                    "current_verdict": current.get("review", {}).get("verdict") if current else "unavailable"})
                    recalculation.append({"parameterization": (parameterizations[alternative["label"]]
                                                               if decision_view else alternative["label"]), "quantity": metric,
                        "output_contract_met": contract_met,
                        "changed_premises": changed,
                        "invalidated_dependencies": ([field for field in dependency.get("invalidated_dependencies", ())
                                                      if isinstance(field, str) and field in declared_fields]
                                                     if decision_view else dependency.get("invalidated_dependencies", [])),
                        **({"invalidated_dependency_count": len(dependency.get("invalidated_dependencies", ()))}
                           if decision_view else {}),
                        "meaning": ("Recorded arithmetic does not meet the requested operation or fixed-input contract; "
                                    "more supporting evidence alone cannot supply the missing evaluation." if not contract_met else
                                    "Historical arithmetic is retained, but its premises are no longer current. "
                                    "Establish the intended physical claim before relying on or recalculating this result.")})
                for key in dependency.get("assumption_versions", {}):
                    assumption = assessments.get(key)
                    if assumption and assumption["reasonableness"] < 1:
                        if decision_view:
                            need = needs.setdefault(key, dict(assumption_rows[key]))
                        else:
                            need = needs.setdefault(key, {k: assumption[k] for k in
                                ("subject", "field", "value", "statement", "reasonableness")})
                            need["reason"] = assumption["review"]["explanation"]
                        affected = need.setdefault("affected_quantities", [])
                        if metric not in affected:
                            affected.append(metric)
        coverage = scenario["coverage"]
        if decision_view:
            coverage = {name: {
                **{key: row[key] for key in ("computed", "recorded_computation", "calculation_status", "status", "output_contract")},
                "figures": [{
                    "parameterization": parameterizations[figure["parameterization"]],
                    **{key: figure[key] for key in ("value", "support", "risk_threshold", "fixed_inputs") if key in figure},
                    "unit": METRICS[name].unit,
                    **{key: figure[key] for key, choices in {
                        "limit": {"finite", "unbounded", "empty", "function"},
                        "regime": {route.regime for route in metric_routes(name)},
                        "operation": {"solve_time", "solve_distance", "evaluate_R_in"},
                        "background": {"steady", "transient"}, "near_field": {"jet", "uniform"},
                    }.items() if figure.get(key) in choices},
                    "function_output": "function" in figure,
                } for figure in row["figures"]],
                "missing": [field for field in row["missing"] if field in declared_fields],
                "applicability_recorded": bool(row["applicability"]),
            } for name, row in coverage.items()}
        targets[subject] = {
            "calibration_linkage": calibration_targets[subject],
            "input_requirements": input_requirements(metrics,
                {fact.field for fact in main_inputs},
                {a["field"] for a in scoped if a["value"] is None},
                scenario["definition"].get("calculation_variables", ())),
            "coverage": coverage,
            "provisional_parameterization_available": scenario["provisional_parameterization_available"],
            "complete_parameterization_available": scenario["complete_parameterization_available"],
            "parameterizations": [{"name": parameterizations[e["label"]] if decision_view else e["label"],
                "computed_quantities": [m for m in metrics if m in e["current_computed_metrics"]],
                "unresolved_quantities": [m for m in metrics if m not in e["current_computed_metrics"]]}
                for e in scenario["alternatives"]],
            "assumption_support_needs": list(needs.values()),
            "recalculation_needs": recalculation,
            "recorded_numeric_fields": sorted({a["field"] for a in scoped if a["value"] is not None}),
            "assessed_numeric_fields": sorted({a["field"] for a in active if a["value"] is not None}),
            "assessed_condition_fields": sorted({a["field"] for a in active if a["value"] is None}),
            "evaluated_parameterizations": len(scenario["alternatives"]),
        }
    return {"targets": targets, "calibration_progress": calibration,
            "requested_quantities_per_target": list(metrics),
            "quantity_coverage": {name: {
                "requested_cases": len(scenarios),
                "computed_cases": sum(s["coverage"][name]["computed"] for s in scenarios.values()),
                "supported_cases": sum(s["coverage"][name]["status"] == "calculated" for s in scenarios.values()),
                "computed_but_unsupported_subjects": [subject for subject, s in scenarios.items()
                    if s["coverage"][name]["computed"] and s["coverage"][name]["status"] != "calculated"],
                "uncomputed_subjects": [subject for subject, s in scenarios.items() if not s["coverage"][name]["computed"]],
                "inapplicable_subjects": [subject for subject, s in scenarios.items() if s["coverage"][name]["status"] == "inapplicable"],
            } for name in metrics},
            "recorded_calculated_quantities": sum(row["recorded_computation"] for scenario in scenarios.values()
                                                  for row in scenario["coverage"].values()),
            "calculated_quantities": sum(row["computed"] for scenario in scenarios.values()
                                         for row in scenario["coverage"].values()),
            "evidence_supported_quantities": sum(row["status"] == "calculated" for scenario in scenarios.values()
                                         for row in scenario["coverage"].values()),
            "interpretation": "Computed consequences and evidence-supported conclusions are separate. "
            "calculated_quantities counts current results meeting their output contracts, even when their hypotheses remain unsupported; it is not a confidence score. "
            "The default contracts require time at fixed distance, distance at fixed time, and R_in at both; formulas alone do not answer them. "
            "Coverage across different parameterizations does not establish one coherent solution. "
            "assumption_support_needs maps weak assumptions to affected outputs; values may remain usable while support improves. "
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
        provisional = bool(scenarios) and all(s["provisional_parameterization_available"] for s in scenarios.values())
        computed = sum(row["computed"] for s in scenarios.values() for row in s["coverage"].values())
        acceptance = live_acceptance(result, run, scenarios)
        data = {
            "objective": record.goal.as_record()["objective"], "reference": PAPER,
            "requested_quantities": list(run.metrics),
            "status": ("conditional_estimates_available" if complete else
                       "provisional_estimates_available" if provisional else "partial_estimates_available" if computed else "incomplete"),
            "computational_progress": {"calculated_quantities": computed,
                "duration_relationships": sum(any(f.get("limit") == "function" for f in row["figures"])
                                              for s in scenarios.values() for row in s["coverage"].values()),
                "recorded_calculated_quantities": sum(row["recorded_computation"] for s in scenarios.values() for row in s["coverage"].values()),
                "requested_quantities": len(scenarios) * len(run.metrics),
                "coherent_provisional_solution_available": provisional},
            "evidence_status": "supported_conditional_coverage" if complete else "incomplete_support",
            "scenarios": scenarios,
            "evidence_and_assumptions": [f.as_record() for f in result.facts],
            "assumption_assessments": list(result.assumptions),
            "qualitative_evidence": list(result.evidence), "attempt_diagnostics": list(result.diagnostics),
            "source_event_types": [row for row in result.source_event_types if row.get("members")],
            "source_target_relationships": list(run.global_goal.ledger.source_target_relationships.values()),
            "scenario_parameter_relations": list(run.global_goal.ledger.scenario_parameter_relations.values()),
            "global_scientific_goal": run.global_goal.preview(),
            "root_credit_projection": run.root_credit_projection(),
            "calculations": list(result.calculations),
            "observation_comparisons": [{**c["output"], "subject": c["subject"],
                "support_status": "current" if current_support(c, assessments, ledger=run.global_goal.ledger) > 0 else "stale_or_unsupported"}
                for c in result.calculations if c["tool"] == "compare_predictions_with_observations"],
            "research_request": run.research_request,
            "model_attempts": run.model_attempts,
            "model_response_failures": [{"operation": operation, "category": category, "count": count}
                                        for (operation, category), count in sorted(failures.items())],
            "implementation_sha256_at_start": dict(run.implementation),
            "source_documents": dict(run.documents),
            "provider_events": list(run.provider_events),
            "runtime_acceptance": acceptance,
            "reading_attempts": list(result.reading_attempts),
            "source_reading_coverage": reading_coverage(result.reading_attempts),
            "episode_tree": {parent.name: [child.name for child in children]
                             for parent, children in run.tree.children.items()},
            "findings": list(result.findings),
            "control": {"ended_by": record.ended_by, "reason": result.stop_reason,
                        "credit_history": list(record.controller_state.history),
                        "rarefaction": record.controller_state.rarefaction,
                        "model_calls": run.model_calls, "total_units": run.total_units,
                        "limits": vars(run.limits),
                        "method": "Found-parameter learning and calculation-step progress are separate additive components, each with weight 1. "
                        "Retained physical defaults and calculated intermediates are excluded from values-to-find coverage. "
                         "Calculation rates and the requested-output multiplier are recorded in global_scientific_goal.calculation_steps.credit_policy. "
                         "Accepted current intermediates earn the base completion floor. Requested outputs multiply the greater of that floor "
                         "and current support, including each method/current/support credit component. When dependencies become stale, "
                         "only the applicable method credit remains; recalculation restores current-result credit. Rejected or incomplete "
                         "model reviews earn no calculation credit. Enumeration, unsuccessful calls and repetition earn no gain. "
                        "Intermediate steps retain their own dependencies and are optional routes, not additional requested conclusions. "
                        "Found-parameter learning retains its evidence scoring independently of calculation validity. "
                        "Completion requires supported requested outputs and calibration lineage in a coherent parameterization. "
                        "Credit can exceed one and is not a completion fraction. Shared credit and the calculation table update "
                        "after each committed verdict, including the suspended root before child return. Refreshes do not create "
                        "yield observations; rolling marginal yield still controls continuation. Operational heuristic, not calibrated confidence.",
                        "input_boundary": ("Runtime disease input and caller-selected fixed scenario conditions; no seeded scientific answers or research evidence."
                                           if run.fixed_scenarios else "Original prompt only; no preloaded scenario parameters or seeded evidence.")},
            "validation": {
                "status": "not_independently_validated",
                "calibration": "Solving Cq from an outbreak and predicting that same outbreak is a consistency check by construction.",
                "independent_validation_requires": "A held-out observation and independently justified transferable assumptions, with no tuning to its outcomes.",
            },
            "paper_coverage": {
                "implemented_metrics": [metric_catalog_record(name) for name in METRICS],
                "scope": "Time, distance and R_in share a constant-source background-plus-local risk model. Transient jet calculations additionally assume an immediately established local plume. An explicit negligible-near-field hypothesis removes the local term consistently from all three operations; masks do not automatically select it.",
                "not_implemented": [
                    "Size-resolved aerosol distributions and their weighted effective radius (SI Eq. S7).",
                    "Direct integration of activity-dependent aerosol size spectra (scalar volume-fraction rescaling is available).",
                    "Distance-resolved masked leakage or thermal-plume exposure when near-field enhancement is not negligible.",
                    "An independent held-out validation experiment selected and evaluated by the research loop.",
                ],
            },
            "interpretation": "Conditional research estimates, not a guarantee of safety. Time fixes separation; distance fixes duration; R_in fixes both. Each result retains those inputs and its risk-model identity. Risk-based separation is not the jet/background concentration crossover.",
        }
        return cls(complete and acceptance["passed"], data)

    def as_record(self):
        return {"passed": self.passed, **self.data}

    def markdown(self):
        def cell(value):
            return str(value).replace("|", "\\|").replace("\n", " ")

        def quantity(row):
            if row.get("status") == "inapplicable":
                return "not applicable"
            if row.get("limit") == "function":
                return cell(row["function"]["expression"])
            if row.get("operation") == "solve_distance":
                if row.get("limit") == "unbounded":
                    return "no finite separation meets the risk criterion"
                if row.get("limit") == "finite" and row.get("value") == 0:
                    return "no positive minimum imposed by this model (not safety at contact)"
            if row.get("regime") == "well_mixed_distance":
                if row.get("limit") == "unbounded":
                    return "no finite separation meets the room-risk criterion"
                if row.get("limit") == "finite" and row.get("value") == 0:
                    return "no positive minimum in the spatially uniform model (not safety at contact)"
            return "unbounded" if row.get("limit") == "unbounded" else (
                f"{row['value']:.8g}" if row.get("value") is not None else "unknown")

        def fixed_inputs(row):
            labels = {"neighbor_distance_m": "distance", "exposure_time_s": "time"}
            return "; ".join(f"{labels.get(field, field)} = {value['value']:.8g} {value['unit']}"
                             for field, value in row.get("fixed_inputs", {}).items())

        lines = ["# Conditional Indoor Transmission Estimates", "", self.data["objective"], "",
                 f"Status: {self.data['status']}", "", self.data["interpretation"], ""]
        acceptance = self.data.get("runtime_acceptance")
        if acceptance:
            lines.extend([f"Runtime acceptance: {'passed' if acceptance['passed'] else 'incomplete'}.", ""])
            if acceptance["missing"]:
                lines.extend(["Unmet runtime requirements: " + ", ".join(acceptance["missing"]) + ".", ""])
        progress = self.data.get("computational_progress")
        if progress:
            lines.extend([f"Coherent provisional solution available: {progress['coherent_provisional_solution_available']}. "
                          f"Evidence status: {self.data['evidence_status']}.", ""])
        goal = self.data.get("global_scientific_goal", {})
        found = goal.get("recorded_target_inputs")
        if found:
            lines.extend([f"{found['recorded']}/{found['required']} values found.", ""])
        calculations = goal.get("calculation_steps", {})
        if calculations.get("steps"):
            scores = goal.get("scores", {})
            policy = calculations.get("credit_policy", {})
            endpoint_rates = policy.get("requested_output_rates")
            if endpoint_rates:
                lines.extend([
                    f"Requested-output credit: {endpoint_rates['completion_floor']:g} for an accepted current result, "
                    f"up to {endpoint_rates['fully_supported']:g} with full support; "
                    f"{endpoint_rates['reusable_completion']:g} remains when it needs updating. "
                    f"Intermediate credit: {policy['completion_floor']:g} when accepted and current; "
                    f"{policy['reusable_completion']:g} remains when stale. Rejected or incomplete reviews earn zero.", ""])
            status_labels = {"not_calculated": "not calculated",
                "calculated_up_to_date": "calculated & up to date",
                "calculated_needs_updating": "calculated needs updating"}
            lines.extend(["## Calculation Progress", "",
                f"Found-parameter credit: {scores.get('found_parameters', 0):.3f}. "
                f"Calculation-step credit: {scores.get('calculation_steps', 0):.3f}.", "",
                "Accepted calculations earn credit under the recorded policy. A stale result retains its method credit for prior completed work; "
                "its current-result credit returns after recalculation. Ready means inputs are available for an explicit choice.", "",
                "| Target scenario | Calculation | Kind | Computed value | Units | Status | Credit | Ready | Changed inputs / reason |",
                "| --- | --- | --- | ---: | --- | --- | ---: | --- | --- |"])
            for step in calculations["steps"]:
                changes = []
                if step["status"] == "calculated_needs_updating":
                    changes = list(dict.fromkeys(change.get("field") or change["reason"]
                        for alternative in step.get("result_alternatives", ())
                        for change in alternative.get("changed_dependencies", ())))
                if step.get("uncredited_reason"):
                    changes.append(step["uncredited_reason"])
                if step.get("credit_basis"):
                    changes.append(step["credit_basis"])
                for difference in step.get("main_input_differences", ()):
                    changes.append(
                        f"{difference['field']}: calculation used "
                        f"{difference['used_value']} {difference['used_unit']}; main table selects "
                        f"{difference['current_selected_value']} {difference['current_selected_unit']}")
                value = step.get("computed_value")
                if isinstance(value, dict):
                    value = value.get("expression", value)
                lines.append(f"| {cell(step['subject'])} | {cell(step['field'])} | {cell(step['kind'])} | "
                             f"{cell(value) if value is not None else '—'} | {cell(step.get('unit') or '—')} | "
                             f"{status_labels[step['status']]} | "
                             f"{step['points']:.3f} | {'yes' if step['ready_to_calculate'] else 'no'} | "
                             f"{cell('; '.join(changes))} |")
            lines.append("")
        for subject, scenario in self.data["scenarios"].items():
            lines.extend([f"## {subject}", "", scenario["definition"].get("description", ""), ""])
            figures = [(name, figure) for name, coverage in scenario["coverage"].items()
                       for figure in coverage.get("figures", [])]
            if figures:
                lines.extend(["### Current Conditional Figures", "",
                    "Support is reported separately from computation. Different parameterizations are not one combined solution.", "",
                    "| Quantity | Value | Unit | Fixed Inputs | Parameterization / Model | Evidence Support |",
                    "| --- | ---: | --- | --- | --- | --- |"])
                for name, figure in figures:
                    support = "not established" if not figure["support"] else "supported" if figure["support"] == 1 else "provisional"
                    model = figure.get("model_id", "")[:12]
                    lines.append(f"| {cell(name)} | {quantity(figure)} | {cell(figure['unit'])} | "
                                 f"{cell(fixed_inputs(figure))} | {cell(figure['parameterization'])} / {model} | {support} |")
                lines.append("")
                lines.extend(f"- {cell(name)}: {cell(figure['applicability_warning'])}"
                             for name, figure in figures if figure.get("applicability_warning"))
                lines.append("")
            if not scenario["alternatives"]:
                lines.append("No admitted parameterization was evaluated.")
            for alternative in scenario["alternatives"]:
                if not alternative["metrics"]:
                    continue
                lines.extend([f"### {alternative['label']}", "", "| Quantity | Recorded Value | Unit | Support | Limitations |",
                              "| --- | ---: | --- | --- | --- |"])
                for name, row in alternative["metrics"].items():
                    quality = alternative["current_metric_support"][name]
                    support = "not established" if not quality else "supported" if quality == 1 else "provisional"
                    notes = [*row.get("missing", []),
                             fixed_inputs(row),
                             row.get("interpretation", "") if row.get("regime") == "well_mixed_distance" or row.get("model_id") else "",
                             row.get("applicability", {}).get("reason", "")]
                    lines.append(f"| {cell(name)} | {quantity(row)} | {cell(row.get('unit', ''))} | {support} | {cell('; '.join(n for n in notes if n))} |")
                qualities = set(alternative["current_metric_support"].values())
                support = ("mixed; see individual quantities" if len(qualities) > 1 else
                           "not established; exploratory calculation only" if not any(qualities) else
                           "supported" if qualities == {1} else "provisional")
                lines.extend(["", f"Current output support: {support}.",
                              "", "Named model assumptions:", ""])
                if not alternative.get("model_review", {}).get("admit", True):
                    lines.append(f"- Model review: {alternative['model_review']['reason']}")
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
        lines.extend(["", "## Validation", "", self.data["validation"]["calibration"], "",
                      "Independent validation: not performed.", "", "## Remaining Scope", ""])
        lines.extend(f"- {item}" for item in self.data["paper_coverage"]["not_implemented"])
        lines.extend(["", "## Episode Control", "",
                      f"Ended: {self.data['control']['reason']}. {self.data['control']['method']}", ""])
        return "\n".join(lines)
