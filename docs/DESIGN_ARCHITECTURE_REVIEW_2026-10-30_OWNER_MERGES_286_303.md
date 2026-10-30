# Design and architecture review — the owner's #286 and #303 (seed-heading re-run, fiber provenance in reports)

Date: 2026-10-30. Baseline: `114a3400` (main after #303).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 19:13–21:13 UTC firings. A read-only review of #303 started beside mine, but a usage limit
stopped it before it reported, so I reviewed #303 myself.
- **#286** records the seed-heading re-run at Villa `39a8cf3a`.
  - It adds the wrapper that paused the loop around that run.
  - It exempts the wrapper from the chain loop-guard test.
  - It stubs docker in a preflight test.
- **#303** makes the candidate ink/fiber report check the fiber label producer's sidecar.
  - The label TIFF is hashed and decoded from the same captured bytes.
  - The new `--require-fiber-metadata` option refuses a candidate without a sidecar.

## What changed

- **`loop_control stop` could fail after it had stopped the loop** (`scripts/loop_control.py`).
  - `running_pid` looks at the lock's owner twice: once to find it, and again after checking that process's
    command and checkout.
  - If the holder exited between the two looks, the second look found no owner, and `running_pid` raised
    "research lock owner changed during inspection".
  - `stop` polls `running_pid` while the loop exits, with no handler for that error. A stop that had worked
    therefore returned 2.
  - The standard suite's `test_loop_control_can_stop_a_registered_probe_cli` failed this way once here, under
    load. It passed 8 times out of 8 alone.
  - A holder gone at the second look has released the lock, so `running_pid` now returns None. A different owner
    at the second look still raises.
  - Two new tests:
    - one makes the holder exit between the looks, and fails on the code before the fix;
    - the other pins the different-owner case.
  - The second look came with #285. My review of #285 (#289) did not catch this.

## Verified, no change needed

- **#286's records.**
  - **The re-run JSON.** Its status is `IDENTICAL`: Villa `39a8cf3a1` against `ccb431818`. Each of the four runs
    is identical to its source and has the same counts and tolerance-2 rows as the `322cb0899` record. Before and
    after differ on both cubes.
  - **The wrapper transcript.**
    - It stopped the loop at 14:34:37, after a cycle that was not one of #264's arms had started
      (`ema_decay_0.999`).
    - Status then gave 1 and the chain 0, and the loop started again at 14:38:55. That is the draft's "paused
      14:34–14:39".
  - **The chain transcript** names Villa `39a8cf3a1` and gives all four `DONE` lines.
  - **The resume-test transcript** gives the draft's counts: with the heading patch alone, 2 failed and 21
    passed; with both patches, 23 passed.
- **#286's wrapper.**
  - It restarts the loop whatever the chain did. Nothing between `stop.sh` and `start.sh` exits, as its test
    checks.
  - The chain it runs checks the loop itself.
- **#303's sidecar check matches the producer.** It checks:
  - contract 1, the label kind and ZYX axes;
  - the label TIFF's shape;
  - a window that starts at the candidate's origin and has its height and width, within the recorded source shape;
  - the absolute source path, dtype, threshold and backend;
  - the label TIFF's hash.
- **#303's byte binding.**
  - The label hash is taken over the captured bytes that are then decoded.
  - The final recheck reads the JSON again through `Snapshot` and the TIFF within its byte budget.
- **#303's recorded geometry.** "Recorded geometry agrees" needs the prediction sidecar (source path, size,
  origin) and the fiber sidecar both to agree with `candidate.json`, as the guide says.

## Observations for the owner (not changed)

- **#286's wrapper.**
  - It sets no trap. Killed between `stop.sh` and `start.sh`, it leaves the loop stopped. Its test checks only
    that no `exit` appears in that span.
  - It hardcodes the owner's paths. It is a record of the October 28 run, not a general tool.
- **#303's baseline count.**
  - Its record says twelve new regressions failed on the baseline. With the merged test file on the parent, 35 of
    the 37 cases fail.
  - In 22 of them the parent counts the candidate as `INSPECTED` where the merged code finds invalid fiber
    metadata.
  - With the two FIFO cases included, the parent's run had not finished after two minutes, consistent with the
    parent opening the FIFO and blocking. Without them it takes 2 s.
- **What #303 attests.** The CT window and the label hash are checked against the producer's declarations. The
  probability TIFF, CT digest and filter hash are only checked as well-formed digests, as its guide says.

## Verification

- **The lock observation tests** give 19 passed. The new exit test fails on the code before the fix.
- **The modules that use the lock observation** give 298 passed: the loop lifecycle, noise probe, workspace,
  promotion, checkpoint tool, handoff and loop-control modules.
- **#303's integration command** gives 213 passed, as recorded. **#286's three test files** give 73 passed.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the changed Python files. Mypy is clean over the
  whole repository (847 files).
- **The standard suite** gives RESULT_SUITE.
- **The test modules outside the standard suite** give RESULT_OUTSIDE.
- **The doc audit** finds no new unresolved reference.
