# Case Reports

## Legacy Workflow Reference

The material below describes the retained legacy fixed-task implementation and
its regression fixtures, not the active prompt-only workflow. The CLI now uses
the approved scientific tree in `research/`. See
[the complete current structure](../docs/RESEARCH_EPISODES.md). Its calculation
tools reuse the local kernels; its investigation branch owns mandatory assumption
assessment and its acquisition branch contains the actual reading episodes.

Hold searched outbreak and source-admission episodes for the generic
indoor-airborne calibration workflow. Runtime outbreak records must be built
from retrieved source text, LLM-extracted exact spans, scored assumption
admission, and deterministic task executors.

The workflow contains a searched infectiousness parent. It starts from a
`disease_name`, optional setting hints, a
`search(query, limit)` provider, an optional
`retrieve(candidate)` provider for metadata-only search hits, and an injected
LLM extraction provider. Its `find_calibration_outbreaks` child performs
outbreak discovery explicitly. Its `calibrate_cq_from_outbreak` child then
consumes the credited search report and inverts one searched outbreak instead
of owning that initial search itself.

The infectiousness parent calibrates `Cq` by passing a credited outbreak-search
child output into its internal calibration child, building attack probability
from LLM-extracted population counts, admitting equivalent removal capacity,
exposure time, behavior, and transmissibility facts from LLM-extracted source
text, and running the final deterministic `Cq` child once those upstream
reports pass. When the caller has not requested a variant, population, or
cross-disease adjustment, the transmissibility child can explicitly credit
neutral identity scaling with `relative_transmissibility = 1.0` instead of
requiring outbreak sources to report that scalar. The parent
preserves extracted source spans and source refs on the credited child outputs
so parent failures can point at the missing or unsupported field. Malformed
retrieval metadata on an otherwise usable candidate is ignored when promoting
candidates into internal LLM source objects; the source text and stable
`source_ref` decide whether the LLM extraction boundary is reachable.

`run_evaluate_safety_guideline_episode` is the safety-guideline
parent. It runs the searched infectiousness parent, admits caller-supplied
target room and exposure values, selects the requested safety-guideline output,
and derives cumulative bound models from the deterministic
`steady_state_cumulative_exposure_bound` leaf before any transient well-mixed
correction. The parent can return the cumulative
exposure-time bound directly, divide it by an admitted `susceptible_count` for
`steady_state_time_bound`, divide it by an admitted `exposure_time_s` for
`steady_state_susceptible_bound`, apply the transient correction to the
cumulative, time, or susceptible bound, compute a long-range indoor
reproductive-number estimate, turn that estimate into a Poisson probability of
at least one transmission, or apply the respiratory-jet correction to the
indoor reproductive number. Transient runs require a target room reconstructed
from enough geometry and loss-rate fields to compute `removal_rate_s`.
Respiratory-jet runs require explicit target values for plume-encounter
probability, mouth area, entrainment coefficient, neighbor distance, and the
well-mixed dilution factor. The room child accepts
either direct `removal_capacity_m3_s` or detailed direct `floor_area_m2`,
`room_height_m` / `room_volume_m3`, `air_exchange_rate_h` /
`outdoor_air_flow_m3_s`, `recirculation_flow_m3_s`, `filter_efficiency`,
`deactivation_rate_h`, and `settling_speed_m_h` values. The target-scenario
admissions validate direct values before deterministic children can consume
them; missing or invalid target fields become structured errors rather than
defaults. When target room or breathing/mask values are absent, the
admission children can run the reusable assumption-search episode, require
LLM-extracted numeric values and a similarity basis from retrieved text, and
report the admitted assumptions back to the guideline parent.

The `find_calibration_outbreaks` child formulates scoped outbreak
queries for a disease and optional setting, runs each query through the
configured search provider, retrieves source text for metadata-only hits when
a retrieval provider is configured, normalizes candidate source records, and
scores the child with the same rarefaction mechanism used by other
search-backed normalization children. When the same source appears under
multiple scoped queries, normalization preserves every query and purpose on
the internal source object passed to LLM extraction. Search previews such as
`snippet`, `description`, and `summary` remain repair context; only full
`text`, `passage`, `markdown`, `content`, `html`, or `abstract` values can
satisfy retrievable-source scoring or be promoted to LLM extraction text.
Search credit covers query formulation, returned results, source metadata,
retrievable page bodies, and source diversity.

