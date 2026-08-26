"""Shared test fixtures.

Thirteen probe test modules set ``CUDA_VISIBLE_DEVICES=""`` at import time so
that villa and torch initialise CPU-only. That assignment is process-wide and
permanent: it happens during collection, before any test runs, and every test
afterwards -- and every subprocess any test spawns -- inherits it. That is how
tests/test_fibers_cli.py came to fail inside a full-suite run while passing on
its own, with cudaErrorNoDevice raised in a child process on a machine whose
GPU was working.

Rather than police thirteen modules, this captures the shell's value once, at
conftest import, which is the earliest point in the session. Tests that spawn
subprocesses and genuinely need the GPU ask for `ambient_env`.
"""

import functools
import os
import subprocess
import sys

import pytest

_AMBIENT_CUDA_VISIBLE_DEVICES = os.environ.get("CUDA_VISIBLE_DEVICES")


@pytest.fixture
def ambient_env():
    """A subprocess env with the session's original CUDA visibility restored.

    Use this for any test that shells out and needs the GPU, so the child sees
    what the shell intended rather than what an unrelated test module set.
    """
    env = dict(os.environ)
    if _AMBIENT_CUDA_VISIBLE_DEVICES is None:
        env.pop("CUDA_VISIBLE_DEVICES", None)
    else:
        env["CUDA_VISIBLE_DEVICES"] = _AMBIENT_CUDA_VISIBLE_DEVICES
    return env


def gpu_is_available() -> bool:
    """True if THIS process can use a CUDA device, not merely import cupy.

    `import cupy` succeeds on a masked or absent GPU, so guarding on the import
    alone turns "no device" into a test failure instead of a skip. Use this for
    tests that touch the GPU in-process; they are bound by whatever this
    process's environment is by the time they run.
    """
    try:
        import cupy as cp

        return cp.cuda.runtime.getDeviceCount() > 0
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def machine_has_gpu() -> bool:
    """True if the MACHINE has a CUDA device, independent of this process.

    A test that shells out with `ambient_env` is not bound by the current
    process's masking, so it must not be skipped on account of it. Asking
    in-process would make the answer depend on whether a probe module happened
    to be imported first, which is collection order -- exactly the fragility
    this file exists to remove. So ask a child that has the ambient env.
    """
    probe = (
        "import cupy;"
        "raise SystemExit(0 if cupy.cuda.runtime.getDeviceCount() > 0 else 1)"
    )
    env = dict(os.environ)
    if _AMBIENT_CUDA_VISIBLE_DEVICES is None:
        env.pop("CUDA_VISIBLE_DEVICES", None)
    else:
        env["CUDA_VISIBLE_DEVICES"] = _AMBIENT_CUDA_VISIBLE_DEVICES
    try:
        return (
            subprocess.run(
                [sys.executable, "-c", probe], env=env, capture_output=True, timeout=120
            ).returncode
            == 0
        )
    except Exception:
        return False
