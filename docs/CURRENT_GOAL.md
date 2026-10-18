# Current Goal and Implementation Boundaries

Updated 2026-10-18 to reflect the user's corrections. This document describes
required behavior, not a claim that the implementation satisfies it. Repository
prose and historical implementation notes do not establish user approval.
Explicit user instructions take precedence.

## Do Not Expand the Requirements

- Do not add scientific-support, reasonableness, applicability, or calculation
  approval reviews without an explicit user instruction. Calling a mechanism
  "mandatory" in code or documentation does not authorize it.
- Do not infer new requirements from words such as scientific, justified,
  supported, safe, or validated. Report provenance and uncertainty using the
  existing records; those words do not authorize another judge or acceptance gate.
- Keep the explicitly requested constants planning, parameter sharing, and
  value-specific source-to-target relevance assessment. They have distinct jobs;
  they do not authorize additional scientific approval mechanisms.
- Preserve source transcription checks: the number, quantity, units, attribution,
  and quoted source span must describe what was retrieved. Checking a copied
  record does not authorize judging whether a scenario may use its value.
- No unapproved gates, scientific cutoffs, confidence thresholds, consistency
  tolerances, or extra stopping rules. If an equation or setting appears wrong,
  show the exact code and explain the uncertainty to the user before changing it.
- Separate verified code behavior, observed run behavior, and hypotheses. A
  hypothetical failure is not evidence of a remaining defect. Do not claim that
  a mechanism occurred in a run without tracing that run.

## Objective

Build the generalized episodic system for the runtime disease and scenarios
selected through `--scenario`. It acquires values through the existing real
search, retrieval, and extraction path and computes:

1. Allowable room time at the scenario's reference separation.
2. Risk-based safe distance at the scenario's reference duration.
3. Indoor reproductive number, R_in, at both reference coordinates.

Compute steady and transient results under the scenario's declared settings.
Do not substitute a concentration crossover, formula inventory, published-answer
match, or planning report for the requested numerical outputs. Do not embed a
particular disease, outbreak, source, or set of empirical answers in the system.

## Scenario Ownership

- Scenario definitions own room, population, activity, ventilation, masks, risk
  criterion, reference coordinates, and model settings. Calculations read those
  settings; episode proposals cannot supply or override them.
- Explicitly select `continuous_unmasked_jet` or `negligible_near_field` in each
  scenario. The existing scenarios explicitly retain the former jet default.
  Future scenarios can explicitly select the other setting. The calculator has
  no implicit near-field default. This choice does not infer mask behavior.
- `well_mixed` describes the background assumption; a well-mixed background can
  coexist with a local jet. Do not conflate these settings.
- Encode assumptions in the scenario's parameter values and model settings.
  Descriptive condition statements are not evidence prerequisites for arithmetic.
  Do not introduce a second approval process for a scenario-owned setting.
- The existing reference coordinates are 1.8288 m and 900 s. Caller-selected
  scenarios can override them. They are evaluation coordinates, not calculated
  safety answers or defaults for an observed outbreak's duration.
- Do not change equations or add multipliers merely because a setting appears
  not to affect a particular term. Show the term and ask the user when its
  intended role is unclear. In particular, do not add mask penetration to the
  local jet term without authorization.

## Planning and Found Values

Before searching, perform the almost-universal-constants planning, then the
shared-parameter assessment, then form the initial list and credit assignment.
Retain gravity, air density, viscosity, and water-like particle density unless
the constants assessment identifies a scenario requiring material variation.
The default scenarios retain those configured values. Only promoted properties
enter the found-value list and sharing assessment; supplied constants earn no
finding credit.

Track independent required values after sharing. Exclude supplied scenario
values, retained constants, and calculated quantities: quanta emission, settling
speed, removal capacity, and removal rate. Do not inflate the denominator with
alternative recipes, extra source scenarios, or calculation steps.

Automatically retain extracted values and populate the main table using the
highest source-scenario relevance for that particular parameter value. Preserve
alternatives as provenance. Low or unknown relevance does not gate availability
or finding credit. Report the investigated target separately from the source
scenario and expose their value-specific relationship assessment.

