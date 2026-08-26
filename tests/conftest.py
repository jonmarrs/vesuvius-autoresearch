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


def ambient_cuda_is_masked() -> bool:
    """True if the SHELL asked for CPU-only, as opposed to a test module doing it."""
    return _AMBIENT_CUDA_VISIBLE_DEVICES == ""


def process_cuda_is_masked() -> bool:
    """True if CUDA is masked in this process right now, by whoever."""
    return os.environ.get("CUDA_VISIBLE_DEVICES") == ""


def gpu_is_available() -> bool:
    """True if THIS process can use a CUDA device.

    Deliberately does NOT touch cupy or torch. An earlier version called
    ``cp.cuda.runtime.getDeviceCount()``, which initialises CUDA; because this
    runs at collection time and test_fibers sorts before test_probe_*, that
    initialisation happened BEFORE the thirteen probe modules set
    CUDA_VISIBLE_DEVICES="", so their masking silently stopped working. Worse,
    it left the state that breaks the usual guard: torch.cuda.is_available()
    True with device_count() 0, so `if is_available(): .cuda()` passes and then
    dies. Measured directly; `import cupy` alone does not poison, the runtime
    call does. So this answers from the environment plus an out-of-process
    probe, and initialises nothing here.
    """
    return not process_cuda_is_masked() and gpu_available_ambiently()


@functools.lru_cache(maxsize=1)
def gpu_available_ambiently() -> bool:
    """True if a CUDA device is usable under the SHELL's environment.

    A test that shells out with `ambient_env` is not bound by the current
    process's masking, so it must not be skipped on account of it. Asking
    in-process would make the answer depend on whether a probe module happened
    to be imported first, which is collection order -- exactly the fragility
    this file exists to remove. So ask a child that has the ambient env.

    Note the deliberate asymmetry: this returns False when the SHELL masked
    CUDA, because that is the caller asking for CPU-only and should be
    honoured, and True/False on device presence otherwise.
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
