# Approved Episode Tree Implementation

Source specification: the user-approved tree attached on 2026-10-09.
This checklist records completion evidence, not a substitute specification.

## Required End State

- [x] Active prompt-only entry point uses one method_loop Context and this tree:
  evaluate_safety_guideline > investigate > strategy > search > page >
  (source_table | report | lexical_probe).
- [x] Root selectable tools: calculate_geometry_and_removal,
  calibrate_infectiousness, calculate_transmission_metrics,
  calculate_conditional_limits, compare_predictions_with_observations.
  Deterministic calculations are leaves, not single-shot episode wrappers.
- [x] Every episode uses numerical credit-yield continuation. Operational
  limits and failed observations are distinguishable from scientific saturation.
- [x] Every parent specifies its child's information contract before execution;
  condensed synthesis and failure explanations inform later proposals.
- [x] Investigation owns candidate assumptions and alternatives. Reasonableness
  assessment is mandatory, including reassessment against new contrary evidence.
  No optional assessment action or assessment episode.
- [x] Search and retrieval are bound execution; page chooses among available
  reading episodes. Tables, sustained report windows, and lexical probes have
  distinct iterative scopes. Working reading memory is not credited evidence.
- [x] Source quotations, units, applicability, and source versions are checked
  before evidence admission. Repeated material cannot manufacture progress.
- [x] Calculations retain exact assumption/model versions. Evidence retractions
  invalidate current support without deleting historical calculations.
- [x] Root credit reflects supported requested conclusions and resolved
  scientific uncertainty, not field/source/call counts. Parents recompute credit.
- [ ] Reports are synthesized at root closure and include applicable risk,
  duration, occupancy, clean-air, and distance quantities with named assumptions,
  evidence, missingness, uncertainty, and calibration/validation distinctions.
- [x] No externally structured answers, seeded research results, cross-repo
  imports, or third-party runtime packages are introduced.
- [x] Offline tests exercise exact topology, controlled choices, mandatory
  assessment, contracts, long-document reading, all tools, version changes,
  failure propagation, numerical limits, and standalone execution.
- [x] Study a live prompt-only trace; record the actual observed behavior and
  limitations separately from synthetic test results.

## Evidence

Implementation in progress. No completion claim yet.

Checked architecture items are verified by the current code and offline traces,
not claims of live scientific success:

- `case_reports/research/engine.py::TREE`, `ResearchRun.episode/child`, and
  `workflow.py::run_guideline_research`: one declared tree and runtime context.
- `tests/test_approved_tree.py::ApprovedTreeTests`: executed ownership, parent
  contracts, tool leaves, mandatory reassessment, failure communication, and
  reinvestigation followed by recalculation under changed assumptions.
- `ReadingBindingTests`: table/report/probe choices, bounded retained memory,
  failed observations, retrieval, and source revisions.
- `CalculationToolTests` and `ReportProjectionTests`: all five tool kernels,
  versioned support, compatible alternatives, calibration dependence, stale
  coverage, source-version verification, comparisons and missingness in reports.
- `tests/test_research.py`: controlled stopping and failures, credit projection,
  the full registered calculator catalog, independent evidence review and
  response contracts. `test_assumption_support.py` checks goal-aligned credit.
- `tests/test_standalone.py`: all imports are local or standard library, and an
  isolated checkout runs the offline suite without site-packages or `.env`.

The offline suite currently runs 204 tests (203 pass; one opt-in live test is
skipped). The first bounded live run of the approved tree completed but produced
no calculations; it exhausted its model-call budget. Its observed response
failures, first corrections, and outstanding live verification are recorded in
`RESPONSE_FAILURE_STUDY.md`. That run does not verify the later corrections.

Report production and interpretation pass synthetic checks, but a successful
unseeded live scientific report remains unverified. The second bounded live run
used the same original request and limits: 29 numeric facts, 193 qualitative
records, one provisional assessment, zero calculations, and model-call exhaustion.
Its provenance checks passed; the earlier numeric-string/source-choice failures
did not recur. See `RESPONSE_FAILURE_STUDY.md` for remaining behavioral limits.
Further reporting, diagnostic-compaction, table-contract, unit-notation and
assessment-contract changes made during or after that run are not part of its
loaded implementation; its startup hashes identify the tested code.

The follow-up contract audit found that the stored parent contract did not reach
the model during child proposals, extraction, or assessment. It now does, with
the parent's selected subject names rather than every known scenario. Tests
inspect the actual model requests, not just the recorded tree. Investigation
can also select a strategy-specific evidence focus without replacing its own
scientific objective. Invalid scalar hypotheses fail before acquisition, and
one failed assessment no longer suppresses independent successful judgments.
These changes have offline coverage but are not verified by V2.

