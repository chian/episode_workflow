# Episodic Workflow

A self-contained controlled-agent workflow for conditional indoor airborne
transmission estimates. The active path uses the existing episode
tree: scientific investigation, iterative evidence acquisition, and deterministic
calculations selected by the scientific parent. Reports are generated at closure.

Runtime and offline tests require only this repository and Python's standard
library. There are no cross-repository imports or packages to install.

## Current Instructions and Status

Read [the current contract](docs/CURRENT_GOAL.md) and
[episode ownership](docs/RESEARCH_EPISODES.md). Explicit user instructions take
precedence. Historical implementation documents are not evidence that their
requirements were authorized.

The requested outputs are allowable room time, risk-based safe distance, and
R_in for runtime disease and scenario inputs, in steady and transient regimes.
Scenarios own numeric inputs and categorical model settings. Each explicitly
selects background plus local jet or negligible near field; episodes cannot
override that choice, and calculators have no implicit near-field default.

Values automatically enter the main table ranked by value-specific source-to-target
relevance. Calculations use that table and current computed results. Do not add
scientific-support approval reviews, gates, cutoffs, or hidden consistency checks.
A current result is reused until an actual dependency changes. Review judgments
do not change numerical freshness or authorize withdrawing completion credit.

The implementation remains unfinished. Some parameter-review and support-related
machinery still requires examination against these instructions. Documentation
changes do not establish that the remaining code is fixed. All current live runs
are stopped; no restart or push is authorized by this README.

## Setup

```bash
python3 -m venv .venv-standalone
.venv-standalone/bin/python -I -S -B . --help
```

Python 3.12 or newer is recommended.

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

Before searching, the constants assessment runs before the shared-parameter
assessment and initial credit assignment. The initial list counts independent
values to find, excluding supplied inputs, retained constants, and computed
quantities. The explicitly requested planning and relevance assessments do not
authorize other approval reviews.

The built-in reference coordinates are 1.8288 m and 900 s; custom scenarios can
override them. Fix distance to solve time, fix time to solve distance, and fix
both to evaluate R_in. Reference coordinates are not presumed-safe answers and
do not supply outbreak durations. Custom scenarios explicitly select
`continuous_unmasked_jet` or `negligible_near_field` in `conditions`.

Target numeric operands bind automatically; proposals cannot select competing
numeric records or change scenario settings. Use one defined calculation per
computed quantity. Reuse current results and mark results stale only when actual
dependencies change. The calculation table contains values, units, readiness,
dependencies, credit, and three progress statuses: not calculated, calculated
and up to date, and calculated needing updating.

Found values earn 1 point each; current intermediates earn 12.5 and requested
outputs earn 25. Stale calculations retain method credit. Existing support bonus
machinery is not authorization for an additional review, and its remaining code
has not been reconciled merely by updating these documents.

`--search-limit` bounds each query's result set. There is no model-call or
per-episode unit budget. `--yield-window` configures child credit history
(default 4), and `--root-yield-window` configures root history (default 12).
The estimator does not compare alternative actions. `--text-window-chars`
bounds a reading window. Stopping is not proof of task completion.

Reports retain actual requested outputs, source provenance, estimates and
calibration lineage. Do not add scientific-support approval as a completion
requirement. Current report acceptance code still requires examination against
that instruction. Report files and checkpoints retain actual run outcomes;
starting a run does not verify its completion.

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

## Architecture and Verification

See [episode ownership](docs/RESEARCH_EPISODES.md). `method_loop` owns episode
iteration and numerical credit projection. This does not authorize a separate
LLM scientific-support review. Calculations remain ordinary tools.

Parent returns are structured JSON from the existing work calls and deterministic
projections. No findings paragraph or extra summarization call. Active state,
credit and episode-visible progress must use the same main values and calculation
status. Preserve source records and history without treating them as alternative
target calculation inputs.

Historical checklists, studies and tests describe prior implementations; their
"approved" labels and checkmarks do not establish current user authorization or
verification. The user's prohibition on tests and calculation replays remains
in effect unless explicitly changed.

## Layout

- `method_loop/`: generic local episode runtime and reporting boundaries.
- `case_reports/research/`: active tree, scientific records, acquisition, tools, report.
- `credit_assignment/`: numerical yield and scientific credit.
- `task_executors/`: deterministic kernels and repository-owned HTTP clients.
- `configured_providers.py`: explicit provider composition.
- `case_reports/README.md`: legacy admission contracts, retained for reference.
