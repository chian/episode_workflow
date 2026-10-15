"""One admitted scientific Goal projection shared by every research episode."""

from __future__ import annotations

from collections import defaultdict

from ...task_executors.scenario_metrics.dependencies import input_requirements
from .modeling import derivation_inputs
from .progress import evidence_key, parameter_requirements
from .records import Credit, Ledger, ResearchResult, current_computation, identity
from .relevance import source_profiles, target_comparison_context
from .scenario_sharing import applicable_assumptions, independent_groups, needed_fields


GLOBAL_GOAL_PROGRESS = "global_goal_progress"
OUTBREAK_OPERATORS = ("cq_from_steady_outbreak", "cq_from_transient_outbreak")
GLOBAL_SCORE_WEIGHTS = {"admitted_progress": 1.0}


def _route_family(route):
    regime = route.get("regime", "")
    if regime.endswith("_uniform"):
        return "uniform"
    if regime.endswith("_jet"):
        return "jet"
    return regime


def _available(ledger, subject):
    numeric = {fact.field for fact in ledger.facts.values() if fact.subject == subject}
    conditions = set()
    for assumption, _relation in applicable_assumptions(ledger, subject):
        if assumption.get("review", {}).get("verdict") not in {"fixed_condition", "supported", "provisional"}:
            continue
        (numeric if assumption["value"] is not None else conditions).add(assumption["field"])
    return numeric, conditions


def _target_routes(ledger, metrics):
    targets = {}
    for subject, scenario in ledger.scenarios.items():
        if scenario.get("role", "target") != "target":
            continue
        numeric, conditions = _available(ledger, subject)
        requirements = input_requirements(metrics, numeric, conditions,
                                          scenario.get("calculation_variables", ()))
        routes_by_metric = {}
        for metric in metrics:
            routes = requirements["unresolved"].get(metric, {}).get("routes", ())
            routes_by_metric[metric] = {_route_family(route): route for route in routes if route.get("regime")}
        families = set.intersection(*(set(routes) for routes in routes_by_metric.values())) if routes_by_metric else set()
        alternatives = []
        for family in sorted(families):
            inputs, needed_conditions = set(), set()
            for metric in metrics:
                route = routes_by_metric[metric][family]
                inputs.update(route["inputs"])
                inputs.update(item["field"] for item in route.get("parameter_constraints", ()))
                needed_conditions.update(route["conditions"])
            required = len(inputs) + len(needed_conditions)
            met = len(inputs & numeric) + len(needed_conditions & conditions)
            alternatives.append({"route": family, "met": met, "required": required,
                                 "fraction": met / required if required else 0.0,
                                 "missing_inputs": sorted(inputs - numeric),
                                 "missing_conditions": sorted(needed_conditions - conditions)})
        chosen = max(alternatives, key=lambda row: (row["fraction"], row["met"], row["route"])) if alternatives else None
        declared_needs = needed_fields(scenario)
        fulfilled_needs = declared_needs & {
            assumption["field"] for assumption, _relation in applicable_assumptions(ledger, subject)
            if assumption["field"] in declared_needs
            and assumption.get("review", {}).get("verdict") in {"supported", "provisional"}
        }
        targets[subject] = {"best_route": chosen, "alternatives": alternatives,
                            "declared_assumptions": {"fulfilled": len(fulfilled_needs),
                                                     "required": len(declared_needs),
                                                     "fulfilled_fields": sorted(fulfilled_needs)}}
    return targets


def _calibration_readiness(ledger):
    fields_by_subject = defaultdict(set)
    observed_by_subject = defaultdict(set)
    for fact in ledger.facts.values():
        if fact.kind == "source_observation" and fact.source:
            fields_by_subject[fact.subject].add(fact.field)
            observed_by_subject[fact.subject].add(fact.field)
    for assumption in ledger.assumptions.values():
        if (assumption["subject"] in fields_by_subject and assumption["value"] is not None
                and assumption.get("review", {}).get("verdict") != "contradicted"):
            fields_by_subject[assumption["subject"]].add(assumption["field"])
    alternatives = []
    for subject, fields in fields_by_subject.items():
        for operator in OUTBREAK_OPERATORS:
            for attack in (True, False):
                needed = derivation_inputs(operator, {"attack_probability": 0} if attack else {})
                met = len(fields & needed)
                alternatives.append({"subject": subject, "operator": operator,
                                     "attack_input": "attack_probability" if attack else "case_counts",
                                     "met": met, "required": len(needed),
                                     "fraction": met / len(needed),
                                     "observed_fields": sorted(observed_by_subject[subject] & needed),
                                     "missing": sorted(needed - fields)})
    best = max(alternatives, key=lambda row: (row["fraction"], row["met"], row["subject"])) if alternatives else None
    return {"best_route": best, "observed_event_count": len(fields_by_subject)}


