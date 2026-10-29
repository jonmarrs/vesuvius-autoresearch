# Inspect a research checkout

Run this before setup or when a launcher appears to do nothing:

```sh
python3 scripts/workspace_status.py
python3 scripts/workspace_status.py --repo /path/to/checkout --json
make status
```

The command needs only Python's standard library. It does not install packages,
load checkpoints or arrays, read study measurements, initialize CUDA, start
processes or write research state. Relative data paths are interpreted from
`--repo`, as they are when the loop runs there. `--config` selects a different
configuration file without changing `config.json`.

It reports the registered process, watchdog pause state, unsupervised training
processes, checkpoint presence, configuration parsing and configured data/label
paths. It shares label selection with the trainer, including refined-label
priority and the confidence-weight requirement for pseudo-labels.

| Exit | Setup status | Meaning |
| --- | --- | --- |
| 0 | `ok` | The inspected local paths and configuration checks passed. |
| 1 | `blocked` | A missing/invalid input or unsupervised trainer needs attention. |
| 2 | `unknown` | An observation could not be completed, such as a remote URI or unavailable process metadata. |

The JSON explicitly records `training_readiness: not_checked`. Existing files
may still have invalid contents. Model compatibility, validation identity,
dependencies, CUDA availability and VRAM need the existing training preflight.
An idle process snapshot does not reserve the GPU. A running process or paused
watchdog is shown separately from filesystem setup; neither establishes that a
new job can start.

For missing data, follow the [README's data layout](../README.md#quick-start)
and check the displayed paths. For an unsupervised trainer, use
`python3 scripts/loop_control.py status` to inspect its PID; `./stop.sh` stops
registered work and orphaned supervised runs, while hand-started runs are
identified for the operator. Stopping research or changing runtime code can
invalidate a registered study window: inspect first and follow that study's
stopping rule. The status command itself leaves it alone.

Process status uses Linux `/proc/locks` to identify the owner of this checkout's
whole-file POSIX lock by device and inode, then verifies the owner's command and
working directory. It never opens or acquires `autoresearch.lock`: inspecting an
idle checkout cannot reserve it, and inspecting from an owner cannot release its
lock. Stale, empty or damaged PID text does not hide a live kernel owner or
redirect a stop to a different PID. A missing kernel observation, unexpected
lock type, foreign owner or changing lock path is reported as unknown, rather
than idle. This requires the host's normal Linux `/proc` view; it is not a
cross-host or GPU-wide reservation. The lock file's PID text is retained for
legacy diagnostics, but status and stop use kernel ownership.

The legacy `submittable` training field and artifact-validator `PASS` are local
contracts. The artifact report now labels its scope and explicitly leaves prize
eligibility unassessed. Consult the [current sourced strategy](RESEARCH_STRATEGY.md)
and official rules when designing a new experiment or preparing a submission.
