# Response Failure Study

## Baseline: Approved Tree V1

Artifacts: `.artifacts/live/approved-tree-v1-report.json` and
`.artifacts/live/approved-tree-v1-audit.json` (local, ignored).
The run used only `docs/ORIGINAL_SCIENTIFIC_REQUEST.txt`, with 80 model calls,
100 total-unit maximum, four search results, and the four requested time/risk/
distance metrics. It ended at the model-call limit after 46 units. It admitted
44 qualitative evidence records, no numeric facts, no assumption assessments,
and no calculations. This is an incomplete run, not scientific convergence.

The recorded failures were not JSON syntax errors. The responses parsed, but
subsequent field, type, or meaning checks rejected them. Counts below refer to
retained rejection records, not necessarily distinct scientific facts.

| Observed Pattern | Count | Interpretation |
| --- | ---: | --- |
| Numeric candidates with string values | 50 | Forty were ordinary numeric text; ten were ranges, inequalities, or approximate text. The prompt said "number as printed" while admission required a finite JSON number. |
| Source choices under the wrong field name | 10 | Responses used `selected_source`, `selected_source_id`, `source`, or `source_id` instead of `option`. Feedback said to choose an unvisited source, obscuring the actual shape error. |
| Source qualitative evidence rejected solely for tagging declared output names | 42 | Evidence about equations, distance scales and model regimes was tagged with names such as `indoor_reproductive_number`; the validator only allowed parameters and conditions. |
| Source qualitative evidence containing other undeclared fields | 7 | Tags included table metadata such as activity and experiment labels; these belong in context, not invented canonical fields. |
| Request-level output requirements proposed as evidence | 4 | These describe the requested task, not scientific support for its answers. They should not become empirical evidence. |
| Reading windows rejected for multiple anchors to the same span | 4 | An overly restrictive memory check could discard the extraction before admission. The old run did not retain those complete responses, so the lost content is unknown. |

Some rejected candidates contain potentially useful quoted source information.
This does not make all rejected candidates valid: the trace also proposed
incubation duration as exposure duration and deposition velocity as a removal
rate. A formatting correction cannot bypass unit and applicability review.

## First Changes

- Explicit JSON Schema types and enumerated names for extraction and source
  selection, with instructions to return instances rather than schema text.
- Numeric scalar facts separated from quoted ranges, bounds and equations.
- Qualitative evidence vocabulary shared between prompt and validator, including
  declared output names. This does not give it calculated-output credit.
- Missing-selection diagnostics identify `option`, the received field names,
  valid choices, and the fact that no source was visited.
- Memory validation no longer discards independently admitted evidence; multiple
  exact anchors to one original span are allowed.
- Model requests and responses retained for local inspection, including raw
  malformed text and valid extraction responses followed by failed reviews.
  Syntax, truncation, duplicate keys, nonfinite numbers, transport failures and
  operational limits have distinct diagnostics. Raw rejected content is not
  promoted to evidence or inserted into parent prompts.

No discarded scientific content was manually added to the report. There is no
automatic numeric-string coercion, guessed range endpoint, JSON repair, or
hidden retry loop.

## Verification and Remaining Work

`python -I -S -B scripts/check.py`: 147 tests, 146 passed and one opt-in live test
skipped. Fixtures cover schema vocabulary/types, precise selection feedback,
range/equation evidence without answer credit, failed-review retention, parser
diagnostics, memory isolation, and standalone execution.

These tests establish boundary behavior, not an observed improvement in live
model behavior. The baseline started before the changes; a new prompt-only
live run is still needed to measure whether format rejection recurs, whether
useful evidence survives full scientific review, and whether enough resources
reach assumption assessment and calculation. Scenario-scope issues, hypotheses
with missing numeric values, and exhaustion before parent assessment also
remain subjects for study; the baseline is not a successful scientific report.

## Follow-Up: Approved Tree V2

