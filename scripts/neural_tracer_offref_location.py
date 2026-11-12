"""After the stop-trim screen (reports/neural_tracer_stop_trim_screen.md), an exploratory analysis, not registered: where
along villa's neural-tracer fibers does the length off the hand-traced reference lie? The screen found that even an
oracle trim at confidence stops removes only 16% of it, and could not say where the rest is.

For each fiber of findings 97/98's stock runs (villa ccb431818, 128 voxels of CT context), inside the cube, each point
is on the reference if the voxel it rounds to lies within the tolerance of a voxel ScrollGT marks as reference (the
screen's oracle test), and is assigned its nearest reference fiber. Each point carries half of each segment it touches.
The off-reference length then splits, without remainder, into:

* whole_off: fibers with no on-reference point;
* tail:<end>: off points before a fiber's first on-reference point or after its last, by that end's stop (finding 101's
  classes: reason, linked or not, within EDGE of a face or not; or outside the cube);
* gap_same: interior runs of off points whose on-reference neighbours on both sides are nearest the same reference fiber;
* gap_switch: interior runs between two different reference fibers.

Counts (keys ending _n) are kept apart from lengths. Two ceilings no tracer could reach: the pooled precision if exactly
the departure-shaped length (tails and gap_switch) were cut and nothing else, and if exactly the whole_off fibers were.

The gate: pooled over the cubes, this point-based precision must be within PROXY_TOL of ScrollGT's pooled precision for
the same runs (the screen's k = 0 rows) at each tolerance, or the status is PROXY_DRIFT.

Beside it, where each point set sits on the CT: per axis, the shift in -3..+3 voxels that maximises the mean CT
(trilinear, integer coordinate = voxel centre) at the traced points and at the reference's resampled points (not
rounded). A maximum at the end of that range is recorded as None: the CT is still rising there.

Development data only: the in-sample cubes. It decides nothing. Writes
reports/evidence/neural_tracer_offref_location_2026-11-05.json once.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_stop_trim_screen as ts  # noqa: E402

cs, f91, al = ts.cs, ts.cs.f91, ts.cs.afv_to_labels
SCREEN = Path("reports/evidence/neural_tracer_stop_trim_screen_2026-11-05.json")
TOLS = (2.0, 4.0)
PROXY_TOL = 0.01
SHIFTS = np.round(np.arange(-3.0, 3.01, 0.25), 2)
CT = {
    256: Path(
        "/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer/ct_context_run/ct"
    ),
    512: Path(
        "/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer/ct_context_512_run/ct"
    ),
}


def point_weights(q: np.ndarray) -> np.ndarray:
    """Half of each segment's length to each of its two points (sums to the polyline's length)."""
    seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
    w = np.zeros(len(q))
    w[:-1] += seg / 2
    w[1:] += seg / 2
    return w


def end_class(e: dict) -> str:
    if e["face_distance"] < 0:
        return "outside_cube"
    linked = "linked" if e["link"] >= 0 else "unlinked"
    return f"{e['reason']}|{linked}|{'edge' if e['face_distance'] < cs.EDGE else 'interior'}"


def locate(
    w: np.ndarray, on: np.ndarray, nearest: np.ndarray, ends: tuple[str, str]
) -> dict:
    """One fiber's off-reference length by place. w: point weights (0 outside the cube), on: on-reference points,
    nearest: each point's nearest reference fiber, ends: end_class of its first and last point."""
    out = defaultdict(float)
    off = (w > 0) & ~on
    if not on.any():
        out["whole_off"] += w[off].sum()
        out["whole_off_n"] += 1
        return dict(out)
    idx = np.nonzero(on)[0]
    a, b = idx[0], idx[-1]
    out["tail:" + ends[0]] += w[:a][off[:a]].sum()
    out["tail:" + ends[1]] += w[b + 1 :][off[b + 1 :]].sum()
    for i, j in zip(idx[:-1], idx[1:], strict=False):
        if j > i + 1:
            key = "gap_same" if nearest[i] == nearest[j] else "gap_switch"
            out[key] += w[i + 1 : j][off[i + 1 : j]].sum()
            out[key + "_n"] += 1
    return dict(out)


