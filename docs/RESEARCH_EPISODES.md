# Approved Scientific Episode Tree

The active API is `run_guideline_research(disease=..., scenario=...)`, also reached through
`run_configured_safety_guideline_request` and the CLI. The executable type tree
is declared once in `case_reports/research/engine.py`. All instances execute in
one `method_loop.Context`; bindings do not start private nested contexts.

The caller supplies the disease and selects fixed cases; `--scenario` defaults
to the Bazant-Bush catalog. Case definitions are inputs, not discoveries or
empirical evidence. The active goal requests only allowable room time,
risk-based safe distance, and R_in. No comparison or answer-matching metric is
part of this goal. See [the current contract](CURRENT_GOAL.md) for scope and
the distinction between fixed conditions, assumptions, and calculation variables.

The V12 follow-up keeps this ownership tree. Parameter derivations are now
declared once for execution and dependency communication. Root progress exposes
their missing inputs and alternative routes, rather than just the name of an
uncomputed derived quantity. The limit and transmission tools execute available
derivations themselves; a separate geometry call is a choice, not a prerequisite.
Root input-resolution credit includes the relevant derivation parameters and
conditions. Only caller-requested outputs belong to its output-credit group;
intermediate quantities do not become additional report goals. Fixed-mode
schemas omit target-scenario creation and comparison actions, scope tool inputs to the
selected subject except for explicit transfer, and exclude fixed conditions and
calculation variables from assumption proposals.

The 2026-10-13 revision allows the parent to register a separate calibration
context only for a subject already identified by admitted source observations.
This neither creates a target case nor supplies an outbreak fixture. The existing
infectiousness tool contains the deterministic `calibrate_cq_from_outbreak`
subtask. Its derived values must retain provenance through transfer and activity
rescaling into target calculations. The parent sees calibration progress and
missing observed inputs; completion checks inspect the resulting lineage.

Earlier runs used caller-designated variable duration to bind numeric
coefficients for steady/transient R_in(t) and the applicable distance boundary
d_min(t). Records retain the variable, its domain, bound inputs, coefficients,
expression, executable kernel identity, assumptions and per-output provenance.
`evaluate_duration_relation` evaluates those records using the existing scalar
kernels. No duration is sampled to manufacture a point estimate. Missing bound
inputs remain missing; a formula label without computed coefficients is not a
completed output. Calculation/provenance credit recognizes these relationships
separately from evidence strength, and report projections do not execute them.
The default clean-start regime explicitly fixes initial concentration to zero
as a definition of that regime, not a discovered disease-dependent value.
Unmasked-jet limitations remain; a masked-case exclusion contains no distance
answer. V14 exercised derivation, function binding and report projection in four
real calculation calls. V15 completed fifteen calculation calls, yielding time
for eight cases and R_in for seven, but selected no distance calculations and
stopped at the root unit limit. Its assumptions remain provisional. Root numeric
options are now separated from condition statements, reviewers receive explicit
selected-input bindings, and terminal diagnostics can be cited even when a child
performed no work. V16 calculated 36 of 40 requested entries, including unmasked
distance relationships, but left masked distance uncomputed and every output
unsupported. It subsequently pursued the masked gap repeatedly and terminated
at an operational limit after Argo quota notices were misclassified as JSON
failures. Post-run quota handling and the control/communication changes below
have only been reviewed by reading. The duration-evaluation helper was not
replayed. No test-suite execution is authorized for this change.

This is ownership, not a predetermined call sequence. `[E]` is an iterative
episode; `[T]` is a selectable deterministic tool.

```text
[E] evaluate_airborne_safety_guideline
    +-- [T] calculate_geometry_and_removal
    +-- [T] calibrate_infectiousness
    |       calibrate_cq_from_outbreak(values, transient=...)
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

## Mandatory Method Wiring

The current root calculation choices expose three ordinary functions from
`task_executors/scenario_metrics/exposure.py`:

```text
[T] calculate_conditional_limits
    solve_time(model, fixed_distance, risk_threshold)
    solve_distance(model, fixed_time, risk_threshold)
[T] calculate_transmission_metrics
    evaluate_R_in(model, fixed_time, fixed_distance)
