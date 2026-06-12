# GPU Fiber / Ridge / Vesselness Detection

`vesuvius_autoresearch.fibers` is a standalone, dependency-light detector for
fiber/ridge/vesselness structure in scroll CT volumes. It runs on NumPy (CPU) or
CuPy (GPU) from the same code, and scales to volumes larger than VRAM via tiled
execution.

## The problem it solves

The natural GPU port of the Frangi/Hessian pipeline calls `cupy.linalg.eigvalsh`
(cuSolver) on a large batch of `(…, 3, 3)` Hessians. That path is unreliable at
production sizes — it raises buffer/allocation or missing-library errors
(`libcusolver.so.*`) — so GPU ridge/vesselness detection was effectively limited
to tiny volumes.

This module replaces the batched `eigvalsh` with a **closed-form analytical
eigensolver for symmetric 3×3 matrices** (Cardano's formula,
`compute_eigenvalues_3x3_batch`), which avoids cuSolver entirely. A per-array
backend dispatch (`get_backend`) lets the same functions run on NumPy or CuPy,
and tiled variants process large volumes with a halo, normalizing each block
against the global smoothed range so tiled output matches the dense path.

Vendored from the validated `sprint033-fibers-gpu` branch (proposed upstream as
[ScrollPrize/villa#1033](https://github.com/ScrollPrize/villa/pull/1033), closed
without review).

## Validated performance

On an NVIDIA RTX 4090 (CuPy 14.0.1 / CUDA 12.9):

- Eigensolver parity vs `numpy.linalg.eigvalsh`: max abs diff **3.1e-10**
  (float64), **6.7e-6** (float32).
- Dense CPU→GPU speedups: **14–94×** over NumPy across 64³–256³.
- Tiled large volumes: **512³ in ~3–5 s at ~1 GB VRAM** (consumer hardware).
- Tiled-vs-dense parity holds to 1e-4 (the halo must cover the filter support,
  `4 * gauss_sigma + 2` voxels; the default halo 16 covers `gauss_sigma=2`).

Full numbers and method: [`reports/fibers_gpu_validation_2026-06.md`](../reports/fibers_gpu_validation_2026-06.md).

## API

```python
import numpy as np
from vesuvius_autoresearch.fibers import detect_vesselness, detect_vesselness_tiled

vol = np.random.rand(128, 256, 256).astype(np.float32)   # [Z,H,W] CT
ves = detect_vesselness(vol)                              # dense (fits in memory)

big = np.random.rand(512, 512, 512).astype(np.float32)
ves_big = detect_vesselness_tiled(big, block_size=128, halo=16)   # tiled
```

`detect_ridges` / `detect_ridges_tiled` have the same signatures. Pass a `cupy`
array to run on GPU; pass a `numpy` array to run on CPU. Constant/blank patches
(common outside the mask) normalize to zeros rather than producing NaNs.

## CLI

```bash
python -m vesuvius_autoresearch.fibers.cli \
    --input vol.npy --filter vesselness --output ves.npy [--preview ves.png]

# large volume:
python -m vesuvius_autoresearch.fibers.cli \
    --input big.npy --filter ridges --output ridges.npy --tiled --block-size 128 --halo 16
```

Uses the GPU automatically when CuPy is importable, else CPU. Prints the backend,
shape, and wall time.

## In this repo

The training loader (`vesuvius_loader.py`) computes the on-the-fly ridge feature
channel via `detect_ridges` from this module. (Before this was vendored, it
imported the broken upstream clone `tools.py`, whose GPU and CPU paths both
failed — so the ridge channel was silently all-zeros whenever `use_ridges=true`.)

## Tests

```bash
PYTHONPATH=. uv run python -m pytest tests/test_fibers.py tests/test_fibers_cli.py
```

Covers eigensolver parity, CPU↔GPU parity, tiled-vs-dense parity, constant-input
NaN-safety, and a CLI round-trip.
