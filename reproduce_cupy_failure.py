import time

import cupy as cp
import numpy as np


def reproduce_failure():
    # Large batch that typically fails with cuSolver
    size = 128
    shape = (size, size, size, 3, 3)
    print(f"Testing CuPy eigvalsh with shape {shape}...")

    # Create random symmetric matrices
    A = cp.random.rand(*shape).astype(cp.float32)
    A = (A + A.transpose(0, 1, 2, 4, 3)) / 2.0

    try:
        start_time = time.time()
        # This is the call that is expected to fail or be extremely slow/memory-intensive
        eigvals = cp.linalg.eigvalsh(A)
        cp.cuda.Stream.null.synchronize()
        print(f"Success! Time: {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"FAILED as expected: {e}")


if __name__ == "__main__":
    reproduce_failure()
