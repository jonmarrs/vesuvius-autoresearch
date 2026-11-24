"""Finding 137, checks written after the result (not registered): did the fit declared clockwise turn the other way
in the scan, and how do its windings meet the sheets the published-direction fit found?

turn    For each of the four read windings of each fit, at 7 rows from 20% to 80% of its height: the angle around
        the band's umbilicus, unwrapped along the columns, from the first valid node to the last. A fit's windings
        all turn one way; the two fits should turn opposite ways if the declared direction took effect.
seams   Along 9 rows (10% to 90%) of each read winding of the fit declared clockwise, every lattice point (4 voxels
        apart, `mesh_step_analysis.lattice_points`) is matched to the nearest lattice point of the published fit's
        raw windings w020 to w050 within 4 voxels (`mesh_step_analysis.ACCEPT`), giving that winding's index k and
        its column fraction f. Walking along the row, a change of k with f jumping by more than half a turn is the
        published fit's own winding seam (the same sheet); a change of k with f continuous is a crossing of |dk|
        sheets. A mirrored spiral that sits on the sheets must cross a net 2 sheets a turn.

usage: wrong_hand_audit.py BAND_DIR OUT.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))
import mesh_step_analysis as analysis  # noqa: E402

READ = ("w033", "w034", "w035", "w036")
STANDS_IN = (
    20,
    50,
)  # the published fit's raw windings that stand in for the sheets, inclusive
TURN_ROWS = (0.2, 0.8, 7)
SEAM_ROWS = (0.1, 0.9, 9)


def fitted(band: Path, arm: str) -> Path:
    (patch,) = sorted((band / "work" / f"fit_{arm}").glob("*_0-patch"))
    return patch / "meshes" / "fitted"


def umbilicus(band: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pts = json.loads((band / "dataset" / "umbilicus.json").read_text())[
        "control_points"
    ]
    pts = sorted(pts, key=lambda p: p["z"])
    return tuple(np.array([p[a] for p in pts], float) for a in "zxy")  # type: ignore[return-value]


def rows(n: int, spec: tuple[float, float, int]) -> np.ndarray:
    lo, hi, k = spec
    return np.linspace(n * lo, n * hi, k).astype(int)


def turn_degrees(
    mesh: Path, umb: tuple[np.ndarray, np.ndarray, np.ndarray]
) -> list[float]:
    """The unwrapped angle around the umbilicus from the first to the last valid node of each sampled row."""
    xyz, valid = analysis.load_tifxyz(mesh)
    uz, ux, uy = umb
    out = []
    for r in rows(xyz.shape[0], TURN_ROWS):
        p = xyz[r][valid[r]]
        if len(p) < 50:
            continue
        cx, cy = np.interp(p[:, 2], uz, ux), np.interp(p[:, 2], uz, uy)
        a = np.unwrap(np.arctan2(p[:, 1] - cy, p[:, 0] - cx))
        out.append(round(float(np.degrees(a[-1] - a[0])), 1))
    return out


def seams(wrong: Path, right: Path) -> dict:
    from scipy.spatial import cKDTree

    pts, lab, frac = [], [], []
    for mesh in sorted(p for p in right.iterdir() if re.fullmatch(r"w[0-9]+", p.name)):
        k = int(mesh.name[1:])
        if not STANDS_IN[0] <= k <= STANDS_IN[1]:
            continue
        p, ok = analysis.lattice_points(*analysis.load_tifxyz(mesh))
        _, cc = np.nonzero(ok)
        pts.append(p[ok])
        lab.append(np.full(len(cc), k))
        frac.append(cc / ok.shape[1])
    tree = cKDTree(np.concatenate(pts))
    labels, fracs = np.concatenate(lab), np.concatenate(frac)
    out = {}
    for name in READ:
        p, ok = analysis.lattice_points(*analysis.load_tifxyz(wrong / name))
        matched = total = wraps = 0
        dks: list[int] = []
        sampled = rows(ok.shape[0], SEAM_ROWS)
        for r in sampled:
            cols = np.flatnonzero(ok[r])
            d, j = tree.query(p[r, cols], distance_upper_bound=analysis.ACCEPT)
            hit = np.isfinite(d)
            total += len(cols)
            matched += int(hit.sum())
            ks, fs = labels[j[hit]], fracs[j[hit]]
            for a in range(1, len(ks)):
                if ks[a] == ks[a - 1]:
                    continue
                if abs(fs[a] - fs[a - 1]) > 0.5:
                    wraps += 1
                else:
                    dks.append(int(ks[a] - ks[a - 1]))
        values, counts = np.unique(dks, return_counts=True)
        out[name] = {
            "rows": len(sampled),
            "lattice_points": total,
            "share_within_accept": round(matched / max(total, 1), 4),
            "published_seams_passed": wraps,
            "crossings": len(dks),
            "crossing_dk_counts": {
                str(int(v)): int(c) for v, c in zip(values, counts, strict=True)
            },
            "net_dk_per_row": round(sum(dks) / len(sampled), 2),
        }
    return out


def main(band: Path, out: Path) -> dict:
    right, wrong = fitted(band, "full"), fitted(band, "full-otherhand")
    umb = umbilicus(band)
    record = {
        "finding": 137,
        "registered": False,
        "written": "after the result, to check it",
        "turn_degrees": {
            arm: {w: turn_degrees(mesh / w, umb) for w in READ}
            for arm, mesh in (("right", right), ("wrong", wrong))
        },
        "seams": {
            "stands_in_for_the_sheets": f"the published fit's raw windings w{STANDS_IN[0]:03d} to w{STANDS_IN[1]:03d}",
            "accept_voxels": analysis.ACCEPT,
            "by_winding": seams(wrong, right),
        },
    }
    out.write_text(json.dumps(record, indent=1) + "\n")
    return record


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    print(json.dumps(main(Path(sys.argv[1]), Path(sys.argv[2])), indent=1))
