"""docs/preregistration/2026-11-02_neural_tracer_refit_retry.md -- villa's neural fiber tracer with its own refit
retry at confidence stops (`TraceParams.refit_retry`, which villa's volume tracer leaves off), on findings 97 and 98's
inputs and command, through scripts/neural_tracer_refit_arm.py.

Finding 102 (reports/neural_tracer_continuity_ceiling.md) found that perfect continuation from the tracer's confidence
stops would raise held-out ERLpen by a median 0.314, and by 0.061 within 20 voxels of each stop. This runs the one
continuation rule villa already has against findings 97 and 98's stock runs (the baseline). A floor arm changes only
the forward chunk, which villa treats as a speed setting, to measure what batch composition alone moves.
* `refit`: the retry on, on all 21 cubes;
* `floor`: villa's tracer through the launcher with `--forward-chunk 64` (villa's default is 128), on the ten held-out
  cubes.

  smoke  the launcher in its `villa` arm, on SMOKE, must reproduce finding 97's run point for point
  score  score each run in the cube's frame at tolerances 2 and 4, beside the baseline; the run records; the
         registered predictions and decision rule. Writes reports/neural_tracer_refit_retry.json.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_ct_context as cc  # noqa: E402
import neural_tracer_steep_heading as sh  # noqa: E402

f91 = cc.f91
PEN, COV, PREC, MERGES = sh.PEN, sh.COV, sh.PREC, "merges"
TOLS, MARGIN = sh.TOLS, sh.MARGIN
HELD, IN_SAMPLE, ALL_CUBES, SMOKE = sh.HELD, sh.IN_SAMPLE, sh.ALL_CUBES, sh.SMOKE
BASE_RUNS = sh.BASE_RUNS
ARMS = ("refit", "floor")
ARM_CUBES = {"refit": ALL_CUBES, "floor": HELD}
IN_EFFECT = {
    "refit": True,
    "floor": False,
}  # refit_retry as the launcher records it in each run
FLOOR_CHUNK = 64  # the floor arm's --forward-chunk
CEILING = Path("reports/neural_tracer_continuity_ceiling.json")
# The registered predictions (docs/preregistration/2026-11-02_neural_tracer_refit_retry.md).
GAIN_BAR = 0.10  # P1: the refit arm's median held-out ERLpen gain
FLOOR_MAX = 0.03  # the floor arm's median |ERLpen change| over the held-out cubes must lie below this
P3_DROP, P3_AT_LEAST = (
    0.03,
    8,
)  # P3: precision at most P3_DROP lower on at least P3_AT_LEAST held-out cubes


def gains(rows: dict, base: dict, cubes, key=PEN) -> dict:
    if zero := [c for c in cubes if base[c][key] <= 0]:
        raise ValueError(f"no gain over a baseline {key} of 0: {zero}")
    return {c: rows[c][key] / base[c][key] - 1 for c in cubes}


def ceiling_gains(path: Path = CEILING) -> dict:
    """Finding 102's ceiling U, as a gain over the same baseline, by cube (tolerance 2)."""
    d = json.loads(path.read_text())
    return {c: d["per_cube"][c]["tol2"]["U"]["gain"] for c in ALL_CUBES}


def run_record(run: Path) -> dict:
    """tiles.jsonl counts (the last line of each tile), its stop counts and seconds, and the launcher's record."""
    lines = [json.loads(s) for s in (run / "tiles.jsonl").read_text().splitlines() if s.strip()]  # fmt: skip
    tiles = {t["tile"]: t for t in lines}
    keys = {"dots", "owned_dots", "traced", "fibers", "traced_vox", "kept_vox"}
    keys |= {k for t in tiles.values() for k in t if k.startswith("stop_")}
    out: dict = {k: int(sum(t.get(k, 0) for t in tiles.values())) for k in sorted(keys)}
    out["seconds"] = round(sum(float(t.get("seconds", 0.0)) for t in tiles.values()), 1)
    out["tiles"] = len(tiles)
    if (run / "refit_arm.json").exists():
        rec = json.loads((run / "refit_arm.json").read_text())
        out["arm"], out["in_effect"] = rec["arm"], rec.get("in_effect")
    return out


def verdict(
    rows: dict, base_rows: dict, records: dict, ceiling: dict | None = None
) -> dict:
    """rows / records: arm -> cube -> row at tolerance 2 / run record; base_rows: findings 97 and 98's rows."""
    out: dict = {"scored": {a: len(rows.get(a, {})) for a in ARMS}}
    if any(
        c not in rows.get(a, {}) or c not in records.get(a, {})
        for a in ARMS
        for c in ARM_CUBES[a]
    ):
        out.update({f"prediction_P{i}": None for i in (1, 2, 3)}, reading=None)
        return out
    g = {a: gains(rows[a], base_rows, ARM_CUBES[a]) for a in ARMS}
    manipulation = {
        a: {c: records[a][c].get("in_effect") is IN_EFFECT[a] for c in ARM_CUBES[a]}
        for a in ARMS
    }
    merges = {a: sum(rows[a][c][MERGES] for c in HELD) for a in ARMS}
    base_merges = sum(base_rows[c][MERGES] for c in HELD)
    precision = {c: rows["refit"][c][PREC] - base_rows[c][PREC] for c in ALL_CUBES}
    floor = statistics.median(abs(g["floor"][c]) for c in HELD)
    out.update(
        pen_gain=g,
        median_gain_held=statistics.median(g["refit"][c] for c in HELD),
        median_gain_in_sample=statistics.median(g["refit"][c] for c in IN_SAMPLE),
        floor_median_abs=floor,
        floor_ok=floor < FLOOR_MAX,
        coverage_factor={
            c: rows["refit"][c][COV] / base_rows[c][COV] for c in ALL_CUBES
        },
        precision_change=precision,
        merges_held={"base": base_merges, **merges},
        manipulation=manipulation,
        manipulation_ok=all(all(m.values()) for m in manipulation.values()),
    )
    if ceiling is not None:
        out["share_of_ceiling"] = {
            c: g["refit"][c] / ceiling[c] for c in HELD if ceiling[c] > 0
        }
    out["prediction_P1"] = out["median_gain_held"] >= GAIN_BAR
    out["prediction_P2"] = merges["refit"] - base_merges <= abs(
        merges["floor"] - base_merges
    )
    out["prediction_P3"] = sum(precision[c] >= -P3_DROP for c in HELD) >= P3_AT_LEAST
    out["reading"] = reading(out)
    return out  # fmt: skip


