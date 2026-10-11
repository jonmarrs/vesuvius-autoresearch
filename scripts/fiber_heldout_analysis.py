"""docs/preregistration/2026-10-11_fiber_heldout_split.md -- ScrollGT's fiber reference mask (fiber_hz_vt) and our
tracer on the 10 villa Dataset004 cubes the mask never trained on.

Per cube: the frame gate (NML nodes on villa's semantic label >= 0.999, and on the P >= 0.5 mask at > 5x its density),
then the oracle, the four floors and the tracer, scored with ScrollGT (fiber scoring version 2, tolerance 2.0).

Usage: .venv/bin/python scripts/fiber_heldout_analysis.py --data-dir DIR --work DIR [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

SG = Path("/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt")
TOL = 2.0
SEMANTIC_GATE = 0.999
ENRICHMENT_GATE = 5.0
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
S5 = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
CUBES = S5 + S3
# Registered in-sample comparison: ScrollGT 0.5.0 connected-components coverage (current annotations).
IN_SAMPLE_CC_COVERAGE = {
    512: {
        "s5_06494_01994_03994_512": 0.8882,
        "s5_06994_00994_04994_512": 0.8130,
        "s5_07994_01994_05494_512": 0.8223,
    },
    256: {
        "s5_03997_01497_03997_256": 0.8666,
        "s5_07997_02997_05497_256": 0.9119,
        "s5_14997_01497_01497_256": 0.8185,
    },
}
CC = "floor_connected_components"


def gate_ok(c: dict) -> bool:
    return (
        c["semantic_landing"] >= SEMANTIC_GATE
        and c["mask_enrichment"] > ENRICHMENT_GATE
    )


def verdict(results: dict) -> dict:
    """results: cube -> {"semantic_landing", "mask_enrichment", "rows"} for every cube whose chain output exists.

    A missing cube refuses any verdict. A cube failing the gate is excluded. Fewer than 6 eligible Scroll-3 cubes
    leaves P1 and P4 unevaluated (None).
    """
    missing = [c for c in CUBES if c not in results]
    if missing:
        return {"status": "INCOMPLETE", "missing": missing}
    eligible = {c: r for c, r in results.items() if gate_ok(r)}
    excluded = sorted(set(results) - set(eligible))
    s3 = [c for c in S3 if c in eligible]
    s5 = [c for c in S5 if c in eligible]
    s3_ok = len(s3) >= 6

    def cov(c):
        return eligible[c]["rows"][CC]["coverage"]

    def pen(c, k):
        return eligible[c]["rows"][k]["erl_merge_penalized"]

    pred = {
        "P1_s3_median_cc_coverage_below_0.8130": (
            statistics.median(cov(c) for c in s3) < min(IN_SAMPLE_CC_COVERAGE[512].values()) if s3_ok else None),
        "P2_both_s5_cc_coverage_below_0.8666": (
            len(s5) == 2 and all(cov(c) < statistics.median(IN_SAMPLE_CC_COVERAGE[256].values()) for c in s5)),
        "P3_cc_raw_erl_above_tracer_on_every_eligible_cube": all(
            r["rows"][CC]["erl"] > r["rows"]["tracer"]["erl"] for r in eligible.values()),
        "P4_tracer_pen_above_cc_on_75pct_of_s3": (
            sum(pen(c, "tracer") > pen(c, CC) for c in s3) >= 0.75 * len(s3) if s3_ok else None),
    }  # fmt: skip
    return {
        "status": "OK" if s3_ok else "NO_S3_VERDICT",
        "eligible": sorted(eligible),
        "excluded": excluded,
        "predictions": pred,
        "descriptive": {
            "s3_cc_coverage": {c: cov(c) for c in s3},
            "s3_cc_coverage_median": statistics.median(cov(c) for c in s3)
            if s3
            else None,
            "s5_cc_coverage": {c: cov(c) for c in s5},
            "tracer_pen_above_cc": {c: pen(c, "tracer") > pen(c, CC) for c in eligible},
        },
    }


def mask_enrichment(skel, mask) -> float:
    """ScrollGT's frame test (tests/test_fiber_target.py): every node rounded, in-bounds kept, rate over density."""
    import numpy as np

    coords = np.concatenate(
        [np.asarray(f.coords, dtype=np.float32) for f in skel.fibers]
    )
    idx = np.round(coords).astype(int)
    nodes = idx[((idx >= 0) & (idx < np.asarray(mask.shape))).all(axis=1)]
    return float(mask[nodes[:, 0], nodes[:, 1], nodes[:, 2]].mean() / mask.mean())


