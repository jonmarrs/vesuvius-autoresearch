"""docs/preregistration/2026-10-25_neural_tracer_steep_heading.md -- villa's neural fiber tracer, with the scan
around each cube, tracing the seed dots it skips where its CT axis misses the presence direction.

Findings 97 and 98 ran villa's tracer on all 21 cubes with 128 voxels of the real scan around each. Finding 99 found
that every classified drop there fails villa's 35-degree test between the CT axis for the dot's fiber family and the
dot's presence direction, in sheets tilted far from vertical. This traces those dots, in two arms, on exactly
findings 97 and 98's inputs and command (scripts/neural_tracer_heading_arm.py):
* `sheet`: from the presence direction projected into the CT's sheet;
* `keep`: from villa's own CT axis, as training seeds are.
Every other dot is headed as villa heads it.

  smoke  the launcher in its `villa` arm, on SMOKE, must reproduce finding 97's run point for point
  score  score each run in the cube's frame at tolerances 2 and 4, beside findings 97 and 98's runs (the baseline);
         the run records; the registered predictions and decision rule. Writes reports/neural_tracer_steep_heading.json.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_ct_context as cc  # noqa: E402
import neural_tracer_ct_context_512 as c512  # noqa: E402

f91 = cc.f91
PEN, COV, PREC = cc.PEN, cc.COV, "precision"
T, G, TOLS, MARGIN = cc.T, cc.G, cc.TOLS, cc.MARGIN
ARMS = ("sheet", "keep")
HELD_S5 = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
S3 = list(c512.S3_CUBES)
HELD = HELD_S5 + S3
IN_256 = [c for c in cc.ALL_CUBES if c not in HELD_S5]
IN_512 = list(c512.S5_CUBES)
IN_SAMPLE = IN_256 + IN_512
ALL_CUBES = HELD + IN_SAMPLE  # the chain's order: held out first
BASE_RUNS = {256: T / "ct_context_run", 512: T / "ct_context_512_run"}
BASE_REPORTS = {
    256: Path("reports/neural_tracer_ct_context.json"),
    512: Path("reports/neural_tracer_ct_context_512.json"),
}
SMOKE = "s5_13497_01497_02497_256"  # held out, 0.266 of its dots skipped: the skip is exercised
# The registered predictions (docs/preregistration/2026-10-25_neural_tracer_steep_heading.md).
P1_FACTOR = 1.15  # sheet: coverage factor on each held-out Scroll-5 cube
P2_RISE_AT_LEAST, P2_MEDIAN = 6, 1.05  # sheet: Scroll 3
# sheet: precision at most P3_DROP lower on at least P3_AT_LEAST held-out cubes
P3_DROP, P3_AT_LEAST = 0.03, 8
P4_AT_LEAST = 7  # sheet's coverage above keep's on at least this many held-out cubes
P5_BAND = (0.95, 1.05)  # both arms: coverage factor on every in-sample cube
M2_SHARE = 0.2  # manipulation: each arm's skipped share at most this fraction of the baseline's, every held-out cube


def size_of(cube: str) -> int:
    return int(cube.rsplit("_", 1)[1])


def box(cube: str) -> str:
    lo, hi = cc.box_grid(MARGIN, size_of(cube))
    return ",".join(str(v) for v in (lo,) * 3 + (hi,) * 3)


def run_record(run: Path) -> dict:
    """tiles.jsonl counts (the last line of each tile) and the launcher's tally of how each offered dot was headed."""
    lines = [json.loads(s) for s in (run / "tiles.jsonl").read_text().splitlines() if s.strip()]  # fmt: skip
    tiles = {t["tile"]: t for t in lines}
    keys = ("dots", "owned_dots", "no_heading", "traced", "fibers", "traced_vox", "kept_vox")  # fmt: skip
    out = {k: int(sum(t.get(k, 0) for t in tiles.values())) for k in keys}
    out["tiles"] = len(tiles)
    out["no_heading_share"] = out["no_heading"] / out["dots"] if out["dots"] else None
    arm = json.loads((run / "heading_arm.json").read_text())
    out["arm"], out["offered"] = arm["arm"], arm.get("offered")
    return out


def baseline() -> tuple[dict, dict, dict]:
    """Findings 97 and 98's rows at tolerances 2 and 4, and their run records, for all 21 cubes."""
    rows2, rows4, records = {}, {}, {}
    for path in BASE_REPORTS.values():
        d = json.loads(path.read_text())
        rows2.update(d["rows_tol2"])
        rows4.update(d["rows_tol4"])
        records.update(d["records"])
    return rows2, rows4, records


def factors(rows: dict, base: dict, cubes, key=COV) -> dict:
    if zero := [c for c in cubes if base[c][key] <= 0]:
        raise ValueError(f"no ratio over a baseline {key} of 0: {zero}")
    return {c: rows[c][key] / base[c][key] for c in cubes}


def manipulation(records: dict, base_records: dict, cubes=HELD) -> dict:
    """Each arm's skipped share at most M2_SHARE of the baseline's on every held-out cube."""
    return {c: records[c]["no_heading_share"] <= M2_SHARE * base_records[c]["no_heading_share"]
            for c in cubes}  # fmt: skip