Artifacts: `.artifacts/live/approved-tree-v2-report.json` and
`.artifacts/live/approved-tree-v2-audit.json` (local, ignored). Same original
request and operational limits as V1; no external scientific records were
provided. This is an observational comparison, not a controlled causal test:
model choices and retrieved material differ between runs.

V2 ended at 80 model calls after 32 units. It retained 29 numeric facts (26
source model parameters and three source observations), 193 qualitative evidence
records, one provisional assumption assessment, and zero calculations. Record
counts do not imply independent claims or root scientific progress. Every
admitted quotation was checked against its retained original source version.

All 80 model responses parsed as JSON objects. All 62 proposed numeric facts used
JSON numbers. Both source-choice responses used the declared `option` field.
The prior numeric-string, unknown evidence-tag, and source-choice field failures
did not recur. Invalid reading memory occurred twice without discarding the
separately admitted evidence.

Remaining observed failures:

- Twenty numeric proposals hit unsupported but dimensionally compatible unit
  notation, including `/h`, `cm/s`, `q/m3`, `q/h`, `people`, and micro-Pascal
  seconds. The six other unit failures used `10-16` as a dimensionless table
  scale; these still need careful treatment of the original header notation,
  not an assumed exponent or range interpretation.
- Seven numeric proposals passed deterministic conversion but were rejected in
  semantic review because a child question or raw basis said to preserve source
  units without conversion. The reviewer treated canonical storage as violating
  that instruction. The printed representation and normalized representation
  need explicit separate meanings, as now supplied by the conversion metadata.
- Two other semantic rejections were substantive: infected count at time t was
  misclassified as secondary cases, and drop number density per radius was
  assigned to aerosol volume fraction without the needed size integration.
  These checks remain in place.
- Thirteen qualitative proposals lacked an exact available source span. No
  quote was repaired by guessing or admitted without verification.
- The first table query supplied `rows: []`, `query: ""`, and `column: ""`.
  Its intent was a scan, but the validator interpreted the present empty row
  list as an explicit selection. The new contract distinguishes the alternatives
  and says to omit rows for a text query.
- Two investigation proposals attempted to redefine existing scenario scopes.
  The current prompts and diagnostics distinguish references from new definitions;
  identical scope definitions reuse their review without transferring support
  to changed definitions.
- Assumption review began only at call 76. Three of four reviews returned
  `supported` despite applicability grade 1. The validator required all grades
  to be 2, but that requirement was absent from the supplied response contract.
  The fourth review yielded the one admitted provisional assessment. Another
  proposed numeric dependency had null value and unit `condition`; it failed
  validation before a review call. That is an unresolved information need, not
  a valid scalar candidate.

The current reasonableness contract now exposes the unchanged consistency rules:
`supported` requires every grade to equal 2, positive grades require evidence
references, and `provisional` requires limitations. Inconsistent responses remain
rejected; neither verdicts nor grades are silently rewritten. Feedback names the
inconsistent dimensions. These assessment changes were made after V2 and have
offline coverage only so far.

The run still did not reach a calculation. Acquisition used most of the available
calls before parent assessment, and scenario proposals remained dependency
templates rather than evaluated parameterizations. The next behavioral study
must distinguish these goal/contract and resource-allocation questions from
formatting failures. No scientific answers have been manually added to make
the report complete.

## Subsequent Interface Checks

The working implementation additionally has explicit alternative JSON Schemas
for table row selection versus literal text queries. Empty row lists are not a
query selector, and invalid row diagnostics name the received values and show
available keys. A test confirms that literal queries can select matching rows
beyond the bounded preview. This does not prescribe which rows an episode reads.
Selected rows are marked consumed only after an evaluated reading, not before
extraction/review. A failed review leaves them selectable with its diagnostic;
the episode still chooses its next action, without an automatic retry.

Rate and quanta notation aliases, centimetre-per-second velocity, and
micro-Pascal-second viscosity have dimension-specific conversions. Review
receives the original printed value/unit, the conversion factor, and the
canonical candidate. It must still judge whether the source supports the
quantity and its assignment. A velocity cannot become a removal rate through
notation normalization. No range midpoint or undocumented scale factor is
inferred.

