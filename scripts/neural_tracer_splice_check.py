"""Finding 105 as polylines: `neural_tracer_splice.py` on each of findings 97 and 98's 21 runs, read from their tiles as
villa writes them, rasterized and scored by ScrollGT at tolerance 0 on the labels grown at τ, beside finding 105's
labelling rows. A check of the tool against the registered result, not a new rule; CPU only.

The gate, per cube: the pieces read from the tiles, unspliced, reproduce finding 105's baseline rows exactly at τ = 2
and 4, and the tool makes as many splices as finding 105's record.

Usage: .venv/bin/python scripts/neural_tracer_splice_check.py [--cubes C ...] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_confidence_stops as cs  # noqa: E402
import neural_tracer_link_splice as ls  # noqa: E402
import neural_tracer_splice as tool  # noqa: E402

F105 = Path("reports/neural_tracer_link_splice.json")
FIELDS = ls.FIELDS + ("precision", "pred_length")


def summarize(per_cube: dict, cubes: list) -> dict | None:
    rows = [per_cube[c] for c in cubes if c in per_cube]
    if not rows:
        return None
    out = {}
    for t in ("tol2", "tol4"):
        poly = [r[t]["poly_gain"] for r in rows]
        out[t] = {
            "median_gain_poly": statistics.median(poly),
            "median_gain_labelling": statistics.median(r[t]["labelling_gain"] for r in rows),
            "min_gain_poly": min(poly),
            "cubes_gaining": sum(g > 0 for g in poly),
            "n": len(rows),
            "merges": {k: sum(r[t][k]["merges"] for r in rows) for k in ("base", "poly")},
            "median_coverage_change": statistics.median(r[t]["poly"]["coverage"] - r[t]["base"]["coverage"] for r in rows),
            "median_precision_change": statistics.median(r[t]["poly"]["precision"] - r[t]["base"]["precision"] for r in rows),
        }  # fmt: skip
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cubes", nargs="*")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/evidence/neural_tracer_splice_polylines_2026-11-06.json"),
    )
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists: the record is written once")
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import _dilate_labels, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    f105 = json.loads(F105.read_text())["per_cube"]
    per_cube, gate = {}, {}
    cubes = args.cubes or ls.HELD_OUT + ls.IN_SAMPLE
    for n, c in enumerate(cubes, 1):
        t0 = time.time()
        size = int(c.rsplit("_", 1)[1])
        pieces, meta, run = tool.load_run(cs.RUNS[size] / c)
        arc = float(run["overlap"]) * float(run["grid_scale"])
        polys, members, summary = tool.splice(pieces, meta, arc)
        problems = [] if summary["splices"] == f105[c]["splices"] else ["splices"]
        if arc != ls.SPLICE_ARC:
            problems.append("arc_limit")
        skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
        zyx = {
            k: afv_to_labels.to_cube_zyx(v, (cs.MARGIN,) * 3) for k, v in pieces.items()
        }
        base_lab = afv_to_labels.rasterize(zyx, (size,) * 3)
        lab = afv_to_labels.rasterize({k: afv_to_labels.to_cube_zyx(v, (cs.MARGIN,) * 3) for k, v in polys.items()},
                                      (size,) * 3)  # fmt: skip
        rec = dict(summary)
        for tol in ls.TOLS:
            t = f"tol{int(tol)}"
            b = score_tracing(
                skel, _dilate_labels(base_lab, tol), tolerance=0.0
            ).as_row()
            s = score_tracing(skel, _dilate_labels(lab, tol), tolerance=0.0).as_row()
            problems += [
                f"{t}:base:{f}" for f in ls.FIELDS if b[f] != f105[c][t]["base"][f]
            ]
            rec[t] = {"base": {f: b[f] for f in FIELDS}, "poly": {f: s[f] for f in FIELDS},
                      "poly_gain": s["erl_merge_penalized"] / b["erl_merge_penalized"] - 1,
                      "labelling_gain": f105[c][t]["splice"]["gain"]}  # fmt: skip
        per_cube[c], gate[c] = rec, problems
        print(f"[{n}/{len(cubes)}] {c}: gate {problems or 'ok'}; {summary['splices']} splices; tol2 poly "
              f"{rec['tol2']['poly_gain']:+.3f} (labelling {rec['tol2']['labelling_gain']:+.3f}); tol4 poly "
              f"{rec['tol4']['poly_gain']:+.3f} ({rec['tol4']['labelling_gain']:+.3f}); {time.time() - t0:.0f} s",
              flush=True)  # fmt: skip
    status = (
        "GATE_FAILED" if any(gate.values()) else ("PARTIAL" if args.cubes else "OK")
    )
    out = {
        "finding": str(F105),
        "status": status,
        "gate": gate,
        "summary": {
            "held_out": summarize(per_cube, ls.HELD_OUT),
            "in_sample": summarize(per_cube, ls.IN_SAMPLE),
        },
        "per_cube": per_cube,
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{status} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
