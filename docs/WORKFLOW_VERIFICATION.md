# Workflow Verification

Historical run record: the results and commands below describe the retired
calculation workflow, not the current episode tree. Its structured target inputs
are no longer accepted by the active CLI. Current structure and commands are in
[Approved Scientific Episode Tree](RESEARCH_EPISODES.md) and the root README.
Current verification is tracked in [Implementation Checklist](IMPLEMENTATION_CHECKLIST.md).
None of the historical successes below verifies the new tree.

Status on 2026-10-08: the strict live integration run passed, with 63 tests
passing and no skipped tests. Runtime search, retrieval, extraction, calibration,
and final-bound output were exercised without mocked providers or supplied
outbreak quantities. This is software/evidence-contract verification, not
clinical validation or a guarantee of safety.

## Exposure Results and Agreement

The original live run returned a cumulative exposure bound, not a distance or a
single maximum room time. The interpretation below was computed afterward from
the retained v6 report using this repository's deterministic time-bound,
susceptible-bound, transmission-rate, reproductive-number, and emission kernels.
It is not another live discovery run or an independent outbreak validation.

### Time in the Illustrative Target Room

The target inputs were illustrative, not a measured user room: equivalent
clean-air removal of `0.5 m3/s` (`1800 m3/h`), breathing flow `0.0001 m3/s`, no
masks, and risk tolerance `epsilon = 0.1`. Transferring the calibrated outbreak
infectiousness to those inputs gives `beta = 3.7705215456e-5 /s` and

```text
R_in_linear = Ns * beta * time_s
Ns * time_s <= 2652.152992 person_s = 44.202550 person_min
time_limit_min = 44.202550 / Ns
```

Here `Ns` is the number of susceptible people, EXCLUDING the one infectious
person assumed present. If everyone else is susceptible, `Ns = N_total - 1`.

| Total occupants, including one infectious person | Susceptible people | Time at the model's R_in = 0.1 threshold |
| --- | --- | --- |
| 2 | 1 | 44.20 min |
| 5 | 4 | 11.05 min |
| 10 | 9 | 4.91 min |
| 20 | 19 | 2.33 min |
| 50 | 49 | 0.90 min (54.13 s) |

Reinserting every unrounded time into the reproductive-number kernel gives
`R_in_linear = 0.1`; the inverse occupancy kernel returns the original `Ns`.
For comparison, 10 total occupants for 30 minutes gives `R_in_linear = 0.6108`
under exactly these inputs, above the selected threshold.

The tolerance is for the whole scenario, not a 10% individual infection risk.
The repo's first-transmission calculation gives `1 - exp(-0.1) = 9.52%` at the
threshold, conditional on one infectious person being present. The threshold
was selected for the test; it is not a recommended acceptable risk. These are
steady, well-mixed, long-range model limits, not guaranteed safe durations.

### R_in and Agreement with the Source Outbreak

For the published R2 restaurant event, use its own reported air removal,
breathing flow, and exposure duration, not the illustrative target's inputs:

| Quantity | Result |
| --- | --- |
| Observed secondary infections per index case | 7 / 1 = 7 |
| Repo's linearized R_in = Ns * beta * time | 7.1211 |
| Linear approximation versus observed count | 1.73% higher |
| Exponential dose-response expected secondary cases | 207 * (1 - exp(-beta * time)) = 7 |
| Reconstructed quanta emission | 1018.04 quanta/h |
| Source paper's reported quanta emission | 1023.4 quanta/h |
| Emission-rate difference | 0.52% lower |

