# Identical-config repeatability probe

`scripts/f1_noise_probe.py` plans repeated fine-tuning trials from one explicit
config and starting checkpoint. It reports descriptive F1 spread only when all
requested trials complete under the current validation protocol. It does not
update the production checkpoint or promotion tolerance.
The protocol is derived by the trainer's shared `validation_protocol` helper
from the planned `depth_band`, including its `+zSTART-END` suffix. Both the raw
result and validation diagnostics must match that exact planned protocol.

## Plan first

```sh
uv run python scripts/f1_noise_probe.py \
  --config config.json --checkpoint best_model.pt \
  --out reports/new_repeatability_probe --runs 4
```

The default is a read-only plan: it reads config/file identities, prints strict
JSON and creates no output directory, caches or lock. It does not validate
checkpoint weights, GPU readiness or training data. Execution checks checkpoint
compatibility before invoking the trainer; data/backend errors remain execution
failures.

Config-relative local paths resolve against the config's directory. Remote URIs
retain their spelling. `--runs` is an integer from 2 to 16. The config's positive
integer time budget is at most 86,400 seconds. `--timeout` is a positive finite
per-trial deadline, defaulting to the training budget plus 900 seconds.

The output must be a new directory outside all declared source files, local
fragment trees and the `scripts`, `src` and Villa code trees. Existing destinations
and symlinks are refused. Reusing the old `local_data/noise_probe` and fixed JSON
destination is retired: choose a new report directory for each execution.
Importing the module starts no work.

## Explicit execution

After resolving the host and scientific choices for the planned experiment:

```sh
uv run python scripts/f1_noise_probe.py \
  --config config.json --checkpoint best_model.pt \
  --out reports/new_repeatability_probe --runs 4 --execute
```

Execution reserves this checkout's `autoresearch.lock`, without clearing its
pause marker. The loop and another probe cannot acquire that lock concurrently.
`./stop.sh` can stop a probe registered by the CLI and pause the watchdog. Keep
the host otherwise idle; this lock does not coordinate independent fits/renders
or another checkout.

Each trial gets a private working directory, starting-checkpoint copy, generated
config, candidate checkpoint, result file, log, data cache, histogram directory
and native/plot/temp cache paths. Tracking is disabled. The source checkpoint
and production `run_result.json` stay untouched. The trainer's existing isolated
`checkpoint_out` path avoids production history, results and promotion files.

The child entry point validates complete starting weights and matching recorded
model/input settings, including dropout, ridge sigma and requested flattening.
Fields used by the trainer's warm-start check must be explicitly recorded;
defaults from the checkpoint reconstruction helper do not satisfy that check.
It then requests the trainer's strict warm-start path: every starting tensor
must load successfully before an optimizer is created. Missing, unreadable or
incompatible weights fail the trial instead of allowing fresh or partial weights.
No separate scoring or promotion formula is implemented. Config serialization
omits the exact default
`max_prize_skel_dist=+inf`; the config loader restores that existing unused
default, keeping generated JSON and summaries standards-compliant.

## Results and failures

A completed directory contains `probe.json` plus `run_01/`, `run_02/`, etc.
Trial directories retain the generated config, starting/candidate checkpoints,
`run_result.json`, `training.log` and any caches. Recorded commands contain the
actual temporary staging paths; use the relative `directory` fields to find
published trial files. Archived configs are provenance, not restart commands.

A trial qualifies only with exit code zero, a nonempty candidate checkpoint,
the current protocol, complete and consistent positive sample counts, a valid
sampling seed and finite F1/threshold/AP-lift/AUC/prevalence values. It need not
improve on the incumbent: `is_success=false` is a normal, valid observation.
Sample counts and target prevalence must agree across trials; otherwise the
scores are not the declared same-sample comparison and no spread is reported.
Reported-only NaNs in the raw trainer JSON are retained for inspection and are
excluded from the strict summary.

Config, starting checkpoint and entry/trainer source hashes are checked before
and after trials. The config is parsed and hashed from the same captured bytes,
and planning rejects an input rewrite before returning a plan. Changing one
invalidates the aggregate. A failed exit,
timeout, interruption or invalid result stops the remaining trials. Supervision
terminates the worker process group before publication. An inspectable failed
execution has `status: FAILED` (or `INTERRUPTED`), `f1_spread: null` and a nonzero
CLI exit; it never estimates a spread from only the surviving trials.
Invalid planning or changed inputs before execution produce no report. Writers
must remain serialized, and an interruption during final publication can discard
staged output.

Only a complete set reports mean, sample standard deviation (`n-1`) and range.
`execution_attempted` records invocation attempts, not proof of GPU work.
`tolerance_calibrated` stays false. File hashes do not snapshot CT, labels,
installed dependencies or every imported source file; keep those inputs stable.
The per-run code/data caches and native source reference do not establish
numerical GPU/CPU parity or production readiness.

**Pooling two batches.** `scripts/noise_probe_pooled.py`, the analysis registered in
`docs/preregistration/2026-10-17_noise_probe_v3_pooled.md`, pools the finished trials of two
batches. As registered, it also counts the trials a batch finished before a later one failed.
It first checks, across both batches, what this probe checks within one:
- one configuration;
- one starting checkpoint and config file (the training code's hashes may differ);
- one validation sample and prevalence;
- no repeated sampling seed.

It refuses to pool otherwise.

[Finding 86](../reports/loop_v2_constant_control.md) records the limitations of F1
near an all-ink ceiling. Host and loop restart decisions are recorded separately
in [the resume note](RESUME_AFTER_RESTART.md). Near an all-ink ceiling,
a small F1 spread does not establish a suitable promotion tolerance. This tool
does not choose a new metric, change stored scientific evidence, or resume the
loop. See the [review report](DESIGN_ARCHITECTURE_REVIEW_2026-10-13_REPEATABILITY.md)
for the repairs and validation limits.
The [follow-up review fixes](DESIGN_ARCHITECTURE_REVIEW_2026-10-14_REPEATABILITY_FIXES.md)
cover required weight loading and configuration snapshot identity.
