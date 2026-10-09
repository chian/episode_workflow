# Credit Assignment

## Calculation

This package holds the first pass/fail credit layer for deterministic
calculations. A registered calculation task runs once, returns one named
output, and then stops.

There is no LLM judge here. The calculation function validates its own inputs,
the shared numeric judge checks the returned output, and the wrapper converts
the attempt into a small parent-facing report.

`CQ_CALIBRATION_CHILDREN` declares the scored child reports used while finding
outbreak sources and calibrating `Cq`. The nested `calibrate_cq_from_outbreak`
task receives the infectiousness parent's credited search output, then admits
outbreak counts, room removal, exposure time, behavior, and transmissibility
before the final deterministic Cq calculation. Deterministic calculation leaves
earn pass/fail credit by returning their named output. Evidence and
assumption-normalization children use `CQ_NORMALIZATION_CRITERIA`: they earn
partial credit while they search for sources, admit values, normalize units,
and check that the admitted assumptions are compatible.

`credit_cq_calibration_child` is the pass/fail child judge for deterministic
children. `score_cq_normalization_child` is the multi-criterion judge for
search-backed evidence and assumption children. `cq_normalization_rarefaction`
turns a child's search score history into the yield verdict for those
search-backed children. Its marginal-gain threshold is adaptive: it is at
least the child's smallest criterion weight and rises with recent productive
gains, so the stop decision comes from rarefaction progress instead of a
fixed search count or hard-coded score.
`sum_cq_calibration_credit` adds the mixed child reports into the parent-facing
`CqCalibrationCreditReport`.

`INFECTIOUSNESS_CHILDREN` declares the first searched infectiousness parent. It
credits explicit calibration-outbreak search, the nested
`calibrate_cq_from_outbreak` inversion, respiratory-activity rescaling, and
the final synthesis step that produces the `quanta_concentration_exhaled_m3`
value expected by a later safety-guideline parent. `sum_infectiousness_credit`
keeps those reports separate from the Cq-calibration sibling set so outbreak
search can be visible above the Cq inversion instead of being buried inside
it.

`GUIDELINE_CHILDREN` declares the first safety-guideline parent. It credits
searched infectiousness estimation, explicit direct target-room admission,
explicit direct target-exposure admission, transmission-model selection, and
the final `compute_safety_bound` deterministic child.
`sum_guideline_credit` keeps the credited
`cumulative_exposure_bound_person_s` value as a safety-guideline main output
for the eventual broader root.

## Inputs

- `task`: a `CalculationTask` declaring the function, output name, accepted
  input names, output domain, and identity version.
- `inputs`: a mapping from input names to raw values for the calculation.
- `calculation_reports`: sibling `CalculationReport` values keyed by
  calculation task name.
- `search_records`: scoped outbreak-search result bundles.
- `candidate_outbreak_sources`: deduplicated outbreak source records emitted by
  the search child.
- `outputs`: a Cq calibration child's raw output mapping.
- `passed_criteria`: evidence or assumption-normalization criteria already
  credited for the child.
- `errors`: a Cq calibration child's failed validations or extraction errors.
- `rarefaction`: the child's numerical stop verdict over its score history.
- `child_reports`: `CqCalibrationChildReport` values keyed by child name.

## Outputs

- `CalculationReport.outputs`: the single credited output on success.
- `CalculationReport.value`: the same numeric output exposed directly when
  the calculation passed, or `None` when it failed before producing the named
  output.
- `CalculationReport.unit`: the unit associated with that single output, such
  as `m3/s`, `1/s`, `quanta/m3`, `person_s`, `probability`, or `scalar`.
- `CalculationReport.errors`: one or more structured errors on failure.
- `CalculationReport.passed`: `True` for a credited calculation and `False`
  otherwise.
- `CalculationReport.score`: `1.0` for pass and `0.0` for fail.
- `CalculationReport.identities`: the credited output identity on success.
- `CalculationReport.stop`: always `True` for this one-shot layer.
- `CqCalibrationChildReport.outputs`: the single credited child output on
  success.
- `CqCalibrationChildReport.errors`: one or more structured errors on failure.
- `CqCalibrationChildReport.should_yield`: `True` when rarefaction decided
  the child can stop searching.
- `CqCalibrationChildReport.rarefaction`: the adaptive threshold, recent gain,
  score resolution, productive-gain baseline, and stop outcome for a
  search-backed child.
- `CqCalibrationCreditReport.outputs`: credited outputs keyed by child.
- `CqCalibrationCreditReport.main_outputs`: the final credited
  `quanta_concentration_exhaled_m3` output.
- `CqCalibrationCreditReport.source_refs`: source refs collected from child
  outputs, including searched outbreak sources and assumption sources.
- `CqCalibrationCreditReport.admitted_assumptions`: field-level admitted
  assumptions keyed by child and field.
- `InfectiousnessCreditReport.admitted_assumptions`: Cq calibration
  assumptions promoted through the `estimate_pathogen_infectiousness` parent
  and keyed by infectiousness child, Cq child, and field.
- `GuidelineCreditReport.admitted_assumptions`: outbreak-infectiousness and
  target-scenario assumptions promoted to the safety-guideline parent and
  keyed by guideline child, nested child, and field.
- `CqCalibrationCreditReport.errors`: child failures annotated with the child
  and expected output.
