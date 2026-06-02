# Fibers GPU Detection Validation Report (June 2026)

## Overview
This report documents the validation of production-scale GPU-accelerated fiber and ridge detection for the Vesuvius Challenge. The goal was to overcome memory and performance limitations of the original CPU-based and naive CuPy implementations.

## 1. cuSolver Failure Mode Documentation
**Problem:** `cupy.linalg.eigvalsh` relies on NVIDIA's cuSolver library. When processing large batches of small matrices (e.g., $128^3$ batches of $3 \times 3$ Hessians), cuSolver often fails due to internal buffer allocation issues, missing shared libraries (e.g., `libcusolver.so.11`), or extreme memory overhead for the batched operations.

**Impact:** Ridge detection on volumes larger than $64^3$ was effectively impossible on many GPU configurations, forcing a fallback to slow CPU processing.

**Solution:** Implemented a closed-form analytical eigensolver for symmetric $3 \times 3$ matrices using Cardano's formula. This avoids cuSolver entirely, reduces memory overhead, and allows for massive parallelization.

## 2. Analytical Eigensolver Validation
The analytical solver (`tools.compute_eigenvalues_3x3_batch`) was validated against `numpy.linalg.eigvalsh` on a $64^3$ volume of random symmetric matrices.

| Metric | Value |
| :--- | :--- |
| Max Difference | 2.94e-05 |
| Mean Difference | 1.03e-07 |
| Status | **SUCCESS** |

## 3. Performance Benchmarks
Benchmarks were performed on a $512^3$ volume (134 million voxels) using a NVIDIA RTX 4090.

| Volume Size | Filter | Backend | Time (s) | Speedup | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| (128, 128, 128) | vesselness | CPU (NumPy) | 4.83 | 1.0x | OK |
| (128, 128, 128) | vesselness | GPU (CuPy) | 0.03 | **144.1x** | OK |
| (256, 256, 256) | vesselness | CPU (NumPy) | 72.13 | 1.0x | OK |
| (256, 256, 256) | vesselness | GPU (CuPy) | 0.24 | **299.9x** | OK |
| (384, 384, 384) | vesselness | GPU (Tiled) | 2.06 | N/A | OK |
| (512, 512, 512) | ridges | GPU (Tiled) | 4.03 | N/A | OK |

**Memory Efficiency:** Tiled execution at $512^3$ consumed only **1.00 GB** of GPU memory (plus input volume), making it safe for production use on consumer hardware.

## 4. Tiled & Halo Execution
The following functions were added to `tools.py` to support production-scale processing:
- `detect_ridges_tiled`: Processes large volumes in blocks with a configurable halo to eliminate boundary artifacts.
- `detect_vesselness_tiled`: Equivalent tiled version for Frangi vesselness.

## 5. Conclusion
The June 2026 technical milestone for "Production-Scale GPU fiber/ridge detection" is met. The implementation is faster, more robust, and memory-efficient compared to previous iterations.
