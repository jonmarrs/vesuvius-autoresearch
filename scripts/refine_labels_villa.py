#!/usr/bin/env python3
"""Vesuvius Autoresearch: Label Refinement via EDT + Frangi (Villa Integration).

Wraps the ``villa/vesuvius/src/vesuvius/image_proc/run/edt_frangi_label.py``
pipeline from the ScrollPrize/villa submodule.  For each label volume in
``--labels_dir`` (Zarr **or** TIFF) the script:

1. Computes an inverse-EDT dilation to expand label boundaries.
2. Runs Frangi-style ridge / vesselness detection to capture fiber-aligned
   structure.
3. Applies morphological cleanup (small-component removal, hole filling).
4. Saves the refined binary labels to ``--output_dir``, preserving filenames.

If Villa's ``vesuvius.image_proc`` is importable the script delegates to it
directly; otherwise an equivalent pipeline is built from ``scipy.ndimage`` and
``skimage.filters``.

Usage::

    uv run scripts/refine_labels_villa.py \\
        --labels_dir local_data/labels \\
        --output_dir local_data/labels_refined \\
        --sigma_frangi 1.0 \\
        --edt_threshold 0.5

See ``--help`` for the full option set.
"""

from __future__ import annotations

import argparse
import glob
import logging
import multiprocessing
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Villa path injection (mirrors preprocess_labels.py & generate_fiber_labels.py)
# ---------------------------------------------------------------------------
_VESUVIUS_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "villa", "vesuvius", "src")
)
if _VESUVIUS_SRC not in sys.path:
    sys.path.insert(0, _VESUVIUS_SRC)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend selection: prefer Villa, fall back to scipy/skimage
# ---------------------------------------------------------------------------
_VILLA_AVAILABLE = False

try:
    from vesuvius.image_proc.distance import dilate_by_inverse_edt
    from vesuvius.image_proc.features.ridges_vessels import (
        detect_ridges_2d,
        detect_ridges_3d,
    )

    _VILLA_AVAILABLE = True
    log.info("Villa image_proc backend loaded successfully.")
except ImportError:
    log.warning(
        "Villa image_proc not importable — using scipy/skimage fallback pipeline."
    )


def _fallback_dilate_by_inverse_edt(
    binary_volume: np.ndarray, dilation_distance: float
) -> np.ndarray:
    """Inverse-EDT dilation (equivalent to ``vesuvius.image_proc.distance``)."""
    from scipy.ndimage import distance_transform_edt

    eps = 1e-6
    edt = distance_transform_edt(1 - binary_volume)
    inv_edt = 1.0 / (edt + eps)
    threshold = 1.0 / dilation_distance
    return (inv_edt > threshold).astype(np.uint8)


def _fallback_detect_ridges(volume: np.ndarray, sigma: float) -> np.ndarray:
    """Frangi vesselness via skimage (fallback when Villa is unavailable)."""
    from skimage.filters import frangi

    if volume.ndim == 2 or volume.ndim == 3:
        return frangi(volume, sigmas=[sigma], black_ridges=False)
    else:
        raise ValueError(f"Unsupported dimensionality: {volume.ndim}")


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_volume(path: Path) -> np.ndarray:
    """Load a label volume from a ``.zarr`` directory or ``.tif`` / ``.tiff`` file."""
    suffix = path.suffix.lower()

    if suffix == ".zarr" or path.is_dir() and (path / ".zarray").exists():
        import zarr

        store = zarr.open(str(path), mode="r")
        # Handle both raw arrays and OME-Zarr (multiscale level "0")
        if isinstance(store, zarr.core.Array):
            return np.asarray(store)
        if "0" in store:
            return np.asarray(store["0"])
        # Last resort: iterate store keys
        for key in store:
            arr = store[key]
            if isinstance(arr, zarr.core.Array):
                return np.asarray(arr)
        raise ValueError(f"Could not locate an array inside Zarr store: {path}")

    if suffix in {".tif", ".tiff"}:
        import tifffile

        return tifffile.imread(str(path))

    if suffix == ".png":
        from PIL import Image

        with Image.open(path) as img:
            arr = np.array(img)
            if arr.ndim == 3:
                arr = arr[:, :, 0]
            return arr

    raise ValueError(f"Unsupported file format: {path}")


