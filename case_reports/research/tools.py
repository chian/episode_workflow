"""Selectable deterministic calculations; admission and credit belong to the parent."""

from ...task_executors.scenario_metrics.catalog import METRICS
from ...task_executors.scenario_metrics.dependencies import input_requirements
from ...task_executors.scenario_metrics.evaluate import UNITS, evaluate_parameters, output_dependencies
from ...task_executors.scenario_metrics.exposure import EXPOSURE_OUTPUTS, MODEL_VERSION
from .modeling import DERIVATIONS, derivation_inputs, derive_parameter, select_facts
from .records import Fact, ResearchResult, identity, current_support, current_computation, assumption_claim, assumption_matches
from .scenarios import check_case_inputs
from .scenario_sharing import shared_assumptions


GEOMETRY = frozenset({"removal_rate_s", "settling_speed_m_s", "critical_aerosol_radius_m",
    "air_mixing_time_s", "concentration_relaxation_time_s", "air_clearance_time_s"})
LIMITS = frozenset({"cumulative_exposure_bound_person_s", "exposure_time_bound_s", "susceptible_bound",
    "total_occupancy_bound", "required_removal_capacity_m3_s", "transient_exposure_time_bound_s",
    "transient_susceptible_bound", "transient_total_occupancy_bound", "transient_interpolation_time_bound_s",
    "critical_distance_m", "risk_threshold_distance_m", "jet_corrected_time_bound_s",
    *(name for name, (operation, _) in EXPOSURE_OUTPUTS.items() if operation != "evaluate_R_in")})
TOOLS = {
    "calculate_geometry_and_removal": "Derive geometry and removal quantities from selected inputs or recorded hypotheses.",
    "calibrate_infectiousness": "Apply an explicitly selected calibration, activity rescaling, or transfer operator.",
    "calculate_transmission_metrics": "Evaluate the shared risk model at fixed time AND fixed distance. Select scenario_reproductive_number and/or transient_scenario_reproductive_number. The reference inputs are bound from the selected case; the agent selects scientific assumptions. Available parameter derivations execute inside this tool.",
    "calculate_conditional_limits": "Invert the shared risk model: allowable_room_time_s (or transient counterpart) fixes distance and solves time; safe_distance_m (or transient counterpart) fixes time and solves distance. Reference inputs are bound from the case. Select either operation or both; no prescribed sequence or separate geometry call is required.",
    "compare_predictions_with_observations": "Compare one versioned prediction with an admitted observation; preserve calibration dependence.",
}
TOOL_METRICS = {
    "calculate_geometry_and_removal": GEOMETRY,
    "calculate_conditional_limits": LIMITS,
    "calculate_transmission_metrics": frozenset(METRICS) - GEOMETRY - LIMITS,
}


def input_options(ledger):
    """Expose numerical hypotheses without promoting them into the evidence ledger."""
    options = ledger.options()
    for i, assumption in enumerate(ledger.assumptions.values(), 1):
        if assumption["value"] is not None:
            options[f"assumption:{i}"] = Fact(assumption["subject"], assumption["field"], assumption["value"],
                assumption["unit"], "model_assumption", assumption["basis"],
                context=assumption["statement"], parents=(assumption["key"],))
    for subject in ledger.scenarios:
        for assumption, relation in shared_assumptions(ledger, subject):
            option = f"shared:{assumption['key']}:{subject}"
            options[option] = Fact(subject, assumption["field"], assumption["value"],
                assumption["unit"], "model_assumption", assumption["basis"],
                context=f"Shared from {assumption['subject']}: {assumption['statement']}",
                parents=(assumption["key"], identity(relation)))
    return options


