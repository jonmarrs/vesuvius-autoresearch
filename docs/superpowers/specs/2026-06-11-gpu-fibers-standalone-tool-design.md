# GPU-Fibers Standalone Tool — Design

**Date:** 2026-06-11
**Status:** approved (pending spec review)
**Goal:** Vendor the validated GPU fiber/ridge/vesselness detection into our own repo as a clean, tested, CLI-runnable package — and repoint the training loader to it, fixing the silent zero-ridges bug. Third Tier-1 deliverable of the June plan.

## Context

The validated fiber-detection code — a closed-form symmetric-3×3 eigensolver (Cardano) that avoids the cuSolver `eigvalsh` failure, per-array backend dispatch (`get_backend`), tiled/halo execution, and a normalize parity fix — exists **only in the fork branch `sprint033-fibers-gpu`** (proposed as villa PR #1033, closed without review). Our autoresearch repo does not contain it; instead `vesuvius_loader.py` imports the **broken upstream clone `tools.py`** for ridge detection.

**Active bug (confirmed empirically):** with `use_ridges=true` (current config), the ridge feature channel is **silently all-zeros**. Both fallbacks fail on the broken clone: the GPU path raises `ImportError: libcusolver.so.11` (the cuSolver bug), and the CPU path raises `TypeError: Argument 'b' has incorrect type (expected cupy…)` (the same numpy-under-cupy-global-backend bug as the Frangi fiber-target bug). The loader catches both and substitutes zeros. So the model trains on a useless second input channel. This is the second silent-zeros bug from depending on the broken clone (Frangi was the first).

Vendoring our validated code fixes the bug and gives us a standalone, prize-worthy tool — completing the decoupling from the closed PR.

## Design

A self-contained package `src/vesuvius_autoresearch/fibers/`, the loader repointed to it.

### Components

1. **`src/vesuvius_autoresearch/fibers/detection.py`** — the vendored core, copied verbatim from `sprint033-fibers-gpu:foundation/datasets/fibers-dataset/tools.py`, keeping only the fiber-detection functions:
   - helpers: `get_backend`, `divide_nonzero`, `normalize`
   - core: `hessian`, `compute_eigenvalues_3x3_batch`
   - detectors: `detect_ridges`, `detect_vesselness`
   - tiled: `_smoothed_global_range`, `_detect_tiled`, `detect_ridges_tiled`, `detect_vesselness_tiled`
   - Drop the unrelated helpers (`nlm`, `nms_3d`, `ms_3d`, `denoise_3d`, `adjust_contrast`, `proximity_boolean_filter`, `detect_edges`) — YAGNI.
   - `cupy` import stays optional (try/except); numpy is the always-available backend.

2. **`src/vesuvius_autoresearch/fibers/__init__.py`** — public API re-export and `__all__`: `detect_ridges`, `detect_vesselness`, `detect_ridges_tiled`, `detect_vesselness_tiled`, `compute_eigenvalues_3x3_batch`.

3. **`src/vesuvius_autoresearch/fibers/cli.py`** — `python -m vesuvius_autoresearch.fibers.cli --input vol.npy --filter {vesselness,ridges} --output out.npy [--tiled] [--block-size N] [--halo N] [--preview out.png]`. Loads a `.npy` CT volume `[Z,H,W]`, runs the chosen detector (GPU via cupy if available and `cupy.asarray`, else numpy), saves the result `.npy`, and optionally a z-mean preview PNG. Prints shape, backend, and wall time.

4. **`tests/test_fibers.py`** — port the 4 parity tests from the branch: eigensolver vs `numpy.linalg.eigvalsh`; CPU↔GPU vesselness parity; tiled-vs-dense parity for vesselness and ridges. GPU-only tests use `pytest.mark.skipif(not HAS_CUPY)`; the eigensolver and tiled-vs-dense tests run on CPU/numpy and always execute.

5. **Loader fix — `src/vesuvius_autoresearch/core/vesuvius_loader.py`** (LOOP-CRITICAL): replace `import tools as fiber_tools` (line 19, the broken clone) with `from vesuvius_autoresearch.fibers import detect_ridges`. Simplify the ridge block (lines ~174–203): the vendored `detect_ridges` works on both numpy and cupy via `get_backend`, so try a cupy GPU pass if available, else a numpy CPU pass — both now produce real ridges (no zeros). Keep the zero-ridge fallback only as a true last resort for unexpected errors, with a warning.
   - The Frangi fiber-target path already uses skimage (working) and is **left unchanged** — out of scope to re-churn it.

6. **Docs** — `docs/FIBER_DETECTION.md` (what it does, the cuSolver problem it solves, the 14–94× / tiled-512³ numbers, CLI usage, link to `reports/fibers_gpu_validation_2026-06.md`) + a README pointer.

### Data flow

`vesuvius_loader.__getitem__` (ridge channel) → `detect_ridges(ct, sigma)` from the vendored package → real ridge map (CPU or GPU). External users / the CLI call the same `detect_*` functions directly on a numpy or cupy array.

## Parallel-safety & risk

- The package, CLI, tests, and docs are self-contained → **parallel-safe** while the loop runs.
- Only the loader edit is loop-critical: **pause loop, repoint, verify the ridge channel is now non-zero, restart** (per [[autoresearch-loop-autocommits]]).
- **Behavioral change:** the ridge input channel goes from all-zeros to real ridge values → models train on genuinely different input. The bandit re-learns from there; note it honestly (don't compare pre/post-fix cycles as if the input were constant).

## Verification

- `pytest tests/test_fibers.py` passes (eigensolver parity ~1e-5 float32 / ~3e-10 float64; tiled-vs-dense to 1e-4).
- CLI round-trip: `--input` a small random `.npy`, `--filter vesselness`, `--output` → finite non-zero result; `--tiled` path agrees with dense on a halo-covered volume.
- Loader: instantiate `FastVesuviusVolume(..., use_ridges=True)`, fetch a patch, assert the ridge channel is **non-zero and finite** (the bug fix).
- `train.py --smoke` passes; a `--test` run with `use_ridges=true` shows no NaN/instability and no "ridge_fallback … using zero ridges" warning.
- Loop restarted, 0 import crashes, a cycle running.
- Diff limited to: `src/vesuvius_autoresearch/fibers/` (new), `src/vesuvius_autoresearch/core/vesuvius_loader.py`, `tests/test_fibers.py`, `docs/FIBER_DETECTION.md`, `README.md`.

## Out of scope

- Re-pointing the Frangi fiber-target path off skimage (already working).
- An ablation of real-vs-zero ridges (deferred; uses GPU).
- The `bench_tools.py` harness (the validation numbers already live in `reports/fibers_gpu_validation_2026-06.md`).
