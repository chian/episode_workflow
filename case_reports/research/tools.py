"""Selectable deterministic calculations; admission and credit belong to the parent."""

from ...task_executors.scenario_metrics.catalog import METRICS
from ...task_executors.scenario_metrics.evaluate import UNITS, evaluate_parameters
from .modeling import DERIVATIONS, derive_parameter, select_facts
from .records import Fact, ResearchResult, identity


GEOMETRY = frozenset({"removal_rate_s", "settling_speed_m_s", "critical_aerosol_radius_m",
    "air_mixing_time_s", "concentration_relaxation_time_s", "air_clearance_time_s"})
LIMITS = frozenset({"cumulative_exposure_bound_person_s", "exposure_time_bound_s", "susceptible_bound",
    "total_occupancy_bound", "required_removal_capacity_m3_s", "transient_exposure_time_bound_s",
    "transient_susceptible_bound", "transient_total_occupancy_bound", "transient_interpolation_time_bound_s",
    "critical_distance_m", "risk_threshold_distance_m", "jet_corrected_time_bound_s"})
TOOLS = {
    "calculate_geometry_and_removal": "Derive geometry and removal quantities from admitted inputs.",
    "calibrate_infectiousness": "Apply an explicitly selected calibration, activity rescaling, or transfer operator.",
    "calculate_transmission_metrics": "Compute dose, R_in, infection probabilities, and steady/transient predictions.",
    "calculate_conditional_limits": "Compute time, occupancy, cumulative exposure, clean-air, and applicable distance limits.",
    "compare_predictions_with_observations": "Compare one versioned prediction with an admitted observation; preserve calibration dependence.",
}


def support_for(ledger, facts, conditions, subject):
    """Resolve exact current support, including transitive calculation lineage."""
    selected = {}
    visiting = set()

    def require(fact):
        if fact.key in visiting:
            raise ValueError("Cyclic parameter provenance")
        matches = [a for a in ledger.assumptions.values() if a["subject"] == fact.subject
                   and a["field"] == fact.field and a["value"] == fact.value and a["reasonableness"] > 0]
        if matches:
            a = max(matches, key=lambda a: a["reasonableness"])
            selected[a["key"]] = a
            return
        derivations = [c for c in ledger.calculations.values() if fact.key in c.get("output_fact_keys", ())]
        if fact.kind != "derived" or not derivations:
            raise ValueError(f"Parameter {fact.field} lacks current evidence-linked reasonableness support")
        calculation = derivations[-1]
        if calculation.get("operator") == "transfer_parameter":
            raise ValueError(f"Transferred {fact.field} needs a reasonableness assessment in its target scenario")
        for key, version in calculation["assumption_versions"].items():
            current = ledger.assumptions.get(key, {})
            if current.get("version") != version or current.get("reasonableness", 0) <= 0:
                raise ValueError(f"Derived {fact.field} depends on a changed or withdrawn assumption")
            selected[key] = current
        visiting.add(fact.key)
        for key in calculation["input_fact_keys"]:
            require(ledger.facts[key])
        visiting.remove(fact.key)

    for fact in facts:
        require(fact)
    for field, statement in conditions.items():
        matches = [a for a in ledger.assumptions.values() if a["subject"] == subject
                   and a["field"] == field and a["statement"] == statement and a["reasonableness"] > 0]
        if not matches:
            raise ValueError(f"Condition {field} lacks current evidence-linked reasonableness support")
        a = max(matches, key=lambda a: a["reasonableness"])
        selected[a["key"]] = a
    return selected


def calculation_record(tool, subject, facts, support, output, *, conditions, basis, **extra):
    record = {"tool": tool, "subject": subject, "input_fact_keys": [f.key for f in facts],
              "input_values": {f.field: f.value for f in facts}, "conditions": dict(conditions),
              "assumption_versions": {k: a["version"] for k, a in support.items()},
              "basis": basis, "output": output, "model_version": "bazant-bush-scalar-v1", **extra}
    record["version"] = identity(record)
    return record


