# Current Goal

Revised on 2026-10-13 at the user's request. This replaces the repository's
paper-scenarios-only goal with the generalized goal below while preserving the
agreed default scenarios, three-output contract, and episodic architecture.
It specifies required behavior, not a claim that acceptance has been achieved.

## Objective

Build one generalized, executable episodic workflow for airborne-disease safety
estimation, with one root named `evaluate_airborne_safety_guideline`.

The workflow starts from runtime inputs including `disease_name`, a target
scenario or scenario set, and optional setting hints. It acquires evidence itself
through the repo-local, copied nano-graphrag search/retrieve episode path, using
real Firecrawl search/retrieval and real LLM extraction through a configured
provider. The current live run uses the Codex CLI ChatGPT login; the local
Argo shim remains an option. It extracts structured quantities from retrieved text, validates exact
source spans and source references, calibrates infectiousness/Cq from searched
outbreak evidence, and evaluates the requested safety quantities with deterministic
Bazant-Bush calculation tools. Child credit and condensed findings inform their
parents' continued decisions.

Return only these three scientific quantities, with their conditions, evidence,
uncertainty, and any structured failures:

1. Allowable time in the room: fix separation and solve duration under the stated
   risk criterion.
2. Risk-based safe distance: fix duration and solve minimum separation under that
   same criterion. Do not substitute a jet/background concentration crossover.
3. Indoor reproductive number, `R_in`: fix both duration and separation and
   evaluate the model.

The workflow must be general across runtime disease and scenario inputs. Do not
hard-code a disease, required paper, named outbreak, case fixture, benchmark, or
pre-entered empirical evidence source. There is no comparison, answer-matching,
or published-number target metric.

## Scenario And Calculation Contract

- Keep `--scenario` flexible. Retain the existing eight Bazant-Bush scenario
  definitions as the default selectable input set, not as the only cases the
  workflow can evaluate. The default scenario definitions are coded once and
  reused; the workflow does not rediscover or invent its target scenarios.
- Fixed room, occupancy, activity, ventilation, mask, population, and risk
  conditions belong to the selected scenario. Setting hints may guide evidence
  acquisition, but do not authorize silently changing those conditions or
  inventing replacement reference rooms.
- Default reference inputs remain six feet (`neighbor_distance_m = 1.8288`) and
  fifteen minutes (`exposure_time_s = 900`), from the agreed Bazant-Bush reference
  choices. `solve_time` fixes separation; `solve_distance` fixes duration;
  `evaluate_R_in` fixes both. These are evaluation inputs, not presumed safe
  answers, event durations to invent, or empirical findings to rediscover.
  Caller-selected scenarios can override them; omitted target reference inputs
  use the declared defaults, not agent-selected values. These defaults must never
  supply an outbreak's exposure duration.
- Use the same risk model and parameterization for all three operations within
  each background regime. Distinguish steady and initially clean-room results.
  Retain the fixed inputs, solved variable, model identity, risk criterion, and
  assumptions with each result. A formula without the requested evaluation is
  not a completed scalar output.
- A background-only calculation cannot substitute for a requested calculation
  under a distance-dependent model. A negligible-near-field approximation must
  be explicit and applied consistently to all three operations, not inferred
  automatically from mask use. Record other model extensions and applicability
  limitations explicitly.
- Report a genuinely unbounded time, no finite separation, or no positive
  distance bound distinctly from a missing calculation. Such outcomes are
  conditional on the chosen model and criterion; they are not unconditional
  safety claims. Do not replace a missing distance calculation with a different
  metric or a time result.
- Generality does not require silently applying an unsuitable model. Surface
  missing physical assumptions and applicability limits, investigate them, and
  report an explicit limitation where the requested calculation is not defined.

## Runtime Evidence And Provenance

- Search is an explicit child episode path wherever outbreak or assumption
  evidence is needed. Use the copied nano-graphrag episode bindings, especially
  the `SearchPageProposer` path, not a private search bypass.
