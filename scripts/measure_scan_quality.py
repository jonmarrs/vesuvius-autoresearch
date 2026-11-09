"""Exploratory CT separability and texture statistics on aligned NRRD cubes.

Requires <cube>/<cube>_volume.nrrd and <cube>/<cube>_mask.nrrd in digit-prefixed
cube directories. Prints finite JSON; --out publishes a separate new report.
MEASURED describes complete descriptive statistics, not validated scan quality.
Hand-annotated cubes may exclude the hardest regions. See docs/SCAN_QUALITY.md.
"""

import argparse
import json
import math
import sys
import zlib
from numbers import Integral
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.labeling.label_artifacts import new_output, publish_new_file

MAX_VOXELS = 256**3
MIN_POPULATION = 1000
MAX_SAMPLES = 200_000
FEATURES = ("intensity_std", "grad_median", "grad_p90_over_p50", "tensor_anisotropy")


def _voxel_limit(max_voxels):
    if type(max_voxels) is not int or max_voxels < 1:
        raise ValueError("max_voxels must be a positive integer")


def _shape(shape, max_voxels):
    _voxel_limit(max_voxels)
    if len(shape) != 3 or any(
        isinstance(value, bool) or not isinstance(value, Integral) or value < 2
        for value in shape
    ):
        raise ValueError("CT and masks must be scalar 3D arrays with each axis >= 2")
    if math.prod(int(value) for value in shape) > max_voxels:
        raise ValueError(f"cube exceeds max_voxels={max_voxels}; use a bounded crop")
    return tuple(int(value) for value in shape)


def _volume(vol, max_voxels):
    vol = np.asarray(vol)
    _shape(vol.shape, max_voxels)
    if not (
        vol.dtype.kind == "u"
        and vol.dtype.itemsize in (1, 2)
        or vol.dtype.kind == "f"
        and vol.dtype.itemsize <= 8
    ):
        raise ValueError("CT must be uint8, uint16 or real floating point")
    if not np.isfinite(vol).all():
        raise ValueError("CT must contain finite intensities")
    return vol


def outcome_separability(vol, mask, *, max_voxels=MAX_VOXELS):
    """Orientation-folded AUC of sheet interior vs gap, with half credit for ties.

    Returns (None, interior_count, gap_count) for insufficient populations. The
    brighter class is chosen on the scored sample; this is not fixed-direction
    predictive accuracy. Sampling remains balanced, capped and seed-0.
    """
    from scipy import ndimage, stats

    vol = _volume(vol, max_voxels)
    mask = np.asarray(mask)
    if mask.shape != vol.shape or mask.dtype.kind not in "biu" or np.any(mask < 0):
        raise ValueError("mask must match CT shape and contain nonnegative integer IDs")
    lab = mask > 0
    interior = ndimage.binary_erosion(lab, iterations=2)
    dist = ndimage.distance_transform_edt(~lab)
    gap = (dist >= 2) & (dist <= 6)
    n_interior, n_gap = int(interior.sum()), int(gap.sum())
    if min(n_interior, n_gap) < MIN_POPULATION:
        return None, n_interior, n_gap
    rng = np.random.default_rng(0)
    n = min(n_interior, n_gap, MAX_SAMPLES)
    # Preserve original intensity precision when determining ties and order.
    a = rng.choice(vol[interior], n, replace=False)
    b = rng.choice(vol[gap], n, replace=False)
    ranks = stats.rankdata(np.concatenate([a, b]), method="average")
    auc = (ranks[:n].sum() - n * (n + 1) / 2) / (n * n)
    return float(max(auc, 1 - auc)), n_interior, n_gap


