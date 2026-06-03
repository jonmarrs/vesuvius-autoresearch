# PR Draft: Production-Scale GPU Ridge and Vesselness Detection for Fibers

## Problem
The current fiber and ridge detection filters in `foundation/datasets/fibers-dataset` are primarily CPU-bound, making them slow for production-scale volumes (e.g., full scroll divisions). While a naive CuPy implementation was attempted previously, it relied on `cupy.linalg.eigvalsh` which often fails on large batches of $3 \times 3$ matrices due to `cuSolver` internal limitations or missing shared libraries (`libcusolver.so.11`).

## Fix
This PR introduces a robust, production-ready GPU backend for fiber detection:
1. **Analytical 3x3 Eigensolver:** Implemented a closed-form symmetric 3x3 eigensolver using Cardano's formula. This bypasses `cuSolver`, significantly reducing memory overhead and avoiding common CuPy/CUDA environment failures.
2. **Tiled Execution with Halo:** Added `detect_ridges_tiled` and `detect_vesselness_tiled` to support processing of arbitrarily large volumes in blocks. This ensures the tools can run on consumer hardware (e.g., 8GB-24GB VRAM) even for full-scale scroll data.
3. **Backend Agnostic Logic:** The tools now automatically switch between NumPy and CuPy backends based on the input array type, preserving existing CPU workflows while enabling transparent GPU acceleration.

## Evidence

### Parity Validation
The analytical solver was validated against `numpy.linalg.eigvalsh` on a $64^3$ volume.
- **Max Difference:** 2.94e-05
- **Mean Difference:** 1.03e-07
- **Tests:** `pytest tests/test_gpu.py` passes.

### Performance Benchmarks (NVIDIA RTX 4090)
| Volume Size | Filter | Backend | Time (s) | Speedup |
| :--- | :--- | :--- | :--- | :--- |
| (128, 128, 128) | vesselness | CPU (NumPy) | 4.83 | 1.0x |
| (128, 128, 128) | vesselness | GPU (CuPy) | 0.03 | **144.1x** |
| (256, 256, 256) | vesselness | CPU (NumPy) | 72.13 | 1.0x |
| (256, 256, 256) | vesselness | GPU (CuPy) | 0.24 | **299.9x** |
| (512, 512, 512) | ridges | GPU (Tiled) | 4.03 | **N/A** |

**Memory Usage:** Tiled execution at $512^3$ uses only ~1.00 GB of GPU memory (excluding input volume).

### Real-Scroll Evidence (PHerc0332)
The implementation was tested on a $256^3$ region of Scroll 4.
- **Processing Time:** 1.18s
- **Observation:** Vesselness signals correctly identified papyrus layers and fiber ridges without artifacts at tile boundaries.
- **Visuals:** Contact sheets showing source vs. vesselness slices are included in the repository documentation.

## Limitations
- The analytical formula is specific to $3 \times 3$ matrices.
- The `detect_edges` and `nms_3d` functions still default to CPU (NumPy) for coordinate interpolation, though the primary bottleneck (Hessian/Eigensolver) is now GPU-accelerated.

## Reproduction Commands
```bash
cd foundation/datasets/fibers-dataset
pytest tests/test_gpu.py
python3 bench/bench_tools.py --sizes 128 256
python3 bench/bench_tools.py --sizes 384 512 --tiled --skip-cpu
```