- Firecrawl calls use the repo-local copy of nano-graphrag's tested Firecrawl
  client. LLM extraction can use the repo-local Argo shim with
  `api_key="no-auth"`, or the repository-owned Codex Responses client with the
  current Codex CLI ChatGPT access token. Codex owns token refresh.
  Search-page selection passes Firecrawl candidates through the repository-owned
  Jev relevance assessor before the model selects a page. No OpenAI-keyed workflow path, cross-repo imports, or runtime dependencies on
  another checkout. Required code must live here or in the Python standard
  library.
- Research model calls declare FAST or REASONING tiers. Configure their model
  identifiers per run; FAST uses no reasoning for Codex, while REASONING uses a
  configured reasoning effort. Search-page and page-child selection and table-page
  extraction match nano-graphrag's FAST call sites. Other scientific calls use
  REASONING. Record the selected tier and model with each model attempt.
- No fake providers or transports, synthetic evidence, hand-entered
  `EvidenceSource` records, `PaperCaseReport` objects, benchmark outbreak records,
  seeded source bodies, pre-extracted findings, or caller-supplied source records
  into a parent. Default scenario definitions are inputs, not an evidence fixture
  and not a required research source.
- Admit empirical quantities only through the workflow's own runtime retrieval
  and LLM extraction path. Validate the extracted units, exact quoted spans, and
  references against the retrieved source. Do not use regex or hand-written text
  extraction to obtain scientific facts; use structured JSON parsing and LLM
  extraction, with deterministic exact-span validation.
- Distinguish four kinds of numeric provenance: caller-owned scenario inputs and
  declared mathematical/unit constants; span-checked empirical findings;
  deterministic values derived from identified inputs; and explicitly proposed
  provisional assumptions. Never relabel one kind as another. Scenario inputs
  and constants receive no evidence-discovery credit.
- Derived assumptions may use indirect evidence and explicit transformations.
  A candidate guess may be calculated before it has supporting evidence, but
  must retain its proposal origin, rationale, uncertainty, and unsupported status.
  Seek direct or indirect numerical or qualitative evidence for its reasonableness.
  Do not invent a source span for an inferred or guessed value.
- Weak or missing assumption support must not gate otherwise defined provisional
  calculations. Evidence affects confidence and credit. Stronger support can
  improve an unchanged assumption; contradictory evidence can invalidate it.
- A successful live run must actually calibrate Cq from outbreak quantities
  admitted through runtime search, retrieval, extraction, and span validation.
  Retain the outbreak setting, calibration assumptions, and transfer assumptions
  linking that calibration to the target scenario. A guessed Cq may support an
  explicitly provisional calculation, but does not satisfy this acceptance step.

## Episodes, Communication, And Credit

- Preserve the approved `method_loop` ownership structure. Each episode is a
  controlled agent loop with a goal, mandatory credit assessment, and numerical
  continuation/stopping based on credit-yield history. Do not turn the tree into
  a fixed sequence of stages or wrap each deterministic function in an episode.
- Project admitted evidence, assessed hypotheses, and calculation results into
  one shared scientific Goal state. Expose its target-route input coverage,
  outbreak-calibration readiness, and completed outputs to the episode levels;
  score new global progress above each episode's inherited baseline, including
  the root. Track both executable route alternatives so progress on a jet input
  is visible even when the uniform route currently has fewer missing inputs.
  Score and report assessed target assumptions fulfilled out of the scenarios'
  declared assumption needs, excluding fixed caller givens. Keep
  source-local evidence credit and assumption review distinct from this
  readiness projection. A route with available inputs is not thereby supported.
- When a reading page, search, or evidence strategy obtains new scored parameter
  evidence, return it to the next scientific owner for assessment. That owner
  can request more evidence if the new source does not support its hypothesis.
- Keep `calibrate_cq_from_outbreak` nested under the infectiousness path, not as
  the root. Deterministic calibration and guideline calculations remain tools
  available to their owning episodes.
- The existing parent tools expose `solve_time`, `solve_distance`, and
  `evaluate_R_in`. The parent can choose calculation tools or investigation
  children and revisit assumptions and calculations as its information improves.
  An investigation that owns recorded hypotheses may also call those reviewed
  deterministic tools and return their results with its evidence. Source-reading
  children only acquire evidence; they do not invent target hypotheses or run
  calculations.
  At each root decision, favor a newly executable provisional calculation over
  another investigation; use its consequences to target the next uncertainty.
  When a specific physical input is missing, request a focused hypothesis
  proposal rather than a broad source survey before trying the calculation.
  Assumption reasonableness assessment remains mandatory credit assignment, not
  an optional tool. Search and document examination remain iterative episodes.
