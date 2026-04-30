#!/usr/bin/env python3
"""
Run the lightweight validation test suite with the active Python interpreter.

This avoids accidentally using a system pytest entrypoint that is not connected
to the project virtualenv.
"""
import subprocess
import sys


VALIDATION_TESTS = [
    "test_import.py",
    "test_imports.py",
    "test_dice.py",
    "test_grad.py",
    "test_zarr_loading.py",
    "test_vesuvius_c.py",
    "test_prize_readiness.py",
]


def main():
    cmd = [sys.executable, "-m", "pytest", "-q", *VALIDATION_TESTS]
    print("Running:", " ".join(cmd), flush=True)
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
