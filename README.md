# Episodic Workflow

A self-contained controlled-agent workflow for conditional indoor airborne
transmission estimates. The active path implements the user-approved episode
tree: scientific investigation, iterative evidence acquisition, and deterministic
calculations selected by the scientific parent. Reports are generated at closure.

Runtime and offline tests require only this repository and Python's standard
library. There are no cross-repository imports or packages to install.

## Current Status

Work in progress; the [current goal](docs/CURRENT_GOAL.md) has not been achieved.
The active interface requires a runtime disease and defaults to caller-owned
Bazant-Bush cases. Its requested scientific outputs are allowable room time,
risk-based safe distance, and R_in. There is no answer-matching objective.

The 2026-10-13 goal restores generalized runtime evidence acquisition and requires
an actual outbreak-based Cq calibration. The active root is
`evaluate_airborne_safety_guideline`; its search episodes use the repository's
`SearchPageProposer`. Target cases remain fixed while separately acquired source
observations can establish calibration contexts. The existing infectiousness
tool owns `calibrate_cq_from_outbreak`; no calculation episodes were added.
Reports now check real provider operations and calibration lineage in addition
to numerical coverage. Live verification of these edits is in progress; the
older results below do not demonstrate this contract. The user has reported
that Argo access has reset, and the new live run has received model responses.

V18 and V19 were stopped after newer edits superseded their loaded code. V19 used
explicit child focus and source-finding versus assumption-hypothesis contracts;
its streaming trace preserves the completed attempts. Neither produced a final
report or verified the three-quantity result. V20 is the fresh active query,
including observational-range provenance, intentional rereading and scoped
synthesis fixes; its end-to-end outcome remains unverified. Run-start
hashes and archived source snapshots identify what each run actually exercises.

The fixed-scenario interface has not been tested with the offline suite, at the
user's instruction. Earlier fixtures still include callers of the previous API.
A full read of the 136 repository-owned files preceded the V12 study; the two
new calculation modules have also been read in full. The current follow-up adds
numerically bound duration relationships, exposes executable derivation
prerequisites, includes those prerequisites in assumption-resolution credit, and
aligns fixed-mode schemas with the caller-owned cases. V14 exercised parameter
derivation, duration-function binding and reporting through actual calculation
calls. No arbitrary duration was substituted to make an output appear complete;
the separate duration-evaluation helper was not replayed or tested.

The historical default-scenario run V16 finished with exit code 1 and
`status: partial_estimates_available`: 36 of 40 requested case/quantity entries
were calculated. All eight cases have steady and clean-start time bounds and
both R_in(t) relationships; the four unmasked cases also have distance(t)
relationships. **Masked distances remain uncomputed, and every calculated
output still has zero evidence-support credit.** These are provisional
consequences, not established safety estimates or completion of the goal.
Hypothesis formation and source navigation improved, but subsequent investigation
repeatedly pursued the masked-model gap without strengthening the already
calculated results. The root reached its 64-unit operational limit at 500 model
calls; its numerical controller still indicated continuation.

