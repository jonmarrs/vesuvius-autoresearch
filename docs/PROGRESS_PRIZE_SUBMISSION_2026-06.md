# Progress Prize Submission (June 2026): GPU-Accelerated Fiber Detection in Villa's `foundation/datasets/fibers-dataset`

**Submission Date:** 2026-06 (target: 2026-06-30 11:59pm PT)
**Submission Form:** TBA — June form not yet open as of 2026-05-15; will be linked here once it goes live.
**Target Prize Tier:** Denarius / Sestertius (open to maintainer judgment)
**Submitter:** Jon Marrs &lt;jdmarrs@gmail.com&gt;
**Repository:** https://github.com/jonmarrs/vesuvius-autoresearch
**License:** MIT (autoresearch); upstream villa PR licensed per ScrollPrize/villa contribution terms
**Status:** QUEUED for June filing. The headline artifact is upstream PR [ScrollPrize/villa#915](https://github.com/ScrollPrize/villa/pull/915), opened 2026-05-15 with full GPU benchmarks attached.
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

### 3. Concurrent upstream contributions (auxiliary, not part of the June prize narrative)

These are small standalone bugfixes shipped to villa in the same week for community benefit. Not prize artifacts in themselves, but worth pointing at:

- [ScrollPrize/villa#913](https://github.com/ScrollPrize/villa/pull/913) — `fix(batchgeneratorsv2): resolve device mismatch in SpatialTransform`. SpatialTransform built sampling grids on CPU while inputs lived on GPU, causing `RuntimeError` in CUDA training loops.
- [ScrollPrize/villa#914](https://github.com/ScrollPrize/villa/pull/914) — `fix(vesuvius-c): accept file:// URLs in vs_download`. `vs_download` rejected any non-200 HTTP status, breaking local-file fetches where libcurl reports `http_code == 0`.

## Why this is prize-worthy

Per the Progress Prize criteria (released early, actually used, well documented):

- **Released early.** PR #915 opened 2026-05-15, six weeks before the June deadline, with the full benchmark table attached and the parity tests passing on the submission hardware.
- **Actually used.** The fiber-detection pipeline is the data-prep stage of every autoresearch ink-detection sweep cycle. The CuPy path moves the bottleneck off the CPU so the GPU stays saturated during training — directly enabling more cycles per night-shift run.
- **Well documented.** Tests, benchmark script, PR description with concrete numbers and a known-caveat section, and a reproducer that anyone with a CUDA GPU can run end-to-end.

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
| Upstream PR | https://github.com/ScrollPrize/villa/pull/915 |
| Auxiliary upstream PRs | [#913](https://github.com/ScrollPrize/villa/pull/913), [#914](https://github.com/ScrollPrize/villa/pull/914) |
| Key files | `foundation/datasets/fibers-dataset/tools.py`, `foundation/datasets/fibers-dataset/tests/test_tools_parity.py`, `foundation/datasets/fibers-dataset/bench/bench_tools.py` |
| Tests | `foundation/datasets/fibers-dataset/tests/test_tools_parity.py` (7 tests; 3 always-on, 4 CuPy-skipif) |
| Reproduction entrypoint | `cd foundation/datasets/fibers-dataset && pytest tests/ && python3 bench/bench_tools.py --sizes 64 128 256` |
| License | MIT (autoresearch); upstream PR per ScrollPrize/villa contribution terms |
| Prior cycle filings | [Part 1](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md), [Part 2](PROGRESS_PRIZE_SUBMISSION_2026-05.md) |

## Public release blurb (for socials / forum announcement)

> Filed for the June 2026 Progress Prize: a CuPy / `cupyx.scipy.ndimage` rewrite of villa's `foundation/datasets/fibers-dataset/tools.py` that moves Frangi vesselness, Hessian ridges, NMS, and Scharr/Pavel edge detection onto GPU with a transparent NumPy / SciPy fallback. Measured on an RTX 4090: `nms_3d` 430× at 256³, `hessian` 226×, `detect_ridges` 82× (the last enabled by replacing batched cuSolver `eigvalsh` with a closed-form 3×3 symmetric eigendecomposition, since cuSolver returns `CUSOLVER_STATUS_INVALID_VALUE` above ~1M batched matrices). Ten passing parity tests + a reproducible benchmark script. PR: https://github.com/ScrollPrize/villa/pull/915.

## Open work (may extend this submission before the June deadline)

- **`vesuvius-c` Python bindings as an upstream PR.** The implementation that backs the May Part 1 submission's Python wrapper (the `ctypes` layer + Blosc2-direct chunk reader) lives in our fork on `cupy-fiber-acceleration`. Carving it out to a real PR against the `vesuvius-c` repo (when located) would land the bindings upstream rather than only in the autoresearch repo.

If this lands before 2026-06-30 it will be added here; if not, this June submission stands on PR #915 alone.
