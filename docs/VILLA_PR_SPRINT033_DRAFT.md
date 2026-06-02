# PR: GPU acceleration for fiber and ridge detection with tiled execution

## Problem

The current fiber filters (`detect_ridges` and `detect_vesselness` in `foundation/datasets/fibers-dataset/tools.py`) are strictly CPU-bound. Furthermore, attempting a naive port to `cupy` results in crashes at production volume sizes because `cupy.linalg.eigvalsh` (which relies on cuSolver) frequently fails on large batched `(N, N, N, 3, 3)` Hessian matrices, either through memory exhaustion or internal cuSolver errors.

## Fix

This PR introduces production-scale GPU acceleration for fiber and vesselness detection:
1. **Closed-form 3x3 eigensolver:** Replaced the generic `eigvalsh` call with a batched, analytical Cardano eigensolver (`compute_eigenvalues_3x3_batch`) which completely bypasses the cuSolver bottlenecks and runs significantly faster and more reliably on the GPU.
2. **GPU Backend (CuPy):** Introduced dynamic backend switching. If a CuPy array is passed to the tools, they automatically run on the GPU; otherwise, they fall back to the existing NumPy/SciPy CPU implementation.
3. **Tiled/Halo Execution Evidence:** Provided a testing harness and tiled execution block structure (`bench_tools.py`) demonstrating that we can now process massive `$384^3$` blocks by intelligently chunking the operations to fit within VRAM constraints.

## Evidence

### Benchmarks
We implemented `bench_tools.py` to compare CPU vs. GPU. As seen below, the GPU backend yields a ~686x speedup at `$256^3$`, bringing execution time down from over 3 minutes to a fraction of a second.

| Volume Size | Backend | Time (s) | Status |
|---|---|---|---|
| (64, 64, 64) | CPU (NumPy) | 0.49 | OK |
| (64, 64, 64) | GPU (CuPy) | 0.03 | OK (17.8x speedup) |
| (128, 128, 128) | CPU (NumPy) | 6.15 | OK |
| (128, 128, 128) | GPU (CuPy) | 0.05 | OK (126.5x speedup) |
| (256, 256, 256) | CPU (NumPy) | 192.22 | OK |
| (256, 256, 256) | GPU (CuPy) | 0.28 | OK (686.6x speedup) |

### Memory Bounds
At `$384^3$`, a single forward pass would typically OOM. Using the tiled implementation block-by-block with aggressive garbage collection:
- `(384, 384, 384)` | GPU (Tiled) | 10.00s | OK
- Peak Memory Used: **0.42 GB**

### Correctness
Added `test_gpu.py` using `pytest`. The analytical 3x3 eigensolver and the full Frangi vesselness outputs have been validated to produce results functionally identical (`rtol=1e-3`, `atol=1e-4`) to the CPU implementation.

## Limitations

- The dynamic switching requires `cupy` and `cupyx.scipy` to be installed. If they are absent, it safely falls back to CPU execution.
- The user must currently manage the host-to-device transfers (passing a `cupy.ndarray` explicitly) and tiling for truly massive inputs (e.g., > `$512^3$`), but the backend functions are fully memory-safe and mathematically stable for large batches now.

## Reproduction Commands

To run the parity tests and benchmarks:
```bash
# Run correctness tests
pytest foundation/datasets/fibers-dataset/tests/test_gpu.py

# Run benchmarks
python3 foundation/datasets/fibers-dataset/bench/bench_tools.py --sizes 64 128 256
python3 foundation/datasets/fibers-dataset/bench/bench_tools.py --sizes 384 --skip-cpu --tiled
```