def bind_reference_inputs(action, ledger, requested_metrics):
    """Carry caller-owned inputs and conditions into review and execution."""
    if action.get("action") not in TOOLS or action.get("action") == "compare_predictions_with_observations":
        return action
    definition = ledger.scenarios.get(action.get("subject"), {})
    conditions = action.get("conditions", {})
    if not isinstance(conditions, dict):
        return action
    check_case_inputs(definition, {}, conditions)
    action = {**action, "conditions": {**definition.get("fixed_conditions", {}), **conditions}}
    allowed = TOOL_METRICS.get(action.get("action"))
    if allowed is None:
        return action
    metrics = action.get("metrics", [name for name in requested_metrics if name in allowed])
    if not isinstance(metrics, list) or any(not isinstance(name, str) or name not in allowed for name in metrics):
        return action
    fixed = definition.get("fixed_parameters", {})
    options = input_options(ledger)
    selected = select_facts(action, options)
    present = {fact.field for fact in selected}
    required = set(input_requirements(metrics, present, action["conditions"])["unresolved"])
    references = list(action["facts"])
    for field in sorted(required.intersection(fixed) - present):
        matches = [key for key, fact in options.items() if fact.subject == action["subject"]
                   and fact.field == field and fact.kind == "scenario_constraint"
                   and fact.value == fixed[field]["value"]]
        if not matches:
            raise ValueError(f"The supplied reference input {field} has no scenario-constraint record")
        references.append(matches[0])
    return {**action, "facts": references}


def support_for(ledger, facts, conditions, subject):
    """Describe support gaps without preventing a conditional calculation."""
    selected = {}
    visiting = set()
    issues = []
    invalidated = []

    def require(fact):
        if fact.key in visiting:
            raise ValueError("Cyclic parameter provenance")
        matches = [a for a in ledger.assumptions.values() if a["subject"] == fact.subject
                   and a["field"] == fact.field and a["value"] == fact.value]
        if not matches and fact.kind == "model_assumption" and len(fact.parents) == 2:
            matches = [a for a, relation in shared_assumptions(ledger, fact.subject)
                       if a["key"] == fact.parents[0] and identity(relation) == fact.parents[1]
                       and a["field"] == fact.field and a["value"] == fact.value]
        if matches:
            a = max(matches, key=lambda a: a["reasonableness"])
            selected[a["key"]] = a
            return
        derivations = [c for c in ledger.calculations.values() if fact.key in c.get("output_fact_keys", ())]
        if fact.kind != "derived" or not derivations:
            issues.append(f"Parameter {fact.field} has no completed reasonableness assessment")
            return
        calculation = derivations[-1]
        if not calculation.get("model_review", {}).get("completed", True):
            same_model = ("tool", "subject", "input_fact_keys", "conditions", "assumption_versions",
                          "operator", "basis", "parameterization")
            completed = [c for c in derivations if c.get("model_review", {}).get("completed", True)
                         and all(c.get(k) == calculation.get(k) for k in same_model)]
            if completed:
                calculation = completed[-1]
        if calculation.get("operator") == "transfer_parameter":
            issues.append(f"Transferred {fact.field} has not been assessed in its target scenario")
        dependency = calculation.get("derived_support", {}).get(fact.field, calculation)
        issues.extend(dependency.get("support_issues", ()))
        invalidated.extend(dependency.get("invalidated_dependencies", ()))
        if (not calculation.get("model_review", {}).get("admit", True)
                or not calculation.get("model_review", {}).get("completed", True)):
            issues.append(f"Derived {fact.field}: {calculation['model_review']['reason']}")
        for key in dependency["assumption_versions"]:
            current = ledger.assumptions.get(key, {})
            if not assumption_matches(dependency, key, current):
                issues.append(f"Derived {fact.field} depends on a changed assumption claim or an unavailable assessment")
                invalidated.append(key)
            if current:
                selected[key] = current
        visiting.add(fact.key)
        # A rationale update can change a fact key without changing its claim.
        # The version/claim checks above still govern whether these inputs apply.
        inputs = {identity(row): Fact(**{**row, "parents": tuple(row.get("parents", ()))})
                  for row in calculation.get("input_records", ())}
        inputs.update((f.key, f) for f in input_options(ledger).values())
        for key in dependency["input_fact_keys"]:
            if key in inputs:
                require(inputs[key])
            else:
                issues.append(f"Derived {fact.field} refers to an input no longer in the current catalog")
                invalidated.append(key)
        visiting.remove(fact.key)

    for fact in facts:
        require(fact)
    for field, statement in conditions.items():
        matches = [a for a in ledger.assumptions.values() if a["subject"] == subject
                   and a["field"] == field and a["statement"] == statement]
        if not matches:
            issues.append(f"Condition {field} has no completed reasonableness assessment")
            continue
        a = max(matches, key=lambda a: a["reasonableness"])
        selected[a["key"]] = a
    return selected, list(dict.fromkeys(issues)), list(dict.fromkeys(invalidated))


