# Design and architecture review — the owner's #338, #339 and #340

Date: 2026-11-05. Baseline: `71045374` (main after #340; #340 merged during the round).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 05:12 UTC firing.
- **#339 re-vendors ScrollGT 0.9.1's fiber scorer.**
  - The scorer's two Euclidean distance transforms now run 64 z planes at a time, with a ceil(tolerance) halo
    (`_distance_blocks`). Its two uses are `_dilate_labels` and the ground-truth-near mask.
  - The scoring version is unchanged.
- **#338 speeds up fragment linking** (`relink_fragments`).
  - A k-d tree finds nearby endpoints. The original distance, angle and cost tests still decide every link.
  - Two correctness fixes come with it: stop reasons for reversed fragments, and input validation.
  - It adds a CPU replay benchmark, its evidence and `docs/FIBER_RELINKING.md`, and it updates the research plan.
- **#340 records the 11-03 GPU window's wrapper and its log** as evidence.
  - Findings 103 and 104 now point to both.
  - It adds the seed-heading draft's check against villa main `2d4067b52`.

This round changes no library code. It adds tests and corrects one line of the research plan. The owner's #341
(fiber detection's boundary halo) merged at 05:46 UTC, while this round was being validated. It touches none of
this round's files, and the next round reviews it.

## What changed

- **Nothing in this repository held the slabs to the whole-volume transform** (`tests/test_fiber_eval_trace.py`).
  - The sync test compares the vendored code with ScrollGT's, which is slabbed too. It skips without a ScrollGT
    checkout beside this one.
  - Two new tests compare the slabs with the transform they replaced:
    - `_dilate_labels` and the near mask against SciPy's whole-volume transform, at six radii;
    - `score_tracing` rows at three tolerances, against a single whole-volume slab.
  - The labels are chosen to reach each part of `_distance_blocks`:
    - ties straddle slab boundaries;
    - the first slab and its halo are empty, with a label in the last slice. On an all-background window, SciPy
      measures to an invented point at (−1, 0, 0). In the first slab that index would wrap to the last slice, and
      the empty-window skip prevents it.
  - I made nine mutants of `_distance_blocks` and its two callers. The new slab tests catch seven:
    - no halo;
    - no halo above the slab;
    - no halo below it;
    - the z indices not shifted back;
    - the core taken from the window's start;
    - the empty-window skip removed;
    - a strict `<` in `_dilate_labels`.
  - **The near mask's strict `<`.** It changes the slab and whole-volume paths alike, so a slab test cannot see it.
    No test in the suite caught it before. A third new test, `test_precision_counts_a_voxel_exactly_at_the_tolerance`,
    now does.
  - **A floor halo instead of ceil** is an equivalent mutant. Voxel offsets are integers, so a neighbour within radius
    r is at most floor(r) slices away.
- **The research plan counted finding 103 among those that close the refit retry** (`docs/research_plan.md`).
  - The plan said "Findings 101–104 in the strategy close the existing refit retry". Finding 103 is the seed-heading
    confirmation; 101, 102 and 104 are the confidence-stop line. The line now names 101, 102 and 104.
- **The relink doc's figures had no test.** The new `tests/test_fiber_relink_record.py` is listed in the suite. It
  binds:
  - `docs/FIBER_RELINKING.md`'s timing table to `reports/evidence/fiber_relink_cpu_2026-11-05.json`;
  - the doc's command, inputs and settings to the record and to the harness;
  - the plan's line to the strategy.
  
  Nine mutants of the doc and the plan all fail it.

## Verified, no change needed

- **The slabs are exact.**
  - In 300 random volumes, slab `_dilate_labels` and the near mask equal the whole-volume transform exactly. The
    volumes were up to 200 slices deep, at four densities and ten radii from 0.5 to 70.
  - So do 972 cases built to tie across slab boundaries: SciPy's tie-break among equidistant labels does not change
    with the window.
  - The proof is short. A core voxel's nearest label within r lies within ceil(r) slices, so it is in the window.
    Distances beyond r are never used.
- **The indexed linker is the exhaustive one.**
  - A cube of half-side `max_gap` contains the Euclidean ball. In floating point, `norm(d)` is never below
    max|dᵢ|, so no pair the old test accepts is missed.
  - Candidates keep the old (a, b) order before the stable sort, so ties resolve as before.
  - In 400 random fragment sets (897 links), the indexed and exhaustive runs give identical fibers, responses and
    stop reasons. The sets were on and off the voxel grid, with gaps including √2 and √3.
- **The stop-reason fix.** A chain that starts or ends on a reversed fragment now takes that fragment's opposite
  stop reason. Nothing outside `trace.py` reads `stop_start` or `stop_end`, so no recorded result changes.
- **The new validation breaks no caller.**
  - The tracer already drops fibers under two points.
  - A one-point fragment already raised `IndexError` in `_endpoint_tangents`, except in a single-fragment result,
    which the old code returned unchecked.
  - `bench_cli` caps `--relink-angle` at 175, so its tangent limit stays within 180.
- **The relink record names its sources.**
  - Its baseline source hash is `trace.py` at `cd3bf6da`, and its candidate hash is `trace.py` on main.
  - Its harness hash is the committed `benchmark_relink.py`.
  - Its medians and speedups follow from its timings.

- **#340's wrapper and log support what findings 103 and 104 say about the run.**
  - The wrapper refuses to start unless its checkout is the clean registration commit, f7145c5d.
  - The log shows the steps in order:
    - `stop.sh rc=0`, then `loop_control status rc=1` (nothing running), with 0 MiB of GPU memory in use;
    - both chains from f7145c5d, at villa `39a8cf3a1` and `ccb431818`;
    - every cube's `DONE`;
    - both `CHAIN_COMPLETE` lines and `start.sh rc=0`.
  - Each report's trace window is its chain's start and end: 12:32–13:15 and 13:15–14:38 PST.
  - The seed-heading chain logs no `SMOKE_OK` by design: it goes on past the smoke only when `smoke.json` says
    identical.
  - The 12:32–12:39 gap before its smoke is the chain's presence step. That is consistent with round #146's
    statement that `presence` ran from the registration commit.
  - The skipped villa-main re-check (no `vc_object_store` built for `deb1b6953`) is the one finding 103 reports.
  - #340's three tests bind these facts, and they pass.
  - This resolves #330's observation, which round #146 repeated, that no loop-pausing wrapper was committed. The
    wrapper is committed as a record, not as a runnable script.

## Observations for the owner (not changed)

- **The relink record's `resampler_source_sha256` is now stale in form only.** It hashes the whole of
  `eval_trace.py` as it stood before #339. #339 changed that file, but `_resample_fiber`, the function the harness
  uses, is unchanged. A re-run of the harness on main records a different hash for the same resampler.
- **The scorer sync test needs `../scrollgt`.** In a checkout without it, #339's verbatim claim and its slab-depth
  test are unchecked. The new tests check exactness, not identity with ScrollGT.
- **The research plan's Villa claims were not checked.** These are the November rollover, the deadline, the prize
  amounts and the issue and PR statuses. They need Villa's GitHub, which this review does not read.
- **#340's villa-main claims were not checked**, for the same reason: the patch no longer applying at `2d4067b52`,
  `ct_seed_heading`'s four arguments and the `GaussianBlur` change.

## Verification

- **The four touched modules:** `test_fiber_eval_trace`, `test_fiber_relink`, `test_fiber_relink_record` and
  `test_fiber_scoring_matches_scrollgt`. They give 72 passed and 15 skipped; the 15 are the sync tests, which have
  no ScrollGT checkout here.
- **Ruff and mypy.** Ruff 0.9.10 `check` and `format` are clean on the changed files. Mypy is clean over the whole
  repository: 886 files.
- **The standard suite** gives round #146's 70 failing ids, both before and after merging #340:
  - the 43 standing failures;
  - the 25 SDK cases;
  - the 2 collection errors.
- **The 239 test modules outside the suite** give 2,252 passed, 82 skipped, 13 failed and 21 errors. These are
  round #146's failures.
  - The 13 fewer passes are `test_fiber_relink.py`'s 13 tests, which #338 moved into the suite.
  - The 2 extra skips are #339's new sync-test cases.
  - #340 adds a 240th module, `test_gpu_window_2026_11_03_record.py`. It passes, as do the three report modules it
    edits around.
  - `test_live_documents_stay_clean` fails as before. It lists only villa paths that this checkout's partial villa
    clone lacks.
- **The doc audit**, run alone, adds seven unresolved commit references. All seven are commits of other
  repositories that this checkout's clones do not hold:
  - villa `2d4067b52`, `baf5e605b`, `9c343a1` and `deb1b6953`;
  - ScrollGT `1605fadb`.
  
  The audit never fetches. Three of the seven are this round's and #146's records quoting the owner's references.