The current offline suite runs 173 tests: 172 pass and the opt-in live test is
skipped. The live V2 run started before these additional table and unit changes;
its startup implementation hashes prevent attributing its behavior to them.

## Parent Contract Follow-Up

The V2 root selected specific target subjects, but the investigation created new
dependency-template subjects instead. Inspection found a real delivery gap:
`EpisodeRequest` retained the parent's reporting contract, while model inputs
during child work omitted it. The message also listed every known scenario,
rather than the root's selected subjects. The current binding now exposes the
actual contract and selected subjects throughout the child branch, including
extraction and mandatory reasonableness review. New tests inspect those model
requests across the executed tree.

The investigation can now specify the evidence focus of a strategy instead of
automatically assigning every strategy its entire scientific field list. The
parent's goal and credit remain unchanged, and neither search order nor reading
order is prescribed. This is a capability for more precise child contracts,
not evidence yet that the live model will use it effectively.

The invalid null numerical dependency is now rejected before acquisition with
an explicit numerical-versus-condition schema. Validation is atomic for newly
proposed candidates. Previously, late failure of one assessment also marked
the entire batch unevaluated; independent successful judgments are now counted
without granting credit to the failed judgment. A proposal begins from current
admitted state so a failed proposal cannot restart assessment from a stale
staging snapshot. These changes do not bypass quotation, applicability, or
reasonableness checks, and have not yet had a fresh live evaluation.

An additional report/communication audit found that assumption summaries and
rendered citations included every evidence option considered by the reviewer,
even options not cited in any criterion. They now carry only the cited basis
plus the number of considered records; the full considered set remains in the
audit. Reassessment still receives all admitted evidence, including cross-field
material, and credit/version logic is unchanged. Tests check this distinction
in parent-facing options, previous judgments, and Markdown citations. V3 started
before this correction.

## Follow-Up: Approved Tree V3

Artifacts: `.artifacts/live/approved-tree-v3-report.json` and
`.artifacts/live/approved-tree-v3-audit.json` (local, ignored). The unchanged
original request was used with the full default 23-metric catalog and limits of
240 model calls, 240 total units and four results per search. V1/V2 used four
metrics and 80 calls, so counts are not directly comparable.

V3 exhausted its model-call budget after 127 units. It retained 71 numeric facts
(62 source model parameters and nine source observations) and 390 qualitative
records, but no assumption assessments and no calculations. All admitted quotes
and recorded source versions passed the provenance verifier. Five unique source
URLs were read in six source selections; one source was reopened by a later query.
The root scientific credit remained zero.

There were 237 parsed JSON-object responses, two HTTP 400 failures during evidence
review, and one malformed synthesis response. All 106 proposed numeric facts used
JSON numbers. All six source choices used the declared option field, and all
eight table-query proposals used one of the declared selector shapes. No scenario
redefinition or numeric-null candidate failure occurred. Three model-condition
candidates were proposed for the parent's actual subjects, but budget exhaustion
prevented their assessment. Thus the revised assessment response contract was
not exercised by this run.

### Rejected and Retained Information

- The malformed response was a 4,971-character synthesis containing an invalid
  JSON backslash escape in mathematical notation. The exact response is retained
  at model call 106. Its 96 input findings and admitted evidence were retained by
  the synthesis fallback; no scientific evidence depended on parsing that prose.
- Evidence-review calls 31 and 233 returned HTTP 400. The preceding extraction
  responses retained ten and five proposed qualitative records, respectively,
  and no numeric proposals. Those records were not admitted through the failed
  reviews. Their availability does not establish their correctness or novelty.
  The HTTP boundary retained status but not provider explanation, so the cause
  cannot be determined from this trace. In particular, it is not evidence of a
  sandbox/network block or necessarily excessive context size.
