"""Request deterministic CUDA algorithms for the lasagna flatten, if asked.

reports/the_flatten_has_no_seed_to_set.md: the flatten has no RNG to seed; its
run-to-run variation is CUDA reduction order (174 scatter/atomic sites, grid_sample
backward, a fused Triton kernel, and no request for determinism anywhere). This
shim is the experiment that report names: does asking PyTorch for deterministic
algorithms make two flattens of identical input converge, or does the run error
on an op that has no deterministic path?

Activated ONLY when FLATTEN_DETERMINISTIC=1 is set, via PYTHONPATH pointing at
this directory (Python imports sitecustomize automatically at startup). Inert
otherwise, so it cannot change any other run.

warn_only=True: an op with no deterministic implementation WARNS instead of
raising, so the run completes and the warnings tell us which ops escaped. That
is more informative than an early crash, and the warnings are captured in the
render log.
"""

import os
import warnings

if os.environ.get("FLATTEN_DETERMINISTIC") == "1":
    # cuBLAS needs this set BEFORE the first CUDA call or it raises at the first
    # matmul in deterministic mode. Set it here, since we run before torch imports.
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    try:
        import torch

        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        # Route every "not deterministic" warning to stderr with a fixed prefix so
        # they can be counted from the log.
        warnings.filterwarnings("always", message=".*does not have a deterministic.*")
        print(
            "[determinism-shim] torch.use_deterministic_algorithms(True, warn_only=True); "
            "cudnn.deterministic=True; CUBLAS_WORKSPACE_CONFIG="
            + os.environ["CUBLAS_WORKSPACE_CONFIG"],
            flush=True,
        )
    except Exception as e:  # never let the shim itself break a run
        print(
            f"[determinism-shim] FAILED to enable: {type(e).__name__}: {e}", flush=True
        )
