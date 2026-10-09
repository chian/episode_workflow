# Episodic Workflow

A self-contained controlled-agent workflow for conditional indoor airborne
transmission estimates. The active path implements the user-approved episode
tree: scientific investigation, iterative evidence acquisition, and deterministic
calculations selected by the scientific parent. Reports are generated at closure.

Runtime and offline tests require only this repository and Python's standard
library. There are no cross-repository imports or packages to install.

## Current Status

Work in progress, published at the user's request before goal completion. The
offline suite has 203 passing tests and one opt-in live test skipped. A complete,
unseeded live quantitative report has not yet been verified. The latest live run
was suspended at the user's pause request; no successful result is claimed.

Remaining issues include undersized child call allowances, withdrawal of prior
assumption support when a reassessment fails operationally, and incomplete
calculation-tool contracts. See [implementation status](docs/IMPLEMENTATION_CHECKLIST.md)
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

The active composition uses repository-owned HTTP clients for Firecrawl
Search/Scrape and Argo-compatible chat completions. Configure this checkout's
ignored `.env` using [.env.example](.env.example):

| Variable | Purpose |
| --- | --- |
| `FIRECRAWL_API_KEY` | Search/retrieval credential |
| `EPISODIC_LLM_BASE_URL` | Chat-completions base URL |
| `EPISODIC_LLM_MODEL` | Model identifier |
| `EPISODIC_LLM_API_KEY` | Optional LLM bearer credential |
| `EPISODIC_LLM_USER` | Optional Argo user field |

TypeSafe is not required by this composition. Its local adapter remains for
legacy regression coverage. Shell values override `.env`; an explicit Python
`env` mapping is isolated from both. No other repository's settings are read.

## Run

```bash
.venv-standalone/bin/python -I -S -B . --request-file research-request.txt \
  --progress --report-path report.json --audit-path episode-record.json
```

Supply the original natural-language request, not externally researched answers
in either JSON or prose. Scenario definitions, searched evidence, and justified
assumptions are developed inside the workflow. Explicit requester constraints
are quoted and reviewed, not treated as empirical evidence. Structured scenario
and seeded-source CLI inputs are disabled.

Use `--metric NAME` repeatedly to select output quantities; without it the core
report catalog is requested. `--format markdown` emits the scientific report.
The retired `--transmission-model` switch is rejected, not routed to an older
pipeline. All quantitative inputs require current evidence-linked support.

`--max-model-calls`, `--max-total-units`, `--max-units-per-episode`, and
`--search-limit` bound operational work. `--yield-window` configures numerical
marginal-yield stopping. Hitting an operational bound is not convergence.
`--text-window-chars` bounds individual reading executions, not document length.

Exit codes: `0` when each requested quantity is covered by a supported conditional
estimate or an explicitly justified model exclusion, `1` for incomplete coverage,
`2` for configuration errors. An exclusion contains no numerical answer. When
all requested outputs are excluded, the status is `requested_model_inapplicable`,
not `conditional_estimates_available`. A successful report is neither a guarantee
of safety nor independent empirical validation.
Unbounded quantities use `value: null, limit: "unbounded"`, preserving strict JSON.
Report files are not overwritten.

## Architecture

See [the complete tree and contracts](docs/RESEARCH_EPISODES.md). Every declared
episode runs through `method_loop`, in one runtime context. Assumption assessment
is mandatory investigation credit machinery, not a selectable action. The five
calculation tools are root leaves, not one-shot episode wrappers. A parent can
investigate changed assumptions, compare outcomes, and select a calculation again.

Calculations retain their input and assumption versions. Reports retain source
text, admitted quotations, reasonableness assessments, conditional quantities,
comparisons, unresolved needs, and the actual termination reason. The recursive
audit additionally records episode requests, parent contracts, and numerical
verdicts. Reading memory alone never earns evidence credit.

The older fixed-task implementation is retained as a legacy regression surface;
it is not the CLI, prompt-only API, or live integration-test path.

## Verification

Offline tests cover scientific kernels, evidence admission, numerical control,
the declared and executed tree, parent contracts, reading modes, mandatory
assessment, provenance, provider failures, and standalone execution. Synthetic
fixtures are not live scientific validation.

For the full live integration test, set `EPISODIC_TEST_RESEARCH_REQUEST` to the
original request and explicitly enable real provider calls:

```bash
.venv-standalone/bin/python -I -S -B scripts/check.py --live
```

Set `EPISODIC_TEST_REPORT_PATH` to a new file to preserve the result, including a
failed report. A bounded exploratory CLI trace is distinct from this passing
end-to-end test. See [implementation evidence](docs/IMPLEMENTATION_CHECKLIST.md)
and [historical verification](docs/WORKFLOW_VERIFICATION.md).

## Layout

- `method_loop/`: generic local episode runtime and reporting boundaries.
- `case_reports/research/`: active tree, scientific records, acquisition, tools, report.
- `credit_assignment/`: numerical yield and scientific credit.
- `task_executors/`: deterministic kernels and repository-owned HTTP clients.
- `configured_providers.py`: explicit provider composition.
- `case_reports/README.md`: legacy admission contracts, retained for reference.
