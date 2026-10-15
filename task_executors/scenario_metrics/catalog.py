"""Dependency contracts, units, equations and applicability for each estimate."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping

from ..cumulative_exposure_bound import transient_time_bound
from ..effective_removal_rate import stokes_settling_speed
from ..inhalation_hazard import steady_state_inhalation_transmission_rate
from .physics import (
    clearance_time, critical_distance, critical_radius, exact_time_bound,
    integrated_concentration, maximum_total_occupancy, ratio,
    threshold_distance, transient_concentration, well_mixed_distance,
)
from .exposure import EXPOSURE_OUTPUTS, FIXED_FIELDS, MODEL_VERSION, calculate_exposure, model_inputs

PAPER = "https://doi.org/10.1073/pnas.2018995118"

# Meanings of model inputs, independent of any selected scenario or value.
# These keep scope comparisons about the input itself rather than its effect on
# a calculated risk. The paper distinguishes subpopulation/strain scaling from
# exhaled quanta and treats masks and ventilation as separate inputs.
PARAMETER_MEANINGS = {
    "breathing_flow_m3_s": "Mean volume flow of air breathed by a person; can vary with physiology and respiratory activity.",
    "quanta_concentration_exhaled_m3": "Infectious quanta per volume of exhaled air before masks; depends on the source and respiratory or vocal activity.",
    "mask_penetration": "Fraction of respiratory aerosol passing through a face covering; depends on covering material and fit.",
    "relative_transmissibility": "Relative susceptibility or transmissibility multiplier for a subpopulation or viral strain; the paper explicitly varies it by age group and strain.",
    "deactivation_rate_s": "Airborne biological deactivation rate, separate from ventilation and filtration removal.",
    "effective_radius_m": "Representative respiratory aerosol radius used in settling calculations; depends on droplet properties and emission context.",
}


@dataclass(frozen=True)
class Metric:
    name: str
    unit: str
    inputs: tuple[str, ...]
    formula: str
    function: Callable[[Mapping[str, float]], float]
    reference: str = "Eq. 5"
    regime: str = "well_mixed"
    interpretation: str = "Conditional model estimate, not a guarantee of safety."

    def as_record(self):
        record = {"name": self.name, "unit": self.unit, "inputs": list(self.inputs),
                "formula": self.formula, "reference": self.reference,
                "source": PAPER, "regime": self.regime,
                "parameter_constraints": self.parameter_constraints(),
                "interpretation": self.interpretation}
        if self.name in EXPOSURE_OUTPUTS:
            operation, background = EXPOSURE_OUTPUTS[self.name]
            record.update(operation=operation, background=background,
                          model_family=MODEL_VERSION, near_field=self.regime.rsplit("_", 1)[1],
                          fixed_fields=list(FIXED_FIELDS[operation]), result_form="scalar")
        return record

    def parameter_constraints(self):
        """One contract for executable exclusions and agent capability information."""
        constraints = []
        jet = self.regime in {"jet", "random_jet"} or self.regime.endswith("_jet")
        if jet:
            constraints.append({"field": "mask_penetration", "operator": "equal", "value": 1,
                "reason": "The continuous-jet model requires unmasked emission and inhalation"})
        if self.regime == "clean_start_interpolation":
            constraints.append({"field": "initial_concentration_quanta_m3", "operator": "equal", "value": 0,
                "reason": "The interpolation assumes a clean start"})
        if jet and "neighbor_distance_m" in self.inputs:
            constraints.append({"field": "neighbor_distance_m", "operator": "minimum", "value": 0.1,
                "reason": "Jet far-field approximation is not valid this close to the mouth"})
        return constraints


def metric(name, unit, inputs, formula, function, reference="Eq. 5", regime="well_mixed", interpretation=None):
    kwargs = {} if interpretation is None else {"interpretation": interpretation}
    return Metric(name, unit, tuple(inputs.split()), formula, function, reference, regime, **kwargs)


HAZARD_FIELDS = ("breathing_flow_m3_s quanta_concentration_exhaled_m3 "
                 "mask_penetration relative_transmissibility removal_capacity_m3_s")
TRANSIENT_FIELDS = ("exposure_time_s emission_rate_quanta_s room_volume_m3 "
                    "removal_rate_s initial_concentration_quanta_m3")


def transient_args(v):
    return {"time_s": v["exposure_time_s"], **{k: v[k] for k in TRANSIENT_FIELDS.split()[1:]}}


_METRICS = (
    metric("equilibrium_droplet_radius_m", "m", "initial_radius_m solute_volume_fraction relative_humidity", "r0*(phi_s/(1-RH))^(1/3)", lambda v: v["initial_radius_m"] * (v["solute_volume_fraction"]/(1-v["relative_humidity"]))**(1/3), "The Well-Mixed Room, evaporation", "evaporation"),
    metric("droplet_evaporation_time_s", "s", "initial_radius_m evaporation_coefficient_m2_s relative_humidity", "r0^2/(theta*(1-RH))", lambda v: v["initial_radius_m"]**2/(v["evaporation_coefficient_m2_s"]*(1-v["relative_humidity"])), "The Well-Mixed Room, evaporation", "evaporation"),
    metric("infectious_dose_virions", "virion", "microscopic_infectivity_per_virion", "1/ci", lambda v: ratio(1, v["microscopic_infectivity_per_virion"]), "Infectiousness", "microphysics", "Characteristic exponential dose giving probability 1-exp(-1), not a hard minimum infectious dose. Requires an infectious-virion basis, not unconverted RNA counts."),
    metric("microphysical_quanta_concentration_m3", "quanta/m3", "microscopic_infectivity_per_virion pathogen_concentration_virions_m3 aerosol_volume_fraction", "ci*cv*phi_a", lambda v: math.prod(v.values()), "Eq. 4, uniform virion concentration and infectivity", "microphysics"),
    metric("activity_rescaled_quanta_concentration_m3", "quanta/m3", "quanta_concentration_exhaled_m3 activity_aerosol_volume_fraction baseline_aerosol_volume_fraction", "Cq_baseline*phi_activity/phi_baseline", lambda v: v["quanta_concentration_exhaled_m3"] * v["activity_aerosol_volume_fraction"] / v["baseline_aerosol_volume_fraction"], "Fig. 2 activity rescaling", "microphysics", "Requires compatible pathogen, infectivity, humidity and size-cutoff assumptions for both measured distributions."),
    metric("quanta_emission_rate_s", "quanta/s", "breathing_flow_m3_s quanta_concentration_exhaled_m3", "Qb*Cq (before masks)", lambda v: v["breathing_flow_m3_s"] * v["quanta_concentration_exhaled_m3"], "Eq. 4"),
    metric("emission_rate_quanta_s", "quanta/s", "quanta_emission_rate_s mask_penetration", "Qb*Cq*pm (one source)", lambda v: v["quanta_emission_rate_s"] * v["mask_penetration"], "Eq. 1"),
    metric("settling_speed_m_s", "m/s", "effective_radius_m particle_density_kg_m3 air_density_kg_m3 air_dynamic_viscosity_pa_s gravity_m_s2", "2*(rho_d-rho_a)*g*r^2/(9*mu)", lambda v: stokes_settling_speed(v["effective_radius_m"], **{k: v[k] for k in ("particle_density_kg_m3", "air_density_kg_m3", "air_dynamic_viscosity_pa_s", "gravity_m_s2")}), "The Well-Mixed Room", "stokes"),
    metric("critical_aerosol_radius_m", "m", "air_exchange_rate_s room_height_m air_dynamic_viscosity_pa_s particle_density_kg_m3 air_density_kg_m3 gravity_m_s2", "sqrt(9*lambda_a*H*mu/(2*g*(rho_d-rho_a)))", lambda v: critical_radius(**v), "The Well-Mixed Room", "stokes"),
    metric("air_mixing_time_s", "s", "room_volume_m3 ventilation_flow_m3_s recirculation_flow_m3_s", "V/(Q+Qr)", lambda v: ratio(v["room_volume_m3"], v["ventilation_flow_m3_s"] + v["recirculation_flow_m3_s"]), "The Well-Mixed Room", "bulk_flow", interpretation="Bulk-flow mixing timescale estimate; does not establish actual spatial uniformity."),
    metric("concentration_relaxation_time_s", "s", "removal_rate_s", "1/lambda", lambda v: ratio(1, v["removal_rate_s"]), "Eq. 1", "concentration_dynamics"),
    metric("air_clearance_time_s", "s", "removal_rate_s clearance_fraction", "-log(1-f)/lambda", lambda v: clearance_time(**v), "Eq. 1, source-off solution", "source_off", interpretation="Time to remove the specified fraction AFTER emissions stop, not while occupied by an infectious source."),
    metric("steady_concentration_quanta_m3", "quanta/m3", "emission_rate_quanta_s removal_capacity_m3_s", "Qb*Cq*pm/Qeff", lambda v: v["emission_rate_quanta_s"] / v["removal_capacity_m3_s"], "Eq. 1", "steady"),
    metric("well_mixed_dilution_factor", "fraction", "breathing_flow_m3_s removal_capacity_m3_s", "Qb/Qeff", lambda v: v["breathing_flow_m3_s"] / v["removal_capacity_m3_s"], "Beyond the Well-Mixed Room"),
    metric("transmission_rate_s", "1/s", HAZARD_FIELDS, "Qb^2*Cq*pm^2*sr/Qeff", lambda v: steady_state_inhalation_transmission_rate(**v), "Eqs. 2, 5", "steady"),
    metric("individual_dose", "quanta", "transmission_rate_s exposure_time_s", "beta*t", lambda v: v["transmission_rate_s"] * v["exposure_time_s"], "Eq. 2, steady integral", "steady"),
    metric("indoor_reproductive_number", "scalar", "susceptible_count individual_dose", "Ns*beta*t", lambda v: v["susceptible_count"] * v["individual_dose"], "Eq. 3, linearized", "steady", "Linearized expected transmissions per one infectious person; not a finite-population count at high dose."),
    metric("individual_infection_probability", "probability", "individual_dose", "1-exp(-dose)", lambda v: -math.expm1(-v["individual_dose"]), "Exponential dose response", "steady"),
    metric("expected_secondary_cases", "person", "susceptible_count individual_infection_probability", "Ns*(1-exp(-dose))", lambda v: v["susceptible_count"] * v["individual_infection_probability"], "Finite-population exponential dose response", "steady"),
    metric("first_transmission_probability", "probability", "indoor_reproductive_number", "1-exp(-Rin)", lambda v: -math.expm1(-v["indoor_reproductive_number"]), "Eq. 3 footnote, independent recipients", "steady"),
    metric("cumulative_exposure_bound_person_s", "person*s", "risk_tolerance transmission_rate_s", "epsilon/beta", lambda v: ratio(v["risk_tolerance"], v["transmission_rate_s"]), regime="steady"),
    metric("exposure_time_bound_s", "s", "risk_tolerance transmission_rate_s susceptible_count", "epsilon/(Ns*beta)", lambda v: ratio(v["risk_tolerance"], v["susceptible_count"] * v["transmission_rate_s"]), regime="steady"),
    metric("susceptible_bound", "person", "risk_tolerance individual_dose", "epsilon/(beta*t)", lambda v: ratio(v["risk_tolerance"], v["individual_dose"]), regime="steady"),
    metric("total_occupancy_bound", "person", "susceptible_bound", "floor(Ns_max)+1", lambda v: maximum_total_occupancy(v["susceptible_bound"]), "Eq. 5, integer inversion", "steady", "Includes one infectious person; threshold boundary uses <=, not a strict < guarantee."),
    metric("risk_budget_fraction", "scalar", "indoor_reproductive_number risk_tolerance", "Rin/epsilon", lambda v: ratio(v["indoor_reproductive_number"], v["risk_tolerance"]) if v["indoor_reproductive_number"] else 0.0, regime="steady"),
    metric("required_removal_capacity_m3_s", "m3/s", "susceptible_count exposure_time_s breathing_flow_m3_s quanta_concentration_exhaled_m3 mask_penetration relative_transmissibility risk_tolerance", "Ns*t*Qb^2*Cq*pm^2*sr/epsilon", lambda v: (ratio(v["susceptible_count"] * v["exposure_time_s"] * v["breathing_flow_m3_s"]**2 * v["quanta_concentration_exhaled_m3"] * v["mask_penetration"]**2 * v["relative_transmissibility"], v["risk_tolerance"]) if all(v[k] for k in ("susceptible_count", "exposure_time_s", "quanta_concentration_exhaled_m3", "mask_penetration", "relative_transmissibility")) else 0.0), "Eq. 5, removal inversion", "steady"),
    metric("relative_risk_index", "scalar", "occupant_count exposure_time_s breathing_flow_m3_s quanta_concentration_exhaled_m3 mask_penetration ventilation_flow_m3_s", "N*t*Cq*Qb^2*pm^2/Q", lambda v: ratio(v["occupant_count"] * v["exposure_time_s"] * v["quanta_concentration_exhaled_m3"] * v["breathing_flow_m3_s"]**2 * v["mask_penetration"]**2, v["ventilation_flow_m3_s"]), "Eq. 6", "steady", "Ventilation-only index, using N rather than Ns; not interchangeable with Rin."),
    metric("transient_concentration_quanta_m3", "quanta/m3", TRANSIENT_FIELDS, "C0*exp(-lambda*t)+P/(lambda*V)*(1-exp(-lambda*t))", lambda v: transient_concentration(**transient_args(v)), "Eq. 1, exact single-bin solution", "transient"),
    metric("integrated_concentration_quanta_s_m3", "quanta*s/m3", TRANSIENT_FIELDS, "Integral(C(t),0,t)", lambda v: integrated_concentration(**transient_args(v)), "Eq. 1, exact single-bin integral", "transient"),
    metric("transient_individual_dose", "quanta", "integrated_concentration_quanta_s_m3 breathing_flow_m3_s mask_penetration relative_transmissibility", "Qb*pm*sr*Integral(C(t),0,t)", lambda v: math.prod(v.values()), "Eqs. 1-2", "transient"),
    metric("transient_indoor_reproductive_number", "scalar", "susceptible_count transient_individual_dose", "Ns*transient_dose", lambda v: math.prod(v.values()), "Eqs. 1-3, exact integrated hazard", "transient"),
    metric("transient_individual_infection_probability", "probability", "transient_individual_dose", "1-exp(-transient_dose)", lambda v: -math.expm1(-v["transient_individual_dose"]), "Exponential dose response", "transient"),
    metric("transient_first_transmission_probability", "probability", "transient_indoor_reproductive_number", "1-exp(-transient_Rin)", lambda v: -math.expm1(-v["transient_indoor_reproductive_number"]), "Independent exponential dose response", "transient"),
    metric("transient_expected_secondary_cases", "person", "susceptible_count transient_individual_infection_probability", "Ns*(1-exp(-transient_dose))", lambda v: math.prod(v.values()), "Finite-population exponential dose response", "transient"),
    metric("transient_exposure_time_bound_s", "s", "risk_tolerance susceptible_count breathing_flow_m3_s mask_penetration relative_transmissibility emission_rate_quanta_s room_volume_m3 removal_rate_s initial_concentration_quanta_m3", "Solve Ns*integrated_hazard(t)=epsilon", lambda v: exact_time_bound(**v), "Eqs. 1-3, numerical inversion", "transient"),
    metric("transient_susceptible_bound", "person", "risk_tolerance transient_individual_dose", "epsilon/transient_dose", lambda v: ratio(v["risk_tolerance"], v["transient_individual_dose"]), "Eqs. 1-3", "transient"),
    metric("transient_total_occupancy_bound", "person", "transient_susceptible_bound", "floor(Ns_transient_max)+1", lambda v: maximum_total_occupancy(v["transient_susceptible_bound"]), "Eqs. 1-3, integer inversion", "transient"),
    metric("transient_interpolation_time_bound_s", "s", "cumulative_exposure_bound_person_s removal_rate_s susceptible_count initial_concentration_quanta_m3", "(B+sqrt(B^2+4*Ns*B/lambda))/(2*Ns)", lambda v: transient_time_bound(v["cumulative_exposure_bound_person_s"], v["removal_rate_s"], v["susceptible_count"]), "Existing transient interpolation; not exact integrated hazard", "clean_start_interpolation", "Approximation reported separately; compare against exact transient inversion before interpreting it as a limit."),
    metric("critical_distance_m", "m", "mouth_area_m2 entrainment_coefficient well_mixed_dilution_factor", "sqrt(Am)/(alpha*fd)", lambda v: critical_distance(**v), "Beyond the Well-Mixed Room, concentration crossover", "jet", "Jet concentration equals background here; NOT the distance at which infection risk vanishes."),
    metric("jet_dilution_ratio", "fraction", "mouth_area_m2 entrainment_coefficient neighbor_distance_m", "sqrt(Am)/(alpha*x)", lambda v: math.sqrt(v["mouth_area_m2"]) / (v["entrainment_coefficient"] * v["neighbor_distance_m"]), "Beyond the Well-Mixed Room", "jet"),
    metric("jet_to_background_ratio", "scalar", "critical_distance_m neighbor_distance_m", "xc/x", lambda v: v["critical_distance_m"] / v["neighbor_distance_m"], "Beyond the Well-Mixed Room", "jet"),
    metric("respiratory_jet_multiplier", "scalar", "plume_encounter_probability jet_to_background_ratio susceptible_count", "pj*xc/(Ns*x)", lambda v: v["plume_encounter_probability"] * v["jet_to_background_ratio"] / v["susceptible_count"], "Eq. 7", "jet"),
    metric("jet_corrected_reproductive_number", "scalar", "indoor_reproductive_number respiratory_jet_multiplier", "Rin*(1+jet_multiplier)", lambda v: v["indoor_reproductive_number"] * (1 + v["respiratory_jet_multiplier"]), "Eq. 7", "jet"),
    metric("risk_threshold_distance_m", "m", "risk_tolerance indoor_reproductive_number susceptible_count plume_encounter_probability critical_distance_m", "Rin*pj*xc/(Ns*(epsilon-Rin))", lambda v: threshold_distance(**v), "Eq. 7, distance inversion", "jet", "Infinity: no finite separation meets the budget. Zero: this model imposes no positive separation; neither is a universal safety claim."),
    metric("jet_corrected_time_bound_s", "s", "risk_tolerance transmission_rate_s susceptible_count respiratory_jet_multiplier", "epsilon/(Ns*beta*(1+jet_multiplier))", lambda v: ratio(v["risk_tolerance"], v["susceptible_count"] * v["transmission_rate_s"] * (1 + v["respiratory_jet_multiplier"])), "Eq. 7, time inversion", "jet"),
    metric("close_contact_equivalent_time_s", "s", "breath_volume_m3 breathing_flow_m3_s well_mixed_dilution_factor", "Vb/(Qb*fd)", lambda v: v["breath_volume_m3"] / (v["breathing_flow_m3_s"] * v["well_mixed_dilution_factor"]), "Beyond the Well-Mixed Room", "jet", "Time in background giving the dose of one undiluted exhaled breath; not an exposure limit."),
    metric("random_orientation_plume_probability", "probability", "entrainment_coefficient", "atan(alpha)/pi", lambda v: math.atan(v["entrainment_coefficient"]) / math.pi, "Eq. 7 discussion", "random_jet"),
    metric("random_spacing_m", "m", "floor_area_m2 occupant_count", "sqrt(A/N)", lambda v: math.sqrt(v["floor_area_m2"] / v["occupant_count"]), "Eq. 7 discussion", "random_jet"),
)

METRICS = {item.name: item for item in _METRICS}

WELL_MIXED_DISTANCE = metric(
    "risk_threshold_distance_m", "m", "risk_tolerance indoor_reproductive_number",
    "0 if R_in <= epsilon, otherwise no finite separation",
    lambda v: well_mixed_distance(**v), "Eq. 5, spatially uniform risk criterion",
    "well_mixed_distance",
    "Steady-background criterion, conditional on negligible near-field enhancement throughout the modeled occupied region. "
    "Zero means no positive minimum imposed by the spatially uniform model, not safety at contact. "
    "Infinity means separation cannot meet the room-risk criterion. The boundary uses <=; "
    "neither branch guarantees safety or models mask leakage, local plumes or other routes.")


def _exposure_metric(name, near_field):
    operation, background = EXPOSURE_OUTPUTS[name]
    inputs = (*model_inputs(background, near_field), *FIXED_FIELDS[operation])
    if operation != "evaluate_R_in":
        inputs += ("risk_tolerance",)
    formula = {
        "solve_time": "Solve B(t) + J*t/x_fixed = epsilon for t",
        "solve_distance": "J*t_fixed/(epsilon-B(t_fixed)); explicit zero/no-finite-distance branches",
        "evaluate_R_in": "B(t_fixed) + J*t_fixed/x_fixed",
    }[operation]
    interpretation = (
        "Time, distance and R_in use the same R(t,x)=B(t)+J*t/x and named assumptions. "
        "Bounds use <= and are not guarantees of safety. R_in is a linearized transmission measure, "
        "not a bounded finite-population case count. "
        + ("J=0 only under an explicit negligible-near-field hypothesis. Zero distance means no positive "
           "minimum in this approximation, not safety at contact. " if near_field == "uniform" else
           "Unmasked continuous-jet approximation; distances below 0.1 m are outside its domain. ")
        + ("Transient B(t) uses the exact constant-source concentration integral. "
           + ("The additive, immediately established local jet is a separate quasi-steady approximation, "
              "not a transient-jet solution reported by the paper." if near_field == "jet" else "")
           if background == "transient" else "B(t) uses steady background concentration.")
    )
    return metric(name, {"solve_time": "s", "solve_distance": "m", "evaluate_R_in": "scalar"}[operation],
        " ".join(inputs), formula,
        lambda v: calculate_exposure(v, operation=operation, background=background, near_field=near_field),
        "Eqs. 1-3 and Eq. 7; transient local term requires a separate approximation",
        f"exposure_{background}_{near_field}", interpretation)


EXPOSURE_ROUTES = {name: tuple(_exposure_metric(name, near_field) for near_field in ("jet", "uniform"))
                   for name in EXPOSURE_OUTPUTS}
METRICS.update((name, routes[0]) for name, routes in EXPOSURE_ROUTES.items())


def metric_routes(name):
    """Alternative kernels for one requested quantity, not additional report goals."""
    if name in EXPOSURE_ROUTES:
        return EXPOSURE_ROUTES[name]
    if name == "risk_threshold_distance_m":
        return METRICS[name], WELL_MIXED_DISTANCE
    return (METRICS[name],)


def select_metric(name, conditions):
    if name in EXPOSURE_ROUTES:
        if {"continuous_unmasked_jet", "negligible_near_field"} <= set(conditions):
            raise ValueError("Jet and negligible-near-field hypotheses require separate parameterizations")
        return EXPOSURE_ROUTES[name][1 if "negligible_near_field" in conditions else 0]
    if name == "risk_threshold_distance_m" and "negligible_near_field" in conditions:
        if "continuous_unmasked_jet" in conditions:
            raise ValueError("Select either a continuous-jet distance model or negligible near-field enhancement, not both in one parameterization")
        return WELL_MIXED_DISTANCE
    return METRICS[name]


def metric_conditions(name, *, regime=None):
    if name not in METRICS:
        return set()
    if name == "jet_dilution_ratio":
        # Local dilution has no well-mixed-room or recipient-breathing input.
        return {"continuous_unmasked_jet"}
    regime = regime or METRICS[name].regime
    needed = {"well_mixed", "single_infectious_source", "uniform_breathing_and_masks"}
    if regime.startswith("exposure_"):
        needed.add("continuous_unmasked_jet" if regime.endswith("_jet") else "negligible_near_field")
        if regime == "exposure_transient_jet":
            needed.add("quasi_steady_local_plume")
        return needed
    if regime == "bulk_flow":
        needed = set()
    elif regime == "stokes":
        needed = {"stokes_particles"}
    elif regime == "evaporation":
        needed = {"equilibrium_evaporation"}
    elif regime == "microphysics":
        needed = {"uniform_virion_infectivity"}
    elif regime == "concentration_dynamics":
        needed = {"well_mixed"}
    elif regime == "source_off":
        needed = {"well_mixed", "emissions_stopped"}
    elif regime == "well_mixed_distance":
        needed.add("negligible_near_field")
    if regime in {"jet", "random_jet"}:
        needed.add("continuous_unmasked_jet")
    if regime == "random_jet":
        needed.add("random_orientation_and_spacing")
    return needed


def metric_catalog_record(name):
    record = METRICS[name].as_record()
    record["routes"] = [{**route.as_record(),
                         "conditions": sorted(metric_conditions(name, regime=route.regime))}
                        for route in metric_routes(name)]
    if name == "risk_threshold_distance_m" or name in EXPOSURE_OUTPUTS:
        record["route_selection"] = (
            "negligible_near_field explicitly selects the spatially uniform risk model; "
            "otherwise the continuous-unmasked-jet kernel applies. The two conditions cannot "
            "be selected together. Mask penetration alone never selects a route. A named "
            "hypothesis may be calculated before support exists, but its support must be assessed. "
            "Assuming away near-field exposure merely to fill distance coverage is not justification.")
    return record


def required_inputs(names):
    """Return leaf input requirements for a requested metric set."""
    result = set()
    def visit(name):
        if name in METRICS:
            for route in metric_routes(name):
                for dependency in (*route.inputs, *(c["field"] for c in route.parameter_constraints())):
                    visit(dependency)
        else:
            result.add(name)
    for name in names:
        visit(name)
    return tuple(sorted(result))
