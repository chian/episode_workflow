"""A bounded executable model catalog with open-ended agent-proposed assumptions."""

from __future__ import annotations

import math

from ...task_executors.scenario_metrics.evaluate import CONDITIONS, UNITS, evaluate_parameters
from ...task_executors.scenario_metrics.physics import integrated_concentration
from .records import Fact, ResearchResult


DERIVATIONS = {
    "cq_from_steady_outbreak": "Infer native Cq from attack probability or secondary cases, Ns, I, t, Qeff, Qb, pm and sr. Exponential dose response; steady concentration.",
    "cq_from_transient_outbreak": "Infer native Cq from the same counts and exact clean-start concentration integral, V and total removal rate. Initial concentration must explicitly be zero.",
    "transfer_parameter": "Transfer one existing parameter to another subject only with a named, independently reviewed compatibility argument. Never invent a scale factor.",
    "cq_from_emission": "Cq=lambda_q/Qb for one named activity/population.",
    "cq_from_microphysics": "Cq=ci*cv*phi_a, with explicitly supported infectious-virion concentration, infectivity and aerosol volume fraction.",
    "cq_activity_rescaling": "Cq_baseline*phi_activity/phi_baseline, with compatible pathogen, humidity, size-cutoff and activity evidence.",
}


def select_facts(action, options):
    keys = action.get("facts")
    if not isinstance(keys, list) or not keys or any(k not in options for k in keys):
        raise ValueError("Choose facts from the current admitted option catalog")
    facts = tuple(options[k] for k in keys)
    if len({f.field for f in facts}) != len(facts):
        raise ValueError("One value per field is required in each parameterization")
    return facts


def review_model(agent, action, facts, context):
    basis = action.get("basis")
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("Every parameterization requires a named rationale")
    review = agent({
        "operation": "review_research_model", "proposal": action,
        "facts": [f.semantic_record() for f in facts], "context": context,
        "instruction": (
            "Check scientific compatibility independently. Reject mixed events, ungrounded transfer "
            "across activities, populations or variants, invented numbers, and double scaling of a "
            "Cq already calibrated to a variant. Conditions are explicit modeling hypotheses, not "
            "observations. Permit reasonable conditional alternatives with limitations. Check the "
            "scenario's fixed user assumptions are preserved. A fit to its own data is not validation."
        ),
        "response_contract": {"type": "object", "additionalProperties": False,
            "required": ["admit", "reason"], "properties": {
                "admit": {"type": "boolean"}, "reason": {"type": "string", "minLength": 1},
                "limitations": {"type": "array", "items": {"type": "string"}}}},
    })
    if type(review.get("admit")) is not bool or not isinstance(review.get("reason"), str) or not review["reason"].strip():
        raise ValueError("Model review requires an admission decision and rationale")
    limits = review.get("limitations", [])
    if not isinstance(limits, list) or any(not isinstance(v, str) for v in limits):
        raise ValueError("Model limitations must be text")
    return review


