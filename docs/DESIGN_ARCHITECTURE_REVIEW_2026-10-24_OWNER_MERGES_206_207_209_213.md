# Design and architecture review — the owner's #206, #207, #209 and #213

Date: 2026-10-24. Baseline: `14b9087d` (main after the owner's #206, #207, #209 and #213).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:12, 01:12, 02:12 and 03:12 UTC firings.
- **#206** pre-registers the tracing-context test: both tracers run on finding 95's 24 octants, each as
  a cube in its own right (`scripts/tracing_context.py`, `repro/fibers/run_tracing_context_chain.sh`).
- **#207** is finding 96 (exploratory): villa's neural tracer drops any seed whose 77-voxel CT window
  crosses the edge of its CT, and ScrollGT's protocol gave it the cube alone
  (`scripts/neural_tracer_boundary.py`, `reports/neural_tracer_boundary.md`).
- **#209** pre-registers the follow-up: the tracer on the five Scroll-5 256³ cubes with 128 voxels of
  real CT around each (`scripts/neural_tracer_ct_context.py`,
  `repro/fibers/run_neural_tracer_ct_context_chain.sh`).
- **#213** bumps certifi in `uv.lock` for PYSEC-2026-4320.

## What changed

- **The GPU chains started when `loop_control.py status` could not tell whether the loop was running.**
  - status exits 0 for a running loop, 1 for none, and 2 when it cannot tell, as when the lock is held
    without a valid PID. Its own comment warns that a traceback's exit 1 would read as nothing running.
    `start.sh` and `scripts/loop_watchdog.sh` start only on 1.
  - The fiber chains aborted only on 0. A 2, or an interpreter that is not there (127), let a GPU study
    start beside the loop, which both pre-registrations say the chain refuses.
  - #206's and #209's chains copied the guard from the pitch and seeding chains. **All four now refuse on
    anything but 1**, with their own message for "cannot tell". The pitch report pins its chain at a
    commit, so the change falsifies no record.
  - `tests/test_fiber_chain_loop_guard.py` runs every chain under `repro/` that checks for the loop
    against a stub checkout, answering status with 0, 1, 2 and 127. With the old guard, the eight
    cases for 2 and 127 fail.
- **Finding 96's JSON was bound to its report, but not to the evidence it was computed from.**
  `tests/test_neural_tracer_boundary.py` gains two tests.
  - **Each row is finding 91's record.** The published coverage, predicted over ground-truth length and
    our tracer's coverage are finding 91's committed rows, every share is the row's own count, the split
    matches finding 91's in-sample list, and `by_size` is `summarize()` of the rows.
  - **"Ten of the 13 cubes on which ScrollGT says it trails our tracer are 256³."** The owner's test
    took the 13 as the cubes not on Scroll 3. They are now the cubes where finding 91's merge-penalized
    ERL is below our tracer's. "The other three ... where the deficit is a tolerance-2 result" is now
    checked too: on all three the neural tracer leads at tolerance 4 in finding 94's rows.
- **Both pre-registrations' figures are bound to the evidence, and their thresholds to the scripts.**
  - **#206** (`tests/test_tracing_context.py`):
    - finding 94's median 0.65 of ours (0.43–0.81) on the eight 256³ cubes, with all three 512³ cubes
      leading;
    - finding 95's 19 of 24 and median 1.08×, and 13 of its 19 leads under 1.15×;
    - finding 91's 92 `bounds` stops against 29,146 others;
    - the 7/8 shell;
    - the P2 band and the n < 20 rule.
  - **#209** (`tests/test_neural_tracer_ct_context.py`):
    - finding 96's 19.00-voxel closest seed on all 21 cubes;
    - the 54–70% drop on the 256³ cubes, and the five cubes' 0.571–0.696 and 0.096–0.238;
    - the in-sample 0.53–0.61 against 0.96–1.16, and the 512³ cubes' 0.256–0.357;
    - P3's 0.83, the 512³ minimum rounded;
    - P1's 0.40, P2's 1.3, the 128-voxel margin and the box.
- **#209's frame shift was untested.** `labels_in_cube` shifts the padded run's fibers back by the margin
  before scoring. Dropping the shift, or reversing it, passed every test. A new test places a fiber in the
  padded frame and checks the voxels it marks in the cube's frame.

## Verified, no change needed

- **Finding 96, against villa's source** (the villa checkout in this container):
  - `CT_CONTEXT_RADIUS = 38` (`tracers/shared/ct_structure.py`);
  - `_ct_context` refuses a window that crosses the CT's edge;
  - seed planes lie at global multiples of `--plane-spacing` within each tile, so a 256³ cube's planes
    are 0 and 64, and the one at 0 is outside the seedable core.
- **Finding 96's arithmetic.** The core, 19–108 and 19–236, is villa's window condition. The shares
  0.348 and 0.618 follow from it. "About a third" and "about a tenth" are 1 − 0.669 and 1 − 0.898.
- **#209's design, against villa's source:**
  - **Seeds** are recorded in global trace-grid xyz (`tile_dots`), so `run_record`'s `seeds - lo`
    measures them in the cube's own grid.
  - **The `.afv`** is the trace grid times the grid scale with no offset (`volume_afv.run_fibers`), so its
    fibers are in the padded CT's voxels.
  - **The box** `64,64,64,192,192,192` is one tile with planes at 64 and 128, the cube's 0 and 64, as in
    finding 91.
  - **The padded presence** has only level 1. villa reads the next level only to weight tiles
    (`tile_weights` returns None without it), so the one tile is still traced.
- **#206's design:**
  - stand-in stems are the octants' absolute origins and never name a real cube;
  - the chain freezes every script its scripts import, which the owner's test checks;
  - the smoke runs before any octant.
- **#213:**
  - the locked certifi 2026.10.23 sdist and wheel hashes and sizes are PyPI's;
  - `uv lock --check` passes.

## Observations for the owner (not changed)

- **The October filing draft does not yet carry finding 96.** Its neural-tracer section says the 256³
  deficit's reasons are "only partly measured". Finding 96 attributes a large part of it to ScrollGT's
  protocol. As with #201 for finding 95, folding it in is the owner's call.
- **#206's "Seed planes ... stay the same, by construction"** holds for the planes' positions. Finding 96
  shows that an octant run cannot seed on the planes at its own faces. Finding 96 records this, and the
  registration is frozen.
- **#209's `score` treats a missing `smoke.json` as passing.** Its status can be OK with
  `smoke_identical` null. The chain writes `smoke.json` before any padded run, so only padded cubes traced
  by hand reach this path.
- **Not checkable here:** the certifi advisory itself (osv.dev is blocked), and #209's raw-scan shape and
  exact reproduction of `s5_07997_02997_05497_256` (dl.ash2txt.org is blocked).

## Verification

- **The three owner test files and the new guard test:** 69 passed and 1 skipped. The skip is the villa
  radius check, which needs the owner's villa path; the radius is 38 in this container's villa.
- **Perturbations:** each of 31 fails a test:
  - 22 figures in the two registrations and finding 96's report;
  - four script constants and the frame shift's two mutants;
  - five edits to finding 96's JSON.
- **The guard test** fails on the old guard for exit codes 2 and 127, on all four chains.
- **Ruff** 0.9.10 `check` and `format` are clean on the touched tests and the three owner scripts.
  `bash -n` is clean on the four chains.
- **The ledger and the suite coverage guard:** 53 passed. The new tests exercise report scripts and
  repro chains, not the loop's code, so they sit outside the standard suite; the guard agrees.
- **Doc guards:** 378 passed and 2 skipped on main `14b9087d` and on the branch.
- **Doc audit:** the branch gains no entries.
- **The standard suite** with the locked-package overlay: 2813 passed, 22 skipped and 1 xfailed, as on
  main. The ten failures are main's ten environmental ones: nine need villa files, one is
  `gp_winner`.
- **No independent review this round.** The changes are a two-line guard in four chains, checked by a
  test that fails on the old guard, and bindings checked by perturbation.
