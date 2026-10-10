#!/usr/bin/env python3
"""
Run the lightweight validation test suite with the active Python interpreter.

This avoids accidentally using a system pytest entrypoint that is not connected
to the project virtualenv.
"""

import subprocess
import sys

VALIDATION_TESTS = [
    "tests/test_experiment_report_contracts.py",
    "tests/test_daily_report.py",
    "tests/test_candidate_fiber_report_contracts.py",
    "tests/test_spatial_inspection_contracts.py",
    "tests/test_spatial_split_mask.py",
    "tests/test_pseudo_handoff_contracts.py",
    "tests/test_pseudo_label_quality.py",
    "tests/test_confidence_weighted_loss.py",
    "tests/test_checkpoint_export_contracts.py",
    "tests/test_villa_optimized_inference_smoke.py",
    "tests/test_geometry_handoff_contracts.py",
    "tests/test_mutex_data_contracts.py",
    "tests/test_volumetric_label_contracts.py",
    "tests/test_label_curation_contracts.py",
    "tests/test_candidate_preprocessing_contracts.py",
    "tests/test_crop_candidate_zarr.py",
    "tests/test_lasagna_fiber_worklist.py",
    "tests/test_execute_lasagna_pipeline_resume.py",
    "tests/test_surface_render_contracts.py",
    "tests/test_render_surface.py",
    "tests/test_sota_convert.py",
    "tests/test_sota_qualitative.py",
    "tests/test_sota_distill_prep.py",
    "tests/test_sota_gt_register.py",
    "tests/test_fiber_workflow_contracts.py",
    "tests/test_fibers.py",
    "tests/test_fibers_cli.py",
    "tests/test_fiber_eval_trace.py",
    "tests/test_checkpoint_tool_contracts.py",
    "tests/test_active_learning.py",
    "tests/test_generate_pseudo_labels.py",
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
