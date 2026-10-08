#!/usr/bin/env python3
"""Generate heuristic 3D ink pseudo-labels from an aligned XY prediction and CT.

The prediction must refer to the bbox's CT y/x columns. Flattened surface UV
maps need a registered transform before use here; matching dimensions are
insufficient. Model probabilities and CT quantiles are heuristics, not measured
3D ink ground truth. CT peaks approximate depth, not an observed surface.

Default thresholds are per-column across the requested z stack. Global mode
uses all voxels in prediction-active columns (the whole bbox when none are
active). Every final label must still pass the prediction, CT, and optional
CT-peak depth gates. Output is a new sparse, full-CT-shape Zarr with a declared
evaluated bbox; zeros outside that bbox are unevaluated.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import zarr

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import ARTIFACT_ERRORS, integer
from scripts.labeling.label_artifacts import (
    bbox_zyx,
    bounded_number,
    level_zero,
    new_output,
    publish_new,
    volume,
)
from scripts.validate_prize_artifact import (
    _check_vc3d_zarr,
    _load_json,
    resolve_artifact_path,
)


def _load_zarr_window(
    zarr_path: str, z0: int, z1: int, y0: int, y1: int, x0: int, x1: int
) -> np.ndarray:
    """Read a (z1-z0, y1-y0, x1-x0) window from a zarr; uint8 inputs scaled to float32 [0,1]."""
    _, arr = volume(zarr_path)
    _, selection = bbox_zyx((z0, z1, y0, y1, x0, x1), arr.shape)
    if arr.dtype.kind not in "uif":
        raise ValueError("CT must contain real numeric intensities")
    raw = arr[selection]
    result = raw.astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError("CT bbox contains nonfinite or unrepresentable intensities")
    if raw.dtype == np.uint8:
        result /= 255.0
    return result


def _load_2d_surface_prediction(
    zarr_path: str, expected_hw: tuple[int, int]
) -> np.ndarray:
    """Read the 2D ink-surface probability map and return shape (H, W) float32 in [0, 1].

    Accept a bare array or group level 0 of shape (H, W) or (1, H, W).
    Floating-point probabilities must be finite in [0, 1]; uint8 encodes [0, 255].
    """
    _, arr = level_zero(zarr_path)

    if arr.ndim == 3 and arr.shape[0] == 1:
        raw = np.asarray(arr[0])
    elif arr.ndim == 2:
        raw = np.asarray(arr)
    else:
        raise ValueError(
            f"ink prediction must have shape (H, W) or (1, H, W), got {arr.shape}"
        )

    if raw.shape != expected_hw:
        raise ValueError(
            f"ink prediction shape {raw.shape} != expected (h, w) from bbox {expected_hw}; "
            "the prediction zarr is in local-window coords, so the bbox h/w must match the prediction size"
        )

    if raw.dtype == np.uint8:
        return raw.astype(np.float32) / 255.0
    if (
        raw.dtype.kind != "f"
        or not np.isfinite(raw).all()
        or np.any((raw < 0) | (raw > 1))
    ):
        raise ValueError(
            "ink prediction must be finite probabilities in [0, 1] or uint8"
        )
    return raw.astype(np.float32)


def _prediction_alignment(prediction_path, ct_path, bbox, declared):
    if declared is not True:
        raise ValueError(
            "declare --aligned-prediction only after verifying CT XY alignment; surface UV maps require registration"
        )
    metadata_path = Path(prediction_path) / "meta.json"
    root, array = level_zero(prediction_path)
    if array.ndim not in (2, 3):
        raise ValueError("prediction must be a 2D map or singleton-depth map")
    if not metadata_path.exists():
        if "multiscales" in root.attrs:
            raise ValueError(
                "OME prediction requires producer meta.json with source_uri and origin_xyz; other frames need explicit registration"
            )
        return {
            "basis": "caller-declared CT XY alignment",
            "origin_zyx": list(bbox[::2]),
        }
    metadata = _load_json(metadata_path)
    origin = metadata.get("origin_xyz")
    if not isinstance(origin, list) or len(origin) != 3:
        raise ValueError("prediction metadata must declare origin_xyz")
    origin_zyx = tuple(
        integer(value, "prediction origin") for value in reversed(origin)
    )
    if origin_zyx != bbox[::2]:
        raise ValueError("prediction origin does not match the CT bbox")
    source = metadata.get("source_uri")
    if (
        not isinstance(source, str)
        or not source
        or Path(source).resolve() != Path(ct_path).resolve()
    ):
        raise ValueError("prediction source_uri does not match the CT source")
    for key, expected in (
        ("height", array.shape[-2]),
        ("width", array.shape[-1]),
        ("slices", 1),
    ):
        if (
            key in metadata
            and integer(metadata[key], f"prediction {key}", 1) != expected
        ):
            raise ValueError(f"prediction metadata {key} does not match the array")
    if metadata.get("prediction_complete", True) is not True:
        raise ValueError("partial prediction is not a complete aligned map")
    if "multiscales" in root.attrs:
        _check_vc3d_zarr(
            Path(prediction_path),
            None,
            "ink prediction",
            (bbox[3] - bbox[2], bbox[5] - bbox[4]),
        )
        # The shared validator checks axes, units, dimensions, and transforms.
        # This workflow also declines compositions outside the producer layout.
        multiscales = root.attrs["multiscales"]
        if len(multiscales) != 1:
            raise ValueError("unsupported OME prediction multiscales")
        frame = multiscales[0]
        transforms = frame["datasets"][0]["coordinateTransformations"]
        if [item.get("type") for item in transforms] != [
            "scale",
            "translation",
        ] or frame.get("coordinateTransformations"):
            raise ValueError(
                "OME prediction coordinates disagree with the supported producer frame"
            )
    return {
        "basis": "caller-declared CT XY alignment with matching producer metadata",
        "origin_zyx": list(origin_zyx),
        "producer_metadata": metadata,
    }


def _prediction_run_metadata(prediction_path, ct_path, bbox, metadata_path):
    """Check supplied run metadata or the producer's conventional sibling file."""
    explicit = metadata_path is not None
    path = (
        Path(metadata_path)
        if explicit
        else Path(prediction_path).with_name(f"{Path(prediction_path).stem}_meta.json")
    )
    if not explicit and not path.exists():
        return {"coverage_basis": "caller-declared fully evaluated prediction"}
    metadata = _load_json(path)
    if (
        metadata.get("prediction_complete") is not True
        or integer(metadata.get("num_parts", 1), "prediction num_parts", 1) != 1
        or integer(metadata.get("part_id", 0), "prediction part_id") != 0
    ):
        raise ValueError(
            "prediction run metadata identifies partial or unverified coverage"
        )
    if (
        bounded_number(
            metadata.get("coverage_fraction"), "prediction coverage_fraction", 0, 1
        )
        != 1
    ):
        raise ValueError("prediction run metadata identifies partial coverage")
    for key, expected in (("source_uri", ct_path), ("vc3d_zarr_path", prediction_path)):
        value = metadata.get(key)
        if (
            not isinstance(value, str)
            or not value
            or resolve_artifact_path(value, path).resolve() != Path(expected).resolve()
        ):
            raise ValueError(f"prediction run metadata {key} does not match the input")
    position = metadata.get("position_xyz")
    if (
        not isinstance(position, list)
        or len(position) != 3
        or tuple(integer(value, "prediction position") for value in reversed(position))
        != bbox[::2]
    ):
        raise ValueError("prediction run metadata position does not match the CT bbox")
    if (
        integer(metadata.get("height_px"), "prediction height_px", 1)
        != bbox[3] - bbox[2]
        or integer(metadata.get("width_px"), "prediction width_px", 1)
        != bbox[5] - bbox[4]
    ):
        raise ValueError("prediction run metadata dimensions do not match the bbox")
    return {
        "coverage_basis": "matching complete prediction run metadata",
        "path": str(path.resolve()),
        "metadata": metadata,
    }


