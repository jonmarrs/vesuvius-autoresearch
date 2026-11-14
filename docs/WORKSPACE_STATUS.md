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

The `training_split` check rejects observable overlap between the validation
volume and labeled or active UA-MT inputs. It recognizes local path aliases,
symlinks, directory ancestry, existing inode aliases and matching remote resource
identifiers, without opening arrays or making network requests. Different remote
URLs, copied volumes and physically overlapping crops remain unverified.
Existing local paths take precedence over URI parsing, matching the CT reader,
including local names containing colons. For symlinked volumes, annotation paths
stay beside the configured volume path, as they do in training.
The `checkpoint_outputs` check protects loop state and named local inputs from
experiment checkpoint and configured curve destinations. The trainer repeats
these checks before work and saving, including step snapshots when their names
are known. Source/writer serialization is still required; these snapshots are
not locks or a proof of scientific holdout independence.

The JSON `data_read_policy` field and human-readable `read_policy` entry show
`strict` or `legacy_permissive` for training; validation is always strict.
Configure `strict_training_reads` as an explicit boolean (`false` by default)
to choose whether training read failures abort. No arrays are read to produce
this report. Unsupported strict UA-MT/Lasagna configurations are rejected.

Configuration reads are limited to **1 MiB** by default. They require a regular
UTF-8 file; directories, FIFOs and files over the selected limit produce a
blocked config check. On POSIX, the shared capture also opens nonblocking and
checks the actual descriptor, so replacing a regular path with a FIFO between
the path check and open cannot make it wait for a writer. Deeply nested JSON and
unresolvable repository/config paths produce structured diagnostics.

For a deliberately larger configuration, select an integer byte budget, up to
**16 MiB**:

```sh
python3 scripts/workspace_status.py --max-config-bytes 2097152 --json
```

JSON output includes `config_byte_limit`. After a successful UTF-8 capture,
`config_source` gives its resolved path, byte count and SHA-256, even if JSON
parsing subsequently fails. Human output prints that fingerprint too. Parsing
and hashing use the same captured bytes, before `ExperimentConfig` normalizes
legacy fields or filters validation overlap. Existing checks continue to show
configured paths and normalization notices. File symlinks remain supported and
the fingerprint names the resolved target; data paths still resolve from `--repo`.

The fingerprint identifies the config bytes inspected, not normalized settings
or checkpoint compatibility. Another writer can replace the config afterward.
A UTF-8 BOM remains a config parse error, matching the existing JSON loader.
The byte budget is not a total memory or filesystem time limit.

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
working directory. The device is the lock's file system's, from mountinfo:
`stat()` reports another on btrfs and on overlayfs with layers on several file
systems. It never opens `autoresearch.lock` for reading or writing, nor acquires
it (an `O_PATH` descriptor names its mount): inspecting an idle checkout cannot
reserve it, and inspecting from an owner cannot release its lock. Stale, empty
or damaged PID text does not hide a live kernel owner or redirect a stop to a
different PID. A missing kernel observation, unexpected lock type, foreign owner
or changing lock path is reported as unknown, rather than idle. This requires
the host's normal Linux `/proc` view; it is not a cross-host or GPU-wide
reservation. The lock file's PID text is retained for legacy diagnostics, but
status and stop use kernel ownership.

The legacy `submittable` training field and artifact-validator `PASS` are local
contracts. The artifact report now labels its scope and explicitly leaves prize
eligibility unassessed. Consult the [current sourced strategy](RESEARCH_STRATEGY.md)
and official rules when designing a new experiment or preparing a submission.