def _save_volume(volume: np.ndarray, output_path: Path) -> None:
    """Save a volume preserving the original format (TIFF or Zarr)."""
    suffix = output_path.suffix.lower()

    if suffix in {".tif", ".tiff"}:
        import tifffile

        tifffile.imwrite(str(output_path), volume, compression="zlib")
    elif suffix == ".zarr":
        import zarr

        zarr.save(str(output_path), volume)
    elif suffix == ".png":
        from PIL import Image

        if volume.ndim == 3 and volume.shape[0] == 1:
            volume = volume[0]
        Image.fromarray((volume * 255).astype(np.uint8)).save(output_path)
    else:
        # Default to TIFF
        import tifffile

        out = output_path.with_suffix(".tif")
        tifffile.imwrite(str(out), volume, compression="zlib")


# ---------------------------------------------------------------------------
# Core refinement pipeline
# ---------------------------------------------------------------------------


@dataclass
class RefinementStats:
    """Collects before/after metrics for a single volume."""

    filename: str = ""
    original_label_voxels: int = 0
    refined_label_voxels: int = 0
    voxels_added: int = 0
    voxels_removed: int = 0
    small_components_removed: int = 0
    holes_filled: int = 0
    elapsed_s: float = 0.0
    status: str = "OK"
    note: str = ""


def _morphological_cleanup(
    labels: np.ndarray,
    *,
    min_component_size: int = 50,
) -> tuple[np.ndarray, int, int]:
    """Remove small connected components and fill small holes.

    Returns
    -------
    cleaned : np.ndarray
        Cleaned binary label volume.
    n_components_removed : int
        Number of small components removed.
    n_holes_filled : int
        Number of hole voxels filled.
    """
    from scipy.ndimage import binary_fill_holes, label as ndimage_label

    # --- Remove small components ---
    labelled, num_features = ndimage_label(labels)
    components_removed = 0
    if num_features > 0:
        component_sizes = np.bincount(labelled.ravel())
        # Index 0 is background — skip it
        for comp_id in range(1, num_features + 1):
            if component_sizes[comp_id] < min_component_size:
                labels[labelled == comp_id] = 0
                components_removed += 1

    # --- Fill small holes ---
    filled = binary_fill_holes(labels).astype(labels.dtype)
    holes_filled = int(np.sum(filled) - np.sum(labels))
    labels = filled

    return labels, components_removed, max(holes_filled, 0)


def refine_single_volume(
    volume: np.ndarray,
    *,
    edt_threshold: float = 0.5,
    sigma_frangi: float = 1.0,
    ridge_threshold: float = 0.5,
    min_component_size: int = 50,
) -> tuple[np.ndarray, RefinementStats]:
    """Apply the EDT + Frangi refinement pipeline to a single label volume.

    Parameters
    ----------
    volume : np.ndarray
        Raw label volume (binary or integer labels binarised internally).
    edt_threshold : float
        Inverse-EDT dilation distance for boundary expansion.
    sigma_frangi : float
        Sigma for the Frangi vesselness / ridge filter.
    ridge_threshold : float
        Binarisation threshold applied to the ridge response.
    min_component_size : int
        Connected components smaller than this are removed.

    Returns
    -------
    refined : np.ndarray
        Refined binary label volume (uint8, values 0/1).
    stats : RefinementStats
        Summary metrics.
    """
    stats = RefinementStats()
    binary = (volume > 0).astype(np.uint8)
    stats.original_label_voxels = int(binary.sum())

    # 1) EDT-based boundary dilation / sharpening
    if _VILLA_AVAILABLE:
        dilated = dilate_by_inverse_edt(binary, edt_threshold)
    else:
        dilated = _fallback_dilate_by_inverse_edt(binary, edt_threshold)

    # Scale to 0-255 so Hessian eigenvalues are large enough for the background term
    dilated_float = dilated.astype(np.float32) * 255.0

    # 2) Frangi / ridge detection
    if _VILLA_AVAILABLE:
        if volume.ndim == 2:
            ridges = detect_ridges_2d(dilated_float, sigma=sigma_frangi)
        elif volume.ndim == 3:
            ridges = detect_ridges_3d(dilated_float, sigma=sigma_frangi)
        else:
            raise ValueError(f"Unsupported dimensionality: {volume.ndim}")
    else:
        ridges = _fallback_detect_ridges(dilated_float, sigma=sigma_frangi)

    # Normalize ridges to [0, 1] to make thresholding robust
    rmin, rmax = ridges.min(), ridges.max()
    if rmax > rmin:
        ridges = (ridges - rmin) / (rmax - rmin)

    refined = (ridges > ridge_threshold).astype(np.uint8)

    # 3) Morphological cleanup
    refined, n_comp_removed, n_holes_filled = _morphological_cleanup(
        refined, min_component_size=min_component_size
    )

    stats.refined_label_voxels = int(refined.sum())
    stats.voxels_added = int(np.sum((refined == 1) & (binary == 0)))
    stats.voxels_removed = int(np.sum((refined == 0) & (binary == 1)))
    stats.small_components_removed = n_comp_removed
    stats.holes_filled = n_holes_filled
    return refined, stats


