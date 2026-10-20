"""Exploratory, after finding 92: is ScrollGT's fiber GT offset from the CT's fiber centres on some cubes?

`neural_tracer_placement.py` records, per cube and thin entrant, `median_disp_perp_zyx`: the median displacement from
centreline to GT along each axis, over samples on fibers within 30 degrees of perpendicular to it. Two checks of what
it shows, each independent of the entrant it tests:

* **Cross-entrant.** One entrant's shift is applied to the other entrant's centreline (prediction + shift, since the
  displacement is GT - prediction), and that entrant's share within 2 voxels of the GT, of its samples within 6, is
  recomputed; and with the opposite shift.
* **The CT alone.** With s the mean of the two entrants' shifts, the CT smoothed at sigma 1 is sampled at the GT
  samples moved to P - t*s, t from -1 to 2 by 1/8: t = 0 is the GT, t = 1 the entrants' centre. t* is where the mean
  is highest; the gain is that mean minus the mean at the GT.

CPU only. Reads finding 91's and finding 85's runs, finding 85's CT arrays and reports/neural_tracer_placement.json;
writes reports/neural_tracer_gt_offset.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_placement as pl  # noqa: E402

CT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/zarr")
T = np.arange(-1, 2.001, 0.125)
SIGMA = 1.0
EDGE = 4  # GT samples this close to a face are left out of the CT profile, so the shifted samples stay inside


def gt_points(fibers, size: int) -> np.ndarray:
    return pl.gt_samples(fibers, size)[0]


def mean_shift(cube: dict) -> np.ndarray:
    return np.mean(
        [cube[e]["median_disp_perp_zyx"] for e in ("neural", "generator")], axis=0
    )


def cross_shift(gt: np.ndarray, pred: np.ndarray, shift: np.ndarray) -> dict:
    """An entrant's share within TOL of the GT (of its samples within RADIUS), as given, moved by another entrant's
    shift, and moved the opposite way."""
    from scipy.spatial import cKDTree

    tree = cKDTree(gt)

    def share(p):
        d, _ = tree.query(p, distance_upper_bound=pl.RADIUS)
        ok = np.isfinite(d)
        return float((d[ok] <= pl.TOL).mean()) if ok.any() else 0.0

    return {
        "le2": share(pred),
        "le2_shifted": share(pred + shift),
        "le2_opposite": share(pred - shift),
    }


def ct_peak(
    vol: np.ndarray, gt: np.ndarray, shift: np.ndarray
) -> tuple[float, float, list[float]]:
    """(t*, gain, profile) of the smoothed CT's mean over GT samples moved to P - t * shift."""
    from scipy import ndimage

    sm = ndimage.gaussian_filter(np.asarray(vol, np.float32), SIGMA)
    profile = [
        float(
            ndimage.map_coordinates(
                sm, (gt - t * shift).T, order=1, mode="nearest"
            ).mean()
        )
        for t in T
    ]
    k = int(np.argmax(profile))
    return float(T[k]), profile[k] - profile[int(np.argmin(np.abs(T)))], profile


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--placement", type=Path, default=Path("reports/neural_tracer_placement.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_gt_offset.json")
    )
    args = ap.parse_args()
    import zarr

    sys.path.insert(0, str(pl.f91.SG / "src"))
    from scrollgt.fibers.target import load_fiber_target

    placement = json.loads(args.placement.read_text())["cubes"]
    cubes = {}
    for c in pl.f91.ALL:
        size = int(c.rsplit("_", 1)[1])
        skel, _, _ = load_fiber_target(pl.f91.SG / "data" / f"fibers_{c}")
        gt = gt_points(skel.fibers, size)
        preds = {
            "neural": pl.predicted(pl.NEURAL / c / "fibers.afv", size),
            "generator": pl.predicted(pl.GENERATOR / f"{c}.afv", size),
        }
        row: dict = {"shift": mean_shift(placement[c]).tolist()}
        for ent, other in (("neural", "generator"), ("generator", "neural")):
            other_shift = np.asarray(placement[c][other]["median_disp_perp_zyx"], float)
            row[ent] = {
                "shift_from_other": other_shift.tolist(),
                **cross_shift(gt, preds[ent], other_shift),
            }
        vol = np.asarray(zarr.open(str(CT / f"{c}.zarr"), mode="r")[:])
        inner = gt[np.all((gt >= EDGE) & (gt < size - EDGE), axis=1)]
        t_star, gain, profile = ct_peak(vol, inner, np.asarray(row["shift"]))
        row["ct"] = {
            "t_star": t_star,
            "gain": gain,
            "profile": profile,
            "sd": float(np.std(vol)),
        }
        cubes[c] = row
        print(c, np.round(row["shift"], 2), round(row["neural"]["le2"], 3), round(row["neural"]["le2_shifted"], 3),
              t_star, flush=True)  # fmt: skip
    out = {
        "status": "exploratory, after finding 92's registered result",
        "t": T.tolist(),
        "sigma": SIGMA,
        "edge": EDGE,
        "placement": str(args.placement),
        "groups": {
            "in_sample": pl.f91.IN_SAMPLE,
            "s3": pl.f91.S3,
            "s5_held_out": pl.f91.S5_HELDOUT,
        },
        "cubes": cubes,
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
