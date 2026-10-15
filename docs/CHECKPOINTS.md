# Checkpoint Continuation

The configured CLI checkpoints by default under a unique directory in
`.artifacts/checkpoints`. `--checkpoint-path PATH` chooses a new directory;
`--resume PATH` continues an existing registration. A checkpoint is not a
scientific evidence source or an alternative workflow provider.

## Explicit Compatible Forks

Ordinary `--resume` still requires unchanged code and reconstructs the complete
saved history. A changed-code experiment may instead explicitly reuse a prefix
ending at a committed, continuing unit boundary:

```sh
python3 -I -S -B . --fork-checkpoint OLD_CHECKPOINT \
  --fork-through-record RECORD_INDEX --checkpoint-path NEW_CHECKPOINT \
  --fork-reason "Reviewed compatibility rationale" \
  --fork-allow-changed path/to/changed.py
```

Repeat `--fork-allow-changed` for every changed implementation file. The declared
set must match exactly; Python/platform changes are rejected. The record index
selects immutable history, not a limit on future work. The original checkpoint
is read under a shared lock and is never modified. The fork records its distinct
identity, parent registration/terminal/prefix hashes, and old/new code identities.
It retains the original episode namespace so the existing reconstruction cursor
can verify every historical request, result, active episode and unit-state hash.
There is no fallback to live providers on divergence. Live work requires separate
host authorization after the whole prefix matches.

This is a new experiment, not OpenChia's unchanged-code interrupted-run resume.
The original run-start code metadata remains historical; fork activation and the
final report's `checkpoint` field identify the current implementation explicitly.
Calls after the selected prefix are not reused, and this choice is recorded.
The ordinary `--resume NEW_CHECKPOINT` command continues a previously created
fork under its own now-fixed implementation and provider configuration.

## Mechanism

The implementation adapts these OpenChia mechanisms into repository-owned code:

- `episode_runtime/testing_harness/reconstruction.py`: ordered frame matching,
  immutable saved replies, sticky divergence, active Episode ancestry, and the
  `prefix_verified` boundary. Local implementation:
  `method_loop/reconstruction.py`.
- `episode_runtime/testing_harness/reconstruction_host.py`: exhausted history
  does not itself authorize new work. The CLI host commits a
  `run_reconstructed` receipt only after the complete prefix matches.
- `episode_runtime/linker.py`'s `_InstrumentedEpisode`: record
  `episode_started`, `unit_completed`, and `episode_completed` at the ordinary
  method-loop boundaries. The original controller and source logic still run.
- `episode_runtime/continuation.py`: preserve the logical run and registration,
  distinguish physical attempts, and bind continuation to the preceding
  interrupted attempt's exact terminal reference.

This is the same reconstruction control protocol with a local filesystem
journal adapter, not an OpenChia RunStore file-format importer. It has no
OpenChia runtime dependency, remote broker authority, or worker container.

All completed external results are committed before the caller receives them:
raw model responses (before JSON parsing), Firecrawl search and retrieval,
Jev scalar/vector assessments, and the source retrieval timestamp. This covers
scenario preflight as well as nested acquisition and review. Completed provider
failures are replayed with their exception type and arguments. Invalid model
JSON remains the original raw response and follows the original parser path.

Resume executes deterministic code locally from the original registration,
supplying those recorded responses in the original cross-child order. The
result is reconstruction of the entire current source/controller state,
including admitted evidence, pending extraction/review, shared assumptions and
calculations, active ancestry, contracts, reading coverage/cursors, selected
actions and iteration/yield histories. Logical model-call accounting therefore
continues at its original position; physical retries of the last unanswered
request are identifiable through attempt/activation receipts.

Every request and lifecycle/diagnostic frame must match before any new provider
call is permitted. A mismatch is a fatal checkpoint error, not an unproductive
scientific episode. This preserves the existing credit and stopping semantics.
No scientific parameters or answers are added by checkpointing.

## Durability And Privacy

The directory contains `manifest.json`, immutable hash-chained `records`,
`pending.json` for an in-flight external request, and physical `attempts`.
Writes use a temporary file, file `fsync`, atomic replacement, and directory
`fsync`. An exclusive process lock prevents concurrent owners. Temporary files
from a crash are ignored; corrupt committed records, gaps, missing completed
tails, altered requests and broken attempt lineage are rejected.

If a process exits without a terminal receipt, the next executor must obtain
the exclusive lock before recording the abandoned attempt as interrupted. A
response committed immediately before a crash is retained even if the pending
marker was not removed. A response never committed cannot be recovered: only
that unanswered observational request may be retried. No receipt-reconciliation
claim is made for external state-changing operations; this adapter does not
support them or overlapping/concurrent external requests.

Provider credentials are loaded from current configuration, never serialized.
Only a hash of non-secret model/provider settings is saved. Known credential
strings are redacted from returned content before both the original consumer
and journal receive it, preserving replay identity without retaining secrets.
Checkpoint records and directories have owner-only permissions. Source/model
content is otherwise retained, so these remain private research artifacts.

Historical trace/progress output is not emitted again during reconstruction.
By default `trace.jsonl` is appended within the same checkpoint; report and
audit files are written after closure. Replaying an already completed run
performs no new external requests and accepts an existing output only if its
contents are identical. Explicit output paths can be supplied independently
of scientific inputs.

## Compatibility And Limits

The CLI's disease, normalized case definitions, additional request, search
result count, reading window and yield window must match. All repository-owned
runtime Python files and the Python/platform identity must match. Semantic code
changes require a new run; there is no silent migration or answer substitution.
Credentials may rotate, but models, routes and other provider settings may not.

The active workflow uses a synchronous, serial method loop with sequential
async provider operations; that is the supported continuation contract.
Arbitrary concurrent Episode execution and serialization of suspended Python
stacks are not implemented. No checkpoint is manufactured from an old trace
that lacked these recording boundaries, including the stopped v44 run.

Verification is focused deterministic infrastructure testing, not scientific
acceptance: nested method-loop reconstruction, fresh Python processes with
different hash seeds, interrupted review, committed failures, raw malformed
JSON, sequential async assessment, process death, locks, corruption, input
compatibility, output deduplication and completed-run replay. No live provider
calls are made by these tests.
