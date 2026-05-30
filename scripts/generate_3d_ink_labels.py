#!/usr/bin/env python3
"""Generate true-3D ink pseudo-labels by gating a 2D ink prediction with CT intensity.

Addresses `ScrollPrize/villa#192 <https://github.com/ScrollPrize/villa/issues/192>`_
("Accurate 3d ink labels", labelled ``good first issue`` + ``help wanted``).

## The annotator-bias / 2D-projection problem

Current ink labels are drawn by a human annotator looking at the model's
prediction and filling in *what they think the letter is*. That has two
failure modes called out explicitly in #192:

1. **Annotator bias** — the label reflects the human's guess at the letter,
   not what's actually detectable in the CT. The model then over-fits to
   features the human thought should be there.
2. **2D → 3D smearing** — the 2D mask is then replicated across all z-layers
   the surface touches, so the resulting "3D" label is just an extruded
   prism. Real ink is *thin and localised* in z.

## Approach in this script

The model's 2D ink probability already encodes "where on the surface does ink
appear, as the model sees it." We use that as the spatial gate. Then we
intersect it with the **CT intensity at the corresponding (z, y, x) voxel** so
only voxels that are *actually radiopaque* (i.e., contain ink material) get
labelled.

Pipeline::

    for each voxel (z, y, x) in bbox:
        ink_2d = ink_pred[y, x]          # 2D surface probability (model)
        ct_z   = ct[z, y, x]              # CT intensity in 3D
        label  = (ink_2d  >= ink_thresh) AND
                 (ct_z    >= ct_percentile_thresh)

The CT threshold is computed *per-column* by default (each (y, x) gets its own
quantile of the CT z-stack), so we adapt to local papyrus density rather than
imposing a global threshold. ``--global-ct-threshold`` switches to a single
scalar threshold computed from the whole bbox.

The result is a 3D zarr where ink labels are present only at voxels where
**both** the model and the CT agree there's ink — addressing #192's
"only the detectable ink patterns" criterion.

## Status: SKETCH

First cut. Several knobs are obvious next-cuts:

* Use the ink probability as a *weight* rather than a hard threshold.
* Add a thin-shell constraint: only label voxels within N voxels of the
  predicted surface (rejects bulk papyrus volume).
* Apply morphological closing to fill 1-voxel holes inside letterforms.
* Cross-validate against any existing manual 3D ink labels if available.

Discuss in #192 before treating output as ground truth.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np


def _load_zarr_window(
    zarr_path: str, z0: int, z1: int, y0: int, y1: int, x0: int, x1: int
) -> np.ndarray:
    """Read a (z1-z0, y1-y0, x1-x0) window from a zarr; uint8 inputs scaled to float32 [0,1]."""
    import zarr

    store = zarr.open(zarr_path, mode="r")
    arr = store if isinstance(store, zarr.core.Array) else store["0"]

    z1 = min(z1, arr.shape[0])
    y1 = min(y1, arr.shape[1])
    x1 = min(x1, arr.shape[2])
    if z0 >= z1 or y0 >= y1 or x0 >= x1:
        raise ValueError(f"empty bbox vs shape {arr.shape}")

    raw = arr[z0:z1, y0:y1, x0:x1]
    if raw.dtype == np.uint8:
        return raw.astype(np.float32) / 255.0
    return raw.astype(np.float32)


def _load_2d_surface_prediction(
    zarr_path: str, expected_hw: tuple[int, int]
) -> np.ndarray:
    """Read the 2D ink-surface probability map and return shape (H, W) float32 in [0, 1].

    The prediction zarrs the autoresearch loop emits have shape ``(1, H, W)`` and live
    under ``<zarr_path>/0`` (rather than at the group root). We try the ``/0`` subdir
    first, fall back to opening ``zarr_path`` directly. The prediction's coordinate
    frame is LOCAL to the prediction window, so we read the full array and check the
    spatial shape against ``expected_hw`` (which the caller derives from the bbox).
    uint8 inputs are scaled to [0, 1] float32.
    """
    import zarr

    try:
        arr = zarr.open(f"{zarr_path}/0", mode="r")
    except Exception:
        store = zarr.open(zarr_path, mode="r")
        arr = store if isinstance(store, zarr.core.Array) else store["0"]

    if arr.ndim == 3:
        raw = np.asarray(arr[0])
    elif arr.ndim == 2:
        raw = np.asarray(arr)
    else:
        raise ValueError(f"unexpected ink prediction zarr ndim {arr.ndim}")

    if raw.shape != expected_hw:
        raise ValueError(
            f"ink prediction shape {raw.shape} != expected (h, w) from bbox {expected_hw}; "
            "the prediction zarr is in local-window coords, so the bbox h/w must match the prediction size"
        )

    if raw.dtype == np.uint8:
        return raw.astype(np.float32) / 255.0
    return raw.astype(np.float32)


def _ensure_output_zarr(
    output_path: str, shape: tuple[int, int, int], chunks=(128, 128, 128)
):
    import zarr

    if Path(output_path).exists():
        return zarr.open(output_path, mode="a")
    return zarr.open(
        output_path,
        mode="w",
        shape=shape,
        chunks=chunks,
        dtype="uint8",
        fill_value=0,
    )


def _apply_surface_manifold_restriction(
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
        ax_top.set_title(f"CT z={z}", fontsize=8)
        ax_top.axis("off")

        ax_bot = axes[1, col]
        ax_bot.imshow(
            ct[z], cmap="gray", vmin=ct_lo, vmax=ct_hi, interpolation="nearest"
        )
        ax_bot.imshow(
            label_volume[z], cmap=label_cmap, vmin=0, vmax=1, interpolation="nearest"
        )
        # Cyan contour of the 2D ink mask (where >= 0.1 by default, hardcoded)
        ax_bot.contour(ink_2d, levels=[0.1], colors="cyan", linewidths=0.6, alpha=0.7)
        n_labels_this_z = int(label_volume[z].sum())
        ax_bot.set_title(f"label+ink @z={z} ({n_labels_this_z}px)", fontsize=8)
        ax_bot.axis("off")

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _filter_small_components(
    label_volume: np.ndarray, min_voxels: int
) -> tuple[np.ndarray, int, int]:
    """Drop 26-connected components below ``min_voxels``.

    Returns the filtered label volume, the number of CCs found before filtering,
    and the number of CCs kept.
    """
    if min_voxels <= 1:
        return label_volume, 0, 0
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
) -> dict:
    """Run the CT-gated 3D ink labelling on the specified bbox.

    Parameters
    ----------
    ct_path
        Zarr of the CT volume (full-scroll shape; we slice the bbox).
    ink_pred_path
        Zarr of the 2D ink-probability surface map (the predict.py output).
    output_path
        Zarr of the 3D ink-label volume to write into.
    z0, z1, y0, y1, x0, x1
        Bbox, inclusive-exclusive.
    ink_threshold
        Minimum 2D ink probability for a (y, x) column to be eligible.
    ct_percentile
        Per-column CT percentile used as the intensity gate. With
        ``global_ct_threshold=True`` this is computed over the whole bbox.
    morphological_close
        Optional radius for a binary closing step to fill 1-voxel holes
        in letterforms. ``0`` (default) disables.
    surface_window
        If > 0, restrict labels to voxels within +/- surface_window of the
        per-column CT-intensity peak. Models the fact that ink sits in a thin
        shell on the papyrus surface, not in the bulk.
    min_component_voxels
        If > 1, drop 26-connected components below this size as noise.
    """
    import zarr  # noqa: F401

    start = time.perf_counter()
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
    label_volume, dropped_off_surface = _apply_surface_manifold_restriction(
        label_volume, ct, surface_window
    )

    # Refinement 2: morphological closing (fill 1-voxel holes in letterforms)
    if morphological_close > 0:
        from scipy.ndimage import binary_closing

        structure = np.ones(
            (morphological_close, morphological_close, morphological_close), dtype=bool
        )
        label_volume = binary_closing(label_volume, structure=structure).astype(
            np.uint8
        )

    # Refinement 3: drop tiny connected components as noise
    label_volume, cc_total, cc_kept = _filter_small_components(
        label_volume, min_component_voxels
    )

    # Write zarr
    out_arr = _ensure_output_zarr(output_path, _infer_full_shape(ct_path))
    out_arr[z0:z1, y0:y1, x0:x1] = label_volume

    # Optional debug PNG
    if debug_png is not None:
        params_label = (
            f"ink>={ink_threshold} ct%={ct_percentile} "
            f"surf_win={surface_window} cc>={min_component_voxels} close={morphological_close}"
        )
        _write_debug_png(debug_png, ct, ink_2d, label_volume, params_label)

    elapsed = time.perf_counter() - start
    return {
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
        "elapsed_s": elapsed,
    }


def _infer_full_shape(ct_path: str) -> tuple[int, int, int]:
    """Read the CT zarr's full shape so the output zarr can mirror it."""
    import zarr

    store = zarr.open(ct_path, mode="r")
    arr = store if isinstance(store, zarr.core.Array) else store["0"]
    return tuple(int(s) for s in arr.shape[:3])


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ct", required=True, help="Path to the input CT zarr.")
    parser.add_argument(
        "--ink-pred",
        required=True,
        help="Path to the 2D ink-probability zarr (predict.py output).",
    )
    parser.add_argument(
        "--output", required=True, help="Path to the output 3D ink-label zarr (uint8)."
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
        help="Use one scalar CT threshold over the whole bbox instead of per-column quantiles.",
    )
    parser.add_argument(
        "--close",
        type=int,
        default=0,
        help="Optional radius for a binary closing step to fill 1-voxel holes (default 0, disabled).",
    )
    parser.add_argument(
        "--surface-window",
        type=int,
        default=0,
        help=(
            "If > 0, restrict labels to voxels within +/- this many z-voxels of the "
            "per-column CT-intensity peak. Models the thin-shell nature of ink on a "
            "papyrus surface. Default 0 (disabled)."
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
            "Optional PNG path. Writes a 2-row contact sheet of CT slices vs labeled "
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
    )
    print(
        f"# OK voxels={result['voxels']} labeled={result['labeled_voxels']} "
        f"(pre_refinement={result['labeled_voxels_pre_refinement']}) "
        f"label_fraction={result['label_fraction']:.6f} "
        f"off_surface_dropped={result['voxels_dropped_off_surface']} "
        f"cc_total={result['connected_components_total']} cc_kept={result['connected_components_kept']} "
        f"surface_active_fraction={result['surface_active_fraction']:.6f} "
        f"elapsed={result['elapsed_s']:.2f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
