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

- **The tracer's presence level is written atomically.** `make_tracer_presence.write_presence` built `OUT/1` in
  place. The chain (`run_neural_tracer_chain.sh`) skips any cube whose presence level exists. The analysis's
  identity check compares the presence's path, not its content.
  - So a write killed partway left an array whose unwritten chunks read as zero presence: fewer seeds, silently.
  - It is now built beside `OUT` and renamed into place, and a leftover from a killed write is cleared.
  - Test: a write killed after one chunk row leaves no `OUT`, and the rerun writes the full level. It fails on main.

## Verified, no change needed

- **#99, finding 91: the analysis is the registered one, and the report matches its data.**
  - `scripts/neural_tracer_analysis.py` implements the preregistration's predictions, thresholds and decision rule:
    - P1 and P3 at 75%, P2 at 60%, each on at least 6 Scroll-3 cubes;
    - P4 on both held-out Scroll-5 cubes against the tracer's own Scroll-3 median;
    - INCOMPLETE when rows are missing, and IDENTITY_FAILED on any `run.json` difference.
  - Recomputed from `reports/neural_tracer_entrant.json`, every number in `reports/neural_tracer_entrant.md` matches:
    - the prediction counts: 8/8, 8/8, 7/8 with the stated exception, and P4's 0.134 and 0.096 against 0.480;
    - the 21-row table and the three group medians;
    - 11 of 11 in-sample cubes trailing our tracer;
    - the stop-reason totals, with no `outside` stops;
    - the tolerance-4 and precision medians;
    - the zero repeat differences;
    - the coverage gap to connected components, 0.480 against 0.826.
- **#99, the chain resumes safely on the tracer's own output.** villa's `volume_afv.export_afv` writes
  `fibers.writing.afv` and renames it to `fibers.afv` only once complete. So the chain's "a cube with a fibers.afv is
  done" cannot pass an incomplete file, and `afv_to_labels.read_afv` refuses one anyway.
- **#100, the v3 noise probe.**
  - The spread matches the JSON: mean 0.2647, sample SD 0.0025, range 0.0054.
  - σ's 95% interval with 3 degrees of freedom is 0.0014–0.0094. The re-derived tolerances are 0.0059, 0.0033 and
    0.022.
  - Every trial beats the incumbent: 0.012–0.018, which is 4.8–6.9 SDs against the stored 0.249348.
  - None clears the 0.03 promotion bar.
- **#95, the villa pin.** At `ccb431818`, `tifxyz/upsampling.interpolate_at_points` now multiplies nominal
  coordinates by `scale` instead of dividing. Our wrapper reads surfaces through `Tifxyz.__getitem__` and
  `upsample_zyx_grid`, which both pass a scale of (1, 1), so nothing here changes. The restart note's account of the
  bump stands.
- **#98 and #94** are sound:
  - the trial's TMPDIR is a short `mkdtemp`, removed in `finally`;
  - `MPLBACKEND=Agg` is forced in `conftest.py` before matplotlib loads, and subprocesses inherit it.

## Observations for the owner (not changed)

- **The tracer chain's GPU guard does not see the loop.** It aborts if another tracer or a noise probe is running, but
  not if the training loop is. The preregistration says sharing the GPU with the loop needs the owner's OK; finding
  91's runs paused the loop by hand.
- **Absolute paths.** `neural_tracer_analysis.py` and the chain hardcode `/home/jon/...`, as the earlier fiber
  analyses do. A run anywhere else needs the environment overrides the shell scripts take; the Python analysis has
  none.
- **The new tests are outside the curated suite.** `run_validation_tests.py` lists 116 of the 297 test files. #94's,
  #99's and #100's tests are not among them, which follows the list's convention.

## Verification

Environment: CPython 3.10 venv (no GPU visible), pytest, Ruff.

- `tests/test_make_tracer_presence.py`: 9 passed. The new case fails on main: `assert not out.exists()`.
- #99's and #100's tests, with the fix: 46 passed.
  - `test_neural_tracer_analysis`, `test_neural_tracer_entrant_report`, `test_make_tracer_presence`;
  - `test_noise_probe_v3_report`, `test_matplotlib_backend`.
- Standard suite: see the PR.

Not verified: any GPU run, and ScrollGT's data (not here). The tracer's report was checked against its committed
JSON, not re-scored.
