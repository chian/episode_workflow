"""Evaluate one named parameterization, preserving missingness and provenance."""

from __future__ import annotations

import math
from typing import Mapping

from .catalog import METRICS


UNITS = {
    "breathing_flow_m3_s": "m3/s", "quanta_concentration_exhaled_m3": "quanta/m3",
    "mask_penetration": "fraction", "relative_transmissibility": "scalar",
    "removal_capacity_m3_s": "m3/s", "removal_rate_s": "1/s",
    "room_volume_m3": "m3", "room_height_m": "m", "floor_area_m2": "m2",
    "susceptible_count": "person", "occupant_count": "person", "index_case_count": "person",
    "secondary_case_count": "person", "attack_probability": "fraction",
    "exposure_time_s": "s", "risk_tolerance": "scalar",
    "air_exchange_rate_s": "1/s", "ventilation_flow_m3_s": "m3/s",
    "recirculation_flow_m3_s": "m3/s", "filter_efficiency": "fraction",
    "deactivation_rate_s": "1/s", "settling_speed_m_s": "m/s",
    "effective_radius_m": "m", "particle_density_kg_m3": "kg/m3",
    "air_density_kg_m3": "kg/m3", "air_dynamic_viscosity_pa_s": "Pa*s",
    "gravity_m_s2": "m/s2", "initial_concentration_quanta_m3": "quanta/m3",
    "mouth_area_m2": "m2", "entrainment_coefficient": "scalar",
    "neighbor_distance_m": "m", "plume_encounter_probability": "fraction",
    "breath_volume_m3": "m3", "clearance_fraction": "fraction",
    "quanta_emission_rate_s": "quanta/s",
    "initial_radius_m": "m", "solute_volume_fraction": "fraction", "relative_humidity": "fraction",
    "evaporation_coefficient_m2_s": "m2/s", "microscopic_infectivity_per_virion": "1/virion",
    "pathogen_concentration_virions_m3": "virion/m3", "aerosol_volume_fraction": "fraction",
    "activity_aerosol_volume_fraction": "fraction", "baseline_aerosol_volume_fraction": "fraction",
}

POSITIVE = frozenset((
    "breathing_flow_m3_s", "room_volume_m3", "room_height_m", "floor_area_m2",
    "particle_density_kg_m3", "air_dynamic_viscosity_pa_s", "gravity_m_s2",
    "mouth_area_m2", "entrainment_coefficient", "neighbor_distance_m",
    "occupant_count", "index_case_count",
    "initial_radius_m", "evaporation_coefficient_m2_s", "baseline_aerosol_volume_fraction",
))
FRACTIONS = frozenset(k for k, unit in UNITS.items() if unit == "fraction")
CONDITIONS = {
    "well_mixed": "Concentration is treated as spatially uniform outside the explicitly modeled jet.",
    "single_infectious_source": "One continuously present infectious person emits at a constant rate.",
    "emissions_stopped": "No further emissions or other concentration inputs occur during the modeled clearance interval.",
    "uniform_breathing_and_masks": "Emitter and recipients share the specified Qb and pm; susceptibility is represented by sr.",
    "continuous_unmasked_jet": "Continuous unmasked respiratory jet; not masked flow, a cough or a sneeze.",
    "stokes_particles": "Spherical particles at low Reynolds number; radius is an effective model input.",
    "random_orientation_and_spacing": "Random relative orientations and uniform planar occupancy.",
    "equilibrium_evaporation": "Equilibrium hygroscopic approximation at stated humidity; theta corresponds to the assumed temperature.",
    "uniform_virion_infectivity": "Uniform infectious virion concentration/infectivity across the specified aerosol distribution; RNA is not silently equated with infectious virions.",
}

DEFAULT_METRICS = (
    "quanta_emission_rate_s", "removal_rate_s", "transmission_rate_s",
    "indoor_reproductive_number", "individual_infection_probability", "expected_secondary_cases",
    "first_transmission_probability", "cumulative_exposure_bound_person_s",
    "exposure_time_bound_s", "total_occupancy_bound", "required_removal_capacity_m3_s",
    "transient_indoor_reproductive_number", "transient_exposure_time_bound_s",
    "transient_total_occupancy_bound", "critical_distance_m", "risk_threshold_distance_m",
    "jet_corrected_reproductive_number", "jet_corrected_time_bound_s",
    "air_mixing_time_s", "concentration_relaxation_time_s", "air_clearance_time_s",
    "critical_aerosol_radius_m", "relative_risk_index",
)