An estimate may supply a needed value when direct reporting is unavailable.
Record its origin and reasoning without labeling it as an extracted source
number. Do not require a separate scientific-support approval to use it.

## Calculations and Reuse

- Target calculations bind values from the main table, supplied scenario inputs,
  retained constants, and current computed results. No caller-selected numeric
  alternatives or overrides. Source calibration uses its own native source records.
- Keep one defined calculation for each computed quantity. Removal capacity uses
  `Q + pf*Qr + lambda_v*V + vs*A`; do not restore the competing `lambda*V` recipe
  or the 2% consistency comparison.
- Reuse a current stored result unchanged. Copying a value must not change it.
  Recalculate because an actual dependency changed, not because another operation
  happened to run or an assessment's opinion changed.
- A numerical function computes numbers from its operands. Its execution wrapper
  records success or an actual error. Do not invent `inapplicable` results or
  discard calculated numbers based on scientific judgment or an arbitrary cutoff.
  Preserve genuine zero and unbounded mathematical results distinctly from missing work.
- Do not put an LLM review between a calculation request and execution. Do not
  silently return a correction as though the requested calculation executed.
- Use one calculation table with computed value, units, dependencies, readiness,
  credit, and three progress statuses: `not_calculated`,
  `calculated_up_to_date`, `calculated_needs_updating`.
- Readiness describes available operands for the scenario's selected calculation.
  Numerical freshness and credit must use that same dependency state. A support
  verdict alone cannot make an unchanged numerical result stale or unusable.

## Credit and Episode Decisions

Keep found-value and calculation-step credit separate and visible. Retain the
existing base policy: one point per independent found value; 12.5 per current
intermediate (2.5 method plus 10 current result); 25 per current requested output
(5 method plus 20 current result). Stale results retain method credit until
updated. Distinct relevant evidence has its existing 0.1 increment.

This instruction correction does not change scoring weights. The historical
support-bonus formula is not authorization to add or retain extra approval calls;
its implementation and remaining review machinery require separate examination.
Do not invent replacement scoring to resolve that mismatch.

Update the main table, calculation status, credit, and episode-visible records
together. Active ancestor credit can update before a child returns. Relevance or
review metadata alone must not retract numerical completion credit or trigger
identical arithmetic again.

The episode chooses whether to investigate or calculate. Explain available
calculation credit so it can choose useful work. Do not force a sequence or claim
that the next action is guaranteed. The yield estimator measures credit history;
it does not compare alternative actions. Preserve the independently configured
root and child windows (12 and 4 by default). Do not add stopping rules here.

## Communication and Operations

- Preserve the existing `method_loop` ownership tree. Deterministic calculations
  are tools, not additional episodes.
- Parent returns are structured JSON with defined fields. No freeform findings
  paragraph, direct child prose, or second summarization call. Gather needed
  structured information in the existing work call.
- Keep existing logs and records. Do not add an issues collection or another
  progress log. Report values found, calculation status, and actual target progress.
- Use the existing Firecrawl and Jev search path. Retain the Codex-login and Argo
  provider options and the configured FAST/REASONING split.
- Keep real source provenance and outbreak-calibration lineage. Do not fabricate
  evidence, inject fixtures, or relabel guesses as observations. Do not turn
  provenance reporting into a separate scientific-support approval requirement.
- Report completion from actual requested results and their recorded inputs;
  stopping alone does not establish completion. Do not add a requirement to win
  an independent scientific-support verdict before results count as calculated.
- The user's prohibition on tests, fake-provider exercises, and calculation
  replays remains in force unless explicitly changed. Static checks and real
  runs require the authorization applicable to those actions. Runs are currently
  stopped; this document does not authorize restarting or pushing changes.

## Implementation Status

These requirements supersede conflicting historical descriptions. Remaining
parameter-review, freshness, scoring, and reporting code has not all been aligned
or verified. Documentation changes do not establish that those defects are fixed.
Read historical trace studies as records of past implementations, not instructions
to restore their behavior.