def predictors(vol, *, max_voxels=MAX_VOXELS):
    """CT-only features in storage-normalized intensity and voxel coordinates."""
    from scipy import ndimage

    vol = _volume(vol, max_voxels)
    if vol.dtype.kind == "f" and (np.any(vol < 0) or np.any(vol > 1)):
        raise ValueError("floating CT must already be in [0,1] for comparable features")
    v = vol.astype(np.float32)
    if vol.dtype.kind == "u":
        v /= 255.0 if vol.dtype.itemsize == 1 else 65535.0
    gz, gy, gx = np.gradient(v)
    g = np.sqrt(gz * gz + gy * gy + gx * gx)
    gm = g[g > 0]
    result = {
        "intensity_std": float(v.std(dtype=np.float64)),
        "grad_median": float(np.median(gm)) if gm.size else None,
        "grad_p90_over_p50": float(np.percentile(gm, 90) / np.percentile(gm, 50))
        if gm.size
        else None,
    }
    del g, gm
    # The full symmetric structure tensor is necessary for orientation invariance.
    jzz, jyy, jxx, jzy, jzx, jyx = (
        ndimage.gaussian_filter(a * b, 2.0, mode="reflect")
        for a, b in ((gz, gz), (gy, gy), (gx, gx), (gz, gy), (gz, gx), (gy, gx))
    )
    del gz, gy, gx
    total = 0.0
    # Eigensolve one plane at a time, avoiding a full N x 3 x 3 matrix allocation.
    for z in range(v.shape[0]):
        tensor = np.empty((*v.shape[1:], 3, 3), dtype=np.float32)
        tensor[..., 0, 0], tensor[..., 1, 1], tensor[..., 2, 2] = jzz[z], jyy[z], jxx[z]
        tensor[..., 0, 1] = tensor[..., 1, 0] = jzy[z]
        tensor[..., 0, 2] = tensor[..., 2, 0] = jzx[z]
        tensor[..., 1, 2] = tensor[..., 2, 1] = jyx[z]
        trace = jzz[z] + jyy[z] + jxx[z]
        top = np.linalg.eigvalsh(tensor)[..., -1]
        ratio = np.divide(top, trace, out=np.zeros_like(trace), where=trace > 0)
        total += float(np.clip(ratio, 0, 1).sum(dtype=np.float64))
    result["tensor_anisotropy"] = total / v.size
    return result


def correlations(rows):
    """Pairwise complete descriptive correlations; tied ranks receive averages."""
    from scipy import stats

    result = {}
    for name in FEATURES:
        pairs = [
            (row[name], row["separability_auc"])
            for row in rows
            if row.get(name) is not None and row.get("separability_auc") is not None
        ]
        x, y = np.asarray(pairs, dtype=float).reshape(-1, 2).T
        reason = None
        if len(pairs) < 4:
            reason = "at least four paired cubes are required"
        elif np.ptp(x) == 0 or np.ptp(y) == 0:
            reason = "constant predictor or outcome"
        result[name] = {
            "status": "INDETERMINATE" if reason else "MEASURED",
            "n": len(pairs),
            "pearson": None if reason else float(stats.pearsonr(x, y).statistic),
            "spearman": None if reason else float(stats.spearmanr(x, y).statistic),
            "reason": reason,
        }
    return result


def _nrrd(read, path, **kwargs):
    """Report pynrrd's leaked parse errors as this input's ValueError."""
    try:
        return read(str(path), **kwargs)
    except (KeyError, StopIteration, zlib.error) as exc:
        # An empty file, an unsupported type or a corrupt gzip payload.
        raise ValueError(f"malformed NRRD {path}: {type(exc).__name__} {exc}") from exc


def _read_pair(volume_path, mask_path, max_voxels):
    import nrrd

    shapes = []
    for path in (volume_path, mask_path):
        if not path.is_file():
            raise ValueError(f"missing regular NRRD input: {path}")
        header = _nrrd(nrrd.read_header, path)
        if "kinds" in header and (
            len(header["kinds"]) != 3
            or any(kind not in {"domain", "space"} for kind in header["kinds"])
        ):
            raise ValueError("NRRD axes must be spatial, not channel/vector/time axes")
        shapes.append(_shape(header.get("sizes", ()), max_voxels))
    if shapes[0] != shapes[1]:
        raise ValueError("CT and mask NRRD header shapes must match")
    vol, _ = _nrrd(nrrd.read, volume_path, index_order="F")
    mask, _ = _nrrd(nrrd.read, mask_path, index_order="F")
    if vol.shape != shapes[0] or mask.shape != shapes[1]:
        raise ValueError("NRRD data shape changed after header inspection")
    return vol, mask