def validate_parameter(field, value, unit):
    if field not in UNITS or unit != UNITS[field]:
        raise ValueError(f"{field} requires canonical unit {UNITS.get(field)}")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} requires a finite number")
    if value < 0 or (field in POSITIVE and value == 0):
        raise ValueError(f"{field} is outside its physical domain")
    if field in FRACTIONS and value > 1:
        raise ValueError(f"{field} must be <= 1")
    if field in {"occupant_count", "index_case_count", "secondary_case_count"} and int(value) != value:
        raise ValueError(f"{field} must be an integer count")


def metric_conditions(name):
    if name not in METRICS:
        return set()
    regime = METRICS[name].regime
    needed = {"well_mixed", "single_infectious_source", "uniform_breathing_and_masks"}
    if regime == "stokes":
        needed = {"stokes_particles"}
    elif regime == "evaporation":
        needed = {"equilibrium_evaporation"}
    elif regime == "microphysics":
        needed = {"uniform_virion_infectivity"}
    elif regime == "concentration_dynamics":
        needed = {"well_mixed"}
    elif regime == "source_off":
        needed = {"well_mixed", "emissions_stopped"}
    if regime in {"jet", "random_jet"}:
        needed.add("continuous_unmasked_jet")
    if regime == "random_jet":
        needed.add("random_orientation_and_spacing")
    return needed


def output_is_resolved(row):
    """A supported exclusion resolves scope, but is never a numerical estimate."""
    applicability = row.get("applicability", {})
    return row.get("status") == "calculated" or (
        row.get("status") == "inapplicable" and bool(applicability.get("reason"))
        and bool(applicability.get("inputs")))


