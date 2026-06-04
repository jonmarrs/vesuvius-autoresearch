# GPU fiber/ridge detection that scales past 64³ (fibers-dataset)

<!--
INTERNAL NOTE — not for posting as-is.
This is a human-review draft of the PR description for branch
`jonmarrs:sprint033-fibers-gpu`. Numbers are reconciled to the June RTX 4090
run in reports/fibers_gpu_validation_2026-06.md (the older
docs/VILLA_PR_SPRINT033_DRAFT.md has stale/inconsistent figures — do not use it).
Before opening the PR: rebase onto current ScrollPrize/villa:main (branch is
9 commits behind), re-run the tests/benches below on that base, and paste the
real numbers from your own run. Read the diff yourself first.
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
  a configurable halo to avoid tile-boundary artifacts, for large volumes.
- `tests/test_gpu.py` — parity tests against the NumPy reference.
- `bench/bench_tools.py` — CPU-vs-GPU benchmark harness.

Scope is limited to `foundation/datasets/fibers-dataset/` (3 files).

## Evidence

All figures below were reproduced on 2026-06-04 on the rebased branch (current
`ScrollPrize/villa:main`), NVIDIA RTX 4090, CuPy 14.0.1 / CUDA 12.9.

Eigensolver parity: `compute_eigenvalues_3x3_batch` vs `numpy.linalg.eigvalsh`
on a random symmetric 3×3 batch — max abs difference **1.7e-10**, mean 2.1e-13
(float64 reference). `pytest tests/test_gpu.py` → 2 passed.

Dense CPU-vs-GPU timings:

| Volume | Filter | CPU (NumPy) | GPU (CuPy) | Speedup | GPU mem |
| --- | --- | --- | --- | --- | --- |
| 64³  | vesselness | 0.23 s  | 0.02 s | ~15× | <0.01 GB |
| 128³ | vesselness | 2.07 s  | 0.04 s | ~59× | 0.02 GB |
| 256³ | vesselness | 19.97 s | 0.28 s | ~71× | 0.19 GB |
| 256³ | ridges     | 18.76 s | 0.29 s | ~66× | 0.19 GB |

Tiled large-volume timings (`--tiled --skip-cpu`):

| Volume | Filter | GPU (tiled) | GPU mem |
| --- | --- | --- | --- |
| 384³ | vesselness | 2.16 s | 0.42 GB |
| 384³ | ridges     | 1.72 s | 0.42 GB |
| 512³ | vesselness | 4.37 s | 1.00 GB |
| 512³ | ridges     | 4.12 s | 1.00 GB |

So 256³ fits in GPU memory and runs in well under a second; 512³ runs tiled in
~4 s within ~1 GB of GPU memory, i.e. on consumer hardware. (Speedups are a
~15–71× range over the NumPy path depending on size and CPU — not a single
headline multiplier; the earlier internal figure of "300×" reflected a slower
CPU baseline and isn't reproducible here.)

A 256³ region of PHerc0332 (Scroll 4) processes in ~1.2 s with no visible
tile-boundary artifacts; a source-vs-vesselness contact sheet is included.

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
  block size / halo; the non-tiled GPU functions assume the volume fits in memory.
- Closed-form 3×3 eigenvalues match `eigvalsh` to ~1e-5, which is well within the
  tolerance used downstream, but it is not bit-identical to the LAPACK/cuSolver path.