V3 completed against the unchanged original request with the full default
23-metric catalog, 240 model calls and 240 total units. This is broader than
the four-metric, 80-call V1/V2 studies, so raw counts are not directly comparable.
Its startup hashes distinguish loaded code from later worktree changes. The
run exhausted 240 model calls after 127 units, retaining 71 numeric source facts
and 390 qualitative records, with zero assessments and zero calculations. All
admitted quotation/source-version checks passed. One synthesis had an invalid
JSON escape; two evidence-review calls returned HTTP 400. The parent contract
reached the child, but acquisition still used the budget before mandatory
reasonableness assessment. This is not a successful quantitative report. The
supported-applicability reporting change and additional unit-notation support
were made after V3 began and are not verified by that run. The same applies to
the corrected condition prerequisites: source-off clearance explicitly requires
stopped emissions rather than a continuously emitting person, concentration
relaxation does not require occupants, and critical aerosol radius requires
the Stokes-particle condition. Focused offline tests cover those contracts.
Assumption summaries and rendered citations now distinguish the reviewer's cited
basis from all evidence made available for consideration. The complete considered
set remains in the audit and is available to new assessments. This change also
postdates V3 startup and has offline coverage only.
After V3, provider instructions explicitly require JSON escaping of backslashes,
and synthesis prefers plain-text mathematical notation. Parser regressions check
invalid versus valid escapes without automatic repair; no new live result is
claimed for this instruction change.

Following V3, parent proposals can allocate optional child-subtree model-call
allowances while retaining their own resources for assessment and decisions.
Descendant allowances cannot exceed an enclosing ceiling; operational exhaustion
remains distinct from numerical saturation. Parent-commissioned return synthesis
uses the parent's allowance. Proposal contexts now use decision-specific evidence
projections, and child reports carry change indexes and new failure diagnostics
instead of repeatedly replaying inherited records. Full provenance and evidence
remain available to independent review. Offline tests cover bounded child work,
condensed communication, repeated/inherited failures, synthesis failure reaching
ancestors, and assessment of existing evidence after failed acquisition. These
changes have not yet been verified by a live run.

The HTTP boundary now retains bounded recognized provider error fields instead
of only status codes, redacting the configured credential before truncation and
omitting headers and unrecognized response fields. Tests cover explanations,
credential redaction, oversized/non-JSON bodies and closed error streams. This
postdates V4 startup; V3's two HTTP 400 causes remain unknown.

V4's early trace reached parent assessment and exposed an invalid root focus
proposal and undersized child allowances. The root now has an explicit JSON
Schema with focus enums and available fact keys, plus diagnostics identifying
invalid focus entries. Context now describes known per-operation model-call
costs rather than assuming an agent understands their composition through the
tree. These changes also postdate V4 startup and have offline coverage only.

