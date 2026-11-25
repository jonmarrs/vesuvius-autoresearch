"""Finding 130: the rendered surface against the predicted sheet, with the fit's grid snapped and with a twice-denser one.

Registration: docs/preregistration/2026-11-20_first_letters_dense_snap.md.

    compare  R OUT.json --windings W... [--base outer80] [--dense dense2]

For each winding of both arms, with band_geometry.py's measures: the final winding's share of nodes within 2 voxels
of the predicted sheet (the surface prediction's signed distance field), overall and by radius tercile; the snapped
nodes' share; and the final winding's share within 2 voxels of its snapped triangles. Measured once.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))

import band_fit_quality as quality  # noqa: E402
import band_geometry as bg  # noqa: E402
import band_index as bi  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402

GAIN = 0.05
ON_TRIANGLES = 0.95


def measure(work: Path, arm: str, name: str, field, on_axis) -> dict:
    final, fv = analysis.load_tifxyz(work / f"final_{arm}" / f"{name}.tifxyz")
    snap, sv = analysis.load_tifxyz(work / f"snap_{arm}" / name)
    points = final[fv].astype(np.float64)
    d = field.at(points)
    radius = np.linalg.norm(points[:, :2] - on_axis(points[:, 2]), axis=1)
    terciles = np.digitize(radius, np.percentile(radius, [100 / 3, 200 / 3]))
    ok = np.isfinite(d)
    return {
        "final_within_2": bg._sheet(field, final, fv)["within_2"],
        "final_within_2_by_radius_tercile": [
            round(float((d[ok & (terciles == k)] <= bg.NEAR).mean()), 4) if (ok & (terciles == k)).any() else None
            for k in range(3)
        ],
        "snapped_within_2": bg._sheet(field, snap, sv)["within_2"],
        "on_snapped_triangles": round(float((bg.distance_to_triangles(points, snap, sv) <= bg.NEAR).mean()), 4),
        "final_nodes": int(fv.sum()),
        "snapped_nodes": int(sv.sum()),
    }  # fmt: skip


def verdict(
    gains: list[float | None], dense_on_triangles: list[float], steps_ok: bool
) -> str:
    # A missing share is not a measured gain. Scoring the others would publish a verdict
    # for a comparison that did not finish.
    if not steps_ok or not gains or any(gain is None for gain in gains):
        return "DOES_NOT_RUN"
    if (
        float(np.median(gains)) >= GAIN
        and float(np.median(dense_on_triangles)) >= ON_TRIANGLES
    ):
        return "DENSE_SNAP_HELPS"
    return "DENSE_SNAP_NO_GAIN"


def compare(root: Path, windings: list[str], base: str, dense: str, field=None) -> dict:
    work = root / "work"
    if field is None:
        field = quality.DistanceField(
            sorted((work / "surf_sdt").glob("*_surf_sdt.ome.zarr"))[0], "1"
        )
    on_axis = bg.axis_centre(bi.axis(root / "dataset" / "umbilicus.json"))
    gates = sorted((work / f"gate_{dense}").glob("*.json"))
    steps_ok = bool(gates) and all(
        json.loads(g.read_text())["exit"] == 0 for g in gates
    )
    rows = {}
    for name in windings:
        rows[name] = {
            arm: measure(work, arm, name, field, on_axis) for arm in (base, dense)
        }
        dense_share = rows[name][dense]["final_within_2"]
        base_share = rows[name][base]["final_within_2"]
        # No finite distance is not a share of zero, so it is not a gain either.
        rows[name]["gain"] = (
            None
            if dense_share is None or base_share is None
            else round(dense_share - base_share, 4)
        )
    gains = [r["gain"] for r in rows.values()]
    on_tri = [r[dense]["on_snapped_triangles"] for r in rows.values()]

    def med(values) -> float | None:
        # A tercile with no finite distance is None. Leave it out of the median; if every
        # winding is outside the field there, the median is absent rather than a crash.
        numbers = [value for value in values if value is not None]
        if not numbers:
            return None
        return round(float(np.median(numbers)), 4)

    def all_measured(values) -> float | None:
        # The gain, and each arm's sheet share, count every winding. Dropping a missing
        # one would publish a median for a comparison the verdict refuses.
        values = list(values)
        if any(value is None for value in values):
            return None
        return med(values)

    return {
        "finding": 130,
        "arms": [base, dense],
        "windings": rows,
        "steps": {g.stem: json.loads(g.read_text()) for g in gates},
        "summary": {
            "gain_median": all_measured(gains),
            "final_within_2_median": {
                a: all_measured(r[a]["final_within_2"] for r in rows.values())
                for a in (base, dense)
            },
            "snapped_within_2_median": {
                a: med(r[a]["snapped_within_2"] for r in rows.values())
                for a in (base, dense)
            },
            "on_snapped_triangles_median": {
                a: med(r[a]["on_snapped_triangles"] for r in rows.values())
                for a in (base, dense)
            },
            "final_within_2_by_radius_tercile_median": {
                a: [
                    med(
                        r[a]["final_within_2_by_radius_tercile"][k]
                        for r in rows.values()
                    )
                    for k in range(3)
                ]
                for a in (base, dense)
            },
        },  # fmt: skip
        "verdict": verdict(gains, on_tri, steps_ok),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compare")
    c.add_argument("root", type=Path)
    c.add_argument("out", type=Path)
    c.add_argument("--windings", nargs="+", required=True)
    c.add_argument("--base", default="outer80")
    c.add_argument("--dense", default="dense2")
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    result = compare(args.root, args.windings, args.base, args.dense)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("summary", "verdict")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