def evaluate_parameters(parameters, conditions, metrics, *, subject, label, provenance=None):
    """All results describe the selected assumptions, not an unconditional safety claim."""
    for name, value in parameters.items():
        validate_parameter(name, value, UNITS.get(name))
    if not isinstance(conditions, Mapping) or any(k not in CONDITIONS for k in conditions):
        raise ValueError("Undeclared model condition")
    for name, basis in conditions.items():
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError(f"Named basis required for {name}")
    values, outputs, issues = dict(parameters), {}, []
    derivations = {}

    def derive(name, inputs, formula, function):
        if all(k in values for k in inputs):
            answer = function(*(values[k] for k in inputs))
            if name in values:
                if not math.isclose(answer, values[name], rel_tol=0.02, abs_tol=1e-12):
                    issues.append(f"Inconsistent {name}: supplied={values[name]:.8g}, {formula}={answer:.8g}")
            else:
                values[name] = answer
                derivations[name] = {"inputs": list(inputs), "formula": formula, "value": answer}

    derive("room_volume_m3", ("floor_area_m2", "room_height_m"), "A*H", lambda a, h: a*h)
    derive("room_height_m", ("room_volume_m3", "floor_area_m2"), "V/A", lambda v, a: v/a)
    derive("ventilation_flow_m3_s", ("air_exchange_rate_s", "room_volume_m3"), "lambda_a*V", lambda a, v: a*v)
    derive("air_exchange_rate_s", ("ventilation_flow_m3_s", "room_volume_m3"), "Q/V", lambda q, v: q/v)
    if "stokes_particles" in conditions and "settling_speed_m_s" not in values:
        m = METRICS["settling_speed_m_s"]
        if all(k in values for k in m.inputs):
            values[m.name] = m.function({k: values[k] for k in m.inputs})
            derivations[m.name] = {"inputs": list(m.inputs), "formula": m.formula, "value": values[m.name]}
    derive("removal_capacity_m3_s", ("ventilation_flow_m3_s", "recirculation_flow_m3_s",
           "filter_efficiency", "deactivation_rate_s", "room_volume_m3", "settling_speed_m_s", "floor_area_m2"),
           "Q+pf*Qr+lambda_v*V+vs*A", lambda q, qr, pf, lv, v, vs, a: q+pf*qr+lv*v+vs*a)
    derive("removal_capacity_m3_s", ("removal_rate_s", "room_volume_m3"), "lambda*V", lambda r, v: r*v)
    derive("removal_rate_s", ("removal_capacity_m3_s", "room_volume_m3"), "Qeff/V", lambda q, v: q/v)
    if "single_infectious_source" in conditions:
        if parameters.get("index_case_count", 1) != 1:
            issues.append("The requested single-source model conflicts with index_case_count")
    if "susceptible_count" in values and "occupant_count" in values and values["susceptible_count"] > values["occupant_count"]-1:
        issues.append("susceptible_count exceeds N-1")

    def compute(name):
        if name in outputs:
            return outputs[name]
        if name not in METRICS:
            if name not in values:
                return {"status": "missing_inputs", "missing": [name]}
            return {"status": "calculated", "value": values[name], "limit": "finite", "unit": UNITS[name]}
        m = METRICS[name]
        row = {**m.as_record(), "value": None, "limit": None, "status": "missing_inputs", "missing": []}
        outputs[name] = row
        if issues:
            row.update(status="inconsistent_inputs", missing=list(issues))
            return row

        def exclude(reason, inputs):
            row.update(status="inapplicable", missing=[], applicability={"reason": reason, "inputs": inputs})
            return row

        if m.regime in {"jet", "random_jet"} and "mask_penetration" in values and values["mask_penetration"] != 1:
            return exclude("The continuous-jet model requires unmasked emission and inhalation",
                           {"mask_penetration": values["mask_penetration"]})
        if m.regime == "clean_start_interpolation" and "initial_concentration_quanta_m3" in values and values["initial_concentration_quanta_m3"] != 0:
            return exclude("The interpolation assumes a clean start",
                           {"initial_concentration_quanta_m3": values["initial_concentration_quanta_m3"]})
        if m.regime == "jet" and "neighbor_distance_m" in m.inputs and values.get("neighbor_distance_m", math.inf) < 0.1:
            return exclude("Jet far-field approximation is not valid this close to the mouth",
                           {"neighbor_distance_m": values["neighbor_distance_m"]})
        needed = metric_conditions(name)
        row["missing"] = [f"condition:{c}" for c in sorted(needed - set(conditions))]
        args = {}
        for dep in m.inputs:
            if dep in values:
                args[dep] = values[dep]
                continue
            child = compute(dep)
            if child["status"] == "inapplicable" and output_is_resolved(child):
                return exclude(f"Required quantity {dep} is inapplicable: {child['applicability']['reason']}",
                               child["applicability"]["inputs"])
            if child["status"] != "calculated":
                row["missing"].extend(child.get("missing") or [dep])
            elif child.get("limit") == "unbounded":
                args[dep] = math.inf
            else:
                args[dep] = child["value"]
        row["missing"] = sorted(set(row["missing"]))
        if row["missing"]:
            return row
        if m.regime in {"jet", "random_jet"} and "mask_penetration" not in values:
            row.update(status="missing_inputs", missing=["mask_penetration"])
            return row
        try:
            answer = m.function(args)
            if math.isnan(answer) or answer < 0:
                raise ValueError("Nonphysical or undefined result")
            row.update(status="calculated", value=answer if math.isfinite(answer) else None,
                       limit="finite" if math.isfinite(answer) else "unbounded")
            if name in {"critical_distance_m", "risk_threshold_distance_m"} and 0 < answer < 0.1:
                row["applicability_warning"] = "The inferred distance lies below the approximate jet virtual-origin scale; do not interpret it as a validated separation."
            values[name] = answer
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            row.update(status="undefined", missing=[str(exc)])
        return row

    requested = {name: compute(name) for name in metrics}
    return {"subject": subject, "label": label, "metrics": requested,
            "parameters": dict(parameters), "derived_parameters": derivations,
            "conditions": dict(conditions), "input_provenance": provenance or {},
            "issues": issues,
            "interpretation": "Conditional model estimates; crossing a budget boundary is not a guarantee of safety.",
            "validation": "No independent validation is implied by solving or reusing a calibration equation."}