V4 finished with the unchanged original request and full metric catalog, bounded
at 120 calls (half V3's allowance). It used 70 units, made eight root investigation
choices, and performed 12 reasonableness reviews, retaining six current judgments
(one supported, five provisional). It retained four numerical source records and
21 qualitative records, but no calculations; provenance checks passed. No child
exceeded its allowance. Numerous allocations were too small to finish extraction
plus review, so reaching assessment is not proof of adequate resource allocation.
Two HTTP 400 failures occurred; no malformed JSON response occurred. The actual
root score also included erroneous discovery credit for the requester-defined
well-mixed premise, because request and target subject labels differed. Mandatory
assessment now explicitly classifies requester conditions using cited admitted
request evidence and a target-scope explanation. Such bindings retain conditional
support but earn zero discovery credit; source evidence or mismatched numerical
values cannot establish that classification. Offline tests cover this change.
V4 is incomplete and does not verify any of the post-startup corrections above.

A further prompt audit found a conflicting provider-level rule: scientific
alternatives were restricted to admitted facts, despite investigation's ability
to propose inferred assumptions. The instruction now reserves that restriction
for calculation execution. Hypotheses may involve unprinted values but still
require independent evidence-linked review before use. A synthetic full-tree
test checks that a provisional inference reaches calculations without becoming
a claimed source value. Root instructions also distinguish executing scientific
work from planning a report generator, while preserving the requested outputs
and the prohibition on silently treating examples as universal defaults.
Assessment-failure summaries now identify the particular candidate, not only
the strategy that proposed it. These corrections are not verified by V4.

V5 tested the unchanged original request and full metric catalog with a
240-call allowance. After its startup, explicit power/inverse-unit spellings
such as `m 2` and `h -1` were added to notation normalization. Cross-dimension
conversions remain rejected. The remaining prose-template response contracts
in the active tree were also replaced with typed JSON Schemas. The evidence
review schema specifies exactly one decision per candidate; page choices declare
the conditional lexical-query requirement. A full-tree test inspects the actual
model requests. These later changes have offline coverage, not V5 live coverage.
A further full-tree synthetic test covers all 23 default quantities in one
coherent parameterization, using reviewed assumptions across geometry/removal,
transmission and conditional-limit tools. It verifies closure coverage and
provenance without treating the fixture as live evidence.
An additional scope correction limits automatically inherited investigation
candidates to the parent's contracted fields and subjects. All evidence remains
visible to review, and explicit related hypotheses are still allowed. A test
checks that out-of-scope assessments retain their versions while cross-field
contrary evidence still reaches the active assessment. This also postdates V5.

The original live request describes a capability for arbitrary cases without
defining a concrete test case. Clarification has been requested about whether
the workflow should choose evidence-backed reference scenarios itself or the
user will provide a natural-language test scenario. No scientific parameter
records, extracted paper values, or hand-written numerical results are to be
preloaded in either mode. End-to-end live success remains unverified.

V5 finished at 240 calls after 133 units with 20 numeric source records, 142
qualitative records, six retained condition judgments and zero calculations.
Provenance checks passed. There were 35 reasonableness calls, but three retained
judgments lost current support when later reassessment hit an operational limit.
The well-mixed requester condition was correctly classified with zero discovery
credit. No malformed JSON occurred. Two HTTP 400 responses explicitly named a
provider biological-risk policy refusal, not a local network restriction; earlier
runs' unexplained HTTP failures cannot be assigned that cause retrospectively.
The parent continued to investigate equation fidelity rather than instantiate a
numerical target parameterization. Five late numerical hypotheses were rejected
because their newly invented subject labels had no reviewed scope definitions.
The subject contract and diagnostic now make this requirement explicit. Compound
unit spacing and the observed exhaled-quanta unit phrase also have tested
normalization, without changing quotations or independent review. These latest
changes are not verified by V5. The full quantitative live goal remains open.

After studying V5's repeated equation-fidelity investigations, root proposals now
receive a compact `scientific_progress` view from the same current-coverage
projection as report closure. This distinguishes assessed conditions from
numerical inputs and actual calculated quantities. It neither executes kernels
nor chooses actions or changes the numerical credit rule. Root instructions also
distinguish existing executable equations from justified scenario parameterizations;
conditional choices are not universal defaults. Three tests cover actual proposal
delivery, partial coverage, support withdrawal and nonmutation.

V6 tested the unchanged original request and full metric scope with these changes
loaded; all implementation hashes matched at completion. It stopped on numerical
low yield at 228 calls and 125 units, not the global operational limit. All 228
responses parsed, with no provider failures. It retained two numerical source
observations, 119 qualitative records and seven condition judgments, but no
numerical hypothesis proposals or calculations. Provenance checks passed. The
parent saw zero numerical coverage and nevertheless kept investigating equation
fidelity. Numerical saturation is not scientific success or literature exhaustion.

Studying V6 exposed a source-reader difference from the reference implementation:
raw substring counts instead of token BM25 with neighboring context. The ranking
is now copied locally from nano-graphrag with its MIT notice, using only stdlib;
there are no cross-repository imports. Ranking preserves all chunks and does not
decide stopping. Original neighbors are retained before processed chunks are
filtered. Tests cover token boundaries, common-term repetition, adjacent context,
stable ties, complete tails and processed-neighbor handling. An observational
replay improved placement of the requested section in retained V6 source text;
that text is not supplied to a new live run.

V6 also admitted a model-extension topic as an additional target case. Scope
instructions now distinguish a case/conditional experiment from an investigation
topic, while allowing explicitly conditional cases when the request leaves them
open. Rejected scope reasons now reach the parent instead of being lost behind a
generic unknown-subject error. These changes have offline coverage, not live
verification. The full quantitative goal remains open.

## Work-In-Progress Publication

User-requested destination: `git@github.com:chian/episode_workflow.git`.

The user subsequently paused the goal and explicitly requested a push now.
This publication is therefore an unfinished snapshot, not a completion claim.
Local Git is initialized on `main`, with the requested URL as `origin`. The
123 source/test/documentation files exclude `.env`, environments, caches and
`.artifacts`. The index scan found no configured API keys or private-key markers.
The full quantitative goal remains incomplete.

- [ ] Finish and verify the full implementation goal before claiming completion.
- [x] Inspect the commit contents for credentials, local configuration, virtual
  environments, and private/raw research artifacts; these must remain excluded.
- [ ] Initialize the repository if needed, commit the verified source and tests,
  and push to the requested destination without overwriting unrelated history.
- [ ] Verify the remote commit and report the repository URL and commit.
