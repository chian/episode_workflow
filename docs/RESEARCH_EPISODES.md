# Approved Scientific Episode Tree

The active prompt-only API is `run_guideline_research`, also reached through
`run_configured_safety_guideline_request` and the CLI. The executable type tree
is declared once in `case_reports/research/engine.py`. All instances execute in
one `method_loop.Context`; bindings do not start private nested contexts.

This is ownership, not a predetermined call sequence. `[E]` is an iterative
episode; `[T]` is a selectable deterministic tool.

```text
[E] evaluate_safety_guideline
    +-- [T] calculate_geometry_and_removal
    +-- [T] calibrate_infectiousness
    +-- [T] calculate_transmission_metrics
    +-- [T] calculate_conditional_limits
    +-- [T] compare_predictions_with_observations
    +-- [E] investigate
            +-- [E] strategy
                    +-- [E] search
                            +-- [E] page
                                    +-- [E] source_table
                                    +-- [E] report
                                    +-- [E] lexical_probe
```

## Mandatory Method Wiring

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
evaluated zero-evidence observations. The rolling marginal-yield rule is an
operational saturation heuristic, not a confidence interval.

Parents can specify an optional positive `child_model_calls` allowance in a
child proposal. It caps calls across that child's entire subtree; descendants
cannot enlarge an enclosing allowance. Omission inherits the remaining parent
allowance. Proposals receive current usage and remaining resources so allocation
can account for mandatory assessment and later decisions. Return synthesis is
commissioned by the invoking parent and charged to that parent's allowance,
as is its assessment. These ceilings never imply scientific convergence or earn
credit. They do not prescribe an action order or replace yield-history stopping.
Context also identifies the known per-operation call costs: proposals, scenario
reviews, extraction plus candidate review, return synthesis, reasonableness
review, and model admission. These are accounting facts, not guarantees of useful
evidence or instructions to choose a particular allowance.

## Scope Ownership

| Episode | Owns | Iterates Over |
| --- | --- | --- |
| evaluate_safety_guideline | Requested scientific conclusions, scenario definitions, assumptions, versioned calculations and discrepancies | Selected tools or investigations |
| investigate | One parent-contracted uncertainty, candidate assumptions/explanations, alternatives and reasonableness | Evidence-acquisition strategies |
| strategy | One evidence approach and feedback about its queries | Newly proposed searches |
| search | One query, its returned source candidates and earlier source outcomes | Selected source episodes |
| page | One retrieved source and its remaining readable material | Available table, report or lexical reading episodes |
| source_table | One physically detected table and prior query results | Parsed-table query executions |
| report | Sustained reading and cross-window subject context | Successive document-order windows |
| lexical_probe | One literal source-local query and ranked remaining spans | Unprocessed chunks |

The collective assumption-justification capability belongs to the investigation
branch. Reading episodes extract evidence; they do not manufacture assumptions.
Provider-level instructions distinguish calculation execution, which selects
admitted inputs, from hypothesis proposal, which may reason about unprinted
values. The latter still needs independent evidence-linked assessment before
becoming an input. The root performs scientific work using the declared kernels;
an implementation plan or parameter glossary does not complete its goal.
Before choosing another action, the root also receives `scientific_progress`:
current coverage for every requested quantity, assessed numerical versus model
condition fields, and whether a coherent parameterization has been evaluated.
It uses the same version-aware projection as report closure. It does not execute
calculations, select a next action, change credit, or admit evidence. A catalog
of source equations cannot appear in this view as numerical output coverage.
`investigate` proposes hypotheses as part of choosing its next strategy. Every
returned strategy passes through mandatory reasonableness assessment before
scientific credit. Newly relevant contrary evidence triggers reassessment of
existing candidates. Assessment is never an optional tool or sibling episode.

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
chunks without a relevance cutoff that silently drops the tail. Successful
reading marks spans processed for later probes within that page scope.

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
The root schema enumerates valid focus keys and currently available fact choices,
distinguishes tool-specific required fields, and does not accept numeric scenario
parameter dictionaries. Invalid focus feedback identifies the offending entries
instead of only saying that the contract failed.

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

Before opening a child, its parent supplies a `ReportContract` naming its next
decision, needed fields, and required synthesis fields. Requests also preserve
the original root task and the actual proposal that opened the child.

The contract includes the parent's selected scenario subjects and is passed to
the model during proposals, extraction, and assessment, not only saved in the
episode audit. Source/calibration subjects may supply evidence but do not
replace those requested targets. An investigation may give a strategy its own
evidence focus, including an intermediate quantity needed to resolve the
parent's uncertainty. That choice scopes local evidence credit; it does not
change the investigation's scientific goal or the episode ownership tree.