def _source_parameter_coverage(fields, parameter):
    """A direct reported value fills its element; inversion inputs fill a route fraction."""
    if parameter in fields:
        return 1.0
    if parameter != "quanta_concentration_exhaled_m3":
        return 0.0
    alternatives = [set(derivation_inputs(operator, {"attack_probability": 0} if attack else {}))
                    for operator in OUTBREAK_OPERATORS for attack in (True, False)]
    return max((len(fields & needed) / len(needed) for needed in alternatives if needed), default=0.0)


def _source_target_learning(result, ledger, targets):
    """One strongest admitted relationship per target need, independent of source count."""
    invalid = {evidence_key(evidence) for assessment in result.assumptions
               for evidence in assessment.get("invalidated_evidence", ())}
    valid_facts = defaultdict(set)
    for fact in result.facts:
        if (fact.kind in {"source_observation", "source_model_parameter"} and fact.source
                and evidence_key(fact.semantic_record()) not in invalid):
            valid_facts[(fact.source, fact.subject)].add(fact.field)
    profiles = {}
    rows = {subject: {} for subject in targets}
    for relation in result.source_target_relationships:
        subject, parameter = relation["target_subject"], relation["parameter"]
        if subject not in targets or parameter not in targets[subject]["needs"]:
            continue
        scenario = ledger.scenarios[subject]
        target = target_comparison_context(scenario, ledger.assumptions.values())
        if relation.get("target_version") != identity(target):
            continue
        if parameter not in profiles:
            profiles[parameter] = source_profiles(result, parameter_requirements(parameter))
        source_key = (relation["source"], relation["source_subject"])
        profile = profiles[parameter].get(source_key)
        if profile is None or relation.get("source_profile_version") != identity(profile):
            continue
        known, considered = relation["known"], relation["considered"]
        comparison_coverage = known / considered if considered else 0.0
        evidence_coverage = _source_parameter_coverage(valid_facts[source_key], parameter)
        quality = round(relation["score"] * comparison_coverage * evidence_coverage, 10)
        previous = rows[subject].get(parameter)
        if quality > (previous or {}).get("credit", 0):
            rows[subject][parameter] = {"credit": quality, "source": relation["source"],
                                        "source_subject": relation["source_subject"],
                                        "relationship_score": relation["score"],
                                        "comparison_coverage": comparison_coverage,
                                        "evidence_coverage": evidence_coverage}
    groups = independent_groups(ledger)
    group_credit = {group["group_id"]: max((rows.get(subject, {}).get(group["parameter"], {}).get("credit", 0)
                         for subject in group["subjects"]), default=0)
                    for group in groups}
    required = len(groups)
    total = sum(group_credit.values())
    return {"by_target": {subject: {"needed_parameters": sorted(row["needs"]),
                                    "covered_parameters": rows[subject]}
                          for subject, row in targets.items()},
            "covered": sum(value > 0 for value in group_credit.values()), "required": required,
            "score": round(total / required, 10) if required else 0.0}


