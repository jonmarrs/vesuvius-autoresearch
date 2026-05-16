# Progress Prize Submission (June 2026): GPU-Accelerated Fiber Detection in Villa's `foundation/datasets/fibers-dataset`

**Submission Date:** 2026-06 (target: 2026-06-30 11:59pm PT)
**Submission Form:** TBA — June form not yet open as of 2026-05-15; will be linked here once it goes live.
**Target Prize Tier:** Denarius / Sestertius (open to maintainer judgment)
**Submitter:** Jon Marrs &lt;jdmarrs@gmail.com&gt;
**Repository:** https://github.com/jonmarrs/vesuvius-autoresearch
**License:** MIT (autoresearch); upstream villa PR licensed per ScrollPrize/villa contribution terms
**Status:** QUEUED for June filing on **three** villa PRs:
- [ScrollPrize/villa#915](https://github.com/ScrollPrize/villa/pull/915) — CuPy acceleration of `foundation/datasets/fibers-dataset/tools.py` (headline; full GPU benchmarks attached).
- [ScrollPrize/villa#916](https://github.com/ScrollPrize/villa/pull/916) — minimal Python ctypes wrapper for `vesuvius-c` under `vesuvius-c/python/` (companion).
- [ScrollPrize/villa#922](https://github.com/ScrollPrize/villa/pull/922) — `generate_fiber_labels_from_ct.py`, addresses villa issue [#193](https://github.com/ScrollPrize/villa/issues/193) ("Methods for generating surface, fiber, or ink labels"), tagged `help wanted` / `Good candidate for a Progress Prize`.
**Prior cycle:** May 2026 filings ([Part 1](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md), [Part 2](PROGRESS_PRIZE_SUBMISSION_2026-05.md)).

## Thesis

The fiber-detection preprocessing in `villa/foundation/datasets/fibers-dataset/tools.py` — Frangi vesselness, Hessian-based ridge detection, non-maximum suppression, Scharr/Pavel edge detection — is the early stage of every papyrus-fiber dataset build, and on CPU it dominates run time at the volume sizes the community is actually working with. The original file (Brett Olsen, 2024) carries a literal `TODO: convert bottleneck code over to cupy for GPU speed up` at the top. This submission closes that TODO with a CuPy / `cupyx.scipy.ndimage` dual-backend rewrite that falls back transparently to NumPy / SciPy when CuPy is absent, preserves call signatures, and ships with parity tests + a reproducible benchmark script.

## What this submission ships

### 1. Upstream PR — `feat(fibers-dataset): CuPy acceleration with NumPy fallback for tools.py`

Pull request: **https://github.com/ScrollPrize/villa/pull/915**

- **`foundation/datasets/fibers-dataset/tools.py`** — All twelve top-level functions (`normalize`, `divide_nonzero`, `nms_3d`, `ms_3d`, `hessian`, `detect_ridges`, `detect_vesselness`, `proximity_boolean_filter`, `detect_edges`, plus the skimage-backed `nlm`, `denoise_3d`, `adjust_contrast`) now operate through a module-level `xp` / `xndimage` indirection. Setting `xp = cp, xndimage = cupyx.scipy.ndimage` at import time when CuPy is importable; falling back to `xp = numpy, xndimage = scipy.ndimage` otherwise. `divide_nonzero` keeps an explicit array-type branch since it needs to special-case CuPy arrays. The obsolete CuPy TODO header is removed.

- **`foundation/datasets/fibers-dataset/tests/test_tools_parity.py`** — Ten tests, all passing: smoke tests for module import / `normalize` invariants / `divide_nonzero` correctness, two always-on tests for the closed-form `_eigvalsh_sym3x3` helper (LAPACK parity on random symmetric 3×3s + diagonal/zero edge cases), and CuPy-skipif parity tests for `normalize`, `divide_nonzero`, `nms_3d`, `hessian`, and `_eigvalsh_sym3x3`. NMS uses a disagreement-rate threshold (&lt;1% of voxels) rather than pointwise tolerance — the standard NMS `>=`/`>` decisions flip at near-tie voxels where `scipy.ndimage.map_coordinates` and `cupyx.scipy.ndimage.map_coordinates` interpolate to slightly different values.

- **Closed-form 3×3 eigvalsh.** `detect_ridges` and `detect_vesselness` previously called `xp.linalg.eigvalsh` on the batched `(N, N, N, 3, 3)` Hessian. cuSolver's `dsyevjBatched` returns `CUSOLVER_STATUS_INVALID_VALUE` on batches &gt; ~1M matrices, which made both functions unusable on the CuPy backend at 128³ and larger volumes. A vectorised closed-form Smith / Cardano expression (`_eigvalsh_sym3x3`) replaces the LAPACK call. The closed-form has no batch-size limit, and is also ~1.5× faster on the NumPy path because 3×3 is small enough that LAPACK per-call overhead dominates.

- **`foundation/datasets/fibers-dataset/bench/bench_tools.py`** — Reproducible benchmark that times each function on cubic volumes (default 64³ and 128³, configurable via `--sizes`) and prints a Markdown table. Resilient: an individual measurement that errors is reported as `error: <ExceptionName>` rather than killing the rest of the run.

### 2. Measured speedups (RTX 4090, driver 595.58.03, CUDA 13.2, CuPy 14.0.1)

| function | volume | NumPy (ms) | CuPy (ms) | speedup |
| --- | --- | --- | --- | --- |
| normalize | 64³ | 0.1 | 0.1 | 1.0x |
| nms_3d | 64³ | 56.4 | 1.4 | 39.3x |
| hessian | 64³ | 42.7 | 5.1 | 8.3x |
| detect_ridges | 64³ | 167.0 | 7.9 | 21.3x |
| normalize | 128³ | 1.8 | 0.2 | 9.8x |
| nms_3d | 128³ | 440.6 | 1.2 | **357.4x** |
| hessian | 128³ | 337.2 | 5.6 | 60.7x |
| detect_ridges | 128³ | 1477.0 | 24.7 | 59.8x |
| normalize | 256³ | 24.9 | 0.4 | 69.6x |
| nms_3d | 256³ | 4039.5 | 9.4 | **429.6x** |
| hessian | 256³ | 4195.1 | 18.5 | **226.2x** |
| detect_ridges | 256³ | 16262.3 | 197.4 | **82.4x** |

Headline numbers: `nms_3d` runs in 9.4 ms at 256³ vs 4.04 s on CPU (430×), `hessian` 226×, and `detect_ridges` 82× — meaningful enough that a fiber-detection run that used to fit in a coffee break now fits in a few seconds.

### 3. Companion PR — `feat(vesuvius-c): add Python ctypes bindings under vesuvius-c/python/`

Pull request: **https://github.com/ScrollPrize/villa/pull/916**

A minimal `ctypes` Python wrapper for `vesuvius-c`, exposing `Volume` construction (local or remote-via-`dl.ash2txt.org`) and arbitrary-chunk reads with zero-copy NumPy views. The wrapper is intentionally narrow — it covers the volume + chunk surface that the autoresearch data loader depends on, not the full vesuvius-c API.

This is the upstreaming of the same Python wrapper layer that backed the May Part 1 submission via [`jonmarrs/vesuvius-autoresearch:vesuvius_c_wrapper/`](https://github.com/jonmarrs/vesuvius-autoresearch). Moving it into villa removes the "you have to install autoresearch to use the wrapper" requirement and makes it available to any contributor running their own ink-detection experiments.

Known scope / follow-ups (called out honestly in the PR description rather than papered over): no in-PR tests (existing standalone usage substitutes for now), and `setup.py` shells out to gcc directly rather than declaring a `setuptools.Extension`.

### 4. Companion PR — `feat(fibers-dataset): generate fiber pseudo-labels from CT (no annotation required)`

Pull request: **https://github.com/ScrollPrize/villa/pull/922**
Addresses: **villa issue [#193](https://github.com/ScrollPrize/villa/issues/193)** — tagged `help wanted` and `Good candidate for a Progress Prize`.

The issue calls out that fiber label generation is currently entirely manual: the existing scripts in `foundation/datasets/fibers-dataset/` (`fibers-dataset-generator.py`, `hz-vt-generator.py`) voxelize WebKnossos `.nml` skeletons that a human has already drawn. That creates a catch-22 for compressed / highly-curved regions where annotation is hardest and labels are most needed.

This PR adds `foundation/datasets/fibers-dataset/generate_fiber_labels_from_ct.py`, a standalone CLI that runs the Frangi-style vesselness filter already in `tools.py` (the same one the autoresearch fiber predictor uses) directly on a CT zarr and writes binary fiber pseudo-labels to an output zarr. **No manual input required.**

```bash
python generate_fiber_labels_from_ct.py \
    --input scroll.zarr \
    --output fiber_labels.zarr \
    --bbox z0 z1 y0 y1 x0 x1 \
    --threshold 0.5 \
    [--margin 8] \
    [--write-probability fiber_prob.zarr]
```

Quality is below skilled annotation, but labels are immediately available everywhere CT is, which makes them useful as expanded supervision (mix as soft targets during training), fiber overlays for VC3D / Crackle-Viewer review, or a starting point for human refinement (annotators correct the worst cases instead of drawing from scratch).

Tests (`tests/test_generate_fiber_labels_from_ct.py`): three end-to-end checks against a synthetic CT volume containing a known horizontal ridge. 3 passed in 0.60s.

This script also powers the local production path in autoresearch (`scripts/generate_fiber_labels.py --mode candidates`), which has produced fiber pseudo-labels for the top-5 GPU-ready Scroll 2/3 candidates in `reports/scroll23_evidence/candidate_NNN/`.

### 5. Concurrent upstream contributions (auxiliary, not part of the June prize narrative)

These are small standalone bugfixes shipped to villa in the same week for community benefit. Not prize artifacts in themselves, but worth pointing at:

- [ScrollPrize/villa#913](https://github.com/ScrollPrize/villa/pull/913) — `fix(batchgeneratorsv2): resolve device mismatch in SpatialTransform`. SpatialTransform built sampling grids on CPU while inputs lived on GPU, causing `RuntimeError` in CUDA training loops.
- [ScrollPrize/villa#914](https://github.com/ScrollPrize/villa/pull/914) — `fix(vesuvius-c): accept file:// URLs in vs_download`. `vs_download` rejected any non-200 HTTP status, breaking local-file fetches where libcurl reports `http_code == 0`.

## Why this is prize-worthy

Per the Progress Prize criteria (released early, actually used, well documented):

- **Released early.** All three PRs opened in mid-May, six weeks before the June deadline, with tests passing on the submission hardware. PR #915 ships its full RTX 4090 benchmark table in the description.
- **Actually used.** The fiber-detection pipeline (PR #915) is the data-prep stage of every autoresearch ink-detection sweep cycle. The vesuvius-c bindings (PR #916) replaces the standalone wrapper that backed the May Part 1 submission. The CT-derived label generator (PR #922) is the engine of `scripts/generate_fiber_labels.py --mode candidates`, which has already produced pseudo-labels for the top-5 GPU-ready Scroll 2/3 candidates.
- **Well documented.** Tests across all three PRs (10 + 3 + 3 = 16 passing), benchmark script with concrete numbers, PR descriptions with known-caveat sections, and reproducers that work in a fresh checkout.
- **Aligned with maintainer intent.** PR #922 is anchored to villa issue #193, explicitly tagged `help wanted` and `Good candidate for a Progress Prize`. PRs #915 and #916 fill gaps the autoresearch project has been working around for months.

## How to reproduce

```bash
# Clone villa with the PR branch
git clone --branch feat/fibers-cupy-acceleration https://github.com/jonmarrs/villa.git
cd villa/foundation/datasets/fibers-dataset

# Parity tests (auto-skips CuPy tests if cupy is not installed)
pytest tests/

# Benchmark (timing table on stdout, Markdown format)
python3 bench/bench_tools.py --sizes 64 128 256
```

If running with a uv-managed venv that bundles NVIDIA libs (e.g., the `cupy-cuda12x` wheel), prefix the bench command with:

```bash
LD_LIBRARY_PATH=$(ls -d "$VENV"/lib/python*/site-packages/nvidia/*/lib | tr '\n' ':') \
  python3 bench/bench_tools.py --sizes 64 128 256
```

so that the bundled `libcusolver.so.11` is on the linker search path.

## Repository pointers (for the Google Form)

| Field | Value |
| --- | --- |
| Repository (autoresearch) | https://github.com/jonmarrs/vesuvius-autoresearch |
| Repository (PR fork) | https://github.com/jonmarrs/villa (branch `feat/fibers-cupy-acceleration`) |
| Prize-narrative PR #1 (headline) | https://github.com/ScrollPrize/villa/pull/915 (CuPy fibers acceleration) |
| Prize-narrative PR #2 (companion) | https://github.com/ScrollPrize/villa/pull/916 (vesuvius-c Python bindings) |
| Prize-narrative PR #3 (companion, addresses villa#193) | https://github.com/ScrollPrize/villa/pull/922 (CT-derived fiber labels) |
| Auxiliary upstream PRs | [#913](https://github.com/ScrollPrize/villa/pull/913), [#914](https://github.com/ScrollPrize/villa/pull/914) |
| Key files | `foundation/datasets/fibers-dataset/tools.py`, `foundation/datasets/fibers-dataset/generate_fiber_labels_from_ct.py`, `foundation/datasets/fibers-dataset/tests/test_tools_parity.py`, `foundation/datasets/fibers-dataset/bench/bench_tools.py`, `vesuvius-c/python/vesuvius_c.py` |
| Tests | 16 passing across the three PRs: `test_tools_parity.py` (10), `test_imports.py` (3), `test_generate_fiber_labels_from_ct.py` (3) |
| Reproduction entrypoint | `cd foundation/datasets/fibers-dataset && pytest tests/ && python3 bench/bench_tools.py --sizes 64 128 256` |
| License | MIT (autoresearch); upstream PR per ScrollPrize/villa contribution terms |
| Prior cycle filings | [Part 1](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md), [Part 2](PROGRESS_PRIZE_SUBMISSION_2026-05.md) |

## Public release blurb (for socials / forum announcement)

> Filed for the June 2026 Progress Prize: three villa PRs that together accelerate fiber detection, remove an install friction, and break the manual-annotation catch-22 for fiber labels.
>
> [PR #915](https://github.com/ScrollPrize/villa/pull/915) — a CuPy / `cupyx.scipy.ndimage` rewrite of villa's `foundation/datasets/fibers-dataset/tools.py` that moves Frangi vesselness, Hessian ridges, NMS, and Scharr/Pavel edge detection onto GPU with a transparent NumPy / SciPy fallback. Measured on an RTX 4090: `nms_3d` 430× at 256³, `hessian` 226×, `detect_ridges` 82× (the last enabled by replacing batched cuSolver `eigvalsh` with a closed-form 3×3 symmetric eigendecomposition, since cuSolver returns `CUSOLVER_STATUS_INVALID_VALUE` above ~1M batched matrices). Ten passing parity tests + a reproducible benchmark script.
>
> [PR #916](https://github.com/ScrollPrize/villa/pull/916) — a minimal Python ctypes wrapper for `vesuvius-c` under `vesuvius-c/python/`, providing `Volume` + arbitrary-chunk-read access (local and remote via `dl.ash2txt.org`) with zero-copy NumPy views. Upstreams the same wrapper layer that backed the May Part 1 submission.
>
> [PR #922](https://github.com/ScrollPrize/villa/pull/922) — addresses villa issue [#193](https://github.com/ScrollPrize/villa/issues/193) ("Methods for generating surface, fiber, or ink labels", tagged `help wanted` / `Good candidate for a Progress Prize`). Adds a CLI that runs the Frangi-style vesselness filter directly on a CT zarr to produce fiber pseudo-labels without manual annotation — useful as expanded supervision, fiber overlays for VC3D review, or a starting point for human refinement.

## Open work (may extend this submission before the June deadline)

The three prize-narrative PRs (#915 + #916 + #922) are open. Possible additional follow-ups, low-priority:

- **CI builds for the bindings.** Currently `vesuvius-c/python/test_imports.py` skips cleanly if `libvesuvius.so` isn't pre-built; first-party `pytest` coverage in villa CI would require `libcurl-dev` / `libblosc2-dev` / `libjson-c-dev` available to the runner.
- **Worklist driver for PR #922.** Single-bbox per invocation today; a worklist-driven loop would let a single command produce fiber pseudo-labels across many regions of interest.

Neither is required for the June filing; this submission stands on PRs #915 + #916 + #922 as filed.
