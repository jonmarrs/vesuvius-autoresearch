# Design and architecture review — the owner's merges of 2026-10-16/17

Date: 2026-10-17. Baseline: `b75a1aa3` (main after #103). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the six PRs the owner merged since the last review of their work:
- #94, Agg forced for the suite;
- #95, the villa pin `9afddaf0f` → `ccb431818`;
- #96, the October filing draft after villa #1928 closed;
- #98, a short private TMPDIR for noise-probe trials;
- #99, villa's neural fiber tracer as a ScrollGT entrant (finding 91);
- #100, the protocol-v3 noise probe.

Each was read for correctness, and each committed result was checked against its own data.

## What changed

- **The tracer's presence level is written atomically, and checked when reused.**
  - `make_tracer_presence.write_presence` built `OUT/1` in place. The chain (`run_neural_tracer_chain.sh`) reuses the
    presence level of any cube whose level exists. The analysis's identity check compares the presence's path, not
    its content.
  - So a write killed partway left an array whose missing chunks read as zero presence: fewer seeds, silently.
  - Now each writer builds the level in a directory of its own beside `OUT` and renames it into place. Two writers
    on one cube cannot clear each other's work: the one that finishes second finds `OUT` written and refuses. A
    writer that fails removes its own directory.
  - Every chunk is written, all-zero ones included. `level_complete` checks a level has all its chunks, and the
    chain refuses a reused level that does not ("FAILED … presence incomplete"). That also catches a partial level
    the in-place writer left before this change.
  - Tests:
    - a write killed partway leaves no `OUT`;
    - two interleaved writers leave one whole level;
    - a level missing a chunk is not complete, while an all-zero one is.

    The first two fail on main.
- **The chain freezes its scripts once per study.** It copied the analysis, the presence maker and the rasteriser into
  the run directory on every launch, resumes included. So a resume after the repository moved swapped them mid-study,
  and only `CHAIN_START` logged the commit. The first launch now copies them; a later one refuses if the repository's
  copy differs.
- **Finding 91's "0 `outside` stops" rested on a test that could not fail.**
  - villa records the outside-the-scan stop as `outside_ct` (`tracing/volume.py`). The test summed a key villa never
    writes, `outside`. It now sums `outside_ct`, and checks the recorded keys are among the five villa writes.
    `outside_ct` is in fact 0.
  - The report also said the zero voxels "never stopped a trace". The `.afv` records stop reasons only for written
    fibers: two each, so 29,238 for 14,619. A trace dropped as short or as a duplicate leaves none there. The report
    now says no written fiber ended on CT 0, and that each run's `tiles.jsonl` (not in this repository) counts
    `stop_outside_ct` for every trace.

## Verified, no change needed

- **#99, finding 91: the analysis is the registered one, and the report matches its data.**
  - `scripts/neural_tracer_analysis.py` implements the preregistration's predictions, thresholds and decision rule:
    - P1 and P3 at 75%, P2 at 60%, each on at least 6 Scroll-3 cubes (6 with a generator row, for P1);
    - P4 on both held-out Scroll-5 cubes against the tracer's own Scroll-3 median;
    - INCOMPLETE below those counts or with a held-out Scroll-5 row missing; a missing in-sample row stays OK;
    - IDENTITY_FAILED on any `run.json` difference, and a refusal of any ScrollGT scoring version but 3.
  - `SETTINGS` equals villa's defaults for every argument that changes the fibers.
  - Recomputed from `reports/neural_tracer_entrant.json`, every other number in `reports/neural_tracer_entrant.md`
    matches:
    - the prediction counts: 8/8, 8/8, 7/8 with the stated exception, and P4's 0.134 and 0.096 against 0.480;
    - the 21-row table and the three group medians;
    - 11 of 11 in-sample cubes trailing our tracer;
    - the stop-reason totals;
    - the tolerance-4 and precision medians;
    - the zero repeat differences;
    - the coverage gap to connected components, 0.480 against 0.826.
- **#99, the chain resumes safely on the tracer's own output.** villa's `volume_afv.export_afv` writes
  `fibers.writing.afv` and renames it to `fibers.afv` once complete, after every tile. So the chain's "a cube with a
  fibers.afv is done" cannot pass an incomplete file, and `afv_to_labels.read_afv` refuses one anyway.
- **#100, the v3 noise probe.**
  - The spread matches the JSON: mean 0.2647, sample SD 0.0025, range 0.0054.
  - σ's 95% interval with 3 degrees of freedom is 0.0014–0.0094. The re-derived tolerances are 0.0059, 0.0033 and
    0.022.
  - Every trial beats the incumbent: 0.012–0.018, which is 4.8–6.9 SDs against the stored 0.249348.
  - None clears the 0.03 promotion bar.
- **#95, the villa pin.**
  - At `ccb431818`, `tifxyz/upsampling.interpolate_at_points` multiplies nominal coordinates by `scale` instead of
    dividing.
  - Our wrapper reads surfaces only through `Tifxyz.__getitem__`. That call, and every other caller in villa, passes
    a scale of (1, 1), so nothing here changes.
  - The restart note's account of the bump stands.
- **#98, #94 and #96** are sound:
  - #98: the trial's TMPDIR is a `mkdtemp`, removed in `finally`;
  - #94: `MPLBACKEND=Agg` is forced in `conftest.py` before matplotlib loads, and subprocesses inherit it;
  - #96: the draft drops the closed villa #1928 from its URL field and says why.

## Observations for the owner (not changed)

- **Finding 91's own presence levels are not checked here.** They were written by the in-place writer. To check that
  none was left partial (the chain would now refuse it), run from the repository root:

  ```sh
  .venv/bin/python -c "import glob, sys; sys.path.insert(0, 'scripts'); import make_tracer_presence as m; print([p for p in glob.glob(sys.argv[1] + '/*_presence.zarr/1') if not m.level_complete(p)])" "$T/presence"
  ```

  `$T` is the chain's tracer directory. An empty list means all are whole.
- **The tracer chain's GPU guard does not see the loop.** It aborts if another tracer or a noise probe is running, but
  not if the training loop is. The preregistration says sharing the GPU with the loop needs the owner's OK; finding
  91's runs paused the loop by hand. It has no lock against a second chain either. The presence writer is now safe
  under one, but two tracers on one cube are not.
- **#98's TMPDIR is short only if the caller's is.** `mkdtemp` without `dir=` honours the parent's `TMPDIR`. The
  socket path is about len(TMPDIR) + 50 bytes, so a parent `TMPDIR` over about 55 characters would bring the
  "AF_UNIX path too long" failure back.
- **Absolute paths.** `neural_tracer_analysis.py` and the chain hardcode `/home/jon/...`, as the earlier fiber
  analyses do. A run anywhere else needs the environment overrides the shell scripts take; the Python analysis has
  none.
- **The new tests are outside the curated suite.** `run_validation_tests.py` lists 116 of the 294 `test_*.py` files.
  #94's, #99's and #100's tests are not among them, which follows the list's convention.

## Verification

Environment: CPython 3.10 venv (no GPU visible), zarr 2.18.3, pytest, Ruff.

- `tests/test_make_tracer_presence.py`: 11 passed. On main:
  - the killed-write case fails with `assert not out.exists()`;
  - the two-writer case fails, because the second writer's error is not the refusal;
  - the completeness case fails, as `level_complete` does not exist there.
- The six test files of #94, #98, #99 and #100, with these changes: 107 passed.
- `tests/test_neural_tracer_entrant_report.py`: 7 passed, with the stop-reason keys pinned.
- The standard suite: see the PR.

Not verified: any GPU run, ScrollGT's data, and finding 91's run directory (none here). The tracer's report was
checked against its committed JSON, not re-scored.