- Sixty-one extraction rejections comprised 28 unit-conversion failures, six
  printed-number mismatches and 27 exact-quotation failures. The newer notation
  support handles 25 of those unit spellings, but is not verified by V3. Unit
  normalization alone does not validate meanings such as percentage increases,
  student counts versus total occupancy, or probability versus infectivity.
- Eleven semantic evidence rejections included infected-attendee counts versus
  secondary cases, mouth area versus floor area, and otherwise valid general
  physical discussion that did not answer a narrowly requested equation lookup.
- Twelve memory updates failed because anchors were not exact or did not refer
  to seen spans. Separately admitted evidence survived those memory failures.

After the run, provider instructions explicitly require correct JSON escaping
of backslashes/control characters, and synthesis prefers plain-text mathematical
notation. Tests distinguish valid escaped notation from invalid raw escapes;
there is no guessed JSON repair. This is an instruction correction to evaluate
in a future run, not proof that the live failure has disappeared.

### Control and Communication Findings

Acquisition consumed the entire model budget: 95 extraction calls, 72 evidence
reviews, 28 syntheses and the remaining proposal/scope calls. Only one root action
and one investigation proposal occurred. The strategy completed one search and
entered a second; numerical yield stops in individual reading episodes did not
return control to the scientific parent soon enough for assessment/calculation.
Increasing the global budget alone did not establish end-to-end success.

Parent-facing requests also remained large despite diagnostic compaction. The
largest serialized request was 1,310,558 characters: evidence options contributed
531,979, child reports 540,217, and accumulated findings 92,229. This measures
serialization size, not provider tokens, and does not prove why HTTP 400 occurred.
The audit retains full records, but passing those records repeatedly into proposal
contexts is not condensed communication. Decision-specific projections and
parent-owned child resource envelopes deserve the next behavioral refinement;
neither requires changing the approved ownership tree or scripting an action order.

The run correctly treated the original prompt as a capability request without
concrete case parameters. It retained arbitrary-case templates instead of silently
assigning reference-paper values to them. The outstanding natural-language test
scenario choice remains distinct from the acquisition/resource issue. No paper
values or finished scientific outputs have been manually inserted into the run.

### Implemented After V3

Parents can now choose an optional model-call allowance for each child subtree.
Actual remaining resources are provided in proposal context, including the fact
that investigate needs a review call for each new or changed candidate. Limits
are inherited and clamped to the enclosing allowance, not automatically divided
by a fixed recipe. Return synthesis and mandatory assessment are charged to the
invoking parent. A local ceiling produces an explicit operational stop, never a
scientific saturation claim. Synthetic end-to-end tests verify that bounded
acquisition can leave resources for assessment and calculation; live use remains
to be studied.

Acquisition proposals now receive source/field/role inventories, while scientific
proposals receive detailed evidence summaries. Exact quotes and source versions
remain in independent reviews and the audit. Child reports carry a change index
and only issues/diagnostics not already held by the invoking parent. Assigning
diagnostic identities on entry prevents inherited failures from appearing new
after later projection. Newly repeated failures still have separate identities.
Synthesis failures also reach ancestor diagnostics without discarding evidence
or changing credit. Successful new judgments on previously held evidence remain
evaluated even if the latest acquisition failed.

An offline re-projection of V3's largest request reduced its serialized size from
1,310,558 to 836,570 characters (36.2%) using only evidence summaries/inventories
and child change indexes. This deliberately leaves old inherited-diagnostic
replays included: their exact delta cannot be reconstructed from that request
alone. It is a size measurement, not a fresh model response or evidence of better
scientific decisions.

The HTTP boundary now preserves bounded recognized error fields (message, type,
code, parameter, detail), redacting the configured credential before truncation.
It omits headers, unrecognized nested request echoes, oversized bodies and
non-JSON error pages. This can expose a future provider's stated reason without
guessing a cause from status alone. It does not reconstruct V3's lost responses
and was implemented after V4 started.