```

Each operation uses the same `R(t,x)=B(t)+J*t/x` within its named model and
background regime. Default references are 1.8288 m and 900 s. These are bound
from the caller's case before model review and execution; no physical hypothesis
is supplied by that binding. Custom case files may supply other references.
Each result records its fixed inputs, model identifier, assumptions and output
contract. Time and distance inversions remain function calls, not episodes;
the parent chooses when to calculate or investigate, with no prescribed order.

The new default metric names are `allowable_room_time_s`, `safe_distance_m`,
`scenario_reproductive_number`, and their `transient_` counterparts. Legacy
background-only metrics and duration relationships remain available but do not
satisfy these contracts. Output credit retains the 1/8 provisional floor for
current contract-matching calculations; stronger support replaces that floor.
Repeats earn no gain. The assumption rubric and numerical controller are
unchanged. This follow-up has not been executed or tested.

```text
parent goal + parent-owned information contract
  -> propose/select a unit
  -> execute the selected child or leaf
  -> mandatory admission/assessment and credit projection
  -> numerical controller verdict and state update
       continue: next proposal receives measured outcomes
       close: contracted synthesis to the parent
```

Only `method_loop.Episode` owns that loop. There is no agent stop action. Each
scope has a numerical yield history; finite source exhaustion and operational
failures have separate termination records. Failed operations do not become
evaluated zero-evidence observations, but every attempted unit enters the yield
history. An unevaluated attempt preserves prior credit and contributes zero
realized gain; it cannot bypass the estimator. Its failure flag, count and
diagnostics remain separate from scientific conclusions. The rolling
marginal-yield rule is an operational saturation heuristic, not a confidence
interval or evidence that unanswered scientific questions are resolved.

Parents specify the child's scientific goal and information contract, not a
model-call allocation. The post-V16 change removes `child_model_calls`, local
call deadlines and resource-allocation context from the agent interfaces. V16's
children almost always ended after one unit under those deadlines, before their
own yield histories could govern iteration. Each child now continues through
the existing method_loop controller, subject to source exhaustion and provider
failure. There is no model-call, whole-run unit, or per-episode unit budget.
Model attempts still distinguish proposal
work from mandatory processing. Synthesis remains commissioned by the invoking
parent. There is no cost term in credit and no prescribed action sequence.

The root requires an information `objective` for a delegated investigation.
Deterministic tool choices retain their required `basis`, parameterization,
numeric references and condition statements; a second `objective` is optional.
This removes a redundant tool-choice rejection seen in V16 without manufacturing
missing scientific inputs or weakening child information contracts.

## Scope Ownership

| Episode | Owns | Iterates Over |
| --- | --- | --- |
| evaluate_airborne_safety_guideline | Requested scientific conclusions within caller-defined scenarios, assumptions and versioned calculations | Selected tools or investigations |
| investigate | One parent-contracted uncertainty, candidate assumptions/explanations, alternatives and reasonableness | Evidence-acquisition strategies |
| strategy | One evidence approach and feedback about its queries | Newly proposed searches |
| search | One query, its returned source candidates and earlier source outcomes | Selected source episodes |
| page | One retrieved source and its remaining readable material | Available table, report or lexical reading episodes |
| source_table | One physically detected table and prior query results | Parsed-table query executions |
| report | Sustained reading and cross-window subject context | Successive document-order windows |
| lexical_probe | One literal source-local query and ranked remaining spans | Unprocessed chunks |

The collective assumption-justification capability belongs to the investigation
branch. Reading episodes extract evidence; they do not manufacture assumptions.
Calculation execution selects existing facts or numerical assumption options,
including guesses whose evidence support is zero. Hypothesis proposal may reason
about unprinted values. Mandatory assessment determines support and credit,
not permission to calculate. The root performs scientific work using the declared kernels;
an implementation plan or parameter glossary does not complete its goal.
Before choosing another action, the root also receives `scientific_progress`:
current coverage for every requested quantity, assessed numerical versus model
condition fields, and whether a coherent parameterization has been evaluated.
It uses the same version-aware projection as report closure. It does not execute
calculations, select a next action, change credit, or admit evidence. A catalog
of source equations cannot appear in this view as numerical output coverage.
`quantity_coverage` also lists computed-but-unsupported cases. Provisional
calculation and evidence refinement are concurrent scientific needs; completing
every numerical field is not a prerequisite for revisiting a weak assumption.

Each metric now declares its enforced `parameter_constraints` once. Execution,
dependency routes, root proposals, reviewers and child synthesis use that same
contract. An implemented metric name does not mean every case has an applicable
route: the continuous-jet kernel still excludes masked parameters. New evidence
can inform a future model extension, but a condition statement cannot add a
kernel or override its domain. Synthesis must distinguish that implementation
gap from a missing hypothesis, weak evidence or a physical contradiction, and
retain useful implications for other cases when evidence has wider relevance.
That capability communication alone did not supply a masked-distance answer or
add an evidence-quality gate. The subsequent extension below adds an explicit
alternative without altering the unmasked-jet formula.

### Shared Risk Model Choice

Both calculation tools expose the same alternative risk models for all three
operations. The continuous-jet route remains unmasked. Selecting the separate
`negligible_near_field` condition sets the local coefficient to zero for time,
distance and R_in together. For distance this means no positive minimum under the room-risk
criterion, or no finite separation meeting it above the criterion. Mask use and
well-mixed background do not automatically select or justify this condition.
The investigation owns the hypothesis and its evidence assessment; the root
selects the named condition with its parameterization. Conflicting conditions
cannot be combined. Reported zero is a model-bound interpretation, not safety
at contact, and the model does not calculate masked leakage or thermal plumes.

Routes expose their own inputs and conditions to proposals and synthesis.
Calculation support follows the actual selected route, including the additional
physical hypothesis. A transient background with the additive jet requires an
explicit `quasi_steady_local_plume` assumption: the local flow is immediately
established while background concentration builds up. This is not a time-resolved
jet model or an approximation automatically justified by clean initial air.
The default point inputs define the three requested evaluations, not new rooms
or manually supplied scientific answers. A supported
kernel exclusion is diagnostic information, not a resolved output: it earns no
output credit and cannot complete a report. The new route has not been executed
or verified in live behavior; V16 contains no results from it.

`investigate` proposes hypotheses as part of choosing its next strategy. Every
returned strategy passes through mandatory reasonableness assessment before
scientific credit. Newly relevant contrary evidence triggers reassessment of
existing candidates. Assessment is never an optional tool or sibling episode.
Its proposal explicitly supplies `candidates`, which may be empty for an
evidence-only iteration. Instructions asking the strategy child to construct
assumptions do not register them: that child returns evidence, while the
investigation owns the inference and target applicability rationale. This
ownership is now explicit after V13 repeatedly delegated it to the wrong scope.
V14 registered candidates, reviewed them, and eventually calculated provisional
outputs. It still assembled inputs broadly across all eight cases before its
first calculation, and later confused condition references with numeric options.
The [trace study](RESPONSE_FAILURE_STUDY.md#v14-provisional-calculations-incomplete-coverage)
records these limitations without changing the ownership tree.

When independent extraction review cannot finish, the child retains candidate
records in diagnostic audit, not the evidence catalog. Its compact
`extraction_state` describes completed deterministic checks, the still-unreviewed
claims/values, affected fields and locations within the versioned source.
Synthesis can use that state to explain consequential failure implications;
it is not appended to the parent's report. A failed synthesis returns only a
communication-failure notice. Useful discovery awaiting review is neither "nothing found" nor a
completed scientific rejection, and earns no evidence credit by itself.

Extraction also preserves measurements of ingredients or related systems that
lack their own numeric model field as qualitative evidence with original numbers,
units and context. Declared field tags identify what those measurements inform;
they do not relabel a measurement as an inferred final parameter. Assumption
inference and its reasonableness assessment remain owned by investigation.

## Acquisition and Reading

A search operation is required when a search episode opens. Fetching and
preparing source material is required when its page opens. Neither is a root
menu action. Candidate selection receives completed source findings and failure
reasons before another source is selected.

Page choices follow the reference repository's table/report/lexical ownership
pattern, implemented locally without imports from that repository. The page
proposer receives source identity, title, size, outline, opening, detected tables
and earlier child outcomes. There is no fixed table-first or prose-first order.

Markdown tables are parsed into addressable original row spans. Table queries
can select rows or search literal text in parsed columns; only a bounded window
is extracted per execution. Unsupported table formats remain readable as source
text through the report/probe paths, rather than fabricated parsed tables.

Report reading groups addressable chunks in document order. Retained working
memory includes a bounded summary, unresolved links, and exact original-source
anchors. Later windows receive those anchors, not every previous full window.
Memory is not evidence and does not earn credit. Lexical probes rank remaining
chunks without a relevance cutoff that silently drops the tail. Unexamined scope
excludes ranges previously supplied to extraction; explicit reexamination can
read them for another question. A reader's own cursor avoids delivering a chunk
twice in that reader; global processed keys do not prohibit intentional rereads.

Each reading execution includes extraction, exact quotation and numeric/unit
checks, and a separate semantic applicability review. Cross-window evidence
must still cite available original text, not the summary. Repeated values and
passages do not create new upstream scientific credit.

Root action proposals, extraction, source selection, and table queries use explicit JSON Schema response contracts in
the prompt. These are not claims of provider-enforced structured generation.
Numeric facts require JSON numbers; strings, ranges, bounds and equations are
not silently coerced into scalar parameters. The qualitative evidence channel
can retain source-supported ranges, equations and applicability statements
about parameters, model conditions or output quantities. Such evidence still
requires exact quotation and semantic review; it does not itself count as a
calculated output or a supported target assumption.
The root schema declares a child objective and assigned scenario subjects,
enumerates currently available calculation inputs, distinguishes tool-specific
required fields, and does not accept numeric scenario parameter dictionaries.

Table queries distinguish explicit row-key lists from literal text searches;
searches cover remaining rows beyond the preview. Failed extraction/review does
not mark selected table rows consumed. Unit review receives the printed value
and notation alongside the canonical value and explicit conversion factor.
Supported unit aliases do not relax physical-dimension or applicability checks.
These include common length/volume, inverse-time, dimensionless and aerosol
volume-ratio notation. Ambiguous OCR or flattened scientific exponents must
remain qualitative evidence with the ambiguity stated, not silently repaired
into scalar facts.

## Parent-Child Contracts

The existing `EpisodeGoal` and parent-owned `ReportContract` define the child
assignment. There is no model-selected `focus` field list or inherited parent
checklist. The parent supplies a specific question and necessary context in its
objective. A root investigation names its assigned scenario subjects explicitly;
source discovery may use an empty subject list. Only those assigned scenario
definitions are supplied to an assumption investigation.

Children do not copy parent findings, uncertainties, diagnostics, the root's
full scenario set or its model catalog into their reasoning prompts. The
method-loop goal retains immutable task ancestry for audit; that does not
authorize copying the ancestry into model input.

Every upward report contains only `findings`: one brief paragraph synthesizing
decision-relevant trends, changed understanding, and consequential uncertainty
or failure implications. It must not contain field checklists, evidence
inventories, tables, reading offsets, raw diagnostics or the child's transcript.
The parent receives these reports through `view.model_inputs`, with its own
previous child returns preserved for steering. A failed synthesis returns a
compact communication-failure notice, not a raw-data fallback.

Detailed admitted evidence, hypotheses, source spans and diagnostics remain in
the scientific records for numerical projection, calculation, independent
review and audit. They are not automatically expanded into a parent's next
decision prompt. Calculation tools still expose their required typed numeric
input options. Scientific-state transfer is separate from agent communication.

The root declares whether it needs source findings or recorded assumption
hypotheses and names the calculation `parameter` served by that investigation.
That scalar assignment is fixed throughout the branch. Its eligible evidence
elements come from existing executable dependencies, not generated search prose.
Child creation rejects a changed parameter. Children receive their own narrow
information contract, never an inherited root field list. Queries and approaches
remain agent choices; naming additional settings cannot expand scoring criteria.
Any proposed assumptions still undergo independent reasonableness assessment.
Root scientific credit is projected from admitted records, not child scores.

This contract correction has been inspected statically only. No tests, replay,
import/compile checks or live runs have exercised it. Historical synthetic
fixtures describing the removed focus and expanded-summary interfaces do not
verify this contract.

An unfinished assumption reassessment preserves the last completed judgment,
its credit, evidence basis and version. Its failure diagnostic identifies that
retained version and the basis that was not reassessed; this distinction survives
parent synthesis. Retention is not a new endorsement of added evidence or a
revised rationale. A failed first assessment admits no evidence or judgment, but
a validated candidate remains selectable as an explicitly `unassessed` hypothesis
with `completed: false`, an empty rubric and zero support/learning credit. Its
claim snapshot allows a later completed review to qualify existing arithmetic;
it cannot become a source observation. Independent completed
assessments in the same iteration still contribute progress, and a later completed
review can correct earlier judgments downward. No monotonic score clamp hides
actual invalidations.

Strategy proposals distinguish the literal search-engine query from their
scientific objective. The provider receives the query unchanged; it does not
execute instructions to open URLs, inspect XML, follow links or extract values.
Source selection and reading remain owned by the existing search/page branches.
The prompt and schema state this boundary without rewriting queries or imposing
a predefined sequence of searches.

Reading choices now state their execution semantics explicitly. `report` advances
from the next unprocessed document span; a section title in its question cannot
reposition that cursor. `lexical_probe` ranks source-local chunks for a targeted
query. Each reading attempt records the source version, question, exact ranges,
completion status and admitted fields. Synthesis receives aggregated examined,
reviewed and unexamined ranges so its brief return can distinguish a failed
review, unread material and a read that did not resolve the question. Those
ranges are not appended to upward reports. The page's source-local availability
view retains coverage on later visits; it does not forbid rereading for a new question.
Coverage is execution metadata, never evidence or positive scientific credit.

The local report retains `model_attempts`: each exact request, parsed response,
or rejected raw model text with its operation and parser diagnosis. A received
JSON object is not necessarily admitted evidence. This audit makes discarded
content inspectable, including a valid extraction followed by a failed review.
Malformed JSON, incomplete output, duplicate keys, nonfinite numbers, and
transport failures remain distinct. Parent diagnostics reference the call and
explain the failure; raw rejected text is not promoted into scientific state or
inserted into parent prompts. There is no silent JSON repair or hidden retry.
Reports therefore contain model prompts and outputs and should be treated as
local research artifacts when deciding what to share.

## Scientific Credit and Tools

Reasonableness has four mandatory dimensions: support, applicability, physical
consistency, and uncertainty. Positive grades require admitted evidence links.
The weakest dimension limits current conclusion support, not calculation.
The former mean-rubric `resolution_credit` has been removed: learning credit
now counts evidenced parameters and distinct relevant evidence as described
below. Unsupported candidates remain selectable as numerical hypotheses.
Merely naming a limitation or repeating an explanation is not new evidence.
A supported refutation can resolve an uncertainty, but cannot authenticate a
calculation. Explicit requester values
are conditions, not empirical discoveries. These ordinal grades are judgments,
not calibrated probabilities.

The mandatory review explicitly classifies whether a candidate instantiates a
requester-defined condition or is a scientific hypothesis. A requester-condition
binding cites admitted request evidence for the same field/value and explains
why it applies to the specific target, including broader scenario-class labels.
It can retain conditional support but earns no discovery credit. Source-model
choices cannot be relabeled requester conditions, and numerical values must
match the cited request. The target-scope interpretation remains an auditable
semantic judgment; subject-name similarity alone is not a binding rule.

The reasonableness response schema exposes the same constraints as admission:
all grades must be 2 for `supported`, positive grades need admitted evidence
references, and `provisional` needs explicit limitations. An inconsistent
verdict is rejected with the offending dimensions, never silently relabeled
or rescued by raising its grades.

Candidate schemas distinguish finite scalar hypotheses from nonnumeric model
conditions. An unknown numeric value remains an information need, not a null
scalar candidate, and candidate validity is checked before acquisition begins.
Assessment still judges reasonableness independently. Successful judgments in a
partially failed assessment batch retain their own credit; failed judgments
remain unresolved with their diagnostics and receive no positive credit.
A valid new assessment of previously admitted evidence also remains evaluated
when the latest acquisition failed. Acquisition failure remains visible; it does
not invalidate independent evidence already held by the investigation.

The fixed-scenario root's score weights parameter learning and calculated
requested outputs. Comparison is absent from its tool menu and credit columns.
The older unlocked internal composition retains comparison machinery; that is
not part of the current public workflow or its goal.
Numerical field presence, source counts, and tool invocations alone do
not earn scientific credit. Multiple target scenarios remain distinct, and a
child's explicitly scoped subjects need not cover every scenario in the root.

Scientific progress uses stable per-scenario units: for each scoped subject and
requirement, project retained parameter learning or current output progress,
then sum across subjects. Requirement-group weights stay fixed.
The parent projects this complete snapshot from its accumulated scientific state,
not from child scores or assessment-event counts. Adding an empty scenario earns
zero and does not change previous credit; repeated reviews or alternative
wordings do not accumulate additional contributions for the same requirement.
Genuine corrections can still decrease a contribution and reset the yield window.

Output progress is the greater of current evidential support and a 1/8 floor
for an actually computed requested quantity under current, noncontradicted
premises. The floor is one rubric increment, not evidence confidence, and does
not add to stronger support. Missing calculations, repeated calls, relabelled
alternatives, stale claims and unsupported inapplicability earn no new floor.
Transitive invalidations remain attached to derived inputs. An unchanged
reassessment can improve support and merge compatible tool outputs without
requiring another calculation; original versions remain in the audit.

The root's progress view and closing report distinguish recorded computations,
current computations, evidential support and coherent parameterization coverage.
Current conditional figures retain their parameterization names and support
grades. Per-assumption feedback identifies affected outputs; changed-premise
feedback explains which historical computations need reconsideration. A
provisional solution does not set the report's evidence-completeness `passed`
flag. Candidate instructions preserve unchanged physical claim statements and
put renewed rationale in `basis`, rather than rewriting a claim as an instruction
to await evidence. The root pursues a provisional solution and then evidence
improvement without a fixed tool order or a new episode type.

This progress score can exceed one. It is not a completion fraction. Parameter
learning can continue as distinct evidence arrives, so this controller has no
finite credit ceiling: rarefaction reports `max_score` and `normalized_score`
as null. The existing rolling marginal-yield rule still stops saturated work;
failed attempts still enter its history with zero gain. No per-episode cap or
cost term is added. Completion still requires the requested conclusions for
every target; stopping for low yield is not completion of the scientific goal.

Acquisition no longer asks an LLM to grade a whole question as 0, 0.5 or 1.
Mandatory projection counts admitted parameter evidence within the fixed
assignment: one point for each filled dependency, then 0.1 per distinct source
corroborating or refining that parameter for the same subject. A differing
reported value can inform the parameter without becoming a second full point
or being automatically declared a contradiction. Repeated readings and identical quoted
material at another location earn nothing. Alternative values and new outbreak
settings do not add scored elements. Source distinctness is not a claim of
statistical independence. Inherited knowledge initializes the episode's score;
it is not credited again as new gain. Indirect evidence can support an inferred
parameter through the investigation's existing reasonableness review; mere
field tags do not fill a parameter.

Current support and retained learning are separate. Reasonableness reviews
classify supporting, contradicting and invalid evidence. Supporting evidence
and genuinely new evidence overturning a previously supported claim are kept
in `learning_evidence`, with their original provenance. At the investigation
and root, reviewed refinement or correction can earn the same 0.1 increment.
Replacing a value does not earn another full point. Repeated reversals, repeated
reviews, and disproving a newly invented unsupported guess earn no increment.
Distinct alternatives remain in the record; source counts never choose the
scientific value. Current support or calculation validity can fall while the
parameter's learning credit rises. Identified extraction/attribution errors are
recorded separately in `invalidated_evidence` and retract affected learning.
The root retains its requirement-group weights and separate output projection.

V23 was terminated at the user's request, with its trace preserved. After
authorization to test and restart, `scripts/replay_parameter_credit.py` projected
the five recorded search-page returns through the new Cq dependency scoring.
The point history was 8, 10, 17, 18, 18, rather than the former constant 0.5.
Already admitted facts from the failed whole-question assessment are included:
that assessment is no longer required. Repeating admitted records earned no
gain; four unchanged observations and four repetitions of the recorded failure
each yielded. This is numerical shadow replay, not a claim about new agent
choices, scientific correctness, or contradiction classification. The script
does not call providers or seed a workflow. Its output is preserved in
`.artifacts/live/v24-credit-shadow-replay.json`.

All 92 production/script Python files parsed, the replay imported the changed
modules in standalone mode, and `git diff --check` passed. V24 was then started
from scratch through the real providers with the default scenario set, no
supplied evidence, and the prior whole-run bounds. Its code snapshot is
`.artifacts/live/v24-loaded-source-snapshot.tar.gz`. Live verification remains
pending; a started run is not evidence of completed safety estimates.

The calculation tools use local kernels. Their mandatory parent review assesses
scientific compatibility; a negative or unavailable judgment records unsupported
status without preventing execution. Deterministic execution still requires
defined numeric inputs, valid domains, consistent units and explicit scenario
identity. These are mathematical/data contracts, not evidence thresholds.
Numeric assumption keys are selectable without turning guesses into retrieved
facts. Tool records retain input records, exact assumption versions, support
gaps, model-review judgments, model identity and outputs. Derived parameters
retain transitive dependencies and remain available for subsequent tools even
when their empirical support is absent. Computed model behavior reaches child
contexts to inform further investigation; it is not relabeled empirical evidence.
Calculation records distinguish the claim (subject, field, value, unit and
statement) from its evidence-review version. A completed reassessment of an
unchanged claim updates support without requiring identical arithmetic again;
original calculation and assessment versions remain intact for audit. A changed
claim or a withdrawn judgment still removes current support. Legacy records
without a claim snapshot remain strict about assessment-version equality.

Each output has its own support dependencies, recorded during deterministic
execution, including geometry derivations and applicability exclusions. Credit,
parent coverage, comparisons and report rows use those dependencies: an
unsupported initial concentration affects transient outputs, not unrelated
steady-state quantities. Whole-input support remains available but does not
override per-output qualification. Named alternatives still require coherent
values and all requested outputs to be resolved for report completion.
Stale calculations remain visible as history but do not count as current report
coverage or expand a supported sensitivity range. Observation comparisons also
show whether their assumptions remain supported and can examine historical
predictions without claiming current support. A failed model reassessment does
not replace an earlier completed judgment with zero-credit output; both records
remain distinguishable. Unsupported outputs are shown as exploratory, not hidden.

The internal kernel catalog includes probabilities, occupancy, cumulative
exposure, clean-air requirements, and distance scales. These are not additional
default report goals. The reported families are room time, risk-based safe
distance, and R_in. Critical distance is the jet/background crossover, not the
reported safe distance.
Missing inputs and regime limitations remain explicit.
Source-off clearance requires an explicitly assessed emissions-stopped interval;
it does not require a continuously present emitter. Concentration relaxation
requires spatial mixing, not occupants. The critical aerosol-radius calculation
requires the Stokes-particle condition used in its settling law.
An exclusion can resolve applicability only when a deterministic tool records
its reason and input basis with current assumption support. It produces no
numeric estimate. Unknown inputs cannot establish an exclusion, and a stale or
bare `inapplicable` label earns neither output credit nor coverage. Reports
distinguish an entirely excluded requested model from available conditional
estimates. Live quantitative verification still requires actual calculations.

The retained legacy prediction/observation comparison preserves observed versus fitted roles and
calibration dependence. Reproducing an outbreak used to calibrate infectiousness
is labeled `calibration_consistency`. Even an out-of-calibration comparison is
not claimed to be independent validation without a held-out protocol.

## Closure and Verification

Lexical probes use locally implemented token BM25 with neighboring-context rank
fusion, adapted from the reference reader under its MIT license. Ranking covers
the full document before excluding processed spans so original adjacency is
preserved. It neither removes low-scoring chunks nor imposes a stopping threshold.

The fixed-scenario workflow rejects new or altered scenario definitions. The
older unlocked internal composition retains scope review for its fixtures; it
does not authorize the active agent to invent cases. Rejection reasons return
to the proposing parent.

The scientific report is built at root closure, not selected as an agent action.
It includes scenario coverage, assumptions and their evidence, versioned
calculations, unresolved issues and actual termination. A report
does not imply convergence merely because some quantities were calculated.

`tests/test_approved_tree.py` checks the declared tree against executed traces,
parent contracts, root tool leaves, mandatory contrary-evidence reassessment,
multiple report windows, table/probe selection, processed spans, source failures,
geometry, calibration, comparison and stale versions. Other tests cover the
remaining kernels, quotation and applicability boundaries, CLI/provider wiring,
and execution without another checkout or installed dependencies.

Historical reports from the old workflow remain historical. They are not
evidence that this tree was used before its implementation.