def scenario_parameter_links(facts, ledger=None):
    """Keep scope provenance even when a shared input feeds a derived parameter."""
    links = []
    seen = set()
    def visit(fact):
        if fact.key in seen:
            return
        seen.add(fact.key)
        if fact.kind == "model_assumption" and len(fact.parents) == 2:
            links.append({"assumption_key": fact.parents[0], "relation_version": fact.parents[1],
                          "target_subject": fact.subject})
        if ledger is not None and fact.kind == "derived":
            for calculation in ledger.calculations.values():
                if fact.key not in calculation.get("output_fact_keys", ()):
                    continue
                for row in calculation.get("scenario_parameter_links", ()):
                    links.append(row)
                records = {identity(row): Fact(**{**row, "parents": tuple(row.get("parents", ()))})
                           for row in calculation.get("input_records", ())}
                records.update((option.key, option) for option in input_options(ledger).values())
                for key in calculation.get("input_fact_keys", ()):
                    if key in records:
                        visit(records[key])
    for fact in facts:
        visit(fact)
    return list({identity(row): row for row in links}.values())


def calculation_record(tool, subject, facts, support, output, *, conditions, basis, **extra):
    record = {"tool": tool, "subject": subject, "input_fact_keys": [f.key for f in facts],
              "input_records": [f.as_record() for f in facts],
              "input_values": {f.field: f.value for f in facts}, "conditions": dict(conditions),
              "assumption_versions": {k: a["version"] for k, a in support.items()},
              "assumption_claims": {k: assumption_claim(a) for k, a in support.items()},
              "basis": basis, "output": output,
              "scenario_parameter_links": scenario_parameter_links(facts),
              "model_version": MODEL_VERSION if set(output).intersection(EXPOSURE_OUTPUTS) else "bazant-bush-scalar-v1", **extra}
    record["version"] = identity(record)
    return record


def output_support(estimate, field, facts, ledger, review, *, derived=False):
    inputs, conditions = output_dependencies(estimate, field, derived=derived)
    selected = [fact for fact in facts if fact.field in inputs]
    support, issues, invalidated = support_for(ledger, selected,
        {k: v for k, v in estimate["conditions"].items() if k in conditions}, estimate["subject"])
    issues.extend(f"Required input {field} was not supplied" for field in inputs if field not in {f.field for f in selected})
    issues.extend(f"Required condition {field} was not supplied" for field in conditions if field not in estimate["conditions"])
    if not derived and estimate["metrics"][field].get("applicability_warning"):
        issues.append(estimate["metrics"][field]["applicability_warning"])
    return {"input_fields": inputs, "condition_fields": conditions,
            "input_fact_keys": [f.key for f in selected],
            "scenario_parameter_links": scenario_parameter_links(selected, ledger),
            "assumption_versions": {k: a["version"] for k, a in support.items()},
            "assumption_claims": {k: assumption_claim(a) for k, a in support.items()},
            "support_issues": issues, "model_review": review, "invalidated_dependencies": invalidated}