# ---------------------------------------------------------------------------
# File-level processing (picklable for multiprocessing)
# ---------------------------------------------------------------------------


def _process_file(
    input_path: str,
    output_dir: str,
    edt_threshold: float,
    sigma_frangi: float,
    ridge_threshold: float,
    min_component_size: int,
) -> RefinementStats:
    """Process one label file end-to-end.  Designed as a top-level function so
    it can be dispatched to a ``multiprocessing.Pool`` without pickling issues.
    """
    path = Path(input_path)
    stats = RefinementStats(filename=path.name)
    start = time.perf_counter()

    try:
        volume = _load_volume(path)
        log.info("Loaded %s  shape=%s  dtype=%s", path.name, volume.shape, volume.dtype)

        refined, stats = refine_single_volume(
            volume,
            edt_threshold=edt_threshold,
            sigma_frangi=sigma_frangi,
            ridge_threshold=ridge_threshold,
            min_component_size=min_component_size,
        )
        stats.filename = path.name

        if output_dir == "IN_PLACE":
            if path.name.endswith(".png"):
                out_path = path.parent / "inklabels_refined.png"
            elif path.name.endswith(".tif") or path.name.endswith(".tiff"):
                out_path = path.parent / f"{path.stem}_refined{path.suffix}"
            else:
                out_path = path.parent / f"{path.name}_refined"
        else:
            out_path = Path(output_dir) / path.name
        _save_volume(refined, out_path)
        log.info(
            "Saved %s  original=%d  refined=%d  +%d/-%d voxels",
            out_path.name,
            stats.original_label_voxels,
            stats.refined_label_voxels,
            stats.voxels_added,
            stats.voxels_removed,
        )
    except Exception as exc:
        stats.status = "ERROR"
        stats.note = f"{type(exc).__name__}: {exc}"
        log.error("Failed to process %s: %s", path.name, stats.note)

    stats.elapsed_s = time.perf_counter() - start
    return stats