def _apply_ct_peak_restriction(
    label_volume: np.ndarray, ct: np.ndarray, surface_window: int
) -> tuple[np.ndarray, int]:
    """Keep labels only within +/- surface_window voxels of the per-column CT peak.

    Ink in a papyrus scroll sits in a thin shell on the surface, not in the bulk.
    We approximate the surface depth at each (y, x) column as ``argmax_z(CT)`` —
    the z-index with the highest CT intensity in that column — and reject labels
    farther than ``surface_window`` voxels from it.
    """
    if surface_window <= 0:
        return label_volume, 0
    surface_z = np.argmax(ct, axis=0).astype(np.int32)  # (H, W)
    z_indices = np.arange(ct.shape[0], dtype=np.int32)[:, None, None]  # (D, 1, 1)
    within_window = (
        np.abs(z_indices - surface_z[None, :, :]) <= surface_window
    )  # (D, H, W)
    before = int(label_volume.sum())
    restricted = (label_volume.astype(bool) & within_window).astype(np.uint8)
    return restricted, before - int(restricted.sum())


def _write_debug_png(
    png_path: str,
    ct: np.ndarray,
    ink_2d: np.ndarray,
    label_volume: np.ndarray,
    params_label: str,
    ink_threshold: float,
    z_origin: int,
    num_slices: int = 4,
) -> None:
    """Write a contact-sheet PNG comparing CT vs label overlay at evenly-spaced z-slices.

    Layout (rows × cols):
      Row 0: ``num_slices`` CT slices in grayscale.
      Row 1: same z-slices with label voxels overlaid in red and the 2D ink-prediction
             contour in cyan.

    Designed for quick eyeballing of "do the labels land on real structure or noise?"
    rather than publication-quality figures.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    depth = ct.shape[0]
    z_indices = np.linspace(0, depth - 1, num=num_slices, dtype=int)

    fig, axes = plt.subplots(
        2, num_slices, figsize=(2.4 * num_slices, 5.4), squeeze=False
    )
    fig.suptitle(params_label, fontsize=9)

    # CT vmin/vmax: use 1-99 percentile so the contrast is consistent
    ct_lo, ct_hi = np.percentile(ct, [1, 99])
    label_cmap = ListedColormap([(0, 0, 0, 0), (1, 0.1, 0.1, 0.55)])

    for col, z in enumerate(z_indices):
        ax_top = axes[0, col]
        ax_top.imshow(
            ct[z], cmap="gray", vmin=ct_lo, vmax=ct_hi, interpolation="nearest"
        )
        ax_top.set_title(f"CT z={z + z_origin}", fontsize=8)
        ax_top.axis("off")

        ax_bot = axes[1, col]
        ax_bot.imshow(
            ct[z], cmap="gray", vmin=ct_lo, vmax=ct_hi, interpolation="nearest"
        )
        ax_bot.imshow(
            label_volume[z], cmap=label_cmap, vmin=0, vmax=1, interpolation="nearest"
        )
        if min(ink_2d.shape) > 1 and ink_2d.min() < ink_threshold < ink_2d.max():
            ax_bot.contour(
                ink_2d, levels=[ink_threshold], colors="cyan", linewidths=0.6, alpha=0.7
            )
        n_labels_this_z = int(label_volume[z].sum())
        ax_bot.set_title(
            f"label+ink @z={z + z_origin} ({n_labels_this_z}px)", fontsize=8
        )
        ax_bot.axis("off")

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _filter_small_components(
    label_volume: np.ndarray, min_voxels: int
) -> tuple[np.ndarray, int | None, int | None]:
    """Drop 26-connected components below ``min_voxels``.

    Returns the filtered label volume, the number of CCs found before filtering,
    and the number of CCs kept. Counts are None when filtering is disabled.
    """
    if min_voxels <= 1:
        return label_volume, None, None
    from scipy.ndimage import label as cc_label

    structure = np.ones((3, 3, 3), dtype=bool)  # 26-connectivity
    labeled, num_components = cc_label(label_volume, structure=structure)
    if num_components == 0:
        return label_volume, 0, 0
    counts = np.bincount(labeled.ravel())
    counts[0] = 0  # never count background
    keep_mask = counts >= min_voxels
    keep_mask[0] = False
    remap = np.zeros(counts.shape[0], dtype=np.uint8)
    remap[keep_mask] = 1
    filtered = remap[labeled].astype(np.uint8)
    return filtered, int(num_components), int(keep_mask.sum())


def generate_3d_ink_labels(
    ct_path: str,
    ink_pred_path: str,
    output_path: str,
    z0: int,
    z1: int,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
    ink_threshold: float = 0.5,
    ct_percentile: float = 85.0,
    global_ct_threshold: bool = False,
    morphological_close: int = 0,
    surface_window: int = 0,
    min_component_voxels: int = 0,
    debug_png: str | None = None,
    aligned_prediction: bool = False,
    prediction_metadata: str | None = None,
) -> dict:
    """Run the CT-gated 3D ink labelling on the specified bbox.

    Parameters
    ----------
    ct_path
        Zarr of the CT volume (full-scroll shape; we slice the bbox).
    ink_pred_path
        Aligned XY probability map, not an unregistered flattened surface map.
    output_path
        New sparse Zarr artifact; existing outputs are rejected.
    z0, z1, y0, y1, x0, x1
        Bbox, inclusive-exclusive.
    ink_threshold
        Minimum 2D ink probability for a (y, x) column to be eligible.
    ct_percentile
        Per-column CT percentile used as the intensity gate. With
        ``global_ct_threshold=True`` uses voxels in prediction-active columns,
        falling back to the whole bbox when no columns are active.
    morphological_close
        Cubic closing radius (side length 2*r+1). Final labels remain inside all
        gates; closing cannot recover ink unsupported by those gates.
    surface_window
        If > 0, restrict labels to voxels within +/- surface_window of the
        per-column CT-intensity peak. This is a depth heuristic.
    min_component_voxels
        If > 1, drop 26-connected components below this size as noise.
    """
    start = time.perf_counter()
    sources = [ct_path, ink_pred_path]
    if prediction_metadata is not None:
        sources.append(prediction_metadata)
    output_path = new_output(output_path, *sources)
    ink_threshold = bounded_number(ink_threshold, "ink_threshold", 0, 1)
    ct_percentile = bounded_number(ct_percentile, "ct_percentile", 0, 100)
    morphological_close = integer(morphological_close, "closing radius")
    surface_window = integer(surface_window, "surface_window")
    min_component_voxels = integer(min_component_voxels, "min_component_voxels")
    if not isinstance(global_ct_threshold, bool):
        raise ValueError("global_ct_threshold must be boolean")
    ct_root, ct_array = volume(ct_path)
    pred_root, pred_array = level_zero(ink_pred_path)
    bbox, selection = bbox_zyx((z0, z1, y0, y1, x0, x1), ct_array.shape)
    z0, z1, y0, y1, x0, x1 = bbox
    alignment = _prediction_alignment(ink_pred_path, ct_path, bbox, aligned_prediction)
    alignment["run_metadata"] = _prediction_run_metadata(
        ink_pred_path, ct_path, bbox, prediction_metadata
    )
    debug_name = None
    if debug_png is not None:
        debug_path = Path(debug_png).resolve()
        if debug_path.parent != output_path or debug_path.suffix.lower() != ".png":
            raise ValueError(
                "debug PNG must be a direct .png child of the new output directory"
            )
        debug_name = debug_path.name
    ct = _load_zarr_window(ct_path, z0, z1, y0, y1, x0, x1)
    ink_2d = _load_2d_surface_prediction(ink_pred_path, expected_hw=(y1 - y0, x1 - x0))

    if ct.shape[1:] != ink_2d.shape:
        raise ValueError(
            f"CT yx shape {ct.shape[1:]} != ink prediction shape {ink_2d.shape}"
        )

    # 2D surface gate
    ink_mask_2d = ink_2d >= ink_threshold  # (H, W) bool

    # 3D intensity gate
    if global_ct_threshold:
        threshold_scalar = float(
            np.percentile(
                ct[:, ink_mask_2d] if ink_mask_2d.any() else ct, ct_percentile
            )
        )
        high_intensity = ct >= threshold_scalar
    else:
        # Per-column threshold: each (y, x) gets its own quantile across z.
        # Where the 2D ink mask is False, threshold is irrelevant; we leave it as inf.
        per_col_thresh = np.full(ink_2d.shape, np.inf, dtype=np.float32)
        if ink_mask_2d.any():
            cols_ct = ct[:, ink_mask_2d]  # (D, K) where K = number of active columns
            quantile_vals = np.percentile(cols_ct, ct_percentile, axis=0)  # (K,)
            per_col_thresh[ink_mask_2d] = quantile_vals
        high_intensity = ct >= per_col_thresh[None, :, :]

    ink_mask_3d_surface = np.broadcast_to(ink_mask_2d[None, :, :], ct.shape)
    label_volume = (ink_mask_3d_surface & high_intensity).astype(np.uint8)
    pre_refinement = int(label_volume.sum())

    # Refinement 1: thin-shell surface restriction
    label_volume, dropped_off_surface = _apply_ct_peak_restriction(
        label_volume, ct, surface_window
    )
    eligible = label_volume.astype(bool)

    # Refinement 2: gated closing; unsupported holes remain excluded.
    if morphological_close > 0:
        from scipy.ndimage import binary_closing

        structure = np.ones((2 * morphological_close + 1,) * 3, dtype=bool)
        label_volume = (
            binary_closing(label_volume, structure=structure) & eligible
        ).astype(np.uint8)

    # Refinement 3: drop tiny connected components as noise
    label_volume, cc_total, cc_kept = _filter_small_components(
        label_volume, min_component_voxels
    )

    result = {
        "bbox": (z0, z1, y0, y1, x0, x1),
        "ink_threshold": ink_threshold,
        "ct_percentile": ct_percentile,
        "global_ct_threshold": global_ct_threshold,
        "morphological_close": morphological_close,
        "surface_window": surface_window,
        "min_component_voxels": min_component_voxels,
        "voxels": int(label_volume.size),
        "labeled_voxels": int(label_volume.sum()),
        "labeled_voxels_pre_refinement": pre_refinement,
        "label_fraction": float(label_volume.mean()),
        "voxels_dropped_off_surface": dropped_off_surface,
        "connected_components_total": cc_total,
        "connected_components_kept": cc_kept,
        "active_surface_columns": int(ink_mask_2d.sum()),
        "surface_active_fraction": float(ink_mask_2d.mean()),
        "elapsed_s": time.perf_counter() - start,
    }
    provenance = {
        "contract": 1,
        "label_kind": "heuristic_3d_ink_pseudo_labels",
        "axes": ["z", "y", "x"],
        "ct_path": str(Path(ct_path).resolve()),
        "prediction_path": str(Path(ink_pred_path).resolve()),
        "ct_shape_zyx": list(ct_array.shape),
        "ct_dtype": str(ct_array.dtype),
        "ct_root_attrs": dict(ct_root.attrs),
        "ct_array_attrs": dict(ct_array.attrs),
        "prediction_root_attrs": dict(pred_root.attrs),
        "prediction_array_attrs": dict(pred_array.attrs),
        "evaluated_bbox_zyx": list(bbox),
        "outside_bbox": "unevaluated; zero is not a verified negative",
        "alignment": alignment,
        "debug_png": debug_name,
        "result": result,
    }
    # Reject nonfinite metadata before publication, including optional producer metadata.
    json.dumps(provenance, allow_nan=False)
    with publish_new(output_path) as staging:
        out_arr = zarr.open(
            str(staging),
            mode="w",
            shape=ct_array.shape,
            chunks=tuple(min(128, size) for size in ct_array.shape),
            dtype="uint8",
            fill_value=0,
            write_empty_chunks=False,
        )
        out_arr[selection] = label_volume
        if debug_name is not None:
            params_label = (
                f"pseudo-labels: ink>={ink_threshold} ct%={ct_percentile} "
                f"peak_win={surface_window} cc>={min_component_voxels} radius={morphological_close}"
            )
            _write_debug_png(
                str(staging / debug_name),
                ct,
                ink_2d,
                label_volume,
                params_label,
                ink_threshold,
                z0,
            )
        # Metadata marks completion only after every requested artifact succeeds.
        result["elapsed_s"] = time.perf_counter() - start
        out_arr.attrs["ink_label_completion"] = provenance
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ct", required=True, help="Path to the input CT zarr.")
    parser.add_argument(
        "--ink-pred",
        required=True,
        help="Path to a CT-XY-aligned 2D ink probability Zarr.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="New output 3D pseudo-label Zarr (uint8); existing paths fail.",
    )
    parser.add_argument(
        "--aligned-prediction",
        action="store_true",
        help="Declare a fully evaluated prediction whose pixels match the bbox's CT XY columns; unregistered UV maps are unsupported.",
    )
    parser.add_argument(
        "--prediction-metadata",
        help="Prediction run JSON; otherwise inspect the conventional PRED_STEM_meta.json sibling when present.",
    )
    parser.add_argument(
        "--bbox",
        type=int,
        nargs=6,
        required=True,
        metavar=("Z0", "Z1", "Y0", "Y1", "X0", "X1"),
        help="Inclusive-exclusive bbox in voxel coordinates.",
    )
    parser.add_argument("--ink-threshold", type=float, default=0.5)
    parser.add_argument(
        "--ct-percentile",
        type=float,
        default=85.0,
        help="CT intensity percentile used as the per-column gate (or global with --global-ct-threshold).",
    )
    parser.add_argument(
        "--global-ct-threshold",
        action="store_true",
        help="Use one scalar threshold over voxels in prediction-active columns.",
    )
    parser.add_argument(
        "--close",
        type=int,
        default=0,
        help="Cubic closing radius (side 2*r+1); results stay within all gates. Default 0 disables.",
    )
    parser.add_argument(
        "--surface-window",
        type=int,
        default=0,
        help=(
            "If > 0, restrict labels to voxels within +/- this many z-voxels of the "
            "per-column CT-intensity peak. This is a depth heuristic. Default 0 disables."
        ),
    )
    parser.add_argument(
        "--min-component-voxels",
        type=int,
        default=0,
        help=(
            "If > 1, drop 26-connected components below this voxel count as noise. "
            "Default 0 (disabled)."
        ),
    )
    parser.add_argument(
        "--debug-png",
        type=str,
        default=None,
        help=(
            "Optional PNG path inside the output directory (e.g. OUTPUT/debug.png). Writes a 2-row contact sheet of CT slices vs labeled "
            "overlay so reviewers can eyeball quality without loading the zarr."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    z0, z1, y0, y1, x0, x1 = args.bbox
    print(
        f"# generate_3d_ink_labels: ct={args.ct} ink_pred={args.ink_pred} "
        f"output={args.output} bbox=({z0},{z1},{y0},{y1},{x0},{x1}) "
        f"ink_threshold={args.ink_threshold} ct_percentile={args.ct_percentile} "
        f"global={args.global_ct_threshold} close={args.close} "
        f"surface_window={args.surface_window} min_cc={args.min_component_voxels}"
    )
    try:
        result = generate_3d_ink_labels(
            args.ct,
            args.ink_pred,
            args.output,
            z0,
            z1,
            y0,
            y1,
            x0,
            x1,
            ink_threshold=args.ink_threshold,
            ct_percentile=args.ct_percentile,
            global_ct_threshold=args.global_ct_threshold,
            morphological_close=args.close,
            surface_window=args.surface_window,
            min_component_voxels=args.min_component_voxels,
            debug_png=args.debug_png,
            aligned_prediction=args.aligned_prediction,
            prediction_metadata=args.prediction_metadata,
        )
    except (*ARTIFACT_ERRORS, RuntimeError) as exc:
        print(f"3D pseudo-label generation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"# OK voxels={result['voxels']} labeled={result['labeled_voxels']} "
        f"(pre_refinement={result['labeled_voxels_pre_refinement']}) "
        f"label_fraction={result['label_fraction']:.6f} "
        f"outside_peak_window_dropped={result['voxels_dropped_off_surface']} "
        f"cc_total={result['connected_components_total']} cc_kept={result['connected_components_kept']} "
        f"surface_active_fraction={result['surface_active_fraction']:.6f} "
        f"elapsed={result['elapsed_s']:.2f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