- Parents specify the information contract needed from each child. Children
  synthesize condensed findings, cumulative support, unresolved uncertainty,
  contradictions, and their implications for the parent's goal. Include actual
  search/reading coverage and distinguish unexamined material from examined but
  uninformative material.
- On failure, communicate what failed, why, and what useful information remains.
  Preserve relevant partial findings without admitting unvalidated content as
  established evidence. The purpose is to improve the parent's future decisions,
  not merely to instruct a retry.
- Roll sibling contributions up to parents without double-counting repeated
  findings or calculations. Credit reflects goal-relevant partial progress,
  usable provisional outputs, and stronger scientific support. Do not reward
  filled fields, renamed parameterizations, raw source counts, or repetition.
- Evidence that corroborates an unchanged assumption is cumulative support, not
  an overwrite or something to ignore. Credit decreases should reflect actual
  loss of previously valid progress, such as invalidated premises, not simply
  another incomplete return. No cost term or cost-based steering is required.
- At numerical stopping, return the best current three-quantity results for each
  selected case, with explicit missing results and evidence status. There is no
  model-call or unit budget; do not equate stopping or populated fields with
  successful completion.

## Acceptance And Failure Boundary

- Verify through a real query across the production search/retrieve/LLM boundary.
  The user's prohibition on running tests remains in force. Do not run test
  suites, fake-provider exercises, or local calculation replays as a substitute.
- A passing root run must show a real search, retrieval of real source text, real
  LLM extraction, span/ref-checked admission, outbreak-based Cq calibration,
  target-scenario calculations for all three quantities, and source references
  and child/parent credit reports tracing the whole path.
- Completion requires scientifically supported outputs with explicit assumptions
  and applicability, not agreement with published answers. Unsupported partial
  estimates remain useful reportable progress, not a completed source-backed
  result. Internal arithmetic consistency alone is not independent scientific
  validation.
- If the real LLM/search/retrieval path is unavailable, fail closed with a
  structured blocker. Do not substitute fixtures, local evidence, another
  unauthorized provider, or a fabricated successful result. Preserve valid
  partial results already acquired during that run and report them as partial.
- Distinguish operational blockers, malformed contracts, evidence uncertainty,
  and physical/model limitations. Missing evidence can motivate more research
  or a provisional assumption; it must not become an execution gate on every
  calculation. Failures must retain enough context to inform a subsequent decision.

## Current State

The user reports that Argo has reset as of 2026-10-13. The historical monthly
access revocation is no longer treated as an outstanding blocker. V18 and V19
made real model, search and retrieval calls with runtime disease input, but were
terminated after source changes superseded their loaded implementations. They
did not produce final reports or establish completion. V19's streamed attempts
remain available. V20 is now the fresh real query of the revised implementation.

The historical V16 query produced unsupported partial estimates; it
did not demonstrate the current three-operation contract. Subsequent edits add
`solve_time`, `solve_distance`, and `evaluate_R_in` in
`task_executors/scenario_metrics/exposure.py`, exposed by the existing parent
tools, without adding episodes. The implemented model is
`R(t,x) = B(t) + J*t/x`; its unmasked continuous-jet route and transient local
plume approximation require explicit applicability assumptions. Its alternative
negligible-near-field hypothesis sets J to zero consistently in all operations.
Outputs retain fixed inputs and model identity; credit and coverage check the
requested operation and supplied coordinates.

The active query has not yet demonstrated the full calculation and support
path. V25 ended incomplete after 665 model calls, with source acquisition but
no outbreak calibration or requested calculations. V26 was launched on
2026-10-14 with Codex CLI ChatGPT authentication replacing the local Argo shim.
Its run-start source archive is retained under `.artifacts/live/`. This goal
has not been achieved; see `RESPONSE_FAILURE_STUDY.md` for earlier observed behavior.

The user replaced the stored goal with this specification and activated it on
2026-10-13. The live verification disease and variant are provided at runtime,
not embedded in code or default scenarios. Report the three main quantities for
each default scenario at the end of verification.
