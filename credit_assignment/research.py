"""Numerical yield control for finite, declared scientific requirements.

This reuses the repository's rolling marginal-credit rarefaction rule. It is
an operational saturation heuristic, not a statistical confidence interval
or a claim that the literature has been exhausted.
"""

from dataclasses import dataclass
import math

from .cq_calibration import cq_normalization_rarefaction


@dataclass(frozen=True)
class ResearchStep:
    stop: bool
    score: float
    gain: float
    evaluated: bool
    reason: str
    requests_transition: bool = False


@dataclass(frozen=True)
class ResearchState:
    stop: bool
    score: float
    history: tuple[float, ...]
    failures: int
    reason: str
    rarefaction: dict | None


class ResearchController:
    """Deduplicate at this scope, never add up children's accumulated credit."""

    def __init__(self, columns, *, window=4, capacity=2, epoch="research-v2", initial=None, groups=None):
        self.columns = tuple(dict.fromkeys(columns))
        if not self.columns or window < 2 or capacity < 1:
            raise ValueError("Research control requires columns, window >= 2 and positive capacity")
        self.window, self.capacity, self.epoch = window, capacity, epoch
        self.groups = groups or (self.columns,)
        if set(c for group in self.groups for c in group) != set(self.columns) or any(not g for g in self.groups):
            raise ValueError("Credit groups must cover the declared columns")
        self.seen = {column: set() for column in self.columns}
        self.qualities = {column: {} for column in self.columns}
        if initial is not None:
            for column, key in initial.identities:
                if column in self.seen:
                    self.seen[column].add(key)
            self._qualities(initial)
        self.history = [self._score()]
        self.window_start = 0
        self.failures = 0
        self.stop = False
        self.reason = "continue"
        self.rarefaction = None

    def _qualities(self, value):
        for column, key, quality in value.qualities:
            if column not in self.qualities:
                raise ValueError("Credit column is outside this episode's goal")
            if isinstance(quality, bool) or not isinstance(quality, (int, float)) or not math.isfinite(quality) or not 0 <= quality <= 1:
                raise ValueError("Credit quality must be finite and between zero and one")
            self.qualities[column][key] = quality

    def _score(self):
        values = {c: max(min(self.capacity, len(self.seen[c])) / self.capacity,
                         max(self.qualities[c].values(), default=0)) for c in self.columns}
        return sum(sum(values[c] for c in group) / len(group) for group in self.groups) / len(self.groups)

    def observe(self, unit_label, value, *, is_root):
        from ..case_reports.research.records import Credit
        if not isinstance(value, Credit):
            raise TypeError("ResearchController requires Credit")
        previous = self.history[-1]
        if not value.evaluated:
            self.failures += 1
            return ResearchStep(False, previous, 0.0, False, "failed_observation")
        for column, key in value.identities:
            if column not in self.seen:
                raise ValueError("Credit column is outside this episode's goal")
            self.seen[column].add(key)
        self._qualities(value)
        score = self._score()
        self.history.append(score)
        if score < previous:
            # Retractions invalidate the previous yield window, not the audit history.
            self.window_start = len(self.history) - 1
        verdict = cq_normalization_rarefaction(
            self.history[self.window_start:], max_score=1.0,
            score_resolution=(1 - 1e-12) / (2 * len(self.columns) * self.capacity * len(self.groups)),
            window_size=self.window,
        )
        self.rarefaction = verdict.as_record()
        self.stop, self.reason = verdict.should_yield, verdict.outcome
        return ResearchStep(self.stop, score, score - previous, True, self.reason)

    def state(self):
        return ResearchState(self.stop, self.history[-1], tuple(self.history),
                             self.failures, self.reason, self.rarefaction)

    def transitioned(self, epoch):
        return ResearchController(self.columns, window=self.window, capacity=self.capacity, epoch=epoch, groups=self.groups)