def reference(skel) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ScrollGT's resampled reference as unique rounded voxels, each with the first fiber that reaches it, and the
    resampled points themselves."""
    from scrollgt.fibers.eval_trace import _resample_fiber

    seen, pts, lab, raw = set(), [], [], []
    for j, f in enumerate(skel.fibers):
        for p, _ in _resample_fiber(f.coords, f.edges, step=cs.STEP):
            if p is None:
                continue
            raw.append(p)
            k = tuple(np.rint(p).astype(int))
            if k not in seen:
                seen.add(k)
                pts.append(k)
                lab.append(j)
    return np.asarray(pts, float), np.asarray(lab), np.asarray(raw, float)


def trilinear(v: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Sample ``v`` at points ``p``. An integer coordinate is that voxel.

    Points outside the volume are held on the boundary. A sample on the far
    face has no next voxel; that neighbour's weight is zero, so the sample is
    the boundary voxel. Stopping one thousandth of a voxel early mixed the
    face with the voxel before it. A non-finite coordinate is NaN. A NaN voxel
    counts only when its weight is positive, so a zero-weight neighbour does
    not clear the sample.
    """
    raw = np.asarray(p, np.float64)
    finite = np.all(np.isfinite(raw), axis=1)
    # Floor of a non-finite coordinate warns and is not a voxel index.
    limit = np.asarray(v.shape, np.float64) - 1
    p = np.clip(np.where(finite[:, None], raw, 0.0), 0, limit)
    i = np.floor(p).astype(np.int64)
    f = p - i
    out = np.zeros(len(p))
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                wz = f[:, 0] if dz else 1.0 - f[:, 0]
                wy = f[:, 1] if dy else 1.0 - f[:, 1]
                wx = f[:, 2] if dx else 1.0 - f[:, 2]
                weight = wz * wy * wx
                use = (weight > 0) & finite
                if not np.any(use):
                    continue
                out[use] += (
                    weight[use] * v[i[use, 0] + dz, i[use, 1] + dy, i[use, 2] + dx]
                )
    out[~finite] = np.nan
    return out


