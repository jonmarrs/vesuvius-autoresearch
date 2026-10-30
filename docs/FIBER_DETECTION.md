# GPU Fiber / Ridge / Vesselness Detection

`vesuvius_autoresearch.fibers` is a standalone, dependency-light detector for
fiber/ridge/vesselness structure in scroll CT volumes. It runs on NumPy (CPU) or
CuPy (GPU) from the same code. The CLI's tiled mode streams volumes from disk
and transfers one halo block at a time, supporting inputs larger than VRAM.

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

These June measurements describe the in-memory API at that revision on an
NVIDIA RTX 4090 (CuPy 14.0.1 / CUDA 12.9). They do not benchmark the disk-streaming
CLI added October 29. An [October 30 public-CT CPU check](../reports/fiber_cli_public_ct_cpu_2026-10-30.md)
records exact output parity and peak RSS on one 256³ cube; it does not measure
CUDA, VRAM or general throughput.

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

Inputs must be finite real 3D CT arrays with each axis at least three voxels.
Integer CT is converted to float32 before smoothing and tiled accumulation.
The in-memory tiled APIs still keep their input and result arrays on the
selected backend; tiling bounds filter temporaries. Use the CLI below for
disk-backed input/output and block transfers.
Filter scales must be finite and positive (`gauss_sigma` may be zero). A tiled
run requires a positive integer block size and a halo covering the Gaussian
support plus two derivative voxels: `int(4 * gauss_sigma + 0.5) + 2`, ten voxels
at the default smoothing scale. A smaller halo is rejected before filtering.

## CLI

```bash
python -m vesuvius_autoresearch.fibers.cli \
    --input vol.npy --filter vesselness --output ves.npy [--preview ves.png]

# large volume:
python -m vesuvius_autoresearch.fibers.cli \
    --input big.npy --filter ridges --output ridges.npy --tiled --block-size 128 --halo 16
```

The default `--device auto` uses a visible CUDA device when available, and runs
on CPU when CuPy or CUDA is unavailable. `--device cpu` avoids probing CUDA;
`--device gpu` requires a working GPU. Allocation and filtering failures on a
usable GPU are reported as failures. Output and preview directories are created
automatically. Prints the backend, shape, and wall time.

### Streaming large NPY volumes

`--tiled` opens the input NPY read-only through a memory map and writes the
float32 response into a staged NPY memory map. A first pass measures the global
Gaussian-smoothed range; a second applies the same ridge/vesselness filter and
writes nonoverlapping core blocks. Only halo blocks cross to the selected
device, and only core results return to the host. GPU allocation/filter errors
remain errors; execution does not switch to CPU mid-run. The original in-memory
Python APIs, filter formulas and CLI float32 output are preserved.

Choose `--block-size` and `--halo` together: work blocks have at most
`block_size + 2 * halo` voxels on each axis, clipped to the input. Their Hessian
and other temporaries must still fit on the device. This is not a hard memory
cap; device allocators and the OS page cache have their own behavior. A preview
also needs a host Y×X mean projection and image buffers.

Keep enough destination space for the complete temporary float32 response
alongside any previous output. The CLI checks available space and uses POSIX
space reservation when supported. Filesystems without reservation support rely
on the space check; space must remain available throughout the run.

### Output safety and failures

The output NPY and optional PNG use the exact paths supplied, without automatic
suffixes. Outputs must be regular files or new paths, and cannot be symlinks,
alias the input, or overlap one another, including through hard links and parent
directory aliases. Path checks run before work and before publication. Both
artifacts are prepared in sibling temporary files; computation and serialization
errors preserve the previous artifacts. Replacements retain permission bits and
new files honor the umask.

The requested old preview is removed immediately before publishing the new
response, then the new preview is renamed into place. A publication error can
therefore leave an array without that PNG; it cannot leave the requested old
preview beside a new array. The two renames are not a transaction. Honor a failed
exit, and rerun to regenerate a missing preview. Unrequested older images are
not tracked or removed.

Keep inputs stable and serialize writers. The source's device/inode/size/mtime
are rechecked before publication, which catches ordinary replacement or edits;
it is not a content hash or a lock. Atomic replacement is not a power-loss
durability guarantee. An interrupted process may leave temporary files.

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
NaN-safety, and dense/streaming GPU CLI round-trips. Native GPU checks require a
visible CUDA device and skip when it is absent or masked. CPU artifact and
bounded-transfer regressions are in `tests/test_fiber_streaming_cli.py` and run
in the curated validation suite. The October 29 streaming review used CPU and a
simulated device-transfer boundary; real CUDA parity, large-scan throughput and
peak RAM/VRAM remain unmeasured for the new CLI path.