def execute_tool(action, ledger, requested_metrics, *, review):
    name = action.get("action")
    if name not in TOOLS:
        raise ValueError("Undeclared deterministic tool")
    if name == "compare_predictions_with_observations":
        return compare(action, ledger, review)
    action = bind_reference_inputs(action, ledger, requested_metrics)
    facts = select_facts(action, input_options(ledger))
    subject = action.get("subject")
    if subject not in ledger.scenarios:
        raise ValueError("Calculations require a reviewed scenario")
    if action.get("operator") != "transfer_parameter" and {f.subject for f in facts} != {subject}:
        raise ValueError("Calculation inputs must belong to the same scenario; transfer must be explicit")
    conditions = action.get("conditions", {})
    if not isinstance(conditions, dict):
        raise ValueError("Conditions must be named statements")
    check_case_inputs(ledger.scenarios[subject], {f.field: f.value for f in facts}, conditions)
    if name == "calibrate_infectiousness":
        required = derivation_inputs(action.get("operator"), {f.field: f.value for f in facts})
        facts = tuple(fact for fact in facts if fact.field in required)
    support, support_issues, invalidated = support_for(ledger, facts, conditions, subject)
    if name == "calibrate_infectiousness":
        # Reuse the parent's support judgment; it does not authorize execution.
        result = derive_parameter(lambda _: review, action, input_options(ledger), {})
        calculation = calculation_record(name, subject, facts, support,
            {f.field: {"value": f.value, "unit": f.unit} for f in result.facts},
            conditions=conditions, basis=action["basis"], operator=action["operator"],
            model_review=review, support_issues=support_issues,
            scenario_parameter_links=scenario_parameter_links(facts, ledger),
            invalidated_dependencies=invalidated,
            output_fact_keys=[f.key for f in result.facts],
            calibration_subjects=sorted({f.subject for f in facts}) if "outbreak" in action["operator"] else [])
        if "outbreak" in action["operator"]:
            calculation["subtask"] = "calibrate_cq_from_outbreak"
            calculation["version"] = identity({k: v for k, v in calculation.items() if k != "version"})
        return ResearchResult(facts=result.facts, findings=result.findings, calculations=(calculation,))
    allowed = TOOL_METRICS[name]
    metrics = action.get("metrics", [m for m in requested_metrics if m in allowed])
    if not isinstance(metrics, list) or any(not isinstance(m, str) or m not in allowed for m in metrics):
        invalid = [m for m in metrics if not isinstance(m, str) or m not in allowed] if isinstance(metrics, list) else metrics
        raise ValueError(f"{name} received invalid metrics {invalid!r}; allowed metric names are {sorted(allowed)!r}. "
                         "Omit metrics to select this tool's requested outputs; no calculation was executed. "
                         "Geometry-derived input parameters are emitted automatically, not selected as metrics.")
    if not metrics and name != "calculate_geometry_and_removal":
        raise ValueError("Select at least one quantity to calculate")
    estimate = evaluate_parameters({f.field: f.value for f in facts}, conditions, tuple(metrics),
        subject=subject, label=action["basis"], provenance={f.field: f.as_record() for f in facts},
        variables=ledger.scenarios[subject].get("calculation_variables", ()))
    estimate["output_contracts"] = {m: ledger.scenarios[subject]["output_contracts"][m]
        for m in metrics if m in ledger.scenarios[subject].get("output_contracts", {})}
    parameterization = action.get("parameterization", action["basis"])
    if not isinstance(parameterization, str) or not parameterization.strip():
        raise ValueError("A calculation needs a named parameterization")
    estimate.update(parameterization=parameterization, label=parameterization)
    estimate.update(assumption_keys=list(support), assumption_versions={k: a["version"] for k, a in support.items()},
                    assumption_claims={k: assumption_claim(a) for k, a in support.items()},
                    assumption_support=list(support.values()),
                    model_review=review, support_issues=support_issues, invalidated_dependencies=invalidated,
                    scenario_parameter_links=scenario_parameter_links(facts, ledger))
    estimate["metric_support"] = {m: output_support(estimate, m, facts, ledger, review) for m in metrics}
    estimate["reasonableness"] = current_support(estimate, ledger.assumptions, ledger=ledger)
    derived = ()
    if name == "calculate_geometry_and_removal" and not estimate["issues"]:
        derived = tuple(Fact(subject, field, row["value"], UNITS[field], "derived", row["formula"],
                            context=action["basis"], parents=tuple(f.key for f in facts
                                if f.field in output_dependencies(estimate, field, derived=True)[0]))
                        for field, row in estimate["derived_parameters"].items())
    calculation = calculation_record(name, subject, facts, support, estimate["metrics"],
        conditions=conditions, basis=action["basis"], output_fact_keys=[f.key for f in derived],
        model_review=review, support_issues=support_issues,
        scenario_parameter_links=scenario_parameter_links(facts, ledger),
        invalidated_dependencies=invalidated,
        derived_parameters=estimate["derived_parameters"], parameterization=parameterization,
        calculation_variables=estimate["calculation_variables"],
        output_contracts=estimate["output_contracts"],
        metric_support=estimate["metric_support"],
        derived_support={f.field: output_support(estimate, f.field, facts, ledger, review, derived=True) for f in derived})
    estimate["calculation_versions"] = [calculation["version"]]
    issues = tuple(dict.fromkeys([*support_issues, *estimate["issues"],
        *(item for row in estimate["metrics"].values() for item in row.get("missing", [])),
        *([f"Model support not established: {review['reason']}"] if not review["admit"] else [])]))
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
    dependency = prediction.get("metric_support", {}).get(metric, prediction)
    support_issues = list(dependency.get("support_issues", ()))
    if (not prediction.get("model_review", {}).get("admit", True)
            or not prediction.get("model_review", {}).get("completed", True)):
        support_issues.append(f"Prediction model support not established: {prediction['model_review']['reason']}")
    lineage, pending, calibration_subjects = set(), list(dependency["input_fact_keys"]), set()
    while pending:
        fact_key = pending.pop()
        if fact_key in lineage:
            continue
        lineage.add(fact_key)
        for calculation in ledger.calculations.values():
            if fact_key in calculation.get("output_fact_keys", ()):
                fact = ledger.facts.get(fact_key)
                provenance = calculation.get("derived_support", {}).get(fact.field, calculation) if fact else calculation
                pending.extend(provenance["input_fact_keys"])
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
                   "input_fact_keys": [*dependency["input_fact_keys"], observation.key],
                   "assumption_versions": dependency["assumption_versions"], "basis": action["basis"],
                   "assumption_claims": dependency.get("assumption_claims", {}),
                   "model_review": review, "support_issues": support_issues}
    calculation["version"] = identity(calculation)
    return ResearchResult(calculations=(calculation,), findings=(
        f"{comparison['category']}: {metric} residual={comparison['residual']:.8g}. {review['reason']}",))


def tool_options(ledger):
    return {key: {"version": c["version"], "tool": c["tool"], "subject": c["subject"],
                  "output": c["output"], "basis": c["basis"], "parameterization": c.get("parameterization"),
                  "current_support": current_support(c, ledger.assumptions, ledger=ledger),
                  "current_computed_metrics": [m for m in c["output"] if current_computation(c, ledger.assumptions, m, ledger=ledger)],
                  "metric_support": {m: current_support(c, ledger.assumptions, metric=m, ledger=ledger)
                                     for m in c.get("metric_support", {})},
                  "model_review": c.get("model_review"), "support_issues": c.get("support_issues", []),
                  "input_values": c.get("input_values", {}), "assumption_versions": c["assumption_versions"],
                  "interpretation": "Computed consequences, not observations. Current computed metrics may have zero evidence support. metric_support qualifies each output; "
                  "current_support describes all selected assumptions, including inputs unused by an individual output."}
            for key, c in ledger.calculation_options().items()}
