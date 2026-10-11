"""docs/preregistration/2026-10-11_afv_generator_entrant.md -- villa PR #1934's automated fiber generator, at its
defaults, scored by ScrollGT on the 11 fiber targets (current annotations) and the 10 held-out cubes.

Each .afv must record the registered model revision and settings, or there is no verdict. It is rasterised as thin
centrelines (afv_to_labels.py) and scored with ScrollGT's score_tracing (fiber scoring version 2, tolerance 2.0).

Usage: .venv/bin/python scripts/afv_generator_analysis.py --work DIR --heldout-data DIR --heldout-result PATH [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402

SG = Path("/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt")
TOL = 2.0
MODEL, REVISION = "Qualzz20/afv_fiber_9um", "e189af7507d16d85d510c372e33d798fc509bb59"
SETTINGS = {
    "mirror": False,
    "threshold_percent": 60.0,
    "block_size": 512,
    "extend": False,
    "max_join_angle_degrees": 45.0,
    "min_length_voxels": 100.0,
    "black_distance_voxels": 16.0,
    "native_scale": 1,
    "origin_xyz": [0, 0, 0],
}
IN_SAMPLE = [
    "s1_00497_01497_03997_256",
    "s1_00497_02497_02997_256",
    "s1_00997_02497_02997_256",
    "s1_08997_02997_02497_256",
    "s1_10997_02997_02997_256",
    "s5_03997_01497_03997_256",
    "s5_07997_02997_05497_256",
    "s5_14997_01497_01497_256",
    "s5_06494_01994_03994_512",
    "s5_06994_00994_04994_512",
    "s5_07994_01994_05494_512",
]
S3 = [
    "s3_00994_00494_01994_512",
    "s3_00994_01994_00494_512",
    "s3_00994_02494_01494_512",
    "s3_01994_01494_00994_512",
    "s3_01994_01994_01494_512",
    "s3_02994_02494_01994_512",
    "s3_03494_01494_00494_512",
    "s3_04494_00994_01494_512",
]
S5_HELDOUT = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
CC = "floor_connected_components"


def identity_problems(gen: dict, size: int) -> list[str]:
    """Differences between an .afv's recorded generator metadata and the registered entrant."""
    bad = []
    if gen.get("model") != MODEL or gen.get("revision") != REVISION:
        bad.append(f"model {gen.get('model')}@{gen.get('revision')}")
    for k, v in SETTINGS.items():
        if gen.get(k) != v:
            bad.append(f"{k}={gen.get(k)!r}")
    if gen.get("size_xyz") != [size] * 3:
        bad.append(f"size_xyz={gen.get('size_xyz')!r}")
    return bad


def verdict(gen_rows: dict, comp: dict, heldout_ok: bool) -> dict:
    """gen_rows: cube -> generator row, or None if its run failed. comp: cube -> {"cc": row, "tracer": row}.

    INCOMPLETE if an in-sample target has no generator row. P4 and P5 are None when the held-out study is not OK or
    fewer than 6 Scroll-3 cubes have both a generator row and comparators.
    """
    missing = [c for c in IN_SAMPLE if gen_rows.get(c) is None]
    if missing:
        return {"status": "INCOMPLETE", "missing_in_sample": missing}
    g = gen_rows
    s3 = [c for c in S3 if g.get(c) is not None and c in comp] if heldout_ok else []
    s3_ok = len(s3) >= 6
    tr = {c: comp[c]["tracer"] for c in comp}
    cc = {c: comp[c]["cc"] for c in comp}
    in512 = [c for c in IN_SAMPLE if c.endswith("_512")]
    in256 = [c for c in IN_SAMPLE if c.endswith("_256")]
    pred = {
        "P1_raw_erl_above_tracer_on_9_of_11": sum(g[c]["erl"] > tr[c]["erl"] for c in IN_SAMPLE) >= 9,
        "P2_coverage_below_tracer_on_9_of_11": sum(g[c]["coverage"] < tr[c]["coverage"] for c in IN_SAMPLE) >= 9,
        "P3_cc_raw_erl_above_generator_on_all_256": all(cc[c]["erl"] > g[c]["erl"] for c in in256),
        "P4_s3_pen_above_tracer_on_75pct": (
            sum(g[c]["erl_merge_penalized"] > tr[c]["erl_merge_penalized"] for c in s3) >= 0.75 * len(s3)
            if s3_ok else None),
        "P5_s3_median_coverage_below_in_sample_512_median": (
            statistics.median(g[c]["coverage"] for c in s3) < statistics.median(g[c]["coverage"] for c in in512)
            if s3_ok else None),
    }  # fmt: skip
    return {
        "status": "OK",
        "heldout_evaluated": s3_ok,
        "s3_cubes": s3,
        "failed_runs": sorted(c for c, v in gen_rows.items() if v is None),
        "predictions": pred,
    }


