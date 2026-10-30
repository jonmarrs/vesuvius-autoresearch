#!/usr/bin/env python3
"""Check local submission mechanics, not scientific accuracy or prize eligibility.

PASS requires a complete prediction whose ink map is sigmoid(ink), a readable
discovery image of a region at least 1 cm wide (the declared scale bar must fit),
valid geometry, and supplied overlap masks. A provided VC3D export must have
coherent array and OME metadata. This does not establish that masks describe the
model's complete training history.

The retained 64px/0.5mm limit is this project's local artifact contract, not
the current official reading-prize rule. Larger windows require independent
anti-hallucination evidence; see docs/RESEARCH_STRATEGY.md.
"""

import argparse
import json
import math
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.candidate_artifacts import write_json
from scripts.text_snapshot import Snapshot
from vesuvius_autoresearch.core.inference_constants import INK_PROBABILITY
from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths

MAX_ML_WINDOW_MM = 0.5
MAX_ML_WINDOW_PX = 64
DEFAULT_VOXEL_UM = 8.0
MAX_METADATA_BYTES = 2 * 1024**2
ARTIFACT_INPUT_KEYS = (
    "output_image_path",
    "source_image_path",
    "train_mask_path",
    "predict_mask_path",
    "vc3d_zarr_path",
    "prediction_zarr_path",
    "fiber_vc3d_zarr_path",
    "fiber_prediction_zarr_path",
    "checkpoint_path",
)


def _reject_constant(value):
    raise ValueError(f"nonfinite JSON value {value}")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def _decode_json(text, path):
    try:
        data = json.loads(
            text, parse_constant=_reject_constant, object_pairs_hook=_unique_keys
        )
    except RecursionError as exc:
        raise ValueError("metadata JSON nesting is too deep") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _load_json(path):
    return _decode_json(Snapshot.read(path, MAX_METADATA_BYTES).text(), path)


def artifact_inputs(metadata_path, metadata, keys=ARTIFACT_INPUT_KEYS):
    reads = [(metadata_path, "prediction metadata")]
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value:
            reads.append((resolve_artifact_path(value, metadata_path), key))
    return reads


def _as_bool(value):
    return value is True or (
        isinstance(value, str)
        and value.strip().lower() in {"1", "true", "yes", "pass", "ok"}
    )


def _positive_number(value, label, integer=False):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(
            f"{label} must be a positive finite {'integer' if integer else 'number'}"
        ) from exc
    if (
        isinstance(value, bool)
        or not math.isfinite(number)
        or number <= 0
        or (integer and not number.is_integer())
    ):
        raise ValueError(
            f"{label} must be a positive finite {'integer' if integer else 'number'}"
        )
    return int(number) if integer else number