def verdict(rows: dict, base_rows: dict, records: dict, base_records: dict) -> dict:
    """rows / records: arm -> cube -> row at tolerance 2 / run record; base_rows / base_records: findings 97 and 98's."""
    out: dict = {"scored": {a: len(rows.get(a, {})) for a in ARMS}}
    if any(
        c not in rows.get(a, {}) or c not in records.get(a, {})
        for a in ARMS
        for c in ALL_CUBES
    ):
        out.update({f"prediction_P{i}": None for i in range(1, 6)}, reading=None)
        return out
    cov = {a: factors(rows[a], base_rows, ALL_CUBES) for a in ARMS}
    prec = {
        a: {c: rows[a][c][PREC] - base_rows[c][PREC] for c in ALL_CUBES} for a in ARMS
    }
    m2 = {a: manipulation(records[a], base_records) for a in ARMS}
    s3 = [cov["sheet"][c] for c in S3]
    out.update(
        coverage_factor=cov,
        precision_change=prec,
        pen_factor={a: factors(rows[a], base_rows, ALL_CUBES, PEN) for a in ARMS},
        median_coverage_factor_scroll3={
            a: statistics.median(cov[a][c] for c in S3) for a in ARMS
        },
        manipulation=m2,
        manipulation_ok={a: all(m2[a].values()) for a in ARMS},
    )
    out["prediction_P1"] = all(cov["sheet"][c] >= P1_FACTOR for c in HELD_S5)
    out["prediction_P2"] = (
        sum(f > 1 for f in s3) >= P2_RISE_AT_LEAST
        and statistics.median(s3) >= P2_MEDIAN
    )
    out["prediction_P3"] = (
        sum(prec["sheet"][c] >= -P3_DROP for c in HELD) >= P3_AT_LEAST
    )
    out["prediction_P4"] = (
        sum(rows["sheet"][c][COV] > rows["keep"][c][COV] for c in HELD) >= P4_AT_LEAST
    )
    lo, hi = P5_BAND
    out["prediction_P5"] = all(lo <= cov[a][c] <= hi for a in ARMS for c in IN_SAMPLE)
    out["reading"] = reading(out)
    return out


def reading(v: dict) -> str | None:
    if not all(v["manipulation_ok"].values()):
        return None
    p1, p2, p3, p4 = (v[f"prediction_P{i}"] for i in range(1, 5))
    if not (p1 or p2):
        return ("tracing the skipped dots adds less coverage than registered: on the held-out cubes the skip is not "
                "the main limit on coverage" + ("" if p3 else ", and the added traces cost precision"))  # fmt: skip
    where = ("on the held-out cubes" if p1 and p2 else
             "on the two held-out Scroll-5 cubes, not as registered on Scroll 3" if p1 else
             "on Scroll 3, not as registered on the two held-out Scroll-5 cubes")  # fmt: skip
    head = f"a seed heading that follows the sheet recovers coverage {where}" + (
        ", keeping its precision" if p3 else ", at a cost in precision"
    )
    tail = ("; the heading matters: villa's own axis, kept, recovers less" if p4 else
            "; but villa's own axis, kept, recovers about as much: what loses the coverage is the 35° skip, not the "
            "heading")  # fmt: skip
    return head + tail


def status(smoke_ok: bool | None, v: dict, failed: list) -> str:
    if smoke_ok is False:
        return "SMOKE_FAILED"
    if failed or v["prediction_P1"] is None:
        return "INCOMPLETE"
    return "OK" if all(v["manipulation_ok"].values()) else "MANIPULATION_FAILED"


def cmd_score(work: Path, out_path: Path) -> int:
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    smoke = json.loads((work / "smoke.json").read_text())["identical"] if (work / "smoke.json").exists() else None  # fmt: skip
    base2, base4, base_rec = baseline()
    rows: dict = {a: {} for a in ARMS}
    rows4: dict = {a: {} for a in ARMS}
    records: dict = {a: {} for a in ARMS}
    failed = []
    for a in ARMS:
        for c in ALL_CUBES:
            run = work / a / c
            if not (run / "fibers.afv").exists():
                failed.append(f"{a}/{c}")
                continue
            skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
            lab = cc.labels_in_cube(run / "fibers.afv", MARGIN, size_of(c))
            r = {t: score_tracing(skel, lab, tolerance=t).as_row() for t in TOLS}
            rows[a][c], rows4[a][c], records[a][c] = r[2.0], r[4.0], run_record(run)
            print(a, c, f"cov {r[2.0][COV]:.3f} (was {base2[c][COV]:.3f})", flush=True)
    v = verdict(rows, base2, records, base_rec)
    rep = json.loads(Path("reports/neural_tracer_entrant.json").read_text())
    t94 = json.loads(Path("reports/tolerance4_rescore.json").read_text())
    out = {
        "status": status(smoke, v, failed),
        "smoke_cube": SMOKE,
        "smoke_identical": smoke,
        "failed": failed,
        "rows_tol2": rows,
        "rows_tol4": rows4,
        "records": records,
        "baseline_rows_tol2": {c: base2[c] for c in ALL_CUBES},
        "baseline_rows_tol4": {c: base4[c] for c in ALL_CUBES},
        "baseline_records": {c: base_rec[c] for c in ALL_CUBES},
        "our_tracer_tol2": {c: rep["comparators"][c]["tracer"] for c in ALL_CUBES},
        "our_tracer_tol4": {c: t94["rows_tracer"][c] for c in ALL_CUBES},
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
                default=Path("reports/neural_tracer_steep_heading.json"),
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