The returned synthesis distinguishes findings, changed evidence/assessments,
unresolved needs, failure explanations, and completion reason. Language-model
compression cannot admit new facts or assign credit. If synthesis fails, the
admitted findings and explicit synthesis failure remain available. Parents
recompute credit on their own scope; they never add up child scores.
Assumption summaries preserve the judgment, limitations and evidence actually
cited in its criteria, not an apparent citation to every available record. The
full considered evidence remains in the audit and available for reassessment;
this communication projection does not alter admission, credit or provenance.

Failure records receive a stable per-run identity before projection. Model-facing
diagnostics group repeated reasons while retaining failure type, source/field,
received field names, compact candidate values, and retained-record counts.
The full rejected proposals stay in the audit, not in every subsequent prompt.
Synthesis starts from newly obtained findings rather than replaying findings
already held by the parent.

Child summaries carry an evidence change index (subject, fields, source, evidence
role and record count), not repeated evidence bodies. Acquisition proposals use
an inventory of available evidence; scientific proposals retain detailed claim
and value summaries. Quotes and source versions remain in the full scientific
state and in independent evidence/assumption reviews. Counts are not credit.
Child synthesis reports only new issues and diagnostics relative to the invoking
parent, preserving stable diagnostic identities. Genuinely new failures remain
distinct. A failed synthesis is also retained in scientific-state diagnostics
for communication to ancestors; it cannot alter previously admitted evidence
or the already-assigned scientific credit.
Mandatory-assessment failures identify the candidate subject, field and value,
not just the enclosing strategy proposal. This preserves which uncertainty was
not evaluated without admitting the failed candidate or prescribing another action.

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
The weakest dimension limits support. A supported refutation can resolve an
uncertainty, but cannot authenticate a calculation. Explicit requester values
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

The root's score separately weights assumption resolution, supported requested
outputs, and evidence-consistency checks. Establishing a discrepancy earns
learning credit too: lower fitting error is not itself the objective. A comparison
to the same observations used in calibration earns no evidence-consistency credit.
Numerical field presence, source counts, and tool invocations alone do
not earn scientific credit. Multiple target scenarios remain distinct, and a
child's explicitly scoped subjects need not cover every scenario in the root.

The calculation tools use local kernels. Their mandatory parent admission checks
scientific compatibility; deterministic execution checks current support and
physical domains. Tool records retain input facts, exact assumption versions,
model identity and outputs. Derived parameters retain transitive dependencies.
Changing or withdrawing support does not delete an old prediction: it makes
that prediction stale until recalculated under the new version.
Stale calculations remain visible as history but do not count as current report
coverage or expand a supported sensitivity range. Observation comparisons also
show whether their assumption versions remain current.

Supported outputs include steady/transient risk and probabilities, duration,
occupancy, cumulative exposure, clean-air requirements, and applicable distance
scales. Critical distance is the jet/background crossover, not a safe distance.
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

Prediction/observation comparison preserves observed versus fitted roles and
calibration dependence. Reproducing an outbreak used to calibrate infectiousness
is labeled `calibration_consistency`. Even an out-of-calibration comparison is
not claimed to be independent validation without a held-out protocol.

## Closure and Verification

Lexical probes use locally implemented token BM25 with neighboring-context rank
fusion, adapted from the reference reader under its MIT license. Ranking covers
the full document before excluding processed spans so original adjacency is
preserved. It neither removes low-scoring chunks nor imposes a stopping threshold.

Scenario scope review distinguishes cases or conditional experiments from model
extensions and investigation topics. Open requests may be instantiated by named
conditional study cases without treating them as user givens or universal results.
Rejection reasons are returned to the proposing parent.

The scientific report is built at root closure, not selected as an agent action.
It includes scenario coverage, assumptions and their evidence, versioned
calculations, comparisons, unresolved issues and actual termination. A report
does not imply convergence merely because some quantities were calculated.

`tests/test_approved_tree.py` checks the declared tree against executed traces,
parent contracts, root tool leaves, mandatory contrary-evidence reassessment,
multiple report windows, table/probe selection, processed spans, source failures,
geometry, calibration, comparison and stale versions. Other tests cover the
remaining kernels, quotation and applicability boundaries, CLI/provider wiring,
and execution without another checkout or installed dependencies.

Historical reports from the old workflow remain historical. They are not
evidence that this tree was used before its implementation.
