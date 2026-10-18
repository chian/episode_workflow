# Episode Architecture and Instruction Boundaries

The current behavioral contract is [CURRENT_GOAL.md](CURRENT_GOAL.md). Explicit
user instructions take precedence. This document describes ownership; it does
not authorize extra reviews, gates, scientific cutoffs, or new completion tests.
Prior versions combined implementation history and instructions, including
unverified claims of approval. Those versions are historical and must not be
used to restore removed behavior.

## Ownership

The active API is `run_guideline_research(disease=..., scenario=...)`, also reached
through the configured provider entry point and CLI. All episodes execute in one
`method_loop.Context`.

```text
[E] evaluate_airborne_safety_guideline
    +-- [T] calculate_geometry_and_removal
    +-- [T] calibrate_infectiousness
    +-- [T] calculate_transmission_metrics
    +-- [T] calculate_conditional_limits
    +-- [E] investigate
            +-- [E] strategy
                    +-- [E] search
                            +-- [E] page
                                    +-- [E] source_table
                                    +-- [E] report
                                    +-- [E] lexical_probe
```

An episode selects work, executes it, receives structured results and credit,
and uses the existing numerical continuation rule. This is not a prescribed
sequence of scientific actions. Mandatory method-loop credit projection does
not mean mandatory LLM scientific approval.

The root owns decisions about target calculations and investigations.
Investigations acquire or estimate missing values. Reading episodes extract
source information; they do not redefine target scenarios. Source calibration
retains the source scenario and native input provenance.

## Scenario and Calculation Boundary

Scenario definitions supply numeric constraints and categorical model settings.
Every scenario explicitly selects background plus local jet or negligible near
field. Neither episode proposals nor a calculator fallback choose that setting.
The existing scenarios retain the jet selection explicitly; future scenarios
can select a different supported setting. A well-mixed background and a local
jet are distinct features, not mutually exclusive labels.

The existing operations are `solve_time`, `solve_distance`, and `evaluate_R_in`.
They use the selected scenario's model and reference coordinates. Target operands
bind automatically from the main table, fixed scenario inputs, retained constants,
and current computed results. Other numeric candidates are provenance and
inference records, not a second calculation input interface.

There is no calculation approval review. Do not introduce one under the name of
compatibility, applicability, safety, support, or consistency. Descriptive
assumptions do not gate numerical execution. Functions return numerical results;
wrappers record execution or an actual error. Do not discard numbers through an
`inapplicable` status or a new scientific cutoff.

Each computed quantity has one defined calculation. Reuse current stored values;
do not run inverse or competing formulas merely to compare their answers.
Calculation status follows actual dependencies, not an assessment verdict:

| Status | Meaning |
| --- | --- |
| `not_calculated` | No completed numerical result exists. |
| `calculated_up_to_date` | The recorded result matches current dependencies and is reused. |
| `calculated_needs_updating` | An actual dependency changed and the result needs recalculation. |

Expose computed value, units, dependencies, readiness, and credit in the same
calculation table. Do not invent an additional progress table or issues list.

## Planning, Relevance, and Source Records

The constants assessment precedes the sharing assessment and initial credit
assignment, before searching. These requested assessments decide which physical
properties require finding and which scenario needs share a value.

Source-to-target relevance grades the source scenario for a particular value.
It ranks values automatically in the main table; it is not a pass/fail scientific
approval. Missing or low relevance does not prohibit retaining or using a value.
Keep investigated targets separate from source scenarios in episode inputs and
reporting. Estimates retain their origin and do not become source quotations.

Exact source checking preserves quantity, number, units, attribution, and source
span. Do not expand transcription checking into a scientific-support judge.
No new reasonableness or applicability assessment is authorized by this document.
The repository still contains parameter-review machinery; describing this boundary
is not a claim that all of that code has been removed or reconciled.

## Credit and Decisions

Keep found-value credit separate from calculation credit. Preserve the current
base rates and expose them to episode decisions: 1 per independent found value,
12.5 per current intermediate, and 25 per current requested output. Actual stale
results retain their method portion (2.5 or 5). Do not change weights as part of
instruction cleanup or add approval calls to justify an existing support bonus.

Main values, calculation dependencies, progress status, and credit must agree.
Review-only changes cannot withdraw current numerical credit or force unchanged
calculations to run again. The root can receive global credit updates while a
child is active. Repeated records do not earn additional credit.

The episode chooses useful calculations or further investigation. The yield
estimator measures recent credit gains; it does not compare alternative actions.
The existing root and child yield windows remain independently configurable.
Neither low yield nor operational termination establishes successful completion.

## Structured Parent Returns

Parents specify the needed information contract. Return the existing structured
JSON fields with their declared meanings:

| Field | Meaning |
| --- | --- |
| `parameter_results` | Numbers, units, origin, status, and references. |
| `reviews` | Existing recorded assessment fields; not authorization for new reviews. |
| `calculations` | Actual numerical outputs, units, and execution statuses. |
| `reading_coverage` | Counts describing examined and remaining material. |
| `operations` | Defined operation categories, statuses, and counts. |
| `completion` | Actual termination and evaluated state. |

Use existing work-call JSON and deterministic projections. No second summary
call, freeform findings paragraph, direct child prose, or raw diagnostic text
returned to the parent. Keep full provenance and raw attempts in existing audit
records; their existence does not authorize injecting freeform text into decisions.

## Reading, Providers, and Storage

Retain the existing Firecrawl search/retrieval and Jev relevance path. Reading
uses table queries, document-order report windows, or source-local lexical probes.
Reading memory is not extracted evidence. Keep source versions and original
quoted spans. Preserve real extraction through the configured model provider;
do not substitute hand-entered or synthetic evidence.

Keep both Codex-login and Argo provider options and the configured FAST/REASONING
model roles. Credentials do not belong in committed source or checkpoint records.

Completed child audit history and model attempts can be archived to the existing
checkpoint. Active state retains what decisions, input binding, and credit need.
Use streaming serialization; do not materialize full recursive archives merely
for a progress report. Historical files and test descriptions record past code;
they are not new instructions or verification of the current implementation.
