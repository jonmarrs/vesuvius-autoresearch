import os
import sys
import time

import cupy as cp
import numpy as np

# Add villa to path
sys.path.insert(
    0, os.path.join(os.getcwd(), "villa/foundation/datasets/fibers-dataset")
)
import tools


def test_analytical_vs_numpy():
    size = 64
    shape = (size, size, size, 3, 3)
    print(f"Testing analytical eigensolver with shape {shape}...")

    # Create random symmetric matrices on CPU
    A_np = np.random.rand(*shape).astype(np.float32)
    A_np = (A_np + A_np.transpose(0, 1, 2, 4, 3)) / 2.0

    # Compute eigenvalues using NumPy (ground truth)
    print("Computing NumPy eigenvalues...")
    start_time = time.time()
    eigvals_np = np.linalg.eigvalsh(A_np)
    print(f"NumPy Time: {time.time() - start_time:.2f}s")

    # Compute eigenvalues using analytical formula on GPU
    print("Computing Analytical eigenvalues on GPU...")
    A_cp = cp.array(A_np)
    start_time = time.time()
    eigvals_cp = tools.compute_eigenvalues_3x3_batch(A_cp)
    cp.cuda.Stream.null.synchronize()
    print(f"Analytical GPU Time: {time.time() - start_time:.2f}s")

    # Compare
    eigvals_analytical_np = cp.asnumpy(eigvals_cp)

    # Note: eigvals_np is sorted, and compute_eigenvalues_3x3_batch also sorts.
    diff = np.abs(eigvals_np - eigvals_analytical_np)
    max_diff = np.max(diff)
    mean_diff = np.mean(diff)

    print(f"Max Diff: {max_diff:.2e}")
    print(f"Mean Diff: {mean_diff:.2e}")

    if max_diff < 1e-3:
        print("SUCCESS: Analytical formula matches NumPy!")
    else:
        print("FAILURE: Diffs too large.")


if __name__ == "__main__":
    test_analytical_vs_numpy()
