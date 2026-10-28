# Process startup and handoff execution review

Reviewed October 28, 2026 against public main
`ec6f4a645dda3c58d789f89f1b21d0df06da06ef` from a separate checkout. Scope:
supervised worker lifetime, stop handling, the post-sprint handoff, its reports
and operator documentation. No live study measurements or GPU jobs were used.

## Findings and implementation

**A stop could escape cleanup during process startup.** `ProcessSupervisor.run`
started a child before entering its cleanup scope or registering the child in
`self.active`. A Python stop handler running between those operations saw no
worker to stop. In the loop, checkpoint restoration could then run while the
worker remained alive. A wrapper around the real `Popen` injected SIGTERM,
SIGHUP and SIGINT immediately after a harmless child started. All three
children survived, and a fourth regression showed a loop-style stop handler
settling while its child was still alive. These four checks failed on the
unchanged implementation.

Startup now occurs inside the cleanup scope. In the main thread, handled stop
signals are briefly queued until the child is registered, then delivered to
the caller's original handlers. Parent signal handlers are restored before
delivery. OS signal masks are not blocked, so children retain ordinary signal
handling. Default and ignored dispositions retain their behavior, including
nohup's ignored SIGHUP. Other threads keep their existing behavior. Existing
group termination, escalation and repeat-stop handling are reused.

**Handoff commands had no configurable execution deadline.** The existing
supervisor already supports a timeout, but the handoff always passed `None`.
The new optional `--step-timeout SECONDS` bounds each command and stops the
pipeline on the first timeout. Positive finite values are checked before any
lock/report writes. The default remains an unlimited wait. Cleanup can take
additional time after the command deadline.

**The initial readiness plan concealed the execution outcome.** Previously a
failed command left its report as `READY` and surfaced through a traceback.
Reports now distinguish `COMPLETE`, `FAILED_TIMEOUT`, `FAILED_STEP` and
`STOPPED`. Failure details name the step and record its cause, timeout or exit
code. Console errors point to the report. A failed or missing command exits 1,
timeout exits 124, refused setup exits 2 and an interrupted CLI exits 130.
Earlier completed steps are retained; the handoff provides no automatic resume
or rollback. The guide explains these boundaries and fixes moved command paths.

## Architecture and review

Keep child ownership and cleanup in `ProcessSupervisor`. The handoff adds
execution policy and report states around that shared mechanism, retaining its
checkout lock until cleanup and outcome recording finish. Signals are deferred
only across child registration, rather than throughout the command. Callback
restoration uses `ExitStack` so restoring another handler still happens if a
callback raises.

The PR review reproduced a second edge case in the initial fix: if process
creation also failed, the queued stop request was skipped. Three new cases
failed for SIGTERM, SIGHUP and SIGINT. Signal replay now runs from `finally`
after restoration, including failed launches. A pending stop still takes
priority over a launch error, rather than allowing the loop to continue.

Review covered ignored signals, returning and exiting handlers, spawn failure,
timeout escalation, child/grandchild termination, local lock release, report
aliases, CLI parsing and stopping before later pipeline steps. The existing
checkout lock is not a host-wide GPU scheduler. Runtime updates still require
the registered study's stopping/deployment discipline; this review performs no
deployment and changes no models or scientific selection rules.

## Verification

Tests use isolated CPU children and tiny synthetic inputs. The startup
regressions initially returned **4 failed, 1 passed**. After the fix, the initial
startup/lifecycle run passed 42 checks; the expanded shutdown/handoff run
passed 88. New regressions are included in the standard validation list.
After the PR review's failed-launch cancellation fix, the four focused suites
(`test_supervisor_startup`, `test_handoff_deadlines`,
`test_post_sprint_villa_handoff` and `test_loop_lifecycle`) passed **92 checks,
no skips, in 25.02 seconds**. Ruff and targeted mypy passed again on the final
source. The three review regressions fail on the first PR revision and pass
on the final revision.

The temporary Python 3.10 environment `/tmp/vesuvius-review-env` exposes already
cached dependencies. Commands run with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''`:

```sh
/tmp/vesuvius-review-env/bin/python -m pytest -q -rs \
  tests/test_supervisor_startup.py tests/test_handoff_deadlines.py \
  tests/test_post_sprint_villa_handoff.py tests/test_loop_lifecycle.py \
  tests/test_noise_probe_contracts.py tests/test_ablation_harness_isolation.py \
  tests/test_pseudo_handoff_contracts.py tests/test_validation_suite_covers_the_loop.py

/tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
# 8 passed, 3 skipped, 0 failed in 11.9 seconds
```

The smoke skips require real training data or Villa's augmentation import. An
initial expanded run returned 241 passed and four environment failures: one
spawn-manager case required local sockets, and three pseudo-label checks
required the pinned Villa sampler source. The latter was retrieved from the
recorded Villa gitlink `ccb431818fa68059138f2c964ae299fc474ff116` and verified as
Git blob `21b068d5a364eb1d1225fe01668d5d70cbb000a8` before rerunning. That source
file is a local test input, not a submodule or dependency update.
With that exact source available and local sockets enabled, the spawn-manager
case and full pseudo-label suite passed **66 checks, no skips, in 46.85 seconds**.
This rerun includes all four initially failing cases; the other 241 selected
cases passed in the initial run. No environment failure remains unresolved in
this selected set. Raw local logs are `/tmp/vesuvius-shutdown-integrated-tests.log`
and `/tmp/vesuvius-shutdown-environment-recheck.log`.

Ruff checks the six changed Python files. Targeted mypy checks the supervisor,
handoff and two new test modules. Diff checks, CLI help and documentation command
paths are checked. The full repository suite, GPU inference/training and a real
post-sprint workflow were not run.