def semantic_landing(skel, semantic) -> float:
    import numpy as np

    hits = total = 0
    for f in skel.fibers:
        ok = f.in_bounds_mask(semantic.shape)
        if not ok.any():
            continue
        idx = np.clip(
            np.rint(f.coords[ok]).astype(int), 0, np.asarray(semantic.shape) - 1
        )
        hits += int((semantic[idx[:, 0], idx[:, 1], idx[:, 2]] > 0).sum())
        total += int(ok.sum())
    return hits / total if total else 0.0


def score_cube(c: str, data_dir: Path, instances: Path) -> dict:
    """Gate measurements for one cube and, if it passes, its ScrollGT rows (oracle, four floors, tracer)."""
    sys.path.insert(0, str(SG / "src"))
    import numpy as np
    import tifffile
    from scrollgt.fibers.eval_trace import oracle_from_skeleton, score_tracing
    from scrollgt.fibers.skeleton_io import (
        Skeleton,
        origin_from_stem,
        parse_nml,
        size_from_stem,
    )
    from scrollgt.fibers.target import _floor_rows

    shape = (size_from_stem(c),) * 3
    full = parse_nml(data_dir / f"{c}.nml", origin_zyx=origin_from_stem(c))
    skel = Skeleton(fibers=[f for f in full.fibers if f.in_bounds_mask(shape).sum() > 1],
                    scale_um=full.scale_um, origin_zyx=full.origin_zyx)  # fmt: skip
    mask = np.load(data_dir / f"{c}_fiberprob.npy") >= 0.5
    entry = {
        "semantic_landing": semantic_landing(full, tifffile.imread(data_dir / f"{c}_semantic.tif")),
        "mask_enrichment": mask_enrichment(full, mask),
        "mask_density": float(mask.mean()),
        "n_fibers_scored": len(skel.fibers),
    }  # fmt: skip
    if gate_ok(entry):
        rows = {
            "oracle": score_tracing(
                skel, oracle_from_skeleton(skel, shape), tolerance=TOL
            ).as_row()
        }
        rows.update(_floor_rows(skel, mask, TOL))
        rows["tracer"] = score_tracing(skel, np.load(instances), tolerance=TOL).as_row()
        entry["rows"] = rows
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument(
        "--out", type=Path, default=Path("reports/fiber_heldout_split.json")
    )
    args = ap.parse_args()
    sys.path.insert(0, str(SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION

    results = {}
    for c in CUBES:
        inst, prob = (
            args.work / f"{c}_instances.npy",
            args.data_dir / f"{c}_fiberprob.npy",
        )
        if not (inst.exists() and prob.exists()):
            print(f"{c}: chain output missing", flush=True)
            continue
        entry = score_cube(c, args.data_dir, inst)
        if "rows" in entry:
            rows = entry["rows"]
            t, k = rows["tracer"], rows[CC]
            print(f"{c}: cc cov {k['coverage']} prec {k['precision']} ERL {k['erl']} pen {k['erl_merge_penalized']} | "
                  f"tracer ERL {t['erl']} pen {t['erl_merge_penalized']} cov {t['coverage']} | oracle ERL "
                  f"{rows['oracle']['erl']} | enrichment {entry['mask_enrichment']:.2f}", flush=True)  # fmt: skip
        else:
            print(f"{c}: GATE FAILED {entry}", flush=True)
        results[c] = entry
    v = verdict(results)
    out = {"scoring_version": SCORING_VERSION, "tolerance": TOL, "in_sample_cc_coverage": IN_SAMPLE_CC_COVERAGE,
           "cubes": results, **v}  # fmt: skip
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v[k] for k in v if k != "descriptive"}, indent=1))
    return 0 if v["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