def execute_tool(action, ledger, requested_metrics, *, review):
    name = action.get("action")
    if name not in TOOLS:
        raise ValueError("Undeclared deterministic tool")
    if not review["admit"]:
        return ResearchResult(issues=(f"Calculation admission rejected: {review['reason']}",),
            diagnostics=({"stage": "calculation_admission", "category": "inapplicable_model",
                          "why": review["reason"]},))
    if name == "compare_predictions_with_observations":
        return compare(action, ledger, review)
    facts = select_facts(action, ledger.options())
    subject = action.get("subject")
    if subject not in ledger.scenarios:
        raise ValueError("Calculations require a reviewed scenario")
    if action.get("operator") != "transfer_parameter" and {f.subject for f in facts} != {subject}:
        raise ValueError("Calculation inputs must belong to the same scenario; transfer must be explicit")
    conditions = action.get("conditions", {})
    if not isinstance(conditions, dict):
        raise ValueError("Conditions must be named, assessed statements")
    support = support_for(ledger, facts, conditions, subject)
    if name == "calibrate_infectiousness":
        # The semantic review already ran in the parent's mandatory admission.
        result = derive_parameter(lambda _: review, action, ledger.options(), {})
        calculation = calculation_record(name, subject, facts, support,
            {f.field: {"value": f.value, "unit": f.unit} for f in result.facts},
            conditions=conditions, basis=action["basis"], operator=action["operator"],
            output_fact_keys=[f.key for f in result.facts],
            calibration_subjects=sorted({f.subject for f in facts}) if "outbreak" in action["operator"] else [])
        return ResearchResult(facts=result.facts, findings=result.findings, calculations=(calculation,))
    allowed = GEOMETRY if name == "calculate_geometry_and_removal" else (
        LIMITS if name == "calculate_conditional_limits" else set(METRICS) - GEOMETRY - LIMITS)
    metrics = action.get("metrics", [m for m in requested_metrics if m in allowed])
    if not isinstance(metrics, list) or any(m not in allowed for m in metrics):
        raise ValueError("Select metrics belonging to this tool")
    if not metrics and name != "calculate_geometry_and_removal":
        raise ValueError("Select at least one quantity to calculate")
    estimate = evaluate_parameters({f.field: f.value for f in facts}, conditions, tuple(metrics),
        subject=subject, label=action["basis"], provenance={f.field: f.as_record() for f in facts})
    parameterization = action.get("parameterization", action["basis"])
    if not isinstance(parameterization, str) or not parameterization.strip():
        raise ValueError("A calculation needs a named parameterization")
    estimate.update(parameterization=parameterization, label=parameterization)
    estimate.update(assumption_keys=list(support), assumption_versions={k: a["version"] for k, a in support.items()},
                    assumption_support=list(support.values()),
                    reasonableness=min((a["reasonableness"] for a in support.values()), default=0))
    derived = ()
    if name == "calculate_geometry_and_removal" and not estimate["issues"]:
        derived = tuple(Fact(subject, field, row["value"], UNITS[field], "derived", row["formula"],
                            context=action["basis"], parents=tuple(f.key for f in facts))
                        for field, row in estimate["derived_parameters"].items())
    calculation = calculation_record(name, subject, facts, support, estimate["metrics"],
        conditions=conditions, basis=action["basis"], output_fact_keys=[f.key for f in derived],
        derived_parameters=estimate["derived_parameters"], parameterization=parameterization)
    estimate["calculation_versions"] = [calculation["version"]]
    issues = tuple(sorted({item for row in estimate["metrics"].values() for item in row.get("missing", [])}))
    return ResearchResult(facts=derived, estimates=(estimate,), calculations=(calculation,),
                          findings=tuple(review.get("limitations", [])), issues=issues)


def compare(action, ledger, review):
    options = ledger.calculation_options()
    key, observation_key, metric = action.get("prediction"), action.get("observation"), action.get("metric")
    if key not in options or observation_key not in ledger.options():
        raise ValueError("Comparison must select an existing calculation and fact")
    prediction, observation = options[key], ledger.options()[observation_key]
    if observation.kind != "source_observation":
        raise ValueError("A model choice or assumption is not an observed validation outcome")
    if observation.subject != prediction["subject"]:
        raise ValueError("Prediction and observation must describe the same scenario")
    comparable = {"attack_probability": {"individual_infection_probability", "transient_individual_infection_probability"},
                  "secondary_case_count": {"expected_secondary_cases", "transient_expected_secondary_cases"}}
    if metric not in comparable.get(observation.field, set()):
        raise ValueError("Prediction and observed quantity have incompatible meanings")
    row = prediction["output"].get(metric, {})
    if row.get("status") != "calculated" or row.get("limit") != "finite":
        raise ValueError("Comparison requires a finite calculated prediction")
    for key, version in prediction["assumption_versions"].items():
        current = ledger.assumptions.get(key, {})
        if current.get("version") != version or current.get("reasonableness", 0) <= 0:
            raise ValueError("Prediction support has changed; the comparison would use a stale calculation")
    lineage, pending, calibration_subjects = set(), list(prediction["input_fact_keys"]), set()
    while pending:
        fact_key = pending.pop()
        if fact_key in lineage:
            continue
        lineage.add(fact_key)
        for calculation in ledger.calculations.values():
            if fact_key in calculation.get("output_fact_keys", ()):
                pending.extend(calculation["input_fact_keys"])
                calibration_subjects.update(calculation.get("calibration_subjects", ()))
    dependent = observation.key in lineage or observation.subject in calibration_subjects
    comparison = {"metric": metric, "predicted": row["value"], "observed": observation.value,
                  "residual": row["value"] - observation.value,
                  "absolute_error": abs(row["value"] - observation.value),
                  "observation": observation.semantic_record(),
                  "prediction_version": prediction["version"],
                  "category": "calibration_consistency" if dependent else "out_of_calibration_comparison",
                  "interpretation": review["reason"],
                  "independent_validation": False,
                  "limitation": "No preregistered held-out protocol or independence from outcome-informed modeling is established."}
    calculation = {"tool": action["action"], "subject": prediction["subject"], "output": comparison,
                   "input_fact_keys": [*prediction["input_fact_keys"], observation.key],
                   "assumption_versions": prediction["assumption_versions"], "basis": action["basis"]}
    calculation["version"] = identity(calculation)
    return ResearchResult(calculations=(calculation,), findings=(
        f"{comparison['category']}: {metric} residual={comparison['residual']:.8g}. {review['reason']}",))


def tool_options(ledger):
    return {key: {"version": c["version"], "tool": c["tool"], "subject": c["subject"],
                  "output": c["output"], "basis": c["basis"], "parameterization": c.get("parameterization")}
            for key, c in ledger.calculation_options().items()}
