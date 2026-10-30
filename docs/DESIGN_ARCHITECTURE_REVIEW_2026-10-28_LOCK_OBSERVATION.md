# Design and architecture review: observing the research lock

Baseline: `87afa92a` (main after PR #284). Scope: setup/status UX, the shared
research lock, launch refusal and stop targeting. This is a focused review of
the process-observation boundary; it is not a review of every research method.

## Findings and fixes

### Status could reserve an idle checkout's lock

`workspace_status.py`, `loop_control.py status`, the launcher and the handoff
all use `loop_control.running_pid`. Its old implementation opened
`autoresearch.lock` with write access and attempted an exclusive nonblocking
`lockf`. With a free lock, an observation briefly became the owner: a concurrent
launcher could fail its own nonblocking acquisition. That conflicts with the
status command's read-only contract.

Opening the file is also unsafe when the observer itself owns its POSIX lock:
closing any descriptor for that inode releases this process's locks on it. The
old function could return idle and release the caller's existing lock.

The shared observer now reads Linux `/proc/locks`, matches the lock's device
and inode, and accepts only the whole-file exclusive POSIX lock used by
`acquire_lock`. It never opens or acquires the research lock file. Acquisition
and PID metadata writing remain in the launcher; observation cannot reserve or
release the lock. No third-party dependency or native ABI structure is needed.

### PID text could hide the owner or select another process

The old observer trusted the PID text after finding a busy lock. A real lock
holder with stale dead-PID text reproduced as idle. If the text named another
live recognized command in the same checkout, that other process passed the
command and working-directory checks, even though it did not own the lock.
The stop path could then signal the wrong process.

The kernel's owner PID is now authoritative. Empty, damaged or stale metadata
does not hide the owner or redirect a stop. The owner must still have an expected
command and working directory. A second ownership observation checks that it
has not changed while the process identity was inspected. Unknown ownership,
an unsupported lock type, a changed inode or a foreign command/checkout fails
closed. No process is stopped by a status check.

The launcher's status meanings remain running/idle/unknown. A recognized actual
owner with damaged metadata is now running, rather than unknown. The existing
launcher regression tests explicitly check that it refuses to start beside it.

## User-facing behavior

- Setup inspection works without write access to the research lock file.
- Workspace JSON still separates setup status from unchecked training readiness.
- Symlink lock paths are identified by their target inode.
- Queued kernel requests are not mistaken for current owners.
- Unsupported or unavailable lock observation produces an actionable unknown
  state rather than an idle result. The status guide documents the Linux host
  `/proc` requirement and the checkout scope.

The observer is still a snapshot, not a GPU reservation. Actual launchers must
acquire the lock. This does not add cross-host locking, solve orphaned handoff
workers, or authorize deploying code into a registered research window.

## Verification

The six integrated suites cover real subprocess locks and stop signals,
damaged/stale PID metadata, competing checkout/command identities, symlinks,
lock replacement, queued requests, unavailable observations, read-only JSON,
launcher behavior and the validation registry.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-review-env/bin/python -m pytest -q -rs \
  tests/test_lock_observation.py tests/test_workspace_status.py \
  tests/test_loop_control_modules.py tests/test_loop_lifecycle.py \
  tests/test_post_sprint_villa_handoff.py \
  tests/test_validation_suite_covers_the_loop.py
```

Result: **133 passed in 35.76s**, no skips. The new lock-observation module is
included in the curated validation registry. Six selected regression cases
also fail when the baseline `running_pid` is loaded through a temporary pytest
plugin; the stale-live-PID case reproduces selection of the wrong process.

```sh
MPLCONFIGDIR=/tmp/vesuvius-status-mpl XDG_CACHE_HOME=/tmp/vesuvius-status-cache \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
```

Result: **8/11 passed, 3 skipped, 0 failed in 24.2s**. The two training-data
checks lack their URI/inklabels; batchgeneratorsv2's transform is unavailable.

Ruff check and format pass on the four changed Python files. Targeted mypy,
using the repository settings and `--follow-imports=silent`, passes on those
four files. `git diff --check` is clean.

No GPU training, deployment, native Villa integration, full repository suite,
cross-host/network-filesystem locking or unusual PID-namespace layout was
tested. No live study measurements were inspected and no model promotion was
performed. The prepared prize answers and research results remain unchanged.