While studying V4's early trace, a root action failed on an invalid focus list.
The root still used a prose-shaped response template where validation required
exact field keys. Its response is now specified by a JSON Schema with focus enums,
available fact choices, condition keys and tool-specific required fields. Invalid
focus diagnostics name the offending entries. Context also describes known call
costs through the tree after V4 showed several reading scopes with too little
allowance for extraction plus mandatory review. This exposes accounting facts;
it does not choose a budget or force an action. Neither change is loaded in V4.
The current offline suite passes 189 tests, with one opt-in live test skipped
(190 total).

## Follow-Up: Approved Tree V4

Artifacts: `.artifacts/live/approved-tree-v4-report.json` and
`.artifacts/live/approved-tree-v4-audit.json` (local, ignored). V4 used the unchanged
original request and full default metric catalog, with 120 model calls, 240 total
units and four search results. It ran to an operational budget stop after 70
units, not numerical convergence, and exited with incomplete report status.

Observed behavior:

- Ten root proposals resulted in eight investigations and two failed proposals.
  Twelve mandatory reasonableness reviews retained six current assessments: one
  supported and five provisional. No calculation tool was selected.
- Four numeric records described two source-event exposure durations in repeated
  passages; these are not four independent measurements. Twenty-one qualitative
  records were admitted. All admitted quotation/source-version checks passed.
- Across 57 child edges, no child exceeded its allowance; ten children consumed
  no model calls. Allocations were often too small to finish useful work. Six
  extraction responses with proposed evidence did not reach independent review:
  calls 22, 56, 59, 67, 83 and 113, retaining six numeric proposals and 39
  qualitative proposals in total. Their raw contents remain available in the
  audit but are not admitted evidence. This motivates exposing real operation
  costs, not inserting those proposals into the scientific report afterward.
- All 118 received model responses parsed as JSON objects; this does not mean
  all contracts or evidence were valid. Calls 25 and 93 returned HTTP 400 with
  no retained provider explanation. One root focus list included the credit
  criterion `evidence_consistency` as an acquisition field, triggering a vague
  contract rejection. The later root schema and diagnostics correct that mismatch.
- Thirteen extraction rejections comprised four unit-label failures and nine
  quotation failures. One memory update failed. Three semantic rejections and
  one no-relevant-evidence diagnosis were retained separately. In particular,
  unrelated jury-trial guidance could not substitute for the requested paper's
  near-field model equations.
- The largest serialized request was 284,111 characters. Its child reports were
  94,727 characters and assumption options 73,707. V4 acquired much less evidence
  than V3 and used half its call allowance, so this is not a controlled measure
  of the communication changes' effect or a claim that context growth is solved.

### Credit Classification Finding

The raw root history was 0, 0.026882, 0.021505, 0.026882, 0.026882, 0.026882.
This is not a clean measure of scientific progress. The request's explicit
well-mixed constraint was extracted under `requested target scenario class`,
while the candidate used `arbitrary_well_mixed_room_case`. Exact subject matching
failed to recognize the requester condition, so it received discovery credit.
The reviewer itself correctly described it as a modeling premise, not empirical
proof of mixing in any real room; the credit projection missed that distinction.

After V4, the mandatory review contract requires an explicit requester-condition
classification, with admitted request citations and a target-scope explanation,
or null for a scientific hypothesis. Validation checks evidence kind, field and
numeric value; the assessor judges scope applicability. An admitted binding
preserves conditional support but earns zero discovery credit. Its citations
remain in summaries. Tests cover different scenario-class labels, missing
classification, source evidence masquerading as a request, and mismatched values.
The historical trace has not been rewritten and this correction is not yet live
verified. It does not introduce new requester facts or relax assumption support.

V4 retained an arbitrary-room template rather than silently supplying numerical
case parameters. No complete quantitative result or cross-case agreement has
been established. The approved ownership tree remains unchanged.

### Proposal Versus Execution Boundary