def afv_generator_metadata(path: Path) -> dict:
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        row = con.execute(
            "SELECT value FROM metadata WHERE key = 'generator'"
        ).fetchone()
        return json.loads(row[0]) if row else {}
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--heldout-data", type=Path, required=True)
    ap.add_argument("--heldout-result", type=Path, required=True)
    ap.add_argument(
        "--out", type=Path, default=Path("reports/afv_generator_entrant.json")
    )
    args = ap.parse_args()
    sys.path.insert(0, str(SG / "src"))
    import numpy as np
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.skeleton_io import (
        Skeleton,
        origin_from_stem,
        parse_nml,
        size_from_stem,
    )
    from scrollgt.fibers.target import load_fiber_target

    ho = (
        json.loads(args.heldout_result.read_text())
        if args.heldout_result.exists()
        else {}
    )
    heldout_ok = ho.get("status") == "OK"
    comp: dict[str, dict] = {}
    for c in IN_SAMPLE:
        meta = json.loads((SG / "data" / f"fibers_{c}" / "meta.json").read_text())
        if (
            meta["ground_truth"]
            .get("nml", {})
            .get("dataset", "")
            .startswith("Dataset004")
            is False
        ):
            raise SystemExit(
                f"{c}: ScrollGT checkout lacks the current annotations (needs 0.5.0)"
            )
        comp[c] = {
            "cc": meta["floors"][CC],
            "tracer": meta["floors"]["tracer_strict_relink"],
        }
    for c, v in ho.get("cubes", {}).items():
        if "rows" in v:
            comp[c] = {"cc": v["rows"][CC], "tracer": v["rows"]["tracer"]}

    gen_rows: dict[str, dict | None] = {}
    identity: dict[str, list[str]] = {}
    for c in IN_SAMPLE + S5_HELDOUT + S3:
        afv = args.work / f"{c}.afv"
        size = size_from_stem(c)
        if not afv.exists():
            gen_rows[c] = None
            print(f"{c}: no .afv (run failed or missing)", flush=True)
            continue
        bad = identity_problems(afv_generator_metadata(afv), size)
        if bad:
            identity[c] = bad
            continue
        shape = (size,) * 3
        fibers = afv_to_labels.read_afv(afv)
        labels = afv_to_labels.rasterize(
            {k: afv_to_labels.to_cube_zyx(v, (0, 0, 0)) for k, v in fibers.items()},
            shape,
        )
        if c in IN_SAMPLE:
            skel, _, _ = load_fiber_target(SG / "data" / f"fibers_{c}")
        else:
            full = parse_nml(
                args.heldout_data / f"{c}.nml", origin_zyx=origin_from_stem(c)
            )
            skel = Skeleton(fibers=[f for f in full.fibers if f.in_bounds_mask(shape).sum() > 1],
                            scale_um=full.scale_um, origin_zyx=full.origin_zyx)  # fmt: skip
        row = score_tracing(skel, labels, tolerance=TOL).as_row()
        row["n_fibers_in_afv"] = len(fibers)
        gen_rows[c] = row
        cmp = comp.get(c)
        extra = (f" | tracer ERL {cmp['tracer']['erl']} pen {cmp['tracer']['erl_merge_penalized']} cov "
                 f"{cmp['tracer']['coverage']} | cc ERL {cmp['cc']['erl']} pen {cmp['cc']['erl_merge_penalized']}"
                 if cmp else "")  # fmt: skip
        print(f"{c}: generator ERL {row['erl']} pen {row['erl_merge_penalized']} cov {row['coverage']} prec "
              f"{row['precision']} merges {row['merges']} inst {row['n_pred_instances']}{extra}", flush=True)  # fmt: skip
    if identity:
        v = {"status": "IDENTITY_FAILED", "identity_problems": identity}
    else:
        v = verdict(gen_rows, comp, heldout_ok)
    out = {"scoring_version": SCORING_VERSION, "tolerance": TOL, "model": MODEL, "revision": REVISION,
           "settings": SETTINGS, "generator_rows": gen_rows, "comparators": comp, **v}  # fmt: skip
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(v, indent=1))
    return 0 if v["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