Runtime outbreak discovery stays explicit at the infectiousness level while
`calibrate_cq_from_outbreak` focuses on the outbreak inversion once source text
has already been found.

The `build_attack_probability` task consumes retrieved source text, calls
the injected LLM extractor, validates that each population-count or attack-rate
field has an exact source span and matching source ref, and then computes
attack probability. It accepts either exposed attendee count or directly
reported susceptible count, and it accepts either secondary case counts or a
reported secondary attack probability normalized to a per-susceptible fraction.
It yields on the first source that passes or after every candidate source has
failed.

The nested `calibrate_cq_from_outbreak` task anchors these direct outbreak-field
children to the source that credited attack probability. A room, exposure,
behavior, or scaling value from another initially searched outbreak cannot be
mixed into the final `Cq` unless it is admitted through the scored assumption
path with a similarity basis. When the attack-probability child does not
credit a source, sibling evidence children fail with a repairable
`missing_child_report` instead of extracting unanchored values.

`build_removal_capacity`, `admit_exposure_time`,
`admit_behavior_assumptions`, and
`admit_population_or_variant_scaling` are reusable scalar evidence
children. Each receives the searched `EvidenceSource` candidates, requests its
own required fields from the injected LLM extractor, fails closed when the
LLM omits a field or cites unsupported text, and yields on the first source
that passes its child-specific normalization criteria. The removal-capacity
child first accepts a sourced `removal_capacity_m3_s`; when that equivalent
value is absent it can extract `room_volume_m3` and an explicitly reported
combined `total_removal_rate_h`, convert the rate to inverse seconds, and
multiply volume by that rate. It does not add component losses a second time.
If no total rate is reported, it can instead extract floor area with either room height or
room volume, air exchange or outdoor ventilation flow, filtered
recirculation, deactivation, and settling speed and compute clean-air removal
capacity with the deterministic `room_volume`, `room_height`,
`air_exchange_rate`, unit-conversion, `filtration_loss_rate`,
`air_purification_rate`, and `removal_capacity` leaves.
The behavior child accepts an explicitly supported `mask_penetration`, an
explicitly supported `mask_filter_efficiency`, or an explicitly supported
unmasked indicator. Filtration efficiency is validated as a fraction or percent
and inverted to the final penetration fraction; an unmasked source statement is
encoded as `unmasked_indicator = 1` and converted to `mask_penetration = 1.0`
before the deterministic `Cq` calculation consumes it.

`find_assumption_sources` is the fallback searched path for scalar
assumptions. When removal-capacity, behavior, or transmissibility fields are
absent from the outbreak sources, the calibration task runs multiple
child-scoped queries through the same search and retrieval providers until
the assumption-source score passes or saturates by the rarefaction rule. A
candidate with only preview text is still scored as incomplete; determining
whether the retrieved text actually supports breathing, mask,
transmissibility, clean-air delivery, or detailed room reconstruction fields is
left to the LLM admission request and its exact-span checks.
The eventual LLM admission must still
return exact numeric evidence spans and must also return a `similarity_basis`
with an exact
`similarity_evidence_span` explaining why the assumption source is close enough
to the target outbreak. Assumption-admission LLM requests include the credited
attack source refs and the failed outbreak-child report so the extractor can
see which target-event facts were missing when it judges similarity.

All removal extractions and all searched assumptions also undergo a separate
LLM applicability review. Acceptance requires explicit scale and mechanism
compatibility, an observed or adopted event parameter (or an allowed comparable
observation), and exact source and target spans. Recommendations, hypothetical
upgrades, device specifications, and unsupported point values from ranges are
not event evidence. The typed decisions and exact citations are validated and
retained as `evidence_applicability`; semantic applicability remains an LLM
judgment, not a guarantee of scientific validity.