def build_report(data, *, max_voxels=MAX_VOXELS):
    import nrrd

    _voxel_limit(max_voxels)
    data = Path(data).resolve()
    if not data.is_dir():
        raise ValueError(f"data must be a local cube directory: {data}")
    rows = []
    # A dangling cube link (e.g. an unmounted external target) is a failed cube.
    for cube in sorted(
        p
        for p in data.iterdir()
        if p.name[:1].isdigit() and (p.is_dir() or not p.exists())
    ):
        vp, mp = cube / f"{cube.name}_volume.nrrd", cube / f"{cube.name}_mask.nrrd"
        row = {"cube": cube.name, "volume_path": str(vp), "mask_path": str(mp)}
        try:
            vol, mask = _read_pair(vp, mp, max_voxels)
            auc, n_int, n_gap = outcome_separability(vol, mask, max_voxels=max_voxels)
            row.update(predictors(vol, max_voxels=max_voxels))
            row.update(
                status="MEASURED" if auc is not None else "INDETERMINATE",
                separability_auc=auc,
                n_interior=n_int,
                n_gap=n_gap,
                samples_per_class=min(n_int, n_gap, MAX_SAMPLES)
                if auc is not None
                else 0,
                shape=list(vol.shape),
                source_dtype=str(vol.dtype),
                reason=None
                if auc is not None
                else "insufficient sheet-interior or gap population",
            )
        except (OSError, ValueError, TypeError, EOFError, nrrd.NRRDError) as exc:
            row.update(status="FAILED", reason=str(exc))
        rows.append(row)
    counts = {
        name.lower(): sum(row["status"] == name for row in rows)
        for name in ("MEASURED", "INDETERMINATE", "FAILED")
    }
    association = correlations(rows)
    status = (
        "FAILED"
        if counts["failed"]
        else (
            "MEASURED"
            if rows
            and not counts["indeterminate"]
            and all(value["status"] == "MEASURED" for value in association.values())
            else "INDETERMINATE"
        )
    )
    aucs = [
        row["separability_auc"]
        for row in rows
        if row.get("separability_auc") is not None
    ]
    return {
        "schema": "scan-quality-v2",
        "scope": "exploratory_scan_quality",
        "status": status,
        "data": str(data),
        "counts": {"requested": len(rows), **counts},
        "recipe": {
            "auc": "max(AUC, 1-AUC), average tied ranks; direction selected on scored sample",
            "sampling_seed": 0,
            "max_samples_per_class": MAX_SAMPLES,
            "min_population_per_class": MIN_POPULATION,
            "interior_erosion_iterations": 2,
            "gap_distance_voxels": [2, 6],
            "intensity_scaling": "uint8/255, uint16/65535; floating CT must be in [0,1]",
            "feature_precision": "float32",
            "tensor_anisotropy": "mean(lambda_max/trace), flat voxels zero",
            "tensor_sigma_voxels": 2.0,
            "tensor_boundary_mode": "reflect",
            "coordinate_units": "voxel indices; physical spacing not applied",
            "max_voxels": max_voxels,
        },
        "auc_summary": {
            "min": min(aucs),
            "median": float(np.median(aucs)),
            "max": max(aucs),
        }
        if aucs
        else None,
        "correlations": association,
        "cubes": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", required=True, help="local root of aligned NRRD cube pairs"
    )
    parser.add_argument(
        "--out", help="new JSON file outside the input tree; otherwise stdout only"
    )
    parser.add_argument(
        "--max-voxels",
        type=int,
        default=MAX_VOXELS,
        help="per-cube voxel bound checked before decoding (default: 256^3)",
    )
    args = parser.parse_args(argv)
    try:
        if args.max_voxels < 1:
            parser.error("--max-voxels must be positive")
        output = new_output(args.out, args.data) if args.out else None
        report = build_report(args.data, max_voxels=args.max_voxels)
        encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if output:
            # Cube directories and individual inputs can be external symlinks.
            # Protect the resolved declared sources, including missing inputs.
            sources = [Path(args.data)]
            for row in report["cubes"]:
                for name in ("volume_path", "mask_path"):
                    path = Path(row[name])
                    sources.extend((path, path.parent))
            with publish_new_file(output, *sources) as staging:
                staging.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        return 0 if report["status"] == "MEASURED" else 1
    except (OSError, ValueError) as exc:
        print(f"scan quality: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
