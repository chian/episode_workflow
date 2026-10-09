"""An additive justification branch for the existing evidence-admission parents.

This binding does not select scenarios, calibrate infectiousness, or calculate
risk. Its parent owns the fields and context to be justified.
"""

from dataclasses import dataclass, replace
import json
from collections.abc import Mapping

from ..credit_assignment.research import ResearchController
from ..method_loop import (
    ChildEpisodeUnit, Episode, EpisodeGoal, EpisodeRequest, Grain, Leaf,
    ReportContract, SourceEnd,
)
from .research.assumptions import RUBRIC, assess_assumption
from .research.records import Credit, Ledger, ResearchMessage, ResearchResult


@dataclass(frozen=True)
class AssumptionLimits:
    max_model_calls: int = 40
    max_units: int = 16
    yield_window: int = 4
    text_window_chars: int = 12000

    def __post_init__(self):
        for name, value in vars(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.yield_window < 2 or self.text_window_chars < 100:
            raise ValueError("Invalid assumption investigation limits")


class AssumptionBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class AssumptionServices:
    search: object = None
    retrieve: object = None
    search_limit: int = 8
    limits: AssumptionLimits | None = None


def latest_assessments(result):
    """Use the current judgment per field, including withdrawals of support."""
    return {a["field"]: a for a in result.assumptions}


def assumption_credit(result, fields):
    latest = latest_assessments(result)
    return Credit(evaluated=result.evaluated, qualities=tuple(
        (field, "current_assessment", latest.get(field, {}).get("resolution_credit", 0))
        for field in fields
    ))


def assumption_summary(result, completion, request):
    """Return only this branch's contracted facts, without a new synthesis policy."""
    latest = latest_assessments(result)
    return {
        "assumptions": [{k: v for k, v in a.items() if k != "key"} for a in latest.values()],
        "findings": list(result.findings),
        "unresolved": list(result.issues),
        "completion": result.stop_reason or completion.ended_by,
    }


def branch_contract(fields, context):
    return ReportContract(
        decision=f"Decide whether {', '.join(fields)} can be admitted for this parent's defined context: {context}",
        measurements={"credit": "Reviewed justification, not populated fields or source counts."},
        information={
            "assumptions": "Current proposed values, reasonableness, evidence, limitations and rejected alternatives.",
            "findings": "What the evidence establishes for this admission decision.",
            "unresolved": "Missing support and failed assessments; not instructions for the parent.",
            "completion": "Numeric yield, exhaustion or operational failure.",
        },
    )


class AssumptionInvestigation:
    """Compose just the branch; the existing admission episode remains its parent."""

    def __init__(self, *, fields, context, llm, sources=(), search=None,
                 retrieve=None, search_limit=8, limits=None):
        self.fields = tuple(fields)
        self.context = dict(context)
        self.llm, self.search, self.retrieve = llm, search, retrieve
        self.sources, self.search_limit = tuple(sources), search_limit
        self.limits = limits or AssumptionLimits()
        self.calls = self.sequence = 0
        self.record = None
        self.documents = {}
        self.controllers = {}
        self.subject = "admission_target"
        self.grain = Grain("assumption_investigation", "evidence approach or assumption candidate",
                           "justified assumptions for the admission parent", self.controller)
        self.evidence_grain = Grain("assumption_evidence", "focused source reading",
                                    "admitted supporting or conflicting evidence", self.controller)
        self.assessment_grain = Grain("assumption_assessment", "candidate review",
                                      "reasonableness assessment", self.controller)

    @property
    def children(self):
        return {self.grain: (self.evidence_grain, self.assessment_grain)}

    def agent(self, request):
        if self.calls >= self.limits.max_model_calls:
            raise AssumptionBudgetExceeded("assumption_model_call_budget_exhausted")
        if self.llm is None:
            raise ValueError("Assumption investigation requires an LLM provider")
        self.calls += 1
        result = self.llm(request)
        if isinstance(result, str):
            result = json.loads(result)
        if not isinstance(result, Mapping):
            raise ValueError("Assumption model response must be an object")
        return result

    def controller(self, path):
        scientific, initial = self.controllers[path[-1][1]]
        return ResearchController(self.fields, initial=initial, capacity=2,
                                  window=self.limits.yield_window,
                                  epoch="assumption_justification_v1")

    def episode(self, parent, source, grain, objective, contract):
        self.sequence += 1
        key = f"{grain.name}:{self.sequence}"
        self.controllers[key] = (source.scientific, source.credit(source.ledger.result()))
        goal = EpisodeGoal.child(parent.goal, objective=objective,
                                 result_contract={"fields": list(self.fields)})
        return Episode(grain, key, source,
                       EpisodeRequest(goal, ResearchMessage(objective, self.fields, (self.subject,)), contract),
                       source.build_result, on_unit=source.after_verdict)

    def open(self, parent, contract):
        initial = ResearchResult(scenarios=({
            "subject": self.subject, "description": str(self.context),
            "basis": "Scope supplied by the existing admission parent; not a new scenario.",
        },))
        source = InvestigationSource(self, initial)
        episode = self.episode(parent, source, self.grain,
                               f"Justify {', '.join(self.fields)} for the admission parent's context.", contract)
        return replace(episode, on_close=lambda record: setattr(self, "record", record))


class AssumptionSource:
    """Shared method_loop plumbing, without shared agent capabilities."""

    scientific = True

    def __init__(self, branch, inherited):
        self.branch, self.ledger = branch, Ledger(inherited)
        self.pending = None
        self.failure = ""
        self.evaluated = 0

    def credit(self, result):
        if self.scientific:
            return assumption_credit(result, self.branch.fields)
        return result.credit(self.branch.fields)

    def receive(self, result, completion=None, request=None):
        self.pending = result
        accumulated = Ledger(self.ledger.result())
        for assessment in result.assumptions:
            accumulated.assumptions.pop(assessment["key"], None)
        accumulated.merge(result)
        return self.credit(accumulated.result(evaluated=result.evaluated))

    def after_verdict(self, item, contribution, view):
        if self.pending is not None:
            # Reassessment order matters, even when a previously seen claim returns.
            for assessment in self.pending.assumptions:
                self.ledger.assumptions.pop(assessment["key"], None)
            self.ledger.merge(self.pending)
            self.evaluated += int(self.pending.evaluated)
            self.pending = None

    def build_result(self, record):
        reason = self.failure or (record.controller_state.reason if record.ended_by == "yield_stop" else record.ended_by)
        return self.ledger.result(evaluated=bool(self.evaluated), stop_reason=reason)

    def inputs(self, view, **kwargs):
        return view.model_inputs({
            "objective": view.goal.as_record()["objective"],
            "context": self.branch.context, "fields": list(self.branch.fields),
            "subject": self.branch.subject,
            "evidence_options": self.ledger.evidence_options(),
            "assessments": self.ledger.assumption_options(),
            "findings": self.ledger.findings, "issues": self.ledger.issues,
            "credit_history": list(view.controller_state.history), **kwargs,
        }, reports=view.child_reports)

    def leaf(self, function, label):
        def execute(_):
            try:
                return function()
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
                if isinstance(exc, AssumptionBudgetExceeded):
                    self.failure = str(exc)
                return ResearchResult(evaluated=False, issues=(f"{label}: {type(exc).__name__}: {exc}",))
        return Leaf(None, execute, lambda _, result: self.receive(result), label)

    def next(self, view):
        if self.failure:
            return SourceEnd("source_failed")
        if view.units_consumed >= self.branch.limits.max_units or self.branch.calls >= self.branch.limits.max_model_calls:
            self.failure = "assumption_operational_budget_exhausted_not_convergence"
            self.ledger.issues.append(self.failure)
            return SourceEnd("source_failed")
        try:
            return self.propose(view)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
            message = f"assumption proposal: {type(exc).__name__}: {exc}"
            return self.leaf(lambda: ResearchResult(evaluated=False, issues=(message,)), "invalid_proposal")


class InvestigationSource(AssumptionSource):
    """Choose evidence approaches and candidate assumptions, not calculations."""

    def propose(self, view):
        from .assumption_evidence import EvidenceSource

        proposal = self.branch.agent(self.inputs(
            view, operation="propose_assumption_investigation", rubric=RUBRIC,
            response_contract={
                "action": "gather_evidence or assess_assumption; no stop action",
                "objective": "specific uncertainty to resolve within the parent's requested fields",
                "query": "for gather_evidence: a new search query, or empty to examine supplied sources",
                "field": "for assess_assumption: one requested field",
                "value": "finite proposed number", "unit": "canonical unit",
                "statement": "precise conditional claim", "basis": "reasoned inference",
                "evidence": ["admitted evidence option keys, including contrary evidence"],
            },
            instruction=(
                "Resolve the parent's assumption question, using findings and numerical yield history. "
                "You may revise the evidence strategy or propose and reassess a candidate. "
                "An inferred value need not be printed in a source, but requires evidence and a bounded inference. "
                "Do not invent evidence, redefine the scenario, calculate risk or prescribe an acceptable risk budget. "
                "Do not override explicit target constraints. Only the numerical controller decides stopping."
            ),
        ))
        objective = proposal.get("objective")
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError("An assumption child needs a scoped objective")
        if proposal.get("action") == "gather_evidence":
            query = proposal.get("query", "")
            if not isinstance(query, str):
                raise ValueError("Evidence query must be text")
            source = EvidenceSource(self.branch, self.ledger.result(), query=query, question=objective)
            grain = self.branch.evidence_grain
            contract = ReportContract(
                decision=f"Assess assumption reasonableness: {objective}",
                measurements={"credit": "New admitted evidence relevant to the requested assumptions."},
                information={"evidence": "Admitted numeric and qualitative passages with applicability.",
                             "findings": "Supporting or conflicting findings.", "unresolved": "Missing evidence and failed readings.",
                             "completion": "Actual completion reason."},
            )
            synthesis = lambda result, completion, request: {
                "evidence": list(result.evidence) + [f.semantic_record() for f in result.facts if f.source],
                "findings": list(result.findings), "unresolved": list(result.issues),
                "completion": result.stop_reason,
            }
        elif proposal.get("action") == "assess_assumption":
            if proposal.get("field") not in self.branch.fields:
                raise ValueError("Candidate field is outside the admission parent's scope")
            constraints = self.branch.context.get("target_scenario", {})
            if proposal["field"] in constraints and proposal.get("value") != constraints[proposal["field"]]:
                raise ValueError("An assumption cannot override an explicit target constraint")
            proposal = {**proposal, "subject": self.branch.subject}
            source = AssessmentSource(self.branch, self.ledger.result(), proposal)
            grain = self.branch.assessment_grain
            contract = branch_contract((proposal["field"],), self.branch.context)
            synthesis = assumption_summary
        else:
            raise ValueError("Unknown assumption action; the agent cannot stop the episode")
        child = self.branch.episode(view, source, grain, objective, contract)
        return ChildEpisodeUnit(child, self.receive, synthesis)


class AssessmentSource(AssumptionSource):
    """One independently reviewed candidate; no searching or proposal capability."""

    def __init__(self, branch, inherited, proposal):
        super().__init__(branch, inherited)
        self.proposal = proposal

    def propose(self, view):
        if view.units_consumed:
            return None
        return self.leaf(lambda: assess_assumption(
            self.branch.agent, self.proposal, self.ledger, self.branch.context,
        ), "assess_assumption_reasonableness")
