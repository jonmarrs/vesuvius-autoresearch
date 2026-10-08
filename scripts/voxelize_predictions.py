#!/usr/bin/env python3
"""Export a bounded 3D probability-grid isosurface as a research OBJ mesh.

Uses scikit-image marching cubes; does not register flattened UV predictions,
prune instance labels, or establish scientific accuracy/submission readiness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from skimage.measure import marching_cubes

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import ARTIFACT_ERRORS
from scripts.geometry_artifacts import finite_coordinates
from scripts.labeling.label_artifacts import (
    MAX_FRAGMENT_VOXELS,
    bounded_number,
    bounded_volume,
    new_output,
    publish_new_file,
)


def export_prediction_mesh(
    source,
    output,
    *,
    threshold=0.5,
    origin_zyx=(0, 0, 0),
    spacing_zyx=(1, 1, 1),
    units="voxel",
    max_voxels=MAX_FRAGMENT_VOXELS,
):
    output = new_output(output, source)
    if output.suffix.lower() != ".obj":
        raise ValueError("mesh output must end with .obj")
    threshold = bounded_number(threshold, "threshold", 0, 1)
    if not 0 < threshold < 1:
        raise ValueError("threshold must be strictly between 0 and 1")
    origin = finite_coordinates(origin_zyx, "origin_zyx")
    spacing = finite_coordinates(spacing_zyx, "spacing_zyx", positive=True)
    if units not in {"voxel", "micrometer"}:
        raise ValueError("units must be voxel or micrometer")
    root, array = bounded_volume(source, max_voxels)
    if min(array.shape) < 2 or array.dtype.kind not in "uifb":
        raise ValueError(
            "mesh input needs a real 3D probability grid with every dimension at least 2"
        )
    values = array[:]
    if not np.isfinite(values).all() or np.any(values < 0) or np.any(values > 1):
        raise ValueError("prediction values must be finite probabilities in [0, 1]")
    if not float(values.min()) < threshold < float(values.max()):
        raise ValueError(
            "threshold must cross the prediction range; no nonempty isosurface"
        )
    vertices, faces, _, _ = marching_cubes(
        values.astype(np.float32), level=threshold, allow_degenerate=False
    )
    if (
        vertices.ndim != 2
        or vertices.shape[1] != 3
        or faces.ndim != 2
        or faces.shape[1] != 3
        or faces.dtype.kind not in "ui"
    ):
        raise ValueError("isosurface must contain XYZ vertices and integer triangles")
    # z/y/x -> x/y/z reverses handedness; reverse triangle winding as well.
    vertices = (vertices.astype(np.float64) * spacing + origin)[:, ::-1]
    faces = faces[:, [0, 2, 1]]
    if not len(vertices) or not len(faces) or not np.isfinite(vertices).all():
        raise ValueError("isosurface has no finite triangle geometry")
    if faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("isosurface contains invalid triangle references")
    record = {
        "contract": 1,
        "purpose": "research probability-grid isosurface",
        "source": str(Path(source).resolve()),
        "source_shape_zyx": list(array.shape),
        "source_dtype": str(array.dtype),
        "source_root_attrs": dict(root.attrs),
        "source_array_attrs": dict(array.attrs),
        "threshold": threshold,
        "origin_zyx": origin.tolist(),
        "spacing_zyx": spacing.tolist(),
        "coordinate_order": "xyz",
        "units": units,
        "frame_basis": "local grid plus caller-declared origin and spacing; no registration applied",
        "vertices": len(vertices),
        "triangles": len(faces),
        "submittable": None,
        "algorithm": "skimage.measure.marching_cubes, float32 field, step_size=1, no padding or pruning",
    }
    header = json.dumps(record, allow_nan=False)
    with publish_new_file(output, source) as staging:
        with staging.open("w") as stream:
            stream.write(f"# autoresearch_geometry {header}\n")
            for x, y, z in vertices:
                stream.write(f"v {x:.17g} {y:.17g} {z:.17g}\n")
            for a, b, c in faces + 1:
                stream.write(f"f {a} {b} {c}\n")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--output-obj", "--output_obj", dest="output_obj", required=True
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--origin-zyx", type=float, nargs=3, default=(0, 0, 0))
    parser.add_argument("--spacing-zyx", type=float, nargs=3, default=(1, 1, 1))
    parser.add_argument("--units", choices=("voxel", "micrometer"), default="voxel")
    parser.add_argument("--max-voxels", type=int, default=MAX_FRAGMENT_VOXELS)
    args = parser.parse_args(argv)
    try:
        record = export_prediction_mesh(
            args.input,
            args.output_obj,
            threshold=args.threshold,
            origin_zyx=args.origin_zyx,
            spacing_zyx=args.spacing_zyx,
            units=args.units,
            max_voxels=args.max_voxels,
        )
    except (*ARTIFACT_ERRORS, RuntimeError, ImportError) as exc:
        print(f"Mesh export failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Research OBJ published: {Path(args.output_obj).resolve()}; vertices={record['vertices']}, triangles={record['triangles']}. Accuracy and submission eligibility are unverified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