def _position(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(
            "3D position must contain three nonnegative voxel indices in x/y/z order"
        )
    for item in value:
        if (
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(item)
            or item < 0
            or int(item) != item
        ):
            raise ValueError(
                "3D position must contain three nonnegative voxel indices in x/y/z order"
            )
    return value


def _local_file_path(value):
    if (
        isinstance(value, str)
        and value.lower().startswith("file:")
        and not Path(value).exists()
    ):
        parts = urlsplit(value)
        if parts.netloc not in {"", "localhost"}:
            raise ValueError("file URI must refer to the local host")
        value = unquote(parts.path)
    return Path(value)


def resolve_artifact_path(value, metadata_path):
    """Prefer metadata-relative paths; accept existing legacy CWD-relative paths."""
    path = _local_file_path(value)
    if path.is_absolute():
        return path
    relative = Path(metadata_path).resolve().parent / path
    if relative.exists() or not path.exists():
        return relative
    return path.resolve()


def _load_mask(path):
    if not Path(path).is_file():
        raise ValueError(f"mask must be a regular file: {path}")
    if Path(path).suffix.lower() == ".npy":
        mask = np.load(path, allow_pickle=False)
    else:
        with Image.open(path) as image:
            mask = np.array(image)
    if (
        not isinstance(mask, np.ndarray)
        or mask.ndim != 2
        or mask.size == 0
        or mask.dtype.kind not in "buif"
        or not np.isfinite(mask).all()
    ):
        raise ValueError(f"mask {path} must be a nonempty finite 2D numeric array")
    if (mask < 0).any():
        raise ValueError(f"mask {path} must contain nonnegative values")
    return mask.astype(bool)


def _candidate_conflicts(metadata, candidate):
    """A queue row supplies context, not replacement prediction geometry."""
    if not isinstance(candidate, dict):
        return ["candidate context must be a JSON object"]
    try:
        position = [float(candidate[key]) for key in ("x", "y", "z")]
        _position(position)
        patch = _positive_number(
            candidate.get("patch_size", 64), "candidate patch size", integer=True
        )
        expected = {
            "source_uri": candidate.get("local_uri") or candidate.get("source_uri"),
            "position_xyz": position,
            "width_px": _positive_number(
                candidate.get("width", patch), "candidate width", integer=True
            ),
            "height_px": _positive_number(
                candidate.get("height", patch), "candidate height", integer=True
            ),
            "patch_size": patch,
            "output_image_path": candidate.get("output_image_path"),
        }
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        return [f"candidate geometry is invalid: {exc}"]
    failures = []
    for key, target in expected.items():
        actual = metadata.get(key)
        if key == "position_xyz":
            actual = metadata.get(key, metadata.get("3d_position_xyz"))
            if actual is None and all(k in metadata for k in ("x", "y", "z")):
                actual = [metadata[k] for k in ("x", "y", "z")]
        if (
            key == "source_uri"
            and isinstance(actual, str)
            and isinstance(target, str)
            and "://" not in actual
            and "://" not in target
        ):
            actual, target = str(Path(actual).resolve()), str(Path(target).resolve())
        if actual != target or target is None:
            failures.append(f"prediction {key} does not match the selected candidate")
    if candidate.get("voxel_um"):
        try:
            size = _positive_number(
                metadata.get("voxel_size_um"), "prediction voxel size"
            )
            target_size = _positive_number(
                candidate["voxel_um"], "candidate voxel size"
            )
            if not math.isclose(size, target_size, abs_tol=1e-6, rel_tol=0):
                failures.append(
                    "prediction voxel size does not match the selected candidate"
                )
        except ValueError as exc:
            failures.append(str(exc))
    return failures


def _check_vc3d_zarr(root, voxel_um, label, image_shape=None):
    """Validate small metadata files; do not scan a volume's chunk payloads."""
    group = _load_json(root / ".zgroup")
    if group.get("zarr_format") != 2:
        raise ValueError(f"{label} VC3D export must be a Zarr v2 group")
    meta = _load_json(root / "meta.json")
    array = _load_json(root / "0" / ".zarray")
    if meta.get("format") != "zarr":
        raise ValueError(f"{label} VC3D meta.json must include format='zarr'")
    size = _positive_number(meta.get("voxelsize"), "VC3D voxelsize")
    if voxel_um is not None and not math.isclose(
        size, voxel_um, abs_tol=1e-6, rel_tol=0
    ):
        raise ValueError(f"{label} VC3D voxelsize does not match metadata voxel size")
    shape = array.get("shape")
    chunks = array.get("chunks")
    if (
        not isinstance(shape, list)
        or len(shape) != 3
        or not isinstance(chunks, list)
        or len(chunks) != 3
    ):
        raise ValueError(
            f"{label} VC3D array must have three-dimensional shape and chunks"
        )
    dimensions = [_positive_number(v, "VC3D shape", integer=True) for v in shape]
    for chunk in chunks:
        _positive_number(chunk, "VC3D chunks", integer=True)
    expected = [
        _positive_number(meta.get(key), f"VC3D {key}", integer=True)
        for key in ("slices", "height", "width")
    ]
    if (
        dimensions != expected
        or dimensions[0] != 1
        or array.get("dtype") != "|u1"
        or array.get("zarr_format") != 2
    ):
        raise ValueError(
            f"{label} VC3D array must be a single uint8 slice matching meta.json dimensions"
        )
    if image_shape is not None and dimensions[1:] != list(image_shape):
        raise ValueError(f"{label} VC3D dimensions do not match prediction metadata")
    attrs = _load_json(root / ".zattrs")
    multiscales = attrs.get("multiscales")
    if (
        not isinstance(multiscales, list)
        or not multiscales
        or not isinstance(multiscales[0], dict)
    ):
        raise ValueError(f"{label} VC3D .zattrs must include multiscales metadata")
    scale_meta = multiscales[0]
    axes = scale_meta.get("axes")
    if (
        not isinstance(axes, list)
        or len(axes) != 3
        or any(not isinstance(axis, dict) for axis in axes)
    ):
        raise ValueError("OME-Zarr axes must be z/y/x spatial axes in micrometer units")
    if [axis.get("name") for axis in axes] != ["z", "y", "x"] or any(
        axis.get("type") != "space" or axis.get("unit") != "micrometer" for axis in axes
    ):
        raise ValueError("OME-Zarr axes must be z/y/x spatial axes in micrometer units")
    datasets = scale_meta.get("datasets")
    if (
        not isinstance(datasets, list)
        or len(datasets) != 1
        or not isinstance(datasets[0], dict)
        or datasets[0].get("path") != "0"
    ):
        raise ValueError("OME-Zarr dataset must describe the exported array '0'")
    transforms = datasets[0].get("coordinateTransformations")
    if not isinstance(transforms, list) or any(
        not isinstance(item, dict) for item in transforms
    ):
        raise ValueError("OME-Zarr dataset must include coordinateTransformations")
    scales = [item.get("scale") for item in transforms if item.get("type") == "scale"]
    if len(scales) != 1 or not isinstance(scales[0], list) or len(scales[0]) != 3:
        raise ValueError(
            "OME-Zarr spatial scale must contain three positive finite numbers"
        )
    spatial_scale = [_positive_number(v, "OME-Zarr spatial scale") for v in scales[0]]
    if not np.allclose(spatial_scale, [size] * 3, rtol=0, atol=1e-6):
        raise ValueError(
            f"OME-Zarr spatial scale {spatial_scale} does not match metadata voxel size {[size] * 3}"
        )
    translations = [
        item.get("translation")
        for item in transforms
        if item.get("type") == "translation"
    ]
    for translation in translations:
        if (
            not isinstance(translation, list)
            or len(translation) != 3
            or any(
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                for v in translation
            )
        ):
            raise ValueError("OME-Zarr translation must contain three finite numbers")
    if meta.get("origin_xyz") is not None:
        origin = _position(meta["origin_xyz"])
        if len(translations) != 1 or not np.allclose(
            translations[0], [v * size for v in reversed(origin)], rtol=0, atol=1e-6
        ):
            raise ValueError(
                "OME-Zarr translation must match VC3D origin_xyz in micrometers"
            )


def _report_template(metadata_path):
    return {
        "status": "FAIL",
        "scope": "local_artifact_checks",
        "prize_eligibility": "not_assessed",
        "metadata_path": str(metadata_path),
        "ml_window_px": None,
        "ml_window_mm": None,
        "checked_zarr_paths": [],
        "failures": [],
        "warnings": [],
    }


def _validate_metadata(
    metadata_path, metadata, train_mask=None, predict_mask=None, zarr_path=None
):
    report = _report_template(metadata_path)
    failures, warnings = report["failures"], report["warnings"]
    voxel_um = None
    image_shape = None
    # Every predictor records it; metadata without it cannot show that the
    # region was predicted in full.
    if metadata.get("prediction_complete") is not True:
        failures.append(
            "prediction is partial or its completeness is unverified; inference shards are not complete submission evidence"
        )
    # The ranker already refuses other recipes: QC-gated maps (before
    # 2026-10-13) sit near zero, and a map without a recipe cannot be placed.
    recipe = metadata.get("inference_recipe")
    ink_recipe = recipe.get("ink_probability") if isinstance(recipe, dict) else None
    if ink_recipe != INK_PROBABILITY:
        failures.append(
            f"ink map's recorded recipe is {ink_recipe!r}, not {INK_PROBABILITY!r}; "
            "QC-gated maps and maps without a recorded recipe are not comparable evidence"
        )
    if "num_parts" in metadata:
        try:
            if _positive_number(metadata["num_parts"], "num_parts", integer=True) != 1:
                failures.append(
                    "prediction is an inference shard; complete region evidence is required"
                )
        except (ValueError, TypeError, OverflowError) as exc:
            failures.append(str(exc))
    if "coverage_fraction" in metadata:
        value = metadata["coverage_fraction"]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value != 1.0
            or not math.isfinite(value)
        ):
            failures.append("prediction coverage is partial or unverified")
    try:
        voxel_um = _positive_number(
            metadata.get("voxel_size_um", metadata.get("voxel_resolution_um")),
            "voxel size",
        )
        patch_size = metadata.get("patch_size", metadata.get("window_size_pixels", 0))
        width = _positive_number(
            metadata.get("width_px", metadata.get("window_width_px", patch_size)),
            "width_px",
            integer=True,
        )
        height = _positive_number(
            metadata.get("height_px", metadata.get("window_height_px", patch_size)),
            "height_px",
            integer=True,
        )
        image_shape = (height, width)
        window = _positive_number(
            metadata.get("ml_window_px", patch_size or max(width, height)),
            "ML window",
            integer=True,
        )
        if (
            "patch_size" in metadata or "window_size_pixels" in metadata
        ) and _positive_number(patch_size, "patch_size", integer=True) != window:
            raise ValueError("ML window must match the declared model patch_size")
        model_config = metadata.get("model_config")
        if (
            isinstance(model_config, dict)
            and "patch_size" in model_config
            and _positive_number(
                model_config["patch_size"], "checkpoint patch_size", integer=True
            )
            != window
        ):
            raise ValueError("ML window must match the checkpoint patch_size")
        window_mm = window * voxel_um / 1000.0
        if not math.isfinite(window_mm):
            raise ValueError("physical ML window size must be finite")
        report["ml_window_px"], report["ml_window_mm"] = window, window_mm
        if window > MAX_ML_WINDOW_PX and window_mm > MAX_ML_WINDOW_MM + 1e-9:
            failures.append(
                f"ML window is {window}px/{window_mm:.3f}mm; local artifact contract expects <= {MAX_ML_WINDOW_PX}px or <= {MAX_ML_WINDOW_MM:.3f}mm"
            )
    except (ValueError, TypeError, OverflowError) as exc:
        failures.append(str(exc))
    if not isinstance(metadata.get("scroll_id"), str) or metadata[
        "scroll_id"
    ].strip().lower() in {"", "unknown"}:
        failures.append("metadata must include a known scroll_id")
    if not any(
        isinstance(metadata.get(key), str) and metadata[key].strip()
        for key in ("segmentation_id", "segmentation_file", "source_uri")
    ):
        failures.append(
            "metadata must include segmentation_id, segmentation_file, or source_uri"
        )
    try:
        position = metadata.get("position_xyz", metadata.get("3d_position_xyz"))
        if position is None and all(key in metadata for key in ("x", "y", "z")):
            position = [metadata[key] for key in ("x", "y", "z")]
        _position(position)
    except (ValueError, TypeError, OverflowError) as exc:
        failures.append(str(exc))
    for key in (
        "scale_bar_cm",
        "has_scale_bar_cm",
        "source_image_is_placeholder",
        "metadata_is_dry_run",
    ):
        value = metadata.get(key, False)
        if not isinstance(value, bool) and not (
            isinstance(value, str)
            and value.strip().lower()
            in {"1", "0", "true", "false", "yes", "no", "pass", "ok"}
        ):
            failures.append(f"{key} must be a boolean declaration")
    if not _as_bool(
        metadata.get("scale_bar_cm", metadata.get("has_scale_bar_cm", False))
    ):
        failures.append("metadata must declare a 1 cm scale bar")
    elif image_shape is not None and voxel_um is not None:
        # A declared bar is checked against the image's physical width: one
        # 1 cm long cannot be drawn on a region narrower than 1 cm.
        extent_mm = image_shape[1] * voxel_um / 1000.0
        if extent_mm < 10.0:
            failures.append(
                f"a 1 cm scale bar cannot fit a {image_shape[1]} px region at "
                f"{voxel_um:g} um ({extent_mm:.2f} mm wide)"
            )
    if _as_bool(metadata.get("source_image_is_placeholder", False)) or metadata.get(
        "evidence_mode"
    ) in ("placeholder", "placeholder_dry_run", "dummy"):
        failures.append(
            "submission image is marked as a placeholder/dry-run artifact; real CT-derived prediction evidence is required"
        )
    if _as_bool(metadata.get("metadata_is_dry_run", False)):
        failures.append(
            "metadata is marked as dry-run/default; real provenance is required"
        )
    if metadata.get("overlap_evidence_mode") in (
        "illustrative",
        "placeholder",
        "dummy",
    ):
        failures.append(
            "train/predict masks are illustrative; actual overlap evidence is required"
        )
    if "candidate" in metadata:
        failures.extend(_candidate_conflicts(metadata, metadata["candidate"]))
    image = metadata.get("output_image_path") or metadata.get("source_image_path")
    if not image:
        failures.append("a static discovery image path must be provided")
    else:
        try:
            image_path = resolve_artifact_path(image, metadata_path)
            if not image_path.is_file():
                raise ValueError("discovery image must be a regular file")
            with Image.open(image_path) as loaded:
                loaded.verify()
        except (OSError, ValueError, TypeError) as exc:
            failures.append(f"discovery image could not be read: {exc}")
    train = train_mask or metadata.get("train_mask_path")
    predict = predict_mask or metadata.get("predict_mask_path")
    if not train or not predict:
        failures.append(
            "train and predict masks must be provided; zero-overlap is unverified"
        )
    else:
        try:
            train_array = _load_mask(
                Path(train)
                if train_mask
                else resolve_artifact_path(train, metadata_path)
            )
            predict_array = _load_mask(
                Path(predict)
                if predict_mask
                else resolve_artifact_path(predict, metadata_path)
            )
            if train_array.shape != predict_array.shape:
                failures.append("train and predict masks must have the same shape")
            if not predict_array.any():
                failures.append("prediction mask must cover at least one pixel")
            if train_array.shape == predict_array.shape:
                overlap = int(np.logical_and(train_array, predict_array).sum())
                if overlap:
                    failures.append(f"train/predict masks overlap in {overlap} pixels")
        except (OSError, ValueError, TypeError) as exc:
            failures.append(f"overlap masks could not be read: {exc}")
    ink = (
        zarr_path
        or metadata.get("vc3d_zarr_path")
        or metadata.get("prediction_zarr_path")
    )
    fiber = metadata.get("fiber_vc3d_zarr_path") or metadata.get(
        "fiber_prediction_zarr_path"
    )
    if not ink:
        warnings.append(
            "VC3D/Zarr export path not provided; export compatibility is unverified"
        )
    if not fiber and (metadata.get("fiber_stats") or metadata.get("fiber_image_path")):
        warnings.append(
            "fiber artifact metadata is present but fiber VC3D/Zarr export path is missing"
        )
    for label, candidate in (("Ink", ink), ("Fiber", fiber)):
        if candidate:
            try:
                root = (
                    Path(candidate)
                    if label == "Ink" and zarr_path
                    else resolve_artifact_path(candidate, metadata_path)
                )
                report["checked_zarr_paths"].append(str(candidate))
                _check_vc3d_zarr(root, voxel_um, label, image_shape)
            except (OSError, ValueError, TypeError) as exc:
                failures.append(f"{label} VC3D export is invalid: {exc}")
    report["status"] = "FAIL" if failures else "PASS"
    return report


