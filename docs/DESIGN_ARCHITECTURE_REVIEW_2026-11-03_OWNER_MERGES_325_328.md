# Design and architecture review — the owner's #325–#328

Date: 2026-11-03. Baseline: `a076e136` (main after #328).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 16:14 UTC firing; main had not moved since #324 at the firings before it. Two read-only reviews
ran beside mine, one of #326 and one of #328. I checked each of their findings before acting on it.
- **#325** makes the supervisor's escalated stop wait for the whole group, as `_kill` does.
- **#326** proposes, unregistered, a pilot of villa's own refit retry at the neural tracer's confidence stops.
- **#327** makes October's ScrollGT cite test read the draft's URL field.
- **#328** proposes, unregistered, a confirmation of the queued seed-heading fix on ten fiber cubes never traced here.

## What changed

- **#325's new test raced its own marker** (`tests/test_loop_lifecycle.py`, in the standard suite).
  - It asserted a `reaped` file that the worker's parent writes after reaping the worker. The group empties at the
    reap, so `stop()` can return before the write.
  - It failed 2 of 53 runs here while other work loaded the machine. The failing runs took 3.05 s, as passing ones do;
    a timed-out `_kill` would have taken over 4 s.
  - With a 0.1 s pause between the reap and the write, it fails every run, though the worker is gone when `stop()`
    returns.
  - It now asserts that the worker's `/proc` entry is gone, which a zombie keeps. That check fails on the supervisor
    before #325 and passed 100 of 100 runs on #325's.
- **#326's smoke was outside the manipulation check** (`scripts/neural_tracer_refit_retry.py`).
  - The proposal says every floor and smoke run must record the retry off, or the status is MANIPULATION_FAILED. The
    scorer read only the refit and floor arms' records, and `smoke` compared only the `.afv` files.
  - `smoke` now records the launcher's `in_effect` and fails unless it is off. `verdict` checks the smoke's record,
    and a score without it fails the check.
- **Failed and incomplete studies still carried a reading** (#326 and #328).
  - #326: on SMOKE_FAILED or INCOMPLETE, `cmd_score` still wrote and printed the reading `verdict` made from the runs.
    The proposal says the tests check that each failure branch emits no reading.
  - #328: the decision and reading survived MANIPULATION_FAILED, SMOKE_FAILED and INCOMPLETE. The proposal applies the
    decision rule to status OK only and says a failed manipulation check voids it.
  - Both scorers now go through `outcome()`, which clears them unless the status is OK.
- **A figure exactly at a threshold could fall on the wrong side** (#326 and #328).
  - ScrollGT's rows are rounded, and differences and ratios of them carry float error. 0.50 − 0.53 is
    −0.030000000000000027, so a precision drop of exactly 0.03 failed "at most 0.03 lower".
  - Likewise for a gain of 0.10 (5.72 / 5.2 − 1), coverage factors of 1.05 and 0.99, and an ERL factor of 0.95. A
    floor change of exactly 0.03 passed "below 0.03".
  - Each comparison now allows 1e-9. The tests use those rows, and each fails with its allowance removed.
- **#328's fetch converted a padded 512³ cube in one piece** (`scripts/seed_heading_confirmation.py`).
  - `cc.to_uint8` on the whole 768³ region holds two float64 copies of it, about 3.6 GB each, and the proposal runs
    `fetch` beside the loop. Finding 98's fetch converts a slab at a time for that reason.
  - `fetch` now does the same. The test fails on #328's code.
- **#328's readings and proposal said the fix costs nothing** (`scripts/seed_heading_confirmation.py`,
  `docs/preregistration/2026-11-02_seed_heading_confirmation.md`).
  - REPLICATED read "at the same precision and merge-penalized ERL". NO_HIGH_SKIP_CUBE read "costs neither", and the
    decision rule let the draft say so.
  - P2 and P5 pass with up to 0.03 of precision and 5% of merge-penalized ERL lost. All three now state those
    allowances.
- **#328's proposal on the tracer's and the presence model's provenance.**
  - It said the tracer's checkpoint "trained on none of them". #326 says only that no fiber-skeletons release is in its
    training data, and that whether its Paris 4 fibers pass through the three Scroll-1 cubes is not public. The
    proposal now says that.
  - It said the presence uses finding 91's model, "checked through the cached inference identity". The identity hashes
    the model files but only keys the cache to the directory as it is now. Nothing compares the hashes with finding
    91's, which are not on record here. The proposal now says that, and `presence.json` records the hashes.
- **#326's quoted villa lines.** The proposal says its test asserts each line it quotes. Two quoted comments from
  `trace.py` were not asserted; the test now asserts both at the pin.
- **Guards no test reached** (#326). The floor's median takes absolute changes; a signed median passed every test.
  A test now pins it.

## Verified, no change needed

- **#325.**
  - On a grace timeout, `stop()` now hands the group to `_kill`, which sends SIGKILL, reaps the leader and waits, for
    at most max(grace, 1) s, until `killpg(group, 0)` finds no member.
  - `stop()`'s other paths are unchanged. No other code kills a supervised group.
  - In 260 runs of the scenario outside pytest, the worker was gone every time `stop()` returned.
- **#327.**
  - The URL field test reads the fenced block under "## URL field". It finds ScrollGT cited once, at `tree/v0.9.0`.
  - The checklist names v0.9.1 as the newest tag by the deadline. The evidence records v0.9.1 as tagged on
    2026-10-27, Pacific.
  - The module gives 39 passed and 4 skipped; the skips need the sibling ScrollGT and inkagree checkouts.
- **#326** (with its review).
  - The launcher's wrap reaches the tracer villa's `main()` builds. `build_tracer` is read there by its module-global
    name, and `trace()` reads `self.p` on every call.
  - The scorer's cube sets equal finding 100's.
  - The ceiling median recomputes from finding 102's record: 0.3144 (0.149–0.479), with 0.0614 within 20 voxels and
    0.1298 within 50.
  - "Two-thirds" is finding 101's report: 2,452 of 7,146 interior confidence stops (34%) are on the reference.
  - The ten unshipped cubes' table matches its evidence, and the counts add up.
  - Its review also ran the chain with stub interpreters: the smoke and the 31 runs in the proposal's order, and
    refusals with the loop running or a script changed. I did not repeat that.
- **#328** (with its review).
  - The finding-100 figures the proposal quotes are bound by its test, which passes against
    `reports/neural_tracer_steep_heading.json`.
  - The two PRs' evidence agrees on the ten cubes, and #326's Dataset003 cubes are #328's three held out from the
    presence model.
  - The chain pins the same villa commit (`39a8cf3a`), checkpoint, tracer Python and `VC_SITE` as the 10-28 re-run,
    and runs the queued patch through villa's own CLI.
- **The new tests.**
  - #326's module gives 29 passed. Of the 7 new cases, 6 fail on #326's code; the seventh pins the floor's absolute
    change, which #326 has right.
  - #328's module gives 21 passed. All 4 new cases fail on #328's code.
  - Each new guard fails a test when removed: 8 mutants in #326's scorer and 7 in #328's.

## Observations for the owner (not changed)

Both studies are proposals, so their design is the owner's call before registration.
- **#326:**
  - **The baseline is not re-scored.** New runs are scored with whatever ScrollGT checkout is beside the repository and
    compared with findings 97 and 98's recorded rows. Only the scoring version is checked.
    - Findings 101 and 102 recorded ScrollGT `6d05d642` and the skeleton hashes.
    - The proposal names ScrollGT's main as `1605fadb`. Its evidence counted with `6d05d64`.
  - **The floor may move nothing.** It changes only `--forward-chunk`, which villa's `TraceParams` comment says
    "bounds memory only: each row's inputs and outputs are unchanged". The retry instead holds a head's row for
    another round, which changes scheduling.
  - **`run.json`'s forward chunk is not checked.** A floor run without `--forward-chunk 64` would equal the baseline,
    giving a floor of 0 and a P2 allowance of 0. That is stricter, not looser.
  - **The manipulation record shows the setting, not a retry.** The wrapper records the field right after setting it.
    Only the unchanged-run check shows whether any retry succeeded.
  - **The summary is stricter than the predictions.** "With no more merges and the same precision" stands for P2,
    which allows the floor's change in merges, and P3, which allows 0.03 lower on 8 of 10 cubes.
  - **The chain.**
    - Its GPU-job scan matches any process whose command line names the launcher, including a parent shell.
    - It takes no lock against a second chain.
- **#328:**
  - **Data identity is not checked.** The evidence records each NML's and image's SHA-256, but `fetch` and `score`
    read whatever single `fibers_*_v*.nml` and image they find.
  - **The manipulation check counts every `no_heading`.** At the pin, villa counts a dot `no_heading` whether its
    heading raised `SeedHeadingError` or failed the 35° test. The patch removes only the second, by design.
    - So an `after` run with `no_heading` above 0 voids the study without showing that the patch failed.
    - It was 0 on all 21 of finding 100's keep runs.
  - **One cube neighbours a finding-100 cube.** `s5_16997_03497_03997_256` is 244 voxels from held-out
    `s5_16997_03997_04497_256` in y and x, at the same z. Padded by 128, their CT contexts overlap; their labels do
    not.
  - **The freeze covers `scripts/` only.** `presence` imports `vesuvius_autoresearch` from the live `src/`.
  - **The chain does not pause the loop.** It refuses while the loop runs. The 10-28 re-run had a wrapper that paused
    and restarted it (`run_villa_seed_heading_rerun_paused.sh`).
  - **Two figures have no source here:** "about 2.5 minutes for a 256³ cube" and "about 0.5 slices a second".
  - **No outcome for a zero baseline.** A cube with no baseline coverage stops `score` with a `ValueError`.
  - **`score` overwrites its result,** as findings 97–102's scorers do. The 10-28 re-run's scorer refuses.

## Verification

- **The changed modules:** lifecycle 38 passed; #326's 29 passed; #328's 21 passed; #327's 39 passed, 4 skipped.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the five changed Python files. Mypy is clean on both
  scripts and over the whole repository (880 files).
- **The standard suite at the baseline** gives the same failures as round #141:
  - the 43 standing failures;
  - the 14 SDK cases that need `s3fs`;
  - the 2 modules that cannot be collected.
- **The 237 test modules outside the suite** give 2,231 passed, 80 skipped, 13 failed and 21 collection errors: the
  same failures as round #141. The two new modules give 50 of the passes.
- **The doc audit's** new unresolved references are ScrollGT's commits named in this record (`1605fadb`, `6d05d64`,
  `6d05d642`), which live in the sibling repository.
  - The 11-02 record's `6d05d642` is listed too; round #141's audit ran before that record was written.
  - One reference resolves that did not before: villa `7154682e1`, in the seed-heading draft.
    - villa is a partial clone. A reviewer's read of a villa commit fetched two packs into it at 16:24–16:25 UTC, and
      that commit is in the first.
    - villa's checkout and `HEAD` are unchanged.
