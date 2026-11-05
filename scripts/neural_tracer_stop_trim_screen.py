"""After finding 101 (reports/neural_tracer_confidence_stops.md), an exploratory screen, not registered: does trimming
the end of each trace that stopped on confidence buy precision? Finding 101 found most of villa's neural-tracer
confidence stops already off the hand-traced fibers, and said that this "does not show that a stop or trim rule would
help". A trim applied after tracing changes no other trace, so the stock runs give its result exactly.

For each fiber of findings 97/98's stock runs (villa ccb431818, 128 voxels of CT context), every interior, unlinked
confidence-stop end (finding 101's definition: no link, at least EDGE voxels from a cube face) loses its last k voxels
of arclength; a piece left shorter than villa's --min-length is dropped, as villa drops short pieces when it writes.
Each cube is then re-scored with ScrollGT at tolerances 2 and 4. k = 0 must reproduce finding 104's recorded baseline
rows on every cube, or the status is BASELINE_DRIFT.

Beside the fixed trims, a ceiling that no tracer could apply: the oracle trims each such end back to its last point
within ORACLE_TOL voxels of a hand-traced fiber (a piece with none is dropped). It bounds what any stop-end trim could
buy in precision without losing covered length.

Development data only: the in-sample cubes. The held-out cubes are not read, so a later trim rule can still be tested
on them. It decides nothing. Writes reports/evidence/neural_tracer_stop_trim_screen_2026-11-05.json once.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_confidence_stops as cs  # noqa: E402

f91, al = cs.f91, cs.afv_to_labels
BASELINE = Path("reports/neural_tracer_refit_retry.json")
KS = (0.0, 10.0, 20.0, 40.0)
TOLS = (2.0, 4.0)
# villa's volume tracer --min-length (points): it drops shorter written pieces
MIN_POINTS = 48
METRICS = ("precision", "coverage", "erl_merge_penalized", "merges")
ORACLE_TOL = 2.0


def trim_end(q: np.ndarray, k: float) -> np.ndarray:
    """Polyline q without the first k voxels of arclength from q[0] (empty if q is no longer than k)."""
    if k <= 0:
        return q
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))])
    if s[-1] <= k:
        return q[:0]
    i = int(np.searchsorted(s, k, side="right"))
    return np.concatenate([[cs._along(q, k)], q[i:]])


def oracle_end(q: np.ndarray, on) -> np.ndarray:
    """q from its first point that `on` (points -> bool) accepts, walking in from q[0] (empty if none is)."""
    hit = np.nonzero(on(q))[0]
    return q[hit[0] :] if len(hit) else q[:0]


def trimmed(fibers: dict, meta: dict, size: int, k, on=None) -> tuple[dict, int, int]:
    """fibers (id -> cube ZYX) with each interior, unlinked confidence-stop end trimmed by k voxels, or, for
    k == "oracle", back to its last point that `on` accepts; (fibers, ends, dropped)."""
    out, ends, dropped = {}, 0, 0

    def cut(q):
        return oracle_end(q, on) if k == "oracle" else trim_end(q, k)

    for fid, poly in fibers.items():
        reasons, links = meta[fid]
        q = poly
        for e in cs.stops(poly, reasons, links, size):
            if (
                e["reason"] != "confidence"
                or e["link"] >= 0
                or e["face_distance"] < cs.EDGE
            ):
                continue
            ends += 1
            q = cut(q) if e["end"] == 0 else cut(q[::-1])[::-1]
        if len(q) < len(poly) and len(q) < MIN_POINTS:
            dropped += 1
            continue
        out[fid] = q
    return out, ends, dropped


def near_reference(skel, tol: float = ORACLE_TOL):
    """points (cube ZYX) -> bool: the voxel each rounds to lies within tol of a voxel ScrollGT marks as reference."""
    from scipy.spatial import cKDTree
    from scrollgt.fibers.eval_trace import _resample_fiber

    ref = [np.rint(p) for f in skel.fibers for p, _ in _resample_fiber(f.coords, f.edges, step=cs.STEP) if p is not None]  # fmt: skip
    tree = cKDTree(np.unique(np.asarray(ref), axis=0))
    return lambda q: tree.query(np.rint(q))[0] <= tol


def screen_cube(cube: str, ks=KS + ("oracle",)) -> dict:
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import score_tracing
    from scrollgt.fibers.target import load_fiber_target

    size = int(cube.rsplit("_", 1)[1])
    run = cs.RUNS[size] / cube
    afv = al.read_afv(run / "fibers.afv")
    meta, problems = cs.read_meta(run, afv)
    if problems:
        raise ValueError(f"{cube}: fiber JSONs do not match the .afv ({problems})")
    fibers = {k: al.to_cube_zyx(v, (cs.MARGIN,) * 3) for k, v in afv.items()}
    skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{cube}")
    on = near_reference(skel)
    out = {}
    for k in ks:
        kept, ends, dropped = trimmed(fibers, meta, size, k, on)
        labels = al.rasterize(kept, (size,) * 3)
        out[k if k == "oracle" else f"{k:g}"] = {
            "rows": {
                f"{t:g}": score_tracing(skel, labels, tolerance=t).as_row()
                for t in TOLS
            },
            "ends_trimmed": ends,
            "fibers_dropped": dropped,
            "fibers_kept": len(kept),
        }
    return out


def summary(per_cube: dict) -> dict:
    """Per k and tolerance: the median change in each metric over the cubes (ERLpen as a ratio), and how many rose."""
    out = {}
    for k in [f"{k:g}" for k in KS[1:]] + ["oracle"]:
        for t in (f"{t:g}" for t in TOLS):
            base = {c: r["0"]["rows"][t] for c, r in per_cube.items()}
            now = {c: r[k]["rows"][t] for c, r in per_cube.items()}
            d_prec = [now[c]["precision"] - base[c]["precision"] for c in base]
            d_cov = [now[c]["coverage"] - base[c]["coverage"] for c in base]
            erl = [
                now[c]["erl_merge_penalized"] / base[c]["erl_merge_penalized"]
                for c in base
            ]
            out[f"k{k}_tol{t}"] = {
                "precision_change_median": statistics.median(d_prec),
                "precision_change_range": [min(d_prec), max(d_prec)],
                "coverage_change_median": statistics.median(d_cov),
                "coverage_change_range": [min(d_cov), max(d_cov)],
                "erlpen_ratio_median": statistics.median(erl),
                "erlpen_rose_on": sum(v > 1 for v in erl),
                "merges": [sum(base[c]["merges"] for c in base), sum(now[c]["merges"] for c in base)],
            }  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=Path("reports/evidence/neural_tracer_stop_trim_screen_2026-11-05.json"))  # fmt: skip
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: the screen writes its record once")
    recorded = json.loads(BASELINE.read_text())
    per_cube, drift = {}, []
    for c in cs.IN_SAMPLE:
        per_cube[c] = screen_cube(c)
        for t in TOLS:
            want = recorded[f"baseline_rows_tol{t:g}"][c]
            got = per_cube[c]["0"]["rows"][f"{t:g}"]
            if any(got[m] != want[m] for m in want if m in got):
                drift.append(f"{c} tol {t:g}")
        r0, r20, ro = (per_cube[c][k]["rows"]["2"] for k in ("0", "20", "oracle"))
        print(
            c,
            *(f"{m} {r0[m]:.4g}->{r20[m]:.4g}|{ro[m]:.4g}" for m in METRICS),
            flush=True,
        )
    out = {
        "after": "reports/neural_tracer_confidence_stops.md (finding 101); not registered, decides nothing",
        "status": "BASELINE_DRIFT" if drift else "OK",
        "baseline_drift": drift,
        "cubes": list(cs.IN_SAMPLE),
        "ks_voxels": list(KS),
        "oracle_tolerance": ORACLE_TOL,
        "edge_voxels": cs.EDGE,
        "min_points": MIN_POINTS,
        "per_cube": per_cube,
        "summary": summary(per_cube),
    }
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(out["status"], "wrote", a.out)
    return 0 if not drift else 1


if __name__ == "__main__":
    sys.exit(main())