def derive_parameter(agent, action, options, context):
    operator = action.get("operator")
    if operator not in DERIVATIONS:
        raise ValueError("Unknown derivation; arbitrary model code is not executed")
    facts = select_facts(action, options)
    subject = action.get("subject")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("A derived parameter needs a subject")
    if operator != "transfer_parameter" and {f.subject for f in facts} != {subject}:
        raise ValueError("Calibration inputs must refer to the same event; explicit transfer is a separate hypothesis")
    review = review_model(agent, action, facts, context)
    if not review["admit"]:
        return ResearchResult(issues=(f"Rejected model: {review['reason']}",))
    v = {f.field: f.value for f in facts}
    field = "quanta_concentration_exhaled_m3"
    kind = "derived"
    if operator == "transfer_parameter":
        if len(facts) != 1:
            raise ValueError("Transfer takes exactly one fact and preserves its numeric value")
        field, value = facts[0].field, facts[0].value
    elif operator == "cq_from_emission":
        value = v["quanta_emission_rate_s"] / v["breathing_flow_m3_s"]
    elif operator == "cq_from_microphysics":
        value = v["microscopic_infectivity_per_virion"] * v["pathogen_concentration_virions_m3"] * v["aerosol_volume_fraction"]
    elif operator == "cq_activity_rescaling":
        value = v["quanta_concentration_exhaled_m3"] * v["activity_aerosol_volume_fraction"] / v["baseline_aerosol_volume_fraction"]
    else:
        attack = v.get("attack_probability")
        if attack is None:
            attack = v["secondary_case_count"] / v["susceptible_count"]
        if not 0 <= attack < 1:
            raise ValueError("Finite Cq inference requires 0 <= attack probability < 1")
        factor = v["index_case_count"] * v["breathing_flow_m3_s"]**2 * v["mask_penetration"]**2 * v["relative_transmissibility"]
        if operator == "cq_from_steady_outbreak":
            factor *= v["exposure_time_s"] / v["removal_capacity_m3_s"]
        else:
            if v["initial_concentration_quanta_m3"] != 0:
                raise ValueError("This calibration operator requires an explicit clean start")
            factor *= integrated_concentration(v["exposure_time_s"], 1, v["room_volume_m3"], v["removal_rate_s"], 0)
        if factor <= 0:
            raise ValueError("No identifiable emission parameter under these assumptions")
        value = -math.log1p(-attack) / factor
    if not math.isfinite(value):
        raise ValueError("Derived parameter is not finite")
    fact = Fact(subject, field, value, UNITS[field], kind,
                f"{operator}: {action['basis']}; review: {review['reason']}",
                context="Conditional on the selected input provenance and model", parents=tuple(f.key for f in facts))
    return ResearchResult((fact,), findings=(f"Derived {field}={value:.8g} for {subject}. "
        "An outbreak inversion is calibration, not independent validation.", *review.get("limitations", [])))


def evaluate_model(agent, action, options, context, metrics, *, assumptions=()):
    facts = select_facts(action, options)
    subject = action.get("subject")
    if {f.subject for f in facts} != {subject}:
        raise ValueError("All scenario inputs must belong to this subject; transfer must be explicit")
    selected = {f.field: f.value for f in facts}
    selected_assumptions = []
    for field, value in selected.items():
        supported = [a for a in assumptions if a["subject"] == subject and a["field"] == field
                     and a["value"] == value and a["reasonableness"] > 0]
        if not supported:
            raise ValueError(f"Parameter {field} lacks an evidence-linked reasonableness assessment")
        selected_assumptions.append(max(supported, key=lambda a: a["reasonableness"]))
    conditions = action.get("conditions", {})
    if not isinstance(conditions, dict) or any(k not in CONDITIONS for k in conditions):
        raise ValueError("Unknown model condition")
    for field, statement in conditions.items():
        supported = [a for a in assumptions if a["subject"] == subject and a["field"] == field
                     and a["statement"] == statement and a["reasonableness"] > 0]
        if not supported:
            raise ValueError(f"Condition {field} lacks an evidence-linked reasonableness assessment")
        selected_assumptions.append(max(supported, key=lambda a: a["reasonableness"]))
    review = review_model(agent, action, facts, context)
    if not review["admit"]:
        return ResearchResult(issues=(f"Rejected model: {review['reason']}",))
    result = evaluate_parameters({f.field: f.value for f in facts}, conditions, metrics,
                                subject=subject, label=action["basis"],
                                provenance={f.field: f.as_record() for f in facts})
    result["assumption_keys"] = [a["key"] for a in selected_assumptions]
    result["assumption_support"] = selected_assumptions
    result["reasonableness"] = min((a["reasonableness"] for a in selected_assumptions), default=0)
    missing = tuple(sorted({item for m in result["metrics"].values() for item in m.get("missing", [])}))
    return ResearchResult(estimates=(result,), findings=tuple(review.get("limitations", [])), issues=missing)