def _process_file_wrapper(args: tuple) -> RefinementStats:
    """Unpack a tuple of arguments for ``multiprocessing.Pool.imap``."""
    return _process_file(*args)


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _discover_label_files(labels_dir: Path) -> list[Path]:
    """Return a sorted list of label volumes found in *labels_dir*."""
    patterns = [
        "*.zarr",
        "*.tif",
        "*.tiff",
        "*/inklabels.png",
        "*/inklabels_filled.png",
        "inklabels.png",
        "inklabels_filled.png",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(labels_dir.glob(pattern))

    # Also detect Zarr directories that don't end in .zarr but contain .zarray
    for child in labels_dir.iterdir():
        if child.is_dir() and (child / ".zarray").exists() and child not in files:
            files.append(child)

    return sorted(set(files))


# ---------------------------------------------------------------------------
# Summary printing
# ---------------------------------------------------------------------------


def _print_summary(results: list[RefinementStats]) -> None:
    """Print a tabulated summary of all processed files."""
    ok = [r for r in results if r.status == "OK"]
    err = [r for r in results if r.status != "OK"]

    print("\n" + "=" * 78)
    print("  LABEL REFINEMENT SUMMARY (EDT + Frangi)")
    print("=" * 78)
    print(
        f"{'File':<35} {'Original':>10} {'Refined':>10} {'Added':>8} {'Removed':>8} "
        f"{'Cleanup':>8} {'Time':>7}"
    )
    print("-" * 78)
    for r in ok:
        print(
            f"{r.filename:<35} {r.original_label_voxels:>10,} {r.refined_label_voxels:>10,} "
            f"{r.voxels_added:>+8,} {r.voxels_removed:>8,} "
            f"{r.small_components_removed:>8} {r.elapsed_s:>6.1f}s"
        )
    print("-" * 78)

    if ok:
        total_orig = sum(r.original_label_voxels for r in ok)
        total_ref = sum(r.refined_label_voxels for r in ok)
        total_add = sum(r.voxels_added for r in ok)
        total_rem = sum(r.voxels_removed for r in ok)
        total_time = sum(r.elapsed_s for r in ok)
        print(
            f"{'TOTAL':<35} {total_orig:>10,} {total_ref:>10,} "
            f"{total_add:>+8,} {total_rem:>8,} {'':>8} {total_time:>6.1f}s"
        )

    if err:
        print(f"\n  {len(err)} file(s) FAILED:")
        for r in err:
            print(f"    {r.filename}: {r.note}")

    print(f"\n  Succeeded: {len(ok)}/{len(results)}")
    print("=" * 78 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Refine label volumes using Villa's EDT + Frangi pipeline.  "
            "Scans --labels_dir for .zarr / .tif files, applies inverse-EDT "
            "boundary dilation, Frangi ridge detection, and morphological "
            "cleanup, then writes results to --output_dir."
        ),
    )

    parser.add_argument(
        "--labels_dir",
        type=Path,
        required=True,
        help="Directory containing label volumes (.zarr, .tif, .tiff).",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="Directory where refined labels will be saved (ignored if --in_place is set).",
    )
    parser.add_argument(
        "--in_place",
        action="store_true",
        help="Save refined labels in the same directory as the input (e.g., as inklabels_refined.png).",
    )
    parser.add_argument(
        "--sigma_frangi",
        type=float,
        default=1.0,
        help="Sigma for the Frangi vesselness / ridge filter (default: 1.0).",
    )
    parser.add_argument(
        "--edt_threshold",
        type=float,
        default=0.5,
        help="Inverse-EDT dilation distance for boundary sharpening (default: 0.5).",
    )
    parser.add_argument(
        "--ridge_threshold",
        type=float,
        default=0.5,
        help="Binarisation threshold for ridge filter output (default: 0.5).",
    )
    parser.add_argument(
        "--min_component_size",
        type=int,
        default=50,
        help="Remove connected components smaller than this (default: 50 voxels).",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Preview files that would be processed without running the pipeline.",
    )
    parser.add_argument(
        "--num_workers",
        type=int,
        default=4,
        help="Number of parallel worker processes (default: 4).",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    labels_dir: Path = args.labels_dir.resolve()

    if args.in_place:
        output_dir = "IN_PLACE"
    else:
        if not args.output_dir:
            log.error("Must specify either --output_dir or --in_place")
            return 1
        output_dir = args.output_dir.resolve()

    if not labels_dir.is_dir():
        log.error("Labels directory does not exist: %s", labels_dir)
        return 1

    files = _discover_label_files(labels_dir)
    if not files:
        log.error("No .zarr / .tif / .tiff files found in %s", labels_dir)
        return 1

    log.info("--- Vesuvius Autoresearch: Label Refinement (EDT + Frangi) ---")
    log.info("Labels dir : %s", labels_dir)
    log.info("Output dir : %s", output_dir)
    log.info("Backend    : %s", "villa" if _VILLA_AVAILABLE else "scipy/skimage")
    log.info("Files found: %d", len(files))
    log.info(
        "Parameters : sigma_frangi=%.2f  edt_threshold=%.2f  ridge_threshold=%.2f  "
        "min_component=%d  workers=%d",
        args.sigma_frangi,
        args.edt_threshold,
        args.ridge_threshold,
        args.min_component_size,
        args.num_workers,
    )

    if args.dry_run:
        print("\n  [DRY RUN] The following files would be processed:\n")
        for f in files:
            print(f"    {f.name}")
        print()
        return 0

    if output_dir != "IN_PLACE":
        output_dir.mkdir(parents=True, exist_ok=True)

    tasks = [
        (
            str(f),
            str(output_dir),
            args.edt_threshold,
            args.sigma_frangi,
            args.ridge_threshold,
            args.min_component_size,
        )
        for f in files
    ]

    results: list[RefinementStats] = []

    if args.num_workers <= 1 or len(tasks) == 1:
        # Serial execution (simpler debugging, avoids fork overhead for 1 file)
        for task in tasks:
            results.append(_process_file_wrapper(task))
    else:
        with multiprocessing.Pool(args.num_workers) as pool:
            from tqdm import tqdm

            for stats in tqdm(
                pool.imap_unordered(_process_file_wrapper, tasks),
                total=len(tasks),
                desc="Refining labels",
            ):
                results.append(stats)

    _print_summary(results)

    n_ok = sum(1 for r in results if r.status == "OK")
    return 0 if n_ok == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
