"""Offline CPU audit against NumPy on one pinned public fiber CT crop.

Input: Dataset001_sk-fibers-20250124/imagesTr/s1_00497_01497_03997_256_0000.tif
from https://dl.ash2txt.org/datasets/fiber-skeletons/. No downloads or installs.
This measures numerical agreement, not tracing/reading quality or GPU parity.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy
import tifffile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from vesuvius_autoresearch.fibers import detection

CT_SHA256 = "0d38453cc37157f46b180e3711172e99f56eb216948eb6755eca0019ad0dbf60"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(actual, reference):
    radius = np.max(np.abs(reference), axis=-1, keepdims=True)
    margin = 64 * np.finfo(reference.dtype).eps * radius
    robust = np.abs(reference) > margin
    return {
        "max_absolute_error": float(np.max(np.abs(actual - reference))),
        "robust_sign_mismatches": int(
            np.count_nonzero(((actual > 0) != (reference > 0)) & robust)
        ),
    }


def gate(values, zero):
    ordered = np.take_along_axis(values, np.argsort(np.abs(values), axis=-1), axis=-1)
    return (ordered[..., 1] <= 0) & (ordered[..., 2] <= 0) & ~zero


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ct", type=Path, required=True)
    parser.add_argument(
        "--out", type=Path, required=True, help="New evidence directory"
    )
    parser.add_argument(
        "--baseline-ref", default="da4d1e829bb8bcd6a639cc7953279c5ebe57ceee"
    )
    args = parser.parse_args(argv)
    if args.ct.stat().st_size > 20 * 1024**2 or sha(args.ct) != CT_SHA256:
        parser.error(
            "CT must be the exact documented public fixture (SHA-256 mismatch)"
        )
    image = tifffile.imread(args.ct)
    if image.shape != (256, 256, 256) or image.dtype != np.uint8:
        parser.error("CT must be the documented 256-cubed uint8 fixture")
    path = "src/vesuvius_autoresearch/fibers/detection.py"
    baseline_commit = subprocess.check_output(
        ["git", "rev-parse", args.baseline_ref], cwd=ROOT, text=True
    ).strip()
    baseline_source = subprocess.check_output(
        ["git", "show", f"{baseline_commit}:{path}"], cwd=ROOT
    )
    args.out.mkdir(parents=True, exist_ok=False)
    baseline_file = args.out / "baseline_detection.py"
    baseline_file.write_bytes(baseline_source)
    spec = importlib.util.spec_from_file_location("_eigenvalue_baseline", baseline_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the pinned baseline module")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    current = detection.compute_eigenvalues_3x3_batch

    def reference_solver(matrix):
        return np.linalg.eigvalsh(detection.symmetrize_upper(matrix))

    solvers = {
        "baseline": baseline.compute_eigenvalues_3x3_batch,
        "candidate": current,
        "numpy": reference_solver,
    }
    raw = image[96:160, 96:160, 96:160].astype(np.float64)
    rows = []
    try:
        for gaussian, sigma in [(2, 6), (1, 2), (2, 3)]:
            matrix, zero = detection.hessian(raw, gauss_sigma=gaussian, sigma=sigma)
            spectra = {name: fn(matrix) for name, fn in solvers.items()}
            responses = {}
            for name, fn in solvers.items():
                detection.compute_eigenvalues_3x3_batch = fn
                responses[name] = detection.detect_vesselness(
                    raw, gauss_sigma=gaussian, sigma=sigma
                )
            row = {"gauss_sigma": gaussian, "sigma": sigma, "comparisons": {}}
            for name in ["baseline", "candidate"]:
                row["comparisons"][name] = {
                    **compare(spectra[name], spectra["numpy"]),
                    "vesselness_gate_disagreements": int(
                        np.count_nonzero(
                            gate(spectra[name], zero) != gate(spectra["numpy"], zero)
                        )
                    ),
                    "max_absolute_vesselness_error": float(
                        np.max(np.abs(responses[name] - responses["numpy"]))
                    ),
                }
            rows.append(row)
    finally:
        detection.compute_eigenvalues_3x3_batch = current

    matrix = np.random.default_rng(4090).normal(size=(1000, 3, 3))
    matrix = (matrix + matrix.swapaxes(-1, -2)) / 2 * 1e-5
    reference = reference_solver(matrix)
    synthetic = {
        name: compare(fn(matrix), reference)
        for name, fn in solvers.items()
        if name != "numpy"
    }
    report = {
        "complete": True,
        "scope": "CPU numerical agreement only; no tracing/reading quality, GPU or prize claim",
        "baseline_commit": baseline_commit,
        "baseline_source_sha256": sha(baseline_file),
        "candidate_source_sha256": sha(Path(detection.__file__)),
        "harness_sha256": sha(Path(__file__)),
        "ct_sha256": CT_SHA256,
        "roi_origin_zyx": [96, 96, 96],
        "roi_shape_zyx": list(raw.shape),
        "synthetic": {"rng_seed": 4090, "matrices": 1000, "scale": 1e-5, **synthetic},
        "public_ct": rows,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "tifffile": tifffile.__version__,
        },
    }
    if sha(args.ct) != CT_SHA256:
        raise ValueError("CT fixture changed during the numerical audit")
    (args.out / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
