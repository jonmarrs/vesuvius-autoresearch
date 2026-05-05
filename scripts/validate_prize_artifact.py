#!/usr/bin/env python3
"""
Validate Vesuvius Challenge prize-readiness artifacts.

This checks the mechanical submission constraints that can be verified locally:
metadata completeness, ML window-size guidance, train/predict overlap, scale-bar
declaration, and VC3D/Zarr export shape/scale metadata.
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np


MAX_ML_WINDOW_MM = 0.5
MAX_ML_WINDOW_PX = 64
DEFAULT_VOXEL_UM = 8.0


def _load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "pass", "ok"}
    return bool(value)


def _check(condition, message, failures, warnings=None, warning=False):
    target = warnings if warning else failures
    if not condition:
        target.append(message)


def _load_mask(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".npy":
        return np.load(path).astype(bool)
    try:
        from PIL import Image

        return np.array(Image.open(path)).astype(bool)
    except Exception as exc:
        raise ValueError(f"could not load mask {path}: {exc}") from exc


def _check_ome_scale_metadata(zarr_dir, voxel_um, failures, warnings):
    zattrs_path = zarr_dir / ".zattrs"
    if not zattrs_path.exists():
        _check(False, f"VC3D export missing OME-Zarr scale metadata {zattrs_path}", failures, warnings, warning=True)
        return

    try:
        zattrs = _load_json(zattrs_path)
    except (OSError, ValueError, TypeError) as exc:
        _check(False, f"VC3D .zattrs could not be parsed: {exc}", failures)
        return

    multiscales = zattrs.get("multiscales") or []
    _check(multiscales, "VC3D .zattrs must include multiscales metadata", failures)
    if not multiscales:
        return

    axes = multiscales[0].get("axes") or []
    axis_units = [axis.get("unit") for axis in axes if axis.get("type") == "space"]
    _check(axis_units and all(unit == "micrometer" for unit in axis_units), "OME-Zarr spatial axes must use micrometer units", failures)

    datasets = multiscales[0].get("datasets") or []
    _check(datasets, "OME-Zarr multiscales metadata must include datasets", failures)
    if not datasets:
        return

    transforms = datasets[0].get("coordinateTransformations") or []
    scales = [item.get("scale") for item in transforms if item.get("type") == "scale"]
    _check(scales, "OME-Zarr dataset must include a scale coordinateTransformation", failures)
    if scales:
        spatial_scale = [float(v) for v in scales[0][-3:]]
        expected = [float(voxel_um)] * 3
        _check(
            np.allclose(spatial_scale, expected, rtol=0, atol=1e-6),
            f"OME-Zarr spatial scale {spatial_scale} does not match metadata voxel size {expected}",
            failures,
        )


def validate(metadata_path, train_mask=None, predict_mask=None, zarr_path=None):
    metadata_path = Path(metadata_path)
    metadata = _load_json(metadata_path)
    failures = []
    warnings = []

    voxel_um = float(metadata.get("voxel_size_um", metadata.get("voxel_resolution_um", DEFAULT_VOXEL_UM)))
    patch_size = int(metadata.get("patch_size", metadata.get("window_size_pixels", 0) or 0))
    width = int(metadata.get("width_px", metadata.get("window_width_px", patch_size) or 0))
    height = int(metadata.get("height_px", metadata.get("window_height_px", patch_size) or 0))
    ml_window_px = int(metadata.get("ml_window_px", patch_size or max(width, height)))
    ml_window_mm = ml_window_px * voxel_um / 1000.0

    _check(metadata.get("scroll_id"), "metadata must include scroll_id", failures)
    _check(
        metadata.get("segmentation_id") or metadata.get("segmentation_file") or metadata.get("source_uri"),
        "metadata must include segmentation_id, segmentation_file, or source_uri",
        failures,
    )
    _check(
        metadata.get("position_xyz") or metadata.get("3d_position_xyz") or all(k in metadata for k in ("z", "y", "x")),
        "metadata must include 3D position",
        failures,
    )
    _check(width > 0 and height > 0, "metadata must include positive width_px/height_px or patch_size", failures)
    _check(voxel_um > 0, "metadata must include positive voxel size", failures)
    _check(
        ml_window_px <= MAX_ML_WINDOW_PX or ml_window_mm <= MAX_ML_WINDOW_MM + 1e-9,
        f"ML window is {ml_window_px}px/{ml_window_mm:.3f}mm; expected <= {MAX_ML_WINDOW_PX}px or <= {MAX_ML_WINDOW_MM:.3f}mm",
        failures,
    )
    _check(
        _as_bool(metadata.get("scale_bar_cm", metadata.get("has_scale_bar_cm", False))),
        "metadata must declare a 1 cm scale bar",
        failures,
    )
    _check(
        not _as_bool(metadata.get("source_image_is_placeholder", False))
        and metadata.get("evidence_mode") not in {"placeholder", "placeholder_dry_run", "dummy"},
        "submission image is marked as a placeholder/dry-run artifact; real CT-derived prediction evidence is required",
        failures,
    )
    _check(
        not _as_bool(metadata.get("metadata_is_dry_run", False)),
        "metadata is marked as dry-run/default; real scroll, segmentation, and 3D position metadata are required",
        failures,
    )

    train_mask_path = train_mask or metadata.get("train_mask_path")
    predict_mask_path = predict_mask or metadata.get("predict_mask_path")
    if train_mask_path and predict_mask_path:
        train = _load_mask(train_mask_path)
        predict = _load_mask(predict_mask_path)
        _check(train.shape == predict.shape, "train and predict masks must have the same shape", failures)
        if train.shape == predict.shape:
            overlap = int(np.logical_and(train, predict).sum())
            _check(overlap == 0, f"train/predict masks overlap in {overlap} pixels", failures)
    else:
        _check(False, "train and predict masks were not provided; zero-overlap is unverified", failures, warnings, warning=True)

    zarr_candidate = zarr_path or metadata.get("vc3d_zarr_path") or metadata.get("prediction_zarr_path")
    if zarr_candidate:
        zarr_dir = Path(zarr_candidate)
        meta_json = zarr_dir / "meta.json"
        zarray_json = zarr_dir / "0" / ".zarray"
        _check(meta_json.exists(), f"VC3D export missing {meta_json}", failures)
        _check(zarray_json.exists(), f"VC3D export missing {zarray_json}", failures)
        if meta_json.exists():
            vc_meta = _load_json(meta_json)
            _check(vc_meta.get("format") == "zarr", "VC3D meta.json must include format='zarr'", failures)
            _check(float(vc_meta.get("voxelsize", 0)) > 0, "VC3D meta.json must include positive voxelsize", failures)
        _check_ome_scale_metadata(zarr_dir, voxel_um, failures, warnings)
    else:
        _check(False, "VC3D/Zarr export path not provided; export compatibility is unverified", failures, warnings, warning=True)

    return {
        "status": "PASS" if not failures else "FAIL",
        "metadata_path": str(metadata_path),
        "ml_window_px": ml_window_px,
        "ml_window_mm": ml_window_mm,
        "failures": failures,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True, help="Prediction or submission metadata JSON")
    parser.add_argument("--train-mask", default=None, help="Optional train mask .npy/image")
    parser.add_argument("--predict-mask", default=None, help="Optional prediction mask .npy/image")
    parser.add_argument("--zarr", default=None, help="Optional VC3D prediction zarr directory")
    parser.add_argument("--out", default=None, help="Optional JSON report path")
    args = parser.parse_args()

    report = validate(args.metadata, args.train_mask, args.predict_mask, args.zarr)
    print(json.dumps(report, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