An extraction with a non-exact evidence span gets at most one same-source
correction request containing the rejected response and validation errors.
The replacement is fully revalidated, with no fuzzy matching or source-text
normalization. Ref mismatches, invalid values, and other non-span failures are
not retried. Extraction reports retain `span_repair_history`, and a credited
child retains that history when its accepted extraction needed a correction.

## Inputs

- `disease_name` and optional setting hints for searched outbreak discovery;
  setting hints may be omitted, supplied as one string, or supplied as a
  sequence that the search boundary joins into the query suffix.
- `search`: `search(query, limit)` callable.
- `retrieve`: optional callable that fetches text for a metadata-only search
  result.
- `llm`: callable that receives an extraction request and returns JSON or a
  mapping of extracted values with source spans.
- `require_transmissibility_evidence`: optional flag for runs that need a
  sourced variant, population, or disease rescaling scalar instead of neutral
  identity scaling.
- `target_scenario`: for the safety-guideline parent,
  `breathing_flow_m3_s`, `mask_penetration`, model-specific
  `risk_tolerance`, `susceptible_count`, `occupant_count`, or
  `exposure_time_s`, and either direct `removal_capacity_m3_s` or detailed
  room-removal fields. Relative-risk runs need detailed room fields that
  produce `room_volume_m3` and `air_exchange_rate_s`; transient runs need
  detailed room fields that produce `removal_rate_s`. Descriptive room,
  activity, masking, or ventilation hints can also scope fallback
  target-assumption searches.
- Retrieved outbreak-report text can support exposed or susceptible counts,
  secondary case counts or secondary attack rates, room metadata, ventilation
  metadata, or a reported equivalent virus-free-air flow that can be normalized
  directly to `removal_capacity_m3_s`.

## Outputs

- `candidate_outbreak_sources`: search-normalized source candidates for later
  extraction.
- `ExtractionReport`: LLM-extracted values, exact evidence spans, source refs,
  optional assumption-admission bases, and structured errors.
- `AssumptionSearchReport`: rarefaction-scored fallback evidence for admitting
  a missing scalar assumption from similar-source evidence.
- `attack_probability_inputs`: secondary-case and susceptible counts that can
  feed `secondary_attack_probability`, or extracted susceptible-count inputs
  plus a normalized reported secondary attack probability.
- `attack_probability`: observed secondary attack probability from
  LLM-extracted outbreak counts.
- `removal_capacity_m3_s`: equivalent virus-free-air delivery admitted from
  an extracted value or computed from extracted room and loss fields,
  normalized to `m3/s`.
- `exposure_time_s`: extracted outbreak exposure duration, normalized to
  seconds.
- `breathing_flow_m3_s`, `mask_penetration`, and
  `relative_transmissibility`: admitted behavior and transmissibility
  assumptions consumed by the final deterministic `Cq` child. Mask penetration
  can be extracted directly or derived as `1 - mask_filter_efficiency` after
  LLM span validation and fraction normalization, or it can be derived from
  explicit unmasked text after span validation. Relative transmissibility can be
  extracted from evidence or explicitly credited as neutral identity scaling
  when no rescaling has been requested.
- `quanta_concentration_exhaled_m3`: `Cq` inferred from the observed attack
  probability, removal capacity, exposure time, breathing flow, mask
  penetration, relative transmissibility, and extracted index-case count.
- `cumulative_exposure_bound_person_s`: the selected person-time
  bound computed from searched infectiousness and admitted target scenario
  values.
- `exposure_time_bound_s`: the selected maximum exposure time for an admitted
  susceptible count.
- `susceptible_bound`: the selected maximum susceptible count for an admitted
  exposure time.
- `CqCalibrationCreditReport`: summed child credit for a full
  attack-probability calibration attempt.
- `GuidelineCreditReport`: summed child credit for a first safety-guideline
  attempt.
- `EpisodeRecord`: the method-loop trace for a full attack-probability
  calibration.

## Credit and yield

- Searched source discovery earns graded credit over scoped queries, returned
  results, source metadata, retrievable text, and source diversity, then yields
  by the Cq normalization rarefaction rule.
