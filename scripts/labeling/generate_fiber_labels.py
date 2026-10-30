#!/usr/bin/env python3
"""Generate bounded fiber labels into a new completed run directory.

Candidate mode uses the repository's vesselness filter on exact local CT
windows. Skeleton mode voxelizes WebKnossos annotations with the legacy PCA
orientation heuristic (horizontal=1, vertical=2, mixed=3). Neither output is
independently verified ground truth. --help and dry-run need no Villa checkout,
CUDA device or WebKnossos import. Keep inputs stable and serialize writers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from math import sqrt
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[2]
for import_root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from scripts.candidate_artifacts import ARTIFACT_ERRORS, integer, write_json
from scripts.labeling.fiber_candidates import load_ct_window as _load_ct_window
from scripts.labeling.label_artifacts import (
    MAX_FRAGMENT_VOXELS,
    new_output,
    publish_new,
)
from vesuvius_autoresearch.fibers import detect_vesselness
from vesuvius_autoresearch.fibers.provenance import file_sha256

# ---------------------------------------------------------------------------
# Skeleton mode (original WebKnossos .nml → voxel labels pipeline)
# ---------------------------------------------------------------------------


def _classify_fiber_pca(
    voxel_coords: np.ndarray, z_threshold: float = 1.0 / sqrt(2)
) -> str:
    if voxel_coords.shape[0] < 2:
        return "horizontal"
    coords = voxel_coords.astype(np.float32)
    centroid = coords.mean(axis=0)
    coords_centered = coords - centroid
    cov = np.cov(coords_centered.T)
    if np.isnan(cov).any() or np.isinf(cov).any():
        return "horizontal"
    eigvals, eigvecs = np.linalg.eig(cov)
    idx = np.argsort(eigvals)[::-1]
    eigvecs = eigvecs[:, idx]
    principal_axis = eigvecs[:, 0]
    principal_axis /= np.linalg.norm(principal_axis) + 1e-8
    z_axis = np.array([1, 0, 0], dtype=float)
    cos_angle = abs(np.dot(principal_axis, z_axis))
    return "vertical" if cos_angle > z_threshold else "horizontal"


def _interpolate_adaptive(
    start_pos, end_pos, curvature_threshold=0.1, max_recursion=100
):
    segment_vector = end_pos - start_pos
    segment_length = np.linalg.norm(segment_vector)
    if max_recursion == 0 or segment_length < curvature_threshold:
        return [start_pos, end_pos]
    mid_pos = (start_pos + end_pos) / 2.0
    left = _interpolate_adaptive(
        start_pos, mid_pos, curvature_threshold, max_recursion - 1
    )
    right = _interpolate_adaptive(
        mid_pos, end_pos, curvature_threshold, max_recursion - 1
    )
    return left[:-1] + right


def _fill_volume_for_tree(tree, output_shape, origins=(0, 0, 0)):
    temp_fiber = np.zeros(output_shape, dtype=np.uint8)
    origins = np.array(origins)
    bounds_xyz = np.asarray(output_shape[::-1])
    for node1, node2 in tree.edges:
        node1_pos = np.array([node1.position.x, node1.position.y, node1.position.z])
        node2_pos = np.array([node2.position.x, node2.position.y, node2.position.z])
        if not np.isfinite([node1_pos, node2_pos]).all():
            raise ValueError("skeleton coordinates must be finite")
        for point in _interpolate_adaptive(node1_pos, node2_pos):
            local = point - origins
            if np.all((local >= 0) & (local < bounds_xyz)):
                voxel_coords = local.astype(int)
                temp_fiber[voxel_coords[2], voxel_coords[1], voxel_coords[0]] = 1
    return temp_fiber


def _expand_and_vesselness(binary_volume: np.ndarray, radius: int = 3) -> np.ndarray:
    if not np.any(binary_volume):
        return np.zeros_like(binary_volume)
    binary_inverted = 1 - binary_volume
    edt = distance_transform_edt(binary_inverted)
    expanded = (edt <= radius).astype(np.uint8)
    vessel = detect_vesselness(expanded.astype(np.float32))
    combined = np.maximum(binary_volume, vessel)
    return (combined > 0.5).astype(np.uint8)


def _process_tree_worker(tree, output_shape, origins, radius):
    temp_fiber = _fill_volume_for_tree(tree, output_shape, origins)
    processed = _expand_and_vesselness(temp_fiber, radius)
    fiber_voxels = np.argwhere(processed > 0)
    orientation = _classify_fiber_pca(fiber_voxels)
    accum_h = np.zeros(output_shape, dtype=np.uint16)
    accum_v = np.zeros(output_shape, dtype=np.uint16)
    if orientation == "vertical":
        accum_v += processed.astype(np.uint16)
    else:
        accum_h += processed.astype(np.uint16)
    return accum_h, accum_v


def _voxelize_skeleton(annotation, output_shape, origins, radius=3, n_workers=1):
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from itertools import islice

    all_trees = list(annotation.skeleton.trees)
    for group in annotation.skeleton.groups:
        all_trees.extend(group.trees)

    accum_h = np.zeros(output_shape, dtype=np.uint8)
    accum_v = np.zeros(output_shape, dtype=np.uint8)
    n_workers = integer(n_workers, "n_workers", 1)
    trees = iter(all_trees)
    with (
        ProcessPoolExecutor(max_workers=n_workers) as executor,
        tqdm(total=len(all_trees), desc="Processing trees") as progress,
    ):
        while batch := tuple(islice(trees, n_workers)):
            # A future retains its whole-cube result. Bound both queued tasks
            # and completed results instead of retaining every tree's arrays.
            futures = {
                executor.submit(
                    _process_tree_worker, tree, output_shape, origins, radius
                )
                for tree in batch
            }
            for future in as_completed(futures):
                h, v = future.result()
                np.maximum(accum_h, h, out=accum_h)
                np.maximum(accum_v, v, out=accum_v)
                futures.remove(future)
                del h, v
                progress.update(1)
            del future
    final = np.zeros(output_shape, dtype=np.uint8)
    mixed = (accum_h > 0) & (accum_v > 0)
    final[mixed] = 3
    final[(accum_h > 0) & (accum_v == 0)] = 1
    final[(accum_v > 0) & (accum_h == 0)] = 2
    return final


def _run_skeleton_mode(args: argparse.Namespace) -> int:
    nml_path = Path(args.nml_path).resolve()
    output_dir = new_output(args.output_dir, nml_path)
    radius = integer(args.radius, "radius")
    workers = integer(args.n_workers, "n_workers", 1)
    match = re.fullmatch(
        r".+_s\d+a?_(\d+)z_(\d+)y_(\d+)x_(\d+)_v\d+\.nml", nml_path.name
    )
    if match is None:
        raise ValueError("NML filename must encode _sN_Zz_Yy_Xx_SIZE_vREV.nml")
    z_start, y_start, x_start, size = map(int, match.groups())
    if size < 3 or size**3 > integer(args.max_voxels, "max_voxels", 1):
        raise ValueError("NML cube must have size >=3 and fit max_voxels")
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "PLANNED",
                    "nml_path": str(nml_path),
                    "output": str(output_dir),
                    "origin_zyx": [z_start, y_start, x_start],
                    "shape_zyx": [size] * 3,
                    "radius": radius,
                    "workers": workers,
                    "scope": "Filename/settings/output checks only; annotation not loaded",
                }
            )
        )
        return 0
    try:
        from webknossos import Annotation
    except ImportError:
        print(
            "error: webknossos is not installed; skeleton mode requires it.",
            file=sys.stderr,
        )
        return 1
    nml_sha = file_sha256(nml_path)
    annotation = Annotation.load(str(nml_path))
    labels = _voxelize_skeleton(
        annotation,
        output_shape=(size,) * 3,
        origins=(x_start, y_start, z_start),
        radius=radius,
        n_workers=workers,
    )
    if (
        labels.shape != (size,) * 3
        or labels.dtype != np.uint8
        or not np.isin(labels, [0, 1, 2, 3]).all()
    ):
        raise ValueError(
            "skeleton labels must be uint8 orientation IDs 0/1/2/3 matching the cube"
        )
    with publish_new(output_dir) as staging:
        label_path = staging / "labels.tif"
        tifffile.imwrite(
            label_path, labels, photometric="minisblack", metadata={"axes": "ZYX"}
        )
        if not np.array_equal(tifffile.imread(label_path), labels):
            raise ValueError("serialized skeleton TIFF failed readback")
        write_json(
            staging / "labels_meta.json",
            {
                "contract": 1,
                "label_kind": "annotation_derived_orientation_heuristic",
                "source_nml": str(nml_path),
                "source_nml_sha256": nml_sha,
                "axes": ["z", "y", "x"],
                "origin_zyx": [z_start, y_start, x_start],
                "shape_zyx": [size] * 3,
                "radius": radius,
                "workers": workers,
                "label_file_sha256": file_sha256(label_path),
            },
        )
        if file_sha256(nml_path) != nml_sha:
            raise ValueError("NML input changed during processing")
    print(f"Labels saved to {output_dir / 'labels.tif'}")
    return 0


def _select_backend(use_gpu):
    from vesuvius_autoresearch.fibers.cli import _array_backend

    _, name = _array_backend("gpu" if use_gpu else "cpu")
    return "cupy" if name == "gpu" else "numpy"


def _run_candidates_mode(args):
    from scripts.labeling.fiber_candidates import run_candidates

    return run_candidates(
        args, select_backend=_select_backend, filter_fn=detect_vesselness
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mode",
        choices=["candidates", "skeleton"],
        default="candidates",
        help="candidates (default): CT-derived pseudo-labels for ranked candidates. "
        "skeleton: voxelize a WebKnossos .nml annotation.",
    )

    # candidates-mode args
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path("reports/scroll23_ranked_candidates.tsv"),
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("reports/fiber_labels_run"),
        help="New completed run directory; must not exist",
    )
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument(
        "--depth", type=int, default=64, help="Z-extent of the CT window in voxels"
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--use-gpu", action="store_true", help="Use the CuPy backend (default: CPU)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan without output writes or CUDA probes",
    )
    parser.add_argument(
        "--max-voxels",
        type=int,
        default=MAX_FRAGMENT_VOXELS,
        help="Maximum requested CT/label voxels per fragment",
    )

    # skeleton-mode args (defaults reproduce the original entry point)
    parser.add_argument(
        "--nml-path",
        type=Path,
        default=Path(
            "villa/foundation/datasets/fibers-dataset/fibers_s5_06500z_02000y_04000x_500_v03.nml"
        ),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("local_data/fibers_dataset")
    )
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument(
        "--n-workers",
        type=int,
        default=1,
        help="Skeleton CPU workers; each holds whole-cube temporaries",
    )
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.mode == "skeleton":
            return _run_skeleton_mode(args)
        return _run_candidates_mode(args)
    except (*ARTIFACT_ERRORS, ImportError, MemoryError) as exc:
        print(f"Fiber label generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