The audit records 25 provider biological-content refusals and 76 responses
misclassified as malformed JSON. Those 76 were identical Argo notices saying
access was revoked because the monthly usage limit was exceeded; they contained
no scientific content. A post-run fix recognizes this explicit provider limit
and prevents further model requests while preserving completed work. It has
been reviewed by reading only, not tested or exercised by another live query.
Restoring Argo access requires resolving that provider quota, not local sandbox
or filesystem permissions. The provider notice directs the user to their
Directorate Operations Officer.
The retained report, recursive audit, progress log and runtime archive are under
`.artifacts/live/default-scenario-v16*`.
See the [V16 study](docs/RESPONSE_FAILURE_STUDY.md#v16-hypothesis-roles-and-reading-coverage).
No tests or calculation replays were run for this change.

Post-V16 changes remove agent-assigned child call quotas, expose the calculator's
enforced applicability constraints to proposals and synthesis, and treat
numerical coverage and evidence strengthening as concurrent needs. Tool choices
retain their required scientific rationale without requiring a duplicate child
objective. The ownership tree, equations and credit weights are unchanged.
These changes have only been reviewed by reading; live behavior remains
unverified and masked-distance capability is still incomplete. See the
[post-V16 study](docs/RESPONSE_FAILURE_STUDY.md#post-v16-episode-control-and-capability-contracts).

The next [distance-regime extension](docs/RESPONSE_FAILURE_STUDY.md#explicit-distance-regimes)
adds an explicit negligible-near-field approximation alongside the unchanged
unmasked jet. It is never selected automatically by mask penetration: the
investigation must propose and assess its applicability. The result distinguishes
no positive minimum in a spatially uniform model from no finite separation
meeting the room-risk criterion. It is not a general masked-plume calculation
or a claim that contact is safe. Kernel exclusions also no longer count as
resolved numerical outputs. This extension is untested and has not been used in
a live query; it does not change V16's missing outputs or complete the goal.

### Earlier Verification

The calculation-contract follow-up defines the default
case fixes 6 ft when solving time, fixes 15 min when solving distance, and fixes
both when evaluating R_in. Three deterministic operations share one conditional
risk model, with steady and transient versions. They are choices under the
existing root tools, not new episodes. Reports retain the actual fixed inputs
and model identity; credit requires the requested operation, not a legacy
background-only output or an unevaluated duration formula. This does not change
the historical V16 figures. No tests have exercised it, and the active queries
have not yet established its complete end-to-end behavior.

The previous validation snapshot recorded 285 passing offline tests and one
opt-in live test skipped; this is not a result for the current changes. V10 used
the unchanged original request and calculated all 23 requested quantities by
call 83. It stopped on numerical saturation at call 473, but assumptions remained
weakly supported and results were split across six parameterization names.
The trace revealed repeated opening-window reading while relevant material was
already retrieved later in the documents. Provenance and calculation replay
checks passed; this is not independent scientific validation. V7 remains
suspended with the older implementation.

Remaining work includes live verification of assumption formation, parent
steering and supported quantitative report generation. Failed reassessments now
retain completed judgments and credit, with unreviewed material identified for
the parent. Search prompts also distinguish literal search queries from browsing
plans. Calculations can now select recorded guesses with no supporting evidence;
support affects credit and report qualification, not permission to compute.
The deeper V8 study found relevant extracted information lost before mandatory
review, not simply an inability to find it. Interrupted review now preserves
that discovery for parent decisions without admitting it as evidence.
V9 exposed further interface and credit defects. Tool schemas now scope output
names to the selected calculator. Reassessing an unchanged claim no longer
invalidates its calculation, and each output's support follows its actual
dependencies. Scientific credit now accumulates per-scenario
reviewed progress instead of averaging over a growing scope; new empty scenarios
neither earn credit nor dilute earlier progress. After the V10 study, versioned
reading coverage now passes upward and survives source revisits. Progress and
closure separate current computations, historical figures, coherent alternatives
and evidence support. A first current numerical consequence earns a small
progress floor without becoming evidence; repetition earns nothing. A failed
first assumption review retains a valid unassessed hypothesis for calculation.
Those earlier changes passed offline tests; their live behavioral effect and a
complete evidence-supported quantitative report remain unverified.
See [implementation status](docs/IMPLEMENTATION_CHECKLIST.md)
and [trace studies](docs/RESPONSE_FAILURE_STUDY.md). Do not treat this snapshot as
a validated safety-assessment system.

## Setup

```bash
python3 -m venv .venv-standalone
.venv-standalone/bin/python -I -S -B scripts/check.py
.venv-standalone/bin/python -I -S -B . --help
```

The checks include execution in an isolated copy without site-packages. Python
3.12 or newer is recommended.

## Providers

The configured composition uses repository-owned HTTP clients for Firecrawl
Search/Scrape. Model calls can use the current Codex CLI ChatGPT login or the
local Argo shim. Configure this checkout's
ignored `.env` using [.env.example](.env.example):

| Variable | Purpose |
| --- | --- |
| `FIRECRAWL_API_KEY` | Search/retrieval credential |
| `TYPESAFE_API_KEY` | Jev credential for search-result relevance assessment |
| `EPISODIC_LLM_PROVIDER` | `codex_oauth` for the Codex CLI login, or `argo` for the legacy local shim |
| `EPISODIC_LLM_MODEL` | REASONING-tier model identifier |
| `EPISODIC_LLM_FAST_MODEL` | FAST-tier model identifier; defaults to the reasoning model when omitted |
| `EPISODIC_LLM_REASONING_EFFORT` | Codex reasoning effort for REASONING calls (default `medium`) |
| `EPISODIC_LLM_FAST_REASONING_EFFORT` | Codex reasoning effort for FAST calls (default `none`) |
| Codex authentication | Reads the current access token from `CODEX_HOME/auth.json` or `~/.codex/auth.json`; Codex owns refresh |
| `EPISODIC_LLM_BASE_URL` | Required only for the optional local Argo shim |
| `EPISODIC_LLM_USER` | Optional Argo user field |
| Argo authentication | Always `api_key="no-auth"`; no Argo bearer credential is read |

Jev scores Firecrawl candidates before the search episode selects a page.
The research agent declares FAST and REASONING call sites in
[model_tiers.py](case_reports/research/model_tiers.py). The FAST tier handles
search-page choice, page-child choice, and table-page extraction, matching the
nano-graphrag bindings. Source-table planning, report/lexical extraction,
scientific decisions, reviews, and new research operations use REASONING.
Each model attempt records the selected tier, model, and Codex reasoning effort.
Shell values override `.env`; an explicit Python
`env` mapping is isolated from both. No other repository's settings are read.

For the Argo option, set `EPISODIC_LLM_PROVIDER=argo`,
`EPISODIC_LLM_BASE_URL=http://127.0.0.1:12329/v1`, and the shim's model name
(for example `gpt55`). Run the local shim with `--no-auth` as before. For the
Codex option, set `EPISODIC_LLM_PROVIDER=codex_oauth` and a Codex model name;
the workflow reads the Codex CLI access token but does not rotate its refresh
token. This checkout currently selects the Codex option.

## Run

```bash
.venv-standalone/bin/python -I -S -B . "$DISEASE_OF_INTEREST" \
  --progress --report-path report.json --audit-path episode-record.json \
  --trace-path workflow-trace.jsonl
```

Supply the disease of interest as the positional argument; there is no built-in
disease. `--scenario` defaults to the fixed Bazant-Bush case catalog and also
accepts `classroom`, `nursing-home`, an individual case name, or a caller-defined
scenario JSON file. Fixed case conditions are inputs, not discoveries. The
workflow investigates the remaining assumptions and their evidence. Optional
`--request-file` supplies additional instructions, not researched answers or
seeded evidence.

Before any research action, the initial parameter list is built from the
executable dependencies of the requested outputs plus explicit scenario needs.
It includes alternative ways to obtain calculation inputs, not a requirement
to fill every alternative before calculating. Caller-fixed inputs and values
derivable entirely from those inputs are excluded from evidence acquisition.
A reasoning call then extracts the differing contextual
features in the selected scenario descriptions and identifies which declared
features and fixed inputs can change each needed parameter's own value. The
system groups cases with the same values for those relevant features. These
groups define the independent values in the progress denominator and credit
assignment. The assessment records its factors and rationale; no case name or
scenario-specific transfer rule is embedded in the code. A value proposed for
any group member can appear as a calculation option in the other members
without adding duplicate assumptions. Changes to a scenario or the value's
review invalidate the applicable link. The sharing judge must cover every
supplied parameter; it groups values but cannot remove required inputs from
credit eligibility. Parameter credit uses the same rule for each group: one
point for admitted evidence-linked learning, plus 0.1 for each distinct
additional supporting source. Fixed scenario givens earn no evidence credit.
Root credit is projected from the shared ledger even when a child has not
returned to it.

The built-in cases use the selected six-foot separation
(`neighbor_distance_m = 1.8288`) and fifteen-minute duration
(`exposure_time_s = 900`) from the paper's reference rules. The calculation
contract is: fix distance to solve allowable time, fix time to solve safe
distance, and fix both to evaluate R_in. All three operations share the same
conditional risk model within each background regime. Neither reference input
is a computed safety answer or something to rediscover. Caller-defined scenario
files can supply other values in their `fixed` inputs. Omitted target reference
coordinates use these same declared defaults. They are never used to fill a
missing outbreak exposure duration. Free duration/distance variables are not
accepted by the scalar three-quantity report contract.

The report requires time, risk-based distance, and R_in, with steady and
initially clean-room regimes distinguished. Partial output sets are rejected;
individual tool calls may still calculate these operations separately.
`--format markdown` emits the scientific report.
The retired `--transmission-model` switch is rejected, not routed to an older
pipeline. Recorded numerical hypotheses can be calculated before justification.
Their inputs and support gaps remain explicit; calculation alone supplies no
empirical support or supported-output credit.

`--search-limit` bounds the result set for each query. There is no model-call,
whole-run unit, or per-episode unit budget. `--yield-window` configures numerical
marginal-yield stopping.
`--text-window-chars` bounds individual reading executions, not document length.

Exit codes: `0` when every required quantity has a coherent supported conditional
result meeting its output contract and the real acquisition and outbreak-calibration
provenance checks pass, `1` for incomplete coverage or acceptance,
`2` for configuration errors. An exclusion contains no numerical answer and does
not complete a requested output. A successful report is neither a guarantee
of safety nor independent empirical validation.
Unbounded quantities use `value: null, limit: "unbounded"`, preserving strict JSON.
Explicitly selected legacy duration-relationship metrics use `value: null, limit: "function"` with
computed coefficients, bound input values, a named executable kernel and the
time domain. These are R_in(t) or risk-threshold-distance relationships, not
answers at an assumed event length. Scalar durations explicitly fixed by a
custom scenario retain scalar outputs. The default six output contracts require
evaluated answers: three quantities in each of two background regimes. An
explicit negligible-near-field hypothesis removes the local contribution from
all three operations; otherwise the unmasked-jet model applies. A transient
background plus a local jet requires the additional `quasi_steady_local_plume`
approximation. Its applicability is investigated, not silently assumed.
Report files are not overwritten. Each CLI run creates a durable checkpoint and
stores its trace, audit and report there unless explicit output paths are given.
The trace is written incrementally as JSON Lines. It retains
actual model requests, responses, provider outcomes and credit verdicts, not
just operation names. Like the final report and audit, it can contain retrieved
source content and should be treated as a local research artifact.

### Checkpoint And Resume

Every new CLI run prints its checkpoint directory. Choose a stable location with
`--checkpoint-path .artifacts/checkpoints/my-run`. Continue the exact saved run:

```bash
python3 . --resume .artifacts/checkpoints/my-run --progress
```

The disease, scenario, request and control settings are restored from the saved
registration. Explicitly changing them is rejected. Resume requires the same
code, Python runtime and non-secret provider configuration; credentials are
loaded afresh and are not stored. Completed provider responses and failures are
replayed locally in their original nested execution order. This rebuilds
evidence, assumptions, calculations, selected actions, reading positions,
contracts and controller histories before new work is authorized. It does not
restart research or merely restore the root score. Only an interrupted request
without a committed response may be retried; these providers perform
observational search, retrieval or model inference, not remote writes.

The implementation follows OpenChia's ordered reconstruction mechanism, copied
and adapted locally: Episode start/unit/completion frames, a read-only
`ReconstructionCursor`, stable logical identity, physical-attempt lineage and a
separate host `run_reconstructed` admission. There are no cross-repository
imports. See [checkpoint guarantees and boundaries](docs/CHECKPOINTS.md).

## Architecture

See [the complete tree and contracts](docs/RESEARCH_EPISODES.md). Every declared
episode runs through `method_loop`, in one runtime context. Assumption assessment
is mandatory investigation credit machinery, not a selectable action. The five
calculation tool implementations are root leaves, not one-shot episode wrappers.
Four are available in the fixed-scenario workflow; the legacy comparison tool is
not offered and does not contribute credit. A parent can investigate changed
assumptions and select a calculation again.

Calculations retain their input and assumption versions. Reports retain source
text, admitted quotations, reasonableness assessments, conditional quantities,
unresolved needs, and the actual termination reason. The recursive
audit additionally records episode requests, parent contracts, and numerical
verdicts. Reading memory alone never earns evidence credit.

The older fixed-task implementation is retained as a legacy regression surface;
it is not the CLI or active research API.

## Verification

Offline tests cover scientific kernels, evidence admission, numerical control,
the declared and executed tree, parent contracts, reading modes, mandatory
assessment, provenance, provider failures, and standalone execution. Synthetic
fixtures are not live scientific validation.

The existing integration-test caller predates the required disease argument and
needs updating before reuse. The current live verification uses the CLI above,
not a test runner. A bounded exploratory CLI trace is not evidence of a passing
end-to-end test. See [implementation evidence](docs/IMPLEMENTATION_CHECKLIST.md)
and [historical verification](docs/WORKFLOW_VERIFICATION.md).

## Layout

- `method_loop/`: generic local episode runtime and reporting boundaries.
- `case_reports/research/`: active tree, scientific records, acquisition, tools, report.
- `credit_assignment/`: numerical yield and scientific credit.
- `task_executors/`: deterministic kernels and repository-owned HTTP clients.
- `configured_providers.py`: explicit provider composition.
- `case_reports/README.md`: legacy admission contracts, retained for reference.