def shift_profile(v: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """(3, len(SHIFTS)): the mean CT at pts shifted along each axis."""
    out = np.zeros((3, len(SHIFTS)))
    for ax in range(3):
        for j, s in enumerate(SHIFTS):
            q = pts.copy()
            q[:, ax] += s
            out[ax, j] = trilinear(v, q).mean()
    return out


def peak(profile: np.ndarray) -> list[float | None]:
    """Per axis, the shift of the maximum, refined by a parabola through it and its neighbours (None at the range's
    end, where the profile has not turned)."""
    step = float(SHIFTS[1] - SHIFTS[0])
    res: list[float | None] = []
    for row in profile:
        j = int(np.argmax(row))
        if not 0 < j < len(row) - 1:
            res.append(None)
            continue
        a, b, c = row[j - 1], row[j], row[j + 1]
        res.append(float(SHIFTS[j] + 0.5 * (a - c) / (a - 2 * b + c) * step))
    return res


def measure_cube(cube: str) -> dict:
    import zarr
    from scipy.spatial import cKDTree

    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.target import load_fiber_target

    size = int(cube.rsplit("_", 1)[1])
    run = cs.RUNS[size] / cube
    afv = al.read_afv(run / "fibers.afv")
    meta, problems = cs.read_meta(run, afv)
    if problems:
        raise ValueError(f"{cube}: fiber JSONs do not match the .afv ({problems})")
    fibers = {k: al.to_cube_zyx(v, (cs.MARGIN,) * 3) for k, v in afv.items()}
    skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{cube}")
    ref, lab, raw = reference(skel)
    tree = cKDTree(ref)
    out = {}
    for t in TOLS:
        place, total, on_len = defaultdict(float), 0.0, 0.0
        for fid, q in fibers.items():
            reasons, links = meta[fid]
            ends = tuple(end_class(e) for e in cs.stops(q, reasons, links, size))
            w = np.where(cs._inside(q, size), point_weights(q), 0.0)
            d, i = tree.query(np.rint(q))
            on = (d <= t) & (w > 0)
            total += w.sum()
            on_len += w[on].sum()
            for k, v in locate(w, on, lab[i], ends).items():
                place[k] += v
        out[f"{t:g}"] = {"length": total, "on_reference": on_len, "place": dict(place)}
    inside = np.concatenate([q[cs._inside(q, size)] for q in fibers.values()])
    v = np.asarray(zarr.open(str(CT[size] / f"{cube}.zarr" / "0"), mode="r")[...])
    out["ct_profile"] = {
        "traced": shift_profile(v, inside + cs.MARGIN).tolist(),
        "reference": shift_profile(v, raw + cs.MARGIN).tolist(),
    }
    return out


def summary(per_cube: dict, screen: dict) -> dict:
    out = {}
    for t in (f"{t:g}" for t in TOLS):
        length = sum(r[t]["length"] for r in per_cube.values())
        on = sum(r[t]["on_reference"] for r in per_cube.values())
        place = defaultdict(float)
        for r in per_cube.values():
            for k, v in r[t]["place"].items():
                place[k] += v
        off = length - on
        rows = [screen["per_cube"][c]["0"]["rows"][t] for c in per_cube]
        pred = sum(r["pred_length"] for r in rows)
        out[f"tol{t}"] = {
            "point_precision": on / length,
            "scrollgt_precision": sum(r["precision"] * r["pred_length"] for r in rows)
            / pred,
            "off_length": off,
            "shares": {k: v / off for k, v in place.items() if not k.endswith("_n")},
            "counts": {k: v for k, v in place.items() if k.endswith("_n")},
            "unplaced": off - sum(v for k, v in place.items() if not k.endswith("_n")),
        }
        departures = (
            sum(v for k, v in place.items() if k.startswith("tail:"))
            + place["gap_switch"]
        )
        out[f"tol{t}"]["precision_without_departures"] = on / (length - departures)
        out[f"tol{t}"]["precision_without_whole_off"] = on / (
            length - place["whole_off"]
        )
    for which in ("traced", "reference"):
        prof = np.mean([r["ct_profile"][which] for r in per_cube.values()], axis=0)
        out[f"ct_peak_{which}"] = peak(prof)
        out[f"ct_peak_{which}_per_cube"] = {
            c: peak(np.asarray(r["ct_profile"][which])) for c, r in per_cube.items()
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=Path("reports/evidence/neural_tracer_offref_location_2026-11-05.json"))  # fmt: skip
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: the analysis writes its record once")
    screen = json.loads(SCREEN.read_text())
    per_cube = {}
    for c in cs.IN_SAMPLE:
        per_cube[c] = measure_cube(c)
        print(c, {t: round(per_cube[c][t]["on_reference"] / per_cube[c][t]["length"], 4) for t in ("2", "4")}, flush=True)  # fmt: skip
    s = summary(per_cube, screen)
    drift = [
        t
        for t in ("tol2", "tol4")
        if abs(s[t]["point_precision"] - s[t]["scrollgt_precision"]) > PROXY_TOL
    ]
    out = {
        "after": "reports/neural_tracer_stop_trim_screen.md; not registered, decides nothing",
        "status": "PROXY_DRIFT" if drift else "OK",
        "proxy_drift": drift,
        "cubes": list(cs.IN_SAMPLE),
        "tolerances": list(TOLS),
        "proxy_tolerance": PROXY_TOL,
        "edge_voxels": cs.EDGE,
        "shifts_voxels": SHIFTS.tolist(),
        "per_cube": per_cube,
        "summary": s,
    }
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(out["status"], "wrote", a.out)
    return 0 if not drift else 1


if __name__ == "__main__":
    sys.exit(main())