- Source discovery and assumption discovery preserve structured
  `retrieval_error` records when a configured retrieval provider cannot fetch
  a metadata-only search hit; URL and DOI values nested in provider metadata
  are kept as the failing field when present. Partial retrieval errors remain
  repair context when other retrieved sources satisfy every score criterion;
  they block the child when they prevent enough usable full text from being
  gathered.
- Population-count extraction fails closed when the LLM provider is missing,
  the response is invalid, a required field is absent, a field has no exact
  source span, the field/unit/source/span members are malformed, its source ref
  does not match the retrieved source, a numeric field is non-finite, its
  confidence or notes are malformed, its confidence is below the extraction
  threshold, or its unit is not normalized to `count`. Duplicate extracted rows
  for the same field fail as ambiguous LLM output.
- Attack-probability construction passes only when LLM-extracted
  `attendee_count` and `index_case_count` pass with either
  `secondary_case_count` or `attack_probability`; count-based extraction then
  runs the deterministic `susceptible_count` and
  `secondary_attack_probability` leaves, while reported attack rates must
  already be normalized to a fraction in `[0, 1)`. Extracted attendee, index,
  and susceptible counts must be positive whole counts; extracted secondary
  counts must be non-negative whole counts.
- Removal-capacity, exposure-time, behavior, and transmissibility children
  pass only after all required extracted fields have matching source refs,
  exact source spans, supported normalized units, and field-specific positive
  or probability-range checks.
- Exposure-time admission also re-runs the deterministic minutes/hours/days to
  seconds leaves and fails if the LLM's normalized value does not match the
  raw supported duration.
- Removal-capacity and behavior admission re-run deterministic flow-unit
  leaves for `m3/h`, `m3/min`, `L/s`, and `cfm` source values and fail if the LLM's
  `m3/s` normalized value is inconsistent.
- Detailed removal-capacity admission rechecks raw metric room geometry,
  hourly rates, outdoor-air flows, and settling speeds before converting them
  for the deterministic room-removal leaves.
- Relative-transmissibility admission cross-checks raw unitless, fold, and
  times-valued scalars before consuming the normalized scalar. When the
  caller has not requested rescaling evidence, it emits a scored neutral
  identity assumption without extracting an incidental comparison from the
  paper. Rescaling is opt-in: the default calibrates on the outbreak's own
  transmissibility scale. Required scaling must be an applicable independent
  model input, not a fitted quanta ratio or background reproduction-number comparison.
- Filter-efficiency and mask-penetration admission cross-check raw fractions
  and percents before consuming the normalized fraction.
- Removal-capacity, behavior, and transmissibility children may fall back to
  searched assumption admission when outbreak sources simply omit the needed
  fields. Unsupported spans, source-ref mismatches, invalid units, malformed
  LLM responses, and invalid values fail closed instead of being repaired by
  an assumption search. Fallback searches receive independent rarefaction
  credit, and the LLM admission fails if its similarity basis is absent or not
  a string, or if its similarity evidence span is absent, not a string, or not
  exact text from the source.
- Detailed removal-capacity fallbacks do not use hidden room or particle-loss defaults:
  floor area, either room height or room volume, either air exchange or outdoor
  ventilation flow, recirculation flow, filter efficiency, deactivation, and
  settling speed must all be extracted and unit-normalized before
  deterministic calculation.
- Admitted assumptions are reported per field with the assumed field name,
  raw value and unit, normalized value and unit, exact evidence span, source
  ref, confidence, notes, and LLM-extracted similarity basis.
- LLM-extracted ordinary evidence and searched assumptions share the same
  field-level confidence threshold; low-confidence values fail before any
  deterministic child can consume the normalized number.
- The Cq-calibration task yields after search, extraction-backed
  normalization, and the final calculation all report; if any upstream child
  fails, the final calculation child reports the missing prerequisite fields.
- Failed children can still attach repair context to the summed parent
  `outputs`, such as a failed `assumption_search` report showing which
  fallback queries ran and why they did not yield usable evidence, or
  `failed_source_reports` showing every searched source whose LLM extraction
  could not be credited.
- The summed parent also exposes a compact `child_reports` map so callers can
  inspect each sibling's score, missing criteria, errors, identities, and
  rarefaction verdict without replaying the `EpisodeRecord`.