The exact recovery of seven infections is by construction: the calibration
inverts that same attack probability. The repo's `indoor_reproductive_number`
uses a linearized hazard expression; it is not the finite-population expected
count at arbitrary attack probabilities. The close emission-rate agreement is
consistent with reported-input rounding: substituting the paper's rounded
3.4% attack rate instead of `7/207` gives 1023.66 quanta/h. It is a useful
reproduction check, not independent predictive validation.
Source: [R2 outbreak analysis, Sections 2.3 and 3.3](https://pmc.ncbi.nlm.nih.gov/articles/PMC8848576/).

### Distance and Other Model Paths

No safe-distance result was obtained. The evaluated well-mixed model has no
distance variable; increasing separation alone does not change its background
risk. The respiratory-jet path was not run on source-backed inputs. It needs
additional assumptions about mouth area, jet entrainment, plume encounters,
and occupancy/time. A candidate separation is an input to that path, not an
automatically inferred safe-distance output.

The jet model adds a nonnegative near-field contribution to background R_in.
Consequently, the times above already consume the whole background risk budget:
any positive jet contribution would require a shorter time or another risk
reduction. They must not be presented as combined near-/far-field safety limits.
No transient comparison was made either: the target run did not supply room
volume or a concentration relaxation rate.
Model basis: [Bazant and Bush, Eqs. 3-7](https://thales.mit.edu/bush/wp-content/uploads/2021/04/BazantBush-PNAS2021.pdf).

### What Has and Has Not Agreed

- The steady time, occupancy, and linearized R_in calculations agree
  algebraically for the same inputs. This is internal consistency.
- The reconstructed restaurant emission agrees with the paper within about
  0.5%, subject to the same assumptions and rounded inputs.
- PMC and ScienceDirect yielded identical Cq values because they contain the
  same paper and event. This is not replication across independent cases.
- Choir and second-disease runs did not produce accepted calibrations or bounds.
  There is no supported cross-case agreement claim, nor a real-data comparison
  of the steady, transient, and jet-corrected model paths.

## Requirement Audit

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Runtime disease, scenario, and setting inputs | Parameterized synthetic runs; live first-disease success and second-disease evidence-poor failure | Verified within this coverage |
| Self-contained search/retrieve path | Local episode binding, Firecrawl, Jev, and Argo clients; isolated checkout and import tests | Verified without sibling imports or third-party Python packages |
| Real runtime acquisition | Live choir and restaurant runs returned retrieved papers and source-backed extraction reports | Verified for these runtime inputs |
| No-auth local Argo shim | Live completion smoke check and real extraction in the CLI runs | Verified with the checkout's local configuration |
| Exact spans, refs, normalization, and event separation | Adversarial extraction tests, independent duration checks, event-isolation tests, credited-event context | Offline checks pass; live rejection of unsupported evidence observed |
| Outbreak-derived Cq and final bound | Strict live restaurant test and independent recomputation from retained source-backed inputs | Verified for one published outbreak |
| Deterministic calculation leaves | Ten model paths; six unbounded bound paths; small-probability stability checks | Covered by offline tests, not clinical validation |
| Sibling credit rollup | Nested sums, criterion-weight consistency, propagation of partial failed-attempt credit | Offline and live checks pass |
| Structured repairable failures | Real reports and adversarial/provider-failure tests | Verified |
| Strict CLI JSON, including unbounded results | Strict parser test; stable identity generation for infinite intermediate bounds | Verified |

## Live Runs

The initial choir runs used this command with real configured providers, no mocked transport,
no supplied outbreak document, and no injected outbreak quantities:

```bash
.venv-standalone/bin/python -I -S -B . "$DISEASE_OF_INTEREST" \
  --setting choir --search-limit 3 \
  --target-scenario '{"removal_capacity_m3_s":0.5,"breathing_flow_m3_s":0.0001,"mask_penetration":1,"risk_tolerance":0.1}'
```

These target-room values are illustrative test inputs, not a safety advice case.
The disease and setting are command arguments; neither is embedded in runtime
calibration logic.

The ignored `.artifacts/live/` directory retains the complete JSON reports.

- First-disease choir run v1: failed because the extraction prompt did not specify
  exact normalized count-unit labels. Added the per-field normalized-unit
  contract without relaxing validation.
- First-disease choir run v2: count, duration, behavior, and neutral-scaling children
  passed for two retrieved sources. All three attempted calibrations failed;
  removal capacity was not credited. Some fallback extractions used unsupported
  `cfm` or `m3/min` units; another cited a non-exact span. This run started before
  the later credit-rollup and event-context corrections and retains its original
  scores.
- First-disease restaurant run v3: used the same command with `--setting restaurant`.
  Exact-span validation rejected review quotations joined with ellipses. The
  audit also found exposed-count/attendance ambiguity and a circular proposed
  transmissibility factor. Extraction/review prompts were tightened.
- First-disease restaurant run v4: returned a numerically passed report, but the audit
  rejected its unsolicited variant scaling. This is **not** counted as
  a verified calibration. Fixed the control flow so default runs retain the
  outbreak's own transmissibility scale; sourced rescaling is explicitly opt-in.
  Added regressions for both modes and missing required scaling evidence.
- Second-disease aircraft run v1: used a separate runtime disease input, setting
  `aircraft`, and search limit 2. Real discovery retrieved an inflight outbreak
  analysis and follow-up sources. Calibration returned a structured failure:
  event duration and applicable removal/behavior inputs were unavailable.
  Applicability review rejected a hypothetical office ventilation rate and
  laboratory respirator test values as incompatible with the aircraft event.
  This run began before the default-scaling control-flow correction.
- First-disease restaurant run v5: ran the strict live integration test with corrected
  native scaling. It failed on non-exact extraction quotations; the failed
  report is retained. Added one bounded same-source span correction request,
  complete revalidation, retained diagnostics, and adversarial retry tests.
- First-disease restaurant run v6: strict live test passed in 198 seconds. The
  successful source reports describe the same published R2 event at PMC and
  ScienceDirect, not two independent outbreaks. One non-exact count quotation
  was corrected by the bounded retry; the rejected response and exact accepted
  span are retained. A third, evidence-poor candidate was not calibrated.

For v6, the retained inputs were 207 susceptible customers, one index case,
seven secondary cases, 2052 seconds, 2.5302 m3/s equivalent clean-air flow,
0.00015 m3/s breathing flow, and unmasked/identity factors of 1. The conditional
calibration was `Cq = 1885.260772800399 quanta/m3`; the illustrative target
produced `2652.1529923804196 person_s`, with parent credit `38/38`. The live test
checked all credited extraction spans, source/target applicability citations,
native scaling, each calibration equation, aggregation, and nested credit sums.
The event parameters come from the [restaurant outbreak analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC8848576/).

The live sources were discovered at runtime, including the Miller choir analysis
at `https://pmc.ncbi.nlm.nih.gov/articles/PMC7537089/` and the CDC outbreak report
at `https://www.cdc.gov/mmwr/volumes/69/wr/mm6919e6.htm`.

## Verified Scope

The removal reconstruction now supports an explicitly reported combined loss
rate times room volume, and deterministic `cfm`/`m3/min` conversions. Removal
values, scaling factors, and searched assumptions receive a separate
source/target applicability review with typed decisions and exact citations.
Synthetic tests verify rejection of recommendations, hypothetical upgrades,
unknown compatibility, and fabricated spans. Semantic applicability is still
an LLM judgment; exact quotations alone are not scientific validation.

Second-disease acquisition and evidence-poor failure were exercised with the
second-disease run. This verifies handling of that runtime input, not that every
disease or outbreak can supply enough evidence for a numerical estimate.
Calibration remains conditional on the source's event-model assumptions and
the selected well-mixed model. Broader numerical validation, uncertainty
propagation, and clinical applicability are outside these software checks.

## Repeatable Checks

```bash
.venv-standalone/bin/python -I -S -B scripts/check.py
```

Offline result: 63 tests run, 62 passed, one live integration test skipped.
Latest live result: 63 tests run, all passed, none skipped.

The successful live invocation was:

```bash
EPISODIC_TEST_DISEASE_NAME="$DISEASE_OF_INTEREST" \
EPISODIC_TEST_SETTING=restaurant \
EPISODIC_TEST_SEARCH_LIMIT=3 \
EPISODIC_TEST_TARGET_SCENARIO_JSON='{"removal_capacity_m3_s":0.5,"breathing_flow_m3_s":0.0001,"mask_penetration":1,"risk_tolerance":0.1}' \
EPISODIC_TEST_REPORT_PATH="$NEW_REPORT_PATH" \
.venv-standalone/bin/python -I -S -B scripts/check.py --live
```

Use a new report filename on reruns; existing artifacts are not overwritten.
Provider results are nondeterministic, and failed evidence still fails the
strict test. Numerical success is never replaced with a fixture or a generic
default. All disease and setting values above are runtime test inputs.
