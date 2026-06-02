#!/usr/bin/env python3
"""Generate fiber labels.

Two modes:

* ``--mode skeleton`` (the original behaviour): voxelize a WebKnossos ``.nml``
  skeleton annotation into per-orientation fiber labels. PCA-classified into
  horizontal (1), vertical (2), or mixed (3). This is the upstream
  ``villa/foundation/datasets/fibers-dataset`` workflow, locally wrapped.

* ``--mode candidates`` (default): closes the unwired foundation hook flagged
  by ``reports/villa_component_coverage.md``. For each top-ranked candidate
  in ``reports/scroll23_ranked_candidates.tsv`` it loads the CT chunk(s)
  covering the candidate window, runs villa's ``tools.detect_vesselness``
  (the same Frangi-style filter the autoresearch fiber predictor uses),
  thresholds the output, and writes ``fiber_prob.tif`` + ``fiber_label.tif``
  into ``reports/scroll23_evidence/candidate_NNN/`` so the evidence chain
  has CT-derived fiber pseudo-labels alongside the manually-annotated set.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Villa-tools import (shared by both modes)
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
FIBER_TOOLS_PATH = os.path.join(
    PROJECT_ROOT, "villa", "foundation", "datasets", "fibers-dataset"
)
if FIBER_TOOLS_PATH not in sys.path:
    sys.path.insert(0, FIBER_TOOLS_PATH)

import tools  # noqa: E402  (sys.path injection happens above)
from tools import detect_vesselness  # noqa: E402  re-exported for skeleton mode

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
    for node1, node2 in tree.edges:
        node1_pos = np.array([node1.position.x, node1.position.y, node1.position.z])
        node2_pos = np.array([node2.position.x, node2.position.y, node2.position.z])
        for point in _interpolate_adaptive(node1_pos, node2_pos):
            voxel_coords = (point - origins).astype(int)
            if np.all((voxel_coords >= 0) & (voxel_coords < np.asarray(output_shape))):
                temp_fiber[voxel_coords[2], voxel_coords[1], voxel_coords[0]] = 1
    return temp_fiber


def _expand_and_vesselness(binary_volume: np.ndarray, radius: int = 3) -> np.ndarray:
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


def _voxelize_skeleton(annotation, output_shape, origins, radius=3, n_workers=None):
    from concurrent.futures import ProcessPoolExecutor, as_completed

    all_trees = list(annotation.skeleton.trees)
    for group in annotation.skeleton.groups:
        all_trees.extend(group.trees)

    accum_h = np.zeros(output_shape, dtype=np.uint8)
    accum_v = np.zeros(output_shape, dtype=np.uint8)
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(
                _process_tree_worker, tree, output_shape, origins, radius
            ): tree
            for tree in all_trees
        }
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Processing trees"
        ):
            h, v = future.result()
            accum_h = np.maximum(accum_h, h)
            accum_v = np.maximum(accum_v, v)
    final = np.zeros(output_shape, dtype=np.uint8)
    mixed = (accum_h > 0) & (accum_v > 0)
    final[mixed] = 3
    final[(accum_h > 0) & (accum_v == 0)] = 1
    final[(accum_v > 0) & (accum_h == 0)] = 2
    return final


def _run_skeleton_mode(args: argparse.Namespace) -> int:
    try:
        from webknossos import Annotation
    except ImportError:
        print(
            "error: webknossos is not installed; skeleton mode requires it.",
            file=sys.stderr,
        )
        return 1

    nml_path = args.nml_path
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading annotation from {nml_path}...")
    annotation = Annotation.load(str(nml_path))

    # Coordinates embedded in the filename: <prefix>_<s5>_<06500z>_<02000y>_<04000x>_<500>_<rev>.nml
    parts = nml_path.name.split("_")
    z_start = int(parts[2][:-1])
    y_start = int(parts[3][:-1])
    x_start = int(parts[4][:-1])
    size = int(parts[5])

    print(f"Generating labels for ({z_start}, {y_start}, {x_start}) size {size}...")
    labels = _voxelize_skeleton(
        annotation,
        output_shape=(size, size, size),
        origins=(x_start, y_start, z_start),
        radius=args.radius,
        n_workers=args.n_workers,
    )
    label_path = output_dir / "labels.tif"
    tifffile.imwrite(label_path, labels)
    print(f"Labels saved to {label_path}")
    return 0


# ---------------------------------------------------------------------------
# Candidates mode (CT-derived fiber pseudo-labels for ranked candidates)
# ---------------------------------------------------------------------------


@dataclass
class _Candidate:
    index: int
    artifact_stem: str
    local_uri: str
    z: int
    y: int
    x: int
    width: int
    height: int
    review_score: float


@dataclass
class _LabelResult:
    candidate_index: int
    artifact_stem: str
    status: str
    prob_path: str | None
    label_path: str | None
    elapsed_s: float
    fiber_voxel_fraction: float | None
    note: str


def _select_backend(use_gpu: bool) -> str:
    """Return the requested backend name."""
    if use_gpu:
        try:
            import cupy as cp

            return "cupy"
        except ImportError:
            print(
                "warning: --use-gpu requested but cupy not importable; using numpy.",
                file=sys.stderr,
            )
    return "numpy"


def _load_candidates(tsv_path: Path, top_n: int) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    with tsv_path.open() as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for index, row in enumerate(reader):
            if index >= top_n:
                break
            candidates.append(
                _Candidate(
                    index=index,
                    artifact_stem=row["artifact_stem"],
                    local_uri=row["local_uri"],
                    z=int(row["z"]),
                    y=int(row["y"]),
                    x=int(row["x"]),
                    width=int(row["width"]),
                    height=int(row["height"]),
                    review_score=float(row["review_score"]),
                )
            )
    return candidates


def _load_ct_window(
    local_uri: str, z: int, y: int, x: int, depth: int, height: int, width: int
) -> np.ndarray:
    """Return a float32 [0, 1] CT window of shape (depth, height, width)."""
    import zarr

    store = zarr.open(local_uri, mode="r")
    arr = store if isinstance(store, zarr.core.Array) else store["0"]

    z_end = min(z + depth, arr.shape[0])
    y_end = min(y + height, arr.shape[1])
    x_end = min(x + width, arr.shape[2])
    raw = arr[z:z_end, y:y_end, x:x_end]
    if raw.dtype == np.uint8:
        return raw.astype(np.float32) / 255.0
    return raw.astype(np.float32)


def _generate_label_for(
    candidate: _Candidate,
    evidence_root: Path,
    depth: int,
    threshold: float,
    backend: str,
) -> _LabelResult:
    candidate_dir = evidence_root / f"candidate_{candidate.index:03d}"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    prob_path = candidate_dir / "fiber_prob.tif"
    label_path = candidate_dir / "fiber_label.tif"

    start = time.perf_counter()
    try:
        ct_patch = _load_ct_window(
            candidate.local_uri,
            candidate.z,
            candidate.y,
            candidate.x,
            depth,
            candidate.height,
            candidate.width,
        )
    except (FileNotFoundError, KeyError, OSError) as exc:
        return _LabelResult(
            candidate_index=candidate.index,
            artifact_stem=candidate.artifact_stem,
            status="MISSING_CT",
            prob_path=None,
            label_path=None,
            elapsed_s=time.perf_counter() - start,
            fiber_voxel_fraction=None,
            note=f"{type(exc).__name__}: {exc}",
        )

    if backend == "cupy":
        import cupy as cp

        ct_input = cp.asarray(ct_patch)
    else:
        ct_input = ct_patch

    vesselness = detect_vesselness(ct_input)

    if backend == "cupy":
        import cupy as cp

        vesselness_np = cp.asnumpy(vesselness)
    else:
        vesselness_np = vesselness

    vesselness_np = np.asarray(vesselness_np, dtype=np.float32)
    fiber_label = (vesselness_np >= threshold).astype(np.uint8)

    tifffile.imwrite(prob_path, vesselness_np)
    tifffile.imwrite(label_path, fiber_label)

    return _LabelResult(
        candidate_index=candidate.index,
        artifact_stem=candidate.artifact_stem,
        status="OK",
        prob_path=str(prob_path),
        label_path=str(label_path),
        elapsed_s=time.perf_counter() - start,
        fiber_voxel_fraction=float(fiber_label.mean()),
        note="",
    )


def _write_summary(
    evidence_root: Path,
    results: list[_LabelResult],
    backend: str,
    threshold: float,
    depth: int,
) -> Path:
    summary_path = evidence_root / "fiber_labels_summary.json"
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backend": backend,
        "threshold": threshold,
        "depth": depth,
        "candidates": [
            {
                "candidate_index": r.candidate_index,
                "artifact_stem": r.artifact_stem,
                "status": r.status,
                "prob_path": r.prob_path,
                "label_path": r.label_path,
                "elapsed_s": round(r.elapsed_s, 3),
                "fiber_voxel_fraction": r.fiber_voxel_fraction,
                "note": r.note,
            }
            for r in results
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2))
    return summary_path


def _run_candidates_mode(args: argparse.Namespace) -> int:
    if not args.candidates.exists():
        print(f"error: candidates TSV not found at {args.candidates}", file=sys.stderr)
        return 1

    candidates = _load_candidates(args.candidates, args.top_n)
    if not candidates:
        print(f"error: no rows loaded from {args.candidates}", file=sys.stderr)
        return 1

    args.evidence_root.mkdir(parents=True, exist_ok=True)
    backend = _select_backend(args.use_gpu)

    print(
        f"# generate_fiber_labels (candidates): "
        f"{len(candidates)} candidate(s) backend={backend} depth={args.depth} threshold={args.threshold}"
    )

    if args.dry_run:
        for c in candidates:
            print(
                f"  [{c.index:03d}] {c.artifact_stem} "
                f"z={c.z} y={c.y} x={c.x} {c.width}x{c.height} "
                f"score={c.review_score:.3f} local_uri={c.local_uri}"
            )
        return 0

    results: list[_LabelResult] = []
    for c in candidates:
        print(f"  [{c.index:03d}] {c.artifact_stem} ... ", end="", flush=True)
        result = _generate_label_for(
            c, args.evidence_root, args.depth, args.threshold, backend
        )
        results.append(result)
        if result.status == "OK":
            print(
                f"OK ({result.elapsed_s:.1f}s fiber_fraction={result.fiber_voxel_fraction:.4f})"
            )
        else:
            print(f"{result.status}: {result.note}")

    summary_path = _write_summary(
        args.evidence_root, results, backend, args.threshold, args.depth
    )
    ok_count = sum(1 for r in results if r.status == "OK")
    print(f"# wrote {ok_count}/{len(results)} labels; summary={summary_path}")
    return 0 if ok_count == len(results) else 2


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
        "--evidence-root", type=Path, default=Path("reports/scroll23_evidence")
    )
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument(
        "--depth", type=int, default=64, help="Z-extent of the CT window in voxels"
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--use-gpu", action="store_true", help="Use the CuPy backend (default: CPU)"
    )
    parser.add_argument("--dry-run", action="store_true")

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
    parser.add_argument("--n-workers", type=int, default=4)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.mode == "skeleton":
        return _run_skeleton_mode(args)
    return _run_candidates_mode(args)


if __name__ == "__main__":
    sys.exit(main())