Reviewing V4's actual strategy text showed repeated formula-inventory planning
and an insistence that numerical proposals be explicitly printed in a source.
The provider system prompt had accidentally imposed that restriction on all
scientific alternatives: it allowed only admitted facts and declared operators.
This conflicted with investigation's intended hypothesis capability. It now
applies to calculation execution, while candidate hypotheses may be inferred
and then independently assessed. Extraction's exact-source requirement is
unchanged. A full-tree synthetic test distinguishes an unprinted provisional
input from the source's reported value and checks its use in calculated outputs.

The root prompt now also distinguishes performing the scientific investigation
from designing a future generator. Templates and formula inventories can inform
the work but do not replace supported conditional conclusions. This adds no
case values, chosen example, source text or action sequence. Scope alignment and
requester constraints remain binding. Per-operation call costs now appear both
in context and in the child-allowance description, since V4's one-call reading
allowances could not cover extraction plus independent review.

Another communication correction names the candidate in each failed mandatory
assessment. Previously every failure carried the same entire strategy proposal;
condensation could then hide which hypothesis had not been evaluated. The new
projection retains subject, field, value and the original failure category. It
does not turn an unsuccessful assessment into evidence or issue recovery orders.

### Remaining Contract Shapes

After V5 began, an interface audit found remaining prose-template contracts for
strategy queries, page choices, evidence review, scope review, model review and
return synthesis. These now use typed JSON Schemas like the other active-tree
operations. Candidate counts and valid option keys are explicit, and lexical
probe choices require a query. These are prompt contracts, not a claim of
provider-enforced structured decoding; existing independent runtime validators
remain in place. No admission or scientific scoring rules were relaxed.

Early V5 reading also rejected unambiguous printed unit spellings `m 2`, `m 3`
and `h -1` with a Unicode minus. Explicit power/inverse-unit grammar now accepts
these without globally removing whitespace or guessing dimensions. Original
printed units and quotes remain available to independent review. Tests also
reject area as volume, area-rate as area, and `m s` as seconds. V5's loaded code
predates these changes. A full-tree synthetic test additionally checks all 23
default quantities assembled from the three calculation groups under one
coherent assessed parameterization. This is not empirical or live validation.
The offline suite now runs 197 tests, with 196 passing and the opt-in live test
skipped.

### Inherited Assessment Scope

The investigation constructor automatically adopted every inherited assessment
as an active candidate, including other subjects and fields outside the parent
contract. V4 call 61 reviewed `emissions_stopped` for the arbitrary-room target
inside a branch contracted to the paper and jet-model subjects. That branch's
proposal introduced no new candidates; the work was inherited automatically.

Automatic adoption now uses the parent's fields and requested subjects, after
the episode is bound. Explicit related hypotheses remain possible. This scopes
assessment work, not its evidence: the independent reviewer still receives all
admitted evidence, including cross-field contradictory material. Other known
assessments remain in shared knowledge for the parent to revisit. A regression
checks both field and subject boundaries and unchanged out-of-scope versions.
The correction was made after V5 startup and is not exercised by that run.

## Follow-Up: Approved Tree V5

Artifacts: `.artifacts/live/approved-tree-v5-report.json` and
`.artifacts/live/approved-tree-v5-audit.json` (local, ignored). The unchanged
original request, all 23 default quantities, 240-call limit, 240-unit limit and
four results per search were used. No prior-run evidence or numerical inputs
were supplied. V5 ended at 240 calls after 133 units, with incomplete status.

### Scientific Outcome

Twenty numeric source records (18 model parameters, two observations), 142
qualitative records and six retained condition judgments were produced. All
admitted quotation/source-version checks passed. No calculation tool was selected.
Ten root proposals led to eight investigations and two failed proposals. The
only target remained an arbitrary-room parameterized template, not a numerical
case. Repeated investigations focused on exact equation grouping and applicability.

Thirty-five reasonableness calls returned valid assessments. The final six
judgments comprised three supported and three provisional verdicts, but three
had their current support withdrawn after a subsequent assessment exhausted its
allowance. Thus verdict counts alone overstate current support. The well-mixed
premise was correctly classified as requester-defined, with zero discovery credit.
The final root score was 0.010753; it is not a measure of numerical report coverage.