def validate(metadata_path, train_mask=None, predict_mask=None, zarr_path=None):
    try:
        metadata_path = _local_file_path(metadata_path)
        source = Snapshot.read(metadata_path, MAX_METADATA_BYTES)
        metadata = _decode_json(source.text(), metadata_path)
    except (OSError, ValueError, TypeError) as exc:
        report = _report_template(metadata_path)
        report["failures"].append(f"metadata could not be loaded: {exc}")
        return report
    report = _checked_validation(
        source.path, metadata, train_mask, predict_mask, zarr_path
    )
    report["metadata_source"] = source.provenance()
    try:
        source.verify()
    except (OSError, ValueError, TypeError) as exc:
        report["status"] = "FAIL"
        report["failures"].append(f"metadata changed during validation: {exc}")
    return report


def _checked_validation(
    metadata_path, metadata, train_mask=None, predict_mask=None, zarr_path=None
):
    try:
        return _validate_metadata(
            metadata_path, metadata, train_mask, predict_mask, zarr_path
        )
    except OverflowError as exc:
        report = _report_template(metadata_path)
        report["failures"].append(
            f"metadata numeric value is outside the supported range: {exc}"
        )
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata", required=True, help="Prediction or submission metadata JSON"
    )
    parser.add_argument("--train-mask", help="Actual train mask .npy/image")
    parser.add_argument("--predict-mask", help="Actual prediction mask .npy/image")
    parser.add_argument("--zarr", help="Optional VC3D prediction zarr directory")
    parser.add_argument("--out", help="Optional JSON report path")
    args = parser.parse_args(argv)
    try:
        metadata_input = _local_file_path(args.metadata)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Invalid metadata path: {exc}\n")
    source, metadata, error = None, {}, None
    try:
        source = Snapshot.read(metadata_input, MAX_METADATA_BYTES)
        metadata = _decode_json(source.text(), args.metadata)
    except (OSError, ValueError, TypeError) as exc:
        error = exc
    try:
        if args.out:
            metadata_file = source.path if source is not None else metadata_input
            reads = artifact_inputs(metadata_file, metadata, ())
            for key in ARTIFACT_INPUT_KEYS:
                try:
                    reads += artifact_inputs(metadata_file, metadata, (key,))[1:]
                except ValueError:
                    # It names no local file (a remote file: URI), so it cannot be the report. The validation
                    # below fails on it, and that FAIL must replace an earlier report, as it did before #279.
                    continue
            reads.append((args.metadata, "requested metadata path"))
            reads.append((ROOT / "autoresearch.lock", "research lock"))
            reads.extend(
                (value, name)
                for name, value in (
                    ("train mask", args.train_mask),
                    ("predict mask", args.predict_mask),
                    ("VC3D export", args.zarr),
                )
                if value
            )
            validate_plan_paths([(args.out, "validation report")], reads)
        if error is not None:
            report = _report_template(args.metadata)
            report["failures"].append(f"metadata could not be loaded: {error}")
        else:
            report = _checked_validation(
                source.path, metadata, args.train_mask, args.predict_mask, args.zarr
            )
        if source is not None:
            report["metadata_source"] = source.provenance()
            source.verify()
        if args.out:
            write_json(args.out, report)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Artifact validation failed: {exc}\n")
    encoded = json.dumps(report, indent=2, allow_nan=False)
    print(encoded)
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
