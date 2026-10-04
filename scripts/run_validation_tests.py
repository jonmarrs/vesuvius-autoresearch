#!/usr/bin/env python3
"""
Run the lightweight validation test suite with the active Python interpreter.

This avoids accidentally using a system pytest entrypoint that is not connected
to the project virtualenv.
"""

import subprocess
import sys

VALIDATION_TESTS = [
    "tests/test_volume_inference_contracts.py",
    "tests/test_detector_contracts.py",
    "tests/test_submission_contracts.py",
    "tests/test_interpolation_evidence.py",
    "tests/test_interpolation_drivers.py",
    "tests/test_production_predict.py",
    "tests/test_predict_checkpoint_loading.py",
    "tests/test_loop_lifecycle.py",
    "tests/test_spiral_driver_failures.py",
    "tests/test_spiral_artifacts.py",
    "tests/test_run_render_slice_guard.py",
    "tests/test_import.py",
    "tests/test_imports.py",
    "tests/test_dice.py",
    "tests/test_grad.py",
    "tests/test_zarr_loading.py",
    "tests/test_volume_cartographer.py",
    "tests/test_prize_readiness.py",
    "tests/test_villa_metrics_integration.py",
]


def main():
    cmd = [sys.executable, "-m", "pytest", "-q", *VALIDATION_TESTS]
    print("Running:", " ".join(cmd), flush=True)
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