Only at call 239 did the branch propose numerical hypotheses: five activity-specific
values, under new colon-suffixed subject labels. No corresponding scenario
definitions were proposed, so validation rejected the batch before acquisition
or admission. None entered the report. The candidate schema and instructions now
explicitly distinguish reviewed scenarios from source-event labels; the diagnostic
names the missing subject and available definitions. No scenario is silently
invented to accommodate a malformed candidate.

### Response And Resource Findings

- All 238 received responses parsed as JSON objects. No malformed JSON occurred;
  this does not establish that every response satisfied its scientific contract.
- Calls 61 and 64 returned HTTP 400 with explicit `bio_policy` refusal text from
  the provider. These are provider-side policy refusals, not evidence of local
  filesystem, AppArmor or network blocking. No bypass was attempted. The causes
  of V3/V4 HTTP failures remain unknown because those responses did not retain
  explanations.
- Sixty-five extraction rejections comprised 35 quotation mismatches, 29 unit
  spellings and one printed-number mismatch. The unit changes made during/after
  V5 recognize 24 of those spellings, including spaced compound units and the
  explicit exhaled-quanta phrase. Recognition alone does not establish admissible
  source meaning. Four invalid memory updates and two semantic rejections were
  recorded separately; memory failures did not discard admitted evidence.
- Eight extraction responses were not followed by independent evidence review,
  retaining 12 numerical and 25 qualitative proposals in the raw audit. Some
  numerical proposals had already failed deterministic unit checks. These are
  candidate counts, not valid evidence counts, and were not added afterward.
- All 98 child edges respected their allowances, but 14 children used zero model
  calls. There were 51 unavailable return syntheses and 15 failed mandatory
  assessments due to operational limits. Undersized allocation remains a real
  behavioral limitation despite the explicit cost information.
- Seven assessment calls concerned inherited fields outside their parent focus
  (123, 146, 172, 198, 235, 236, 240). This reinforces the scoped-inheritance fix
  described above; V5 did not load it.
- The largest serialized request was 763,480 characters at call 238: child reports
  contributed 258,036, assumption summaries 145,736, evidence summaries 132,973,
  diagnostics 115,017 and accumulated findings 49,755. These are characters, not
  provider tokens. Context remains large; comparisons with other runs are not
  controlled measurements of a single change.

The typed remaining response contracts, scoped inherited assessments, final
unit-notation changes and candidate-subject clarification have offline coverage.
The full-tree synthetic test covers all default output quantities under one
coherent parameterization, but cannot establish live discovery or scientific
success. V5 does not complete the quantitative workflow goal. No commit or push
has been made; publication remains conditional on that goal's completion.

### Scientific Parent Feedback

V5's parent repeatedly investigated equation fidelity while no target numerical
parameterization existed. The parent received a yield score, the metric catalog,
evidence and earlier findings, but lacked a compact view of current requested
conclusions. Root proposals now receive `scientific_progress` from the same
version-aware projection used for report coverage. It explicitly distinguishes
assessed numerical fields, assessed conditions, unevaluated outputs, supported
calculations and withdrawn support. It is a read-only assessment view, not a
hidden calculation, extra action, or instruction to follow a prescribed sequence.

The root instructions clarify that registered equations are already executable
kernels, whereas a numerical parameterization still needs justified inputs.
General applicability is not a claim that one input set holds for every room;
named conditional parameterizations do not become universal defaults or requester
givens. No case, source or value has been supplied from outside the workflow.
The actual proposal view, partial coverage, stale support and unchanged admitted
state are covered by offline tests. Live behavioral improvement remains unproven.

## V6: Valid JSON, Unresolved Scientific Goal

V6 used the unchanged original request and all 23 default quantities. Its loaded
implementation hashes matched the files at completion. The run stopped on the
root's numerical low-yield rule at 228 calls and 125 units, below its 240-call
ceiling. This is operational saturation, not scientific completion or proof that
the literature is exhausted. No calculation was produced.