def scientific_goal_status(result, metrics):
    ledger = Ledger(result)
    targets = _target_routes(ledger, metrics)
    calibration = _calibration_readiness(ledger)
    current = ledger.assumptions
    computed = sum(any(estimate["subject"] == subject and current_computation(estimate, current, metric, ledger=ledger)
                       for estimate in ledger.estimates.values())
                   for subject in targets for metric in metrics)
    requested = len(targets) * len(metrics)
    route_fractions = [alternative["fraction"] for row in targets.values()
                       for alternative in row["alternatives"]]
    route_score = sum(route_fractions) / len(route_fractions) if route_fractions else 0.0
    for subject, row in targets.items():
        row["needs"] = sorted(needed_fields(ledger.scenarios[subject]))
    source_learning = _source_target_learning(result, ledger, targets)
    target_inputs = {}
    for subject, row in targets.items():
        fields = {}
        for field in row["needs"]:
            assessments = [(a, relation) for a, relation in applicable_assumptions(ledger, subject)
                           if a.get("field") == field]
            usable = [item for item in assessments if item[0].get("review", {}).get("verdict") in {"supported", "provisional"}]
            choices = usable or assessments
            selected = max(choices, key=lambda item: (item[0].get("reasonableness", 0),
                1 if item[1] is None else 0)) if choices else None
            current, relation = selected if selected else (None, None)
            if current is None:
                fields[field] = {"status": "missing"}
                continue
            verdict = current.get("review", {}).get("verdict", "unassessed")
            status = ("reviewed_usable" if verdict in {"supported", "provisional"} else
                      "recorded_unassessed" if verdict == "unassessed" else
                      "recorded_unsupported" if verdict == "unsupported" else "contradicted")
            fields[field] = {"status": status, "review_verdict": verdict,
                             "value": current["value"], "unit": current["unit"],
                             "statement": current["statement"],
                             "origin_subject": current["subject"],
                             "scope_group_id": relation["group_id"] if relation else None}
        target_inputs[subject] = fields
    independent = []
    for group in independent_groups(ledger):
        assessments = [a for a in ledger.assumptions.values()
                       if a.get("subject") in group["subjects"] and a.get("field") == group["parameter"]
                       and a.get("value") is not None and a.get("role") not in
                       {"scenario_constraint", "request_constraint"}]
        found = [a for a in assessments if a.get("review", {}).get("verdict") != "contradicted"]
        reviewed = [a for a in found if a.get("review", {}).get("verdict") in {"supported", "provisional"}]
        independent.append({"group_id": group["group_id"], "parameter": group["parameter"],
            "subjects": group["subjects"], "found": bool(found), "reviewed": bool(reviewed),
            "origin_subject": (reviewed or found)[-1]["subject"] if reviewed or found else None})
    recorded_target_inputs = sum(row["found"] for row in independent)
    required_target_inputs = len(independent)
    assumption_coverage = {"fulfilled": sum(row["reviewed"] for row in independent),
                           "required": len(independent)}
    from .assumptions import scientific_credit
    groups = independent_groups(ledger)
    focus = tuple(sorted({group["parameter"] for group in groups} | set(metrics)))
    credit = scientific_credit(result, focus, outputs=metrics)
    components = [{"field": field, "element": element, "points": points}
                  for field, element, points in credit.qualities]
    scores = {"admitted_progress": round(sum(row["points"] for row in components), 10)}
    return {"target_routes": targets, "calibration": calibration,
            "target_assumptions": assumption_coverage,
            "recorded_target_inputs": {"recorded": recorded_target_inputs,
                                       "required": required_target_inputs},
            "independent_target_values": independent,
            "target_inputs": target_inputs,
            "source_target_learning": source_learning,
            "computed_outputs": computed, "requested_outputs": requested,
            "credit_components": components,
            "scores": scores,
            "weighted_score": round(sum(scores[name] * weight for name, weight in GLOBAL_SCORE_WEIGHTS.items()), 10),
            "score_weights": dict(GLOBAL_SCORE_WEIGHTS)}


class ScientificGoalState:
    """Preview admitted contributions, then retain them after the episode verdict."""

    def __init__(self, metrics, initial=None):
        self.metrics = tuple(metrics)
        self.ledger = Ledger(initial or ResearchResult())

    def preview(self, contribution=None):
        projected = Ledger(self.ledger.result())
        if contribution is not None:
            projected.merge(contribution)
        return scientific_goal_status(projected.result(), self.metrics)

    def commit(self, contribution):
        self.ledger.merge(contribution)
        return self.preview()

    def credit(self, contribution=None):
        status = self.preview(contribution)
        return Credit(evaluated=contribution.evaluated if contribution is not None else True,
                      qualities=((GLOBAL_GOAL_PROGRESS, "admitted_progress", status["weighted_score"]),),
                      quality_resolution=0.1)
