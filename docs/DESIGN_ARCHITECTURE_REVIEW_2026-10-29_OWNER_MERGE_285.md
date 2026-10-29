# Design and architecture review — the owner's #285 (observing the research lock)

Date: 2026-10-29. Baseline: `0288e994` (main after #285).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 17:14–19:13 UTC firings. #285 makes `loop_control.running_pid` read the lock's owner from
Linux `/proc/locks` instead of probing the lock with `lockf`, so that inspecting a checkout can neither reserve its
lock nor release the caller's own. Status, stop, the launcher, the workspace report, the handoff, promotion, the
re-score and the ablation all use it. I reviewed it myself; it is one function and its tests.

## What changed

- **Status read a running loop as idle on btrfs and on some overlayfs mounts** (`scripts/loop_control.py`).
  - `/proc/locks` names a locked file by its file system's device. `_lock_owner` matched the device `stat()`
    reports, which is not always that device:
    - btrfs reports each subvolume's device, the top level's included;
    - overlayfs with layers on several file systems reports a layer's.
  - I mounted both here and ran a loop holding the lock in each. The owner was missed on both btrfs mounts
    (a subvolume, `stat()` 0:31 against `/proc/locks` 00:2f, and the top level) and on a mixed overlay
    (0:2d against 00:2c). On each:
    - `running_pid` returned None, and `loop_control.py status` exited 1, "nothing running";
    - `loop_control.py stop`, which `stop.sh` runs, printed "No autoresearch work running. Watchdog paused." and
      exited 0 with the holder still running (run on the subvolume and the mixed overlay);
    - so `start.sh` would clear the pause and launch a second loop, which then fails to take the lock, and the
      workspace report and the handoff's gate would read the loop as absent (the handoff's `pgrep` pattern still
      names it).

    Promotion, the re-score and the ablation still refused, because their own `acquire_lock` fails. Before #285,
    the `lockf` probe was right on these file systems.
  - The device now comes from the file's mount. An `O_PATH` descriptor's fdinfo gives its mount ID and inode, and
    `/proc/self/mountinfo` gives that mount's device, the one `/proc/locks` prints.
  - Such a descriptor cannot take a lock. Closing it drops none, unlike closing any descriptor opened for I/O.
    I checked this on ext4, overlay and btrfs: a lock held by the inspecting process survives an `O_PATH` close,
    and the same process's plain open and close releases it.
  - Every other check of #285 is unchanged: the lock type, the whole-file range, the queued requests, the
    replaced path and the owner's command and checkout.
  - With the fix, status names the holder on ext4, tmpfs, overlay (one file system and several) and btrfs (top
    level and subvolume). On the btrfs subvolume and the mixed overlay, an idle lock reads idle, `stop` ends the
    holder with SIGTERM, and an owner inspecting itself keeps its lock.
  - The new test in `tests/test_lock_observation.py` simulates btrfs by shifting the device `stat()` reports for
    the lock, and checks that the lock is opened only with `O_PATH`. It fails on #285's observer, which returns
    None.
- **Without `O_PATH` (not Linux), status reports unknown, not idle.** #285 failed there by reading `/proc/locks`,
  an `OSError` that status reports as exit 2. The descriptor is now taken first, so a missing `os.O_PATH` would
  have escaped `main()` as exit 1, which `start.sh` reads as idle. It is a `RuntimeError` now, and a test pins
  exit 2.
- **The status guide** (`docs/WORKSPACE_STATUS.md`) says where the device comes from and that the lock is never
  opened for reading or writing.
- **Three comments** said `running_pid` opens and closes the lock file, which would drop the caller's lock
  (`promote_loop_candidate.py`, `reevaluate_best_model.py`, `run_post_sprint_villa_handoff.py`). Since #285 it
  does not. Each caller still skips it once it holds the lock, now because it would name the caller itself. The
  comments say so. The 10-15 re-score review record says the same and is left as the record of its date.

## Verified, no change needed

- **#285's design.** The kernel's owner is authoritative, and the PID text in the file is only metadata.
  - Damaged, empty or stale text neither hides the owner nor redirects a stop. A live process named in stale text
    is not signalled (`test_stale_live_pid_cannot_redirect_stop`).
  - The owner must still run a lock-holding script in this checkout, and a second reading must name the same owner.
  - Queued requests (`->` rows) are skipped. Major and minor numbers are read as hex, as the kernel prints them,
    which covers NVMe's major 259 (`103`).
  - Only a whole-file POSIX write lock is accepted. I held a read lock, a partial-range lock and an OFD lock (PID
    −1) here, and status reported each as unknown, as #285's test does for `flock`. An owner outside this PID
    namespace (PID 0) fails the same check.
- **Callers' error handling.** `loop_control.main`, the workspace report, the re-score and the ablation catch
  `OSError` and `RuntimeError`, and the handoff catches everything. The new errors are `RuntimeError`s.
- **#285's tests.** Its record names six regression cases that fail on the observer before #285; 13 of its 15
  lock-observation tests do. With #285, they and the launcher's test pass here, and its six suites give 133 passed.

## Verification

- **The lock-observation tests** give 17 passed. Run on #285's `loop_control.py`, the two new tests fail.
- **Every test file that uses a touched script** (22 files) gives 661 passed and 2 skipped. That ran before the
  non-Linux guard, which only the lock-observation tests reach.
- **The standard suite** gives the same 43 failures as on main, from `s3fs`, `numba`, `jsonschema` and Villa
  files absent here. The same 2 modules cannot be collected (`tensorstore`, `s3fs`).
- **Ruff 0.9.10** `check` and `format` are clean on the five changed Python files. Mypy is clean over the whole
  repository (831 files).
- **The file system probes** need root (mounts of tmpfs, overlay and a loop-mounted btrfs image) and
  `btrfs-progs`, so they are not in the suite. I ran them in this container (kernel 6.18).