All 228 responses parsed, with no provider failures. The run retained two
numerical source observations, 119 qualitative records and seven condition
judgments. No numerical assumption was proposed. Thirty-three reasonableness
calls and five root choices did not establish a numerical parameterization. The
new scientific-progress view was present in every root choice after the first,
showing zero calculated quantities and no assessed numerical inputs. That
feedback alone did not redirect the parent's repeated equation investigations.

Twelve deterministic extraction rejections comprised eight quotation mismatches
and four count-unit spellings (`attendees`, `attendees infected`, `passengers`,
`passengers infected`). Three reading-memory updates failed their contracts.
Five independent evidence reviews rejected candidates. One correctly rejected an
OCR mixing-time expression whose dimensions conflicted with its stated physical
meaning; valid JSON is not a substitute for scientific review. Forty return
syntheses and three mandatory assessments were unavailable because of local
operational allowances. The largest serialized request, call 199, was 642,330
characters, including 177,104 in child reports and 164,906 in assumption summaries.
Context volume and allocation behavior remain limitations.

### Local Reader Ranking

The reader used raw substring counts rather than the reference nano-graphrag
reader's token BM25/context rank fusion. The latter is now adapted locally with
its MIT notice. It ranks direct chunks and neighboring windows at radii 1 and 4;
all chunks remain eligible and only the episode decides stopping. Ranking uses
the original document before filtering already-processed chunks, avoiding false
adjacency across gaps. No external runtime import or additional dependency exists.

For the V6 retained main-paper document, the section-title query at calls 62 and
88 had old top chunks 3, 21, 17; new top chunks are 18, 17, 19. The heading occurs
in chunk 17. The longer query at call 84 changed from 3, 21, 18 to 19, 18, 21.
These are observational full-document rankings, not reconstructed processed-state
executions or proof of successful extraction. They identify a retrieval-order
improvement to test, without injecting retained evidence into later runs.

### Scope Contract

The scope reviewer admitted a respiratory-jet model extension as a target case,
causing closure to expect all requested quantities for that topic too. Root and
scope-review instructions now distinguish calculation topics from cases or
conditional experiments. Agent-proposed study conditions remain allowed under
an open request, but must not replace specified cases or claim universal results.
Scope rejection now preserves the reviewer's reason for the parent. These are
generic contract changes, not supplied cases, values, source URLs or action order.
Offline tests cover them; V6 predates both changes and does not verify them live.

## V7: Suspended, Not A Completed Study

V7 used the original request and all 23 default quantities, with a larger
480-call operational ceiling and the same numerical stopping rule. No prior
evidence, source text or parameter records were supplied. The user paused the
goal after about 84 minutes; the process was suspended with its in-memory state
intact. The latest completed verdict recorded 302 calls, followed by further
proposal calls. The final report and audit have not been generated. This is not
a completed live verification, and exact final counts remain unavailable.

Unlike V6, the root selected calculation tools. Visible attempts were rejected
by model admission or failed because selected parameters lacked current support;
no successful quantitative report has been verified. The trace also contains
explicit provider biological-policy refusals, not local permission failures.

Two concrete code-level concerns emerged, neither fixed in this snapshot:

- A failed mandatory reassessment sets an earlier assessment's reasonableness
  and resolution credit to zero, creating a new version even when the failure
  is operational rather than a scientific verdict. Later tool calls then reject
  those inputs. This needs a distinction between an unfinished reassessment and
  an actual withdrawal of scientific support.
- The root's metric choices are not constrained to each tool's actual metric
  group, and independent model review does not receive the registered metric
  catalog. A visible proposal mixed outputs belonging to different tools; the
  reviewer also identified an undefined formula basis. The executable contracts
  need to be made explicit to both selection and review.

Undersized child allowances still leave some extracted candidates without their
mandatory independent review. These observations are preliminary log/code study,
not a reconstruction of the unfinished audit. The user requested publication of
the current work in progress while the goal remains paused.
