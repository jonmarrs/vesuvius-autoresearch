# GPU fiber/ridge detection that scales past 64³ (fibers-dataset)

<!--
INTERNAL NOTE — strip this comment before posting.
PR description for branch `jonmarrs:sprint033-fibers-gpu` (4 commits).
All numbers below are from the 2026-06-09 re-run on the rebased branch
(current ScrollPrize/villa:main), RTX 4090, CuPy 14.0.1 / CUDA 12.9,
GPU otherwise idle. Tests: 4 passed.
-->

## What this does

`detect_ridges` and `detect_vesselness` in `foundation/datasets/fibers-dataset/tools.py`
are CPU-only today, and a naive CuPy port doesn't help: `cupy.linalg.eigvalsh`
(cuSolver) is unreliable on large batches of `(..., 3, 3)` Hessians — it hits
buffer/allocation errors or missing-library failures — so in practice ridge and
vesselness detection has been limited to small volumes (~64³) on GPU.

This PR makes the GPU path work at the volume sizes that actually show up in
scroll data. The key change is replacing the batched `eigvalsh` call with a
closed-form analytical eigensolver for symmetric 3×3 matrices (Cardano's
formula), which avoids cuSolver entirely. On top of that it adds an optional
CuPy backend with a NumPy/SciPy fallback, and tiled/halo variants for volumes
that don't fit in VRAM at once.

Motivation: this is the kind of tooling needed to generate fiber labels at scroll
scale (cf. issue #193, "Methods for generating surface, fiber, or ink labels") —
the CPU path is too slow to run over whole regions.

## Changes

- `compute_eigenvalues_3x3_batch` — closed-form symmetric 3×3 eigenvalues; works
  on NumPy or CuPy arrays, no cuSolver dependency.
- `detect_ridges` / `detect_vesselness` — dispatch to GPU when handed a CuPy
  array, otherwise unchanged CPU behavior (NumPy/SciPy fallback preserved).
- `detect_ridges_tiled` / `detect_vesselness_tiled` — block-wise processing with
  a configurable halo, for large volumes. A cheap first pass computes the global
  min/max of the smoothed volume so per-block normalization matches the dense
  path exactly — without this, tiled results silently diverge from dense by up
  to ~3e-2 because `normalize()` is a global min-max scaling.
- `tests/test_gpu.py` — eigensolver parity vs `numpy.linalg.eigvalsh`, CPU/GPU
  backend parity, and tiled-vs-dense parity for both filters.
- `bench/bench_tools.py` — CPU-vs-GPU benchmark harness.

Scope is limited to `foundation/datasets/fibers-dataset/` (3 files).

## Evidence

All figures below were measured on 2026-06-09 on the rebased branch (current
`ScrollPrize/villa:main`), NVIDIA RTX 4090, CuPy 14.0.1 / CUDA 12.9.

Eigensolver parity: `compute_eigenvalues_3x3_batch` vs `numpy.linalg.eigvalsh`
on random symmetric 3×3 batches — max abs difference **3.1e-10** (float64),
**6.7e-6** (float32). Tiled-vs-dense parity holds to 1e-4 for both filters.
`pytest tests/test_gpu.py` → 4 passed.

Dense CPU-vs-GPU timings:

| Volume | Filter | CPU (NumPy) | GPU (CuPy) | Speedup | GPU mem |
| --- | --- | --- | --- | --- | --- |
| 64³  | vesselness | 0.24 s  | 0.02 s | ~14× | <0.01 GB |
| 64³  | ridges     | 0.22 s  | 0.01 s | ~20× | <0.01 GB |
| 128³ | vesselness | 1.85 s  | 0.03 s | ~67× | 0.02 GB |
| 128³ | ridges     | 2.10 s  | 0.03 s | ~68× | 0.02 GB |
| 256³ | vesselness | 19.39 s | 0.21 s | ~93× | 0.19 GB |
| 256³ | ridges     | 19.23 s | 0.20 s | ~94× | 0.19 GB |

Tiled large-volume timings (`--tiled --skip-cpu`, includes the global-range pass):

| Volume | Filter | GPU (tiled) | GPU mem |
| --- | --- | --- | --- |
| 384³ | vesselness | 2.17 s | 0.42 GB |
| 384³ | ridges     | 1.40 s | 0.42 GB |
| 512³ | vesselness | 4.54 s | 1.00 GB |
| 512³ | ridges     | 3.29 s | 1.00 GB |

So 256³ fits in GPU memory and runs in ~0.2 s; 512³ runs tiled in ~3–5 s within
~1 GB of GPU memory, i.e. on consumer hardware. Speedups are a ~14–94× range
over the NumPy path depending on size — not a single headline multiplier.

A 256³ region of PHerc0332 (Scroll 4) processes in ~1.2 s with no visible
tile-boundary artifacts (run 2026-06-04 on the pre-rebase branch);
[source-vs-vesselness contact sheet](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/real_scroll_evidence/vesselness_contact_sheet.png).

## How to reproduce

```bash
cd foundation/datasets/fibers-dataset
pytest tests/test_gpu.py
python3 bench/bench_tools.py --sizes 64 128 256
python3 bench/bench_tools.py --sizes 384 512 --tiled --skip-cpu
```

## Limitations

- Requires `cupy` (+ `cupyx.scipy`) for the GPU path; without them it falls back
  to CPU automatically.
- For volumes that exceed VRAM, the caller chooses the tiled entry points and the
  block size / halo. The halo must cover the filter support
  (`4 * gauss_sigma + 2` voxels; the default halo of 16 covers the default
  `gauss_sigma=2`) for tiled results to match dense execution.
- Closed-form 3×3 eigenvalues match `eigvalsh` to ~1e-5 in float32 (~3e-10 in
  float64), which is well within the tolerance used downstream, but it is not
  bit-identical to the LAPACK/cuSolver path.