def reading(v: dict) -> str | None:
    if not (v["manipulation_ok"] and v["floor_ok"]):
        return None
    p1, p2, p3 = (v[f"prediction_P{i}"] for i in (1, 2, 3))
    head = f"villa's refit retry raises held-out ERLpen by a median {v['median_gain_held']:.3f}"
    if p1 and p2 and p3:
        return (head + ", without more merges and keeping its precision: propose a registered test on cubes outside "
                "these 21 and, separately, exposing --refit-retry in villa's volume tracer, checked again on villa's "
                "main")  # fmt: skip
    costs = [
        s
        for s, ok in (("with more merges", p2), ("at a cost in precision", p3))
        if not ok
    ]
    if p1:
        return (head + ", but " + " and ".join(costs) + ": the strategy stops a candidate whose gain depends on wrong "
                "connections or lost precision")  # fmt: skip
    tail = [s for s, ok in (("adds merges", p2), ("costs precision", p3)) if not ok]
    return (head + ", under the 0.10 bar: it does not realize the continuity ceiling; close it as a continuation rule"
            + ("; it also " + " and ".join(tail) if tail else ""))  # fmt: skip


def status(smoke_ok: bool | None, v: dict, failed: list) -> str:
    if smoke_ok is False:
        return "SMOKE_FAILED"
    if smoke_ok is None or failed or v["prediction_P1"] is None:
        return "INCOMPLETE"
    if not v["manipulation_ok"]:
        return "MANIPULATION_FAILED"
    return "OK" if v["floor_ok"] else "FLOOR_TOO_LARGE"


def cmd_score(work: Path, out_path: Path) -> int:
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    smoke = json.loads((work / "smoke.json").read_text())["identical"] if (work / "smoke.json").exists() else None  # fmt: skip
    base2, base4, _ = sh.baseline()
    rows: dict = {a: {} for a in ARMS}
    rows4: dict = {a: {} for a in ARMS}
    records: dict = {a: {} for a in ARMS}
    unchanged: dict = {a: {} for a in ARMS}
    failed = []
    for a in ARMS:
        for c in ARM_CUBES[a]:
            run = work / a / c
            if not (run / "fibers.afv").exists():
                failed.append(f"{a}/{c}")
                continue
            skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
            lab = cc.labels_in_cube(run / "fibers.afv", MARGIN, sh.size_of(c))
            r = {t: score_tracing(skel, lab, tolerance=t).as_row() for t in TOLS}
            rows[a][c], rows4[a][c], records[a][c] = r[2.0], r[4.0], run_record(run)
            base_afv = BASE_RUNS[sh.size_of(c)] / "neural" / c / "fibers.afv"
            unchanged[a][c] = cc.f96_afv_identical(run / "fibers.afv", base_afv)
            print(
                a, c, f"ERLpen {r[2.0][PEN]:.2f} (was {base2[c][PEN]:.2f})", flush=True
            )
    ceiling = ceiling_gains()
    v = verdict(rows, base2, records, ceiling)
    out = {
        "registration": "docs/preregistration/2026-11-02_neural_tracer_refit_retry.md",
        "status": status(smoke, v, failed),
        "smoke_cube": SMOKE,
        "smoke_identical": smoke,
        "failed": failed,
        "rows_tol2": rows,
        "rows_tol4": rows4,
        "records": records,
        "unchanged": unchanged,
        "baseline_rows_tol2": {c: base2[c] for c in ALL_CUBES},
        "baseline_rows_tol4": {c: base4[c] for c in ALL_CUBES},
        "baseline_records": {
            c: run_record(BASE_RUNS[sh.size_of(c)] / "neural" / c) for c in ALL_CUBES
        },
        "ceiling_gain": ceiling,
        "verdict": v,
    }
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {out['status']}; reading {v.get('reading')}; wrote {out_path}")
    return 0 if out["status"] == "OK" else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("smoke", "score"):
        p = sub.add_parser(name)
        p.add_argument("--work", type=Path, required=True)
        if name == "score":
            p.add_argument(
                "--out",
                type=Path,
                default=Path("reports/neural_tracer_refit_retry.json"),
            )
    args = ap.parse_args(argv)
    if args.cmd == "smoke":
        same = cc.f96_afv_identical(
            args.work / "smoke" / SMOKE / "fibers.afv",
            BASE_RUNS[256] / "neural" / SMOKE / "fibers.afv",
        )
        (args.work / "smoke.json").write_text(
            json.dumps({"cube": SMOKE, "identical": same}) + "\n"
        )
        print("SMOKE_OK" if same else "SMOKE_FAILED")
        return 0 if same else 1
    return cmd_score(args.work, args.out)


if __name__ == "__main__":
    sys.exit(main())
