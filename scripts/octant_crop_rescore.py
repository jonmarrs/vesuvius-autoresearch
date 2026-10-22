"""docs/preregistration/2026-10-21_octant_crop.md -- is the neural tracer's deficit on the 256³ in-sample cubes the cube
size? The three in-sample 512³ cubes are scored in their eight 256³ octants.

For each octant, villa's neural tracer's labelling (finding 91's .afv, rasterised as finding 91 did) and our tracer's
(finding 80's instances) are cropped to it, and the ground truth is cropped the same way: shifted to the octant, and
kept where a fiber has at least two nodes inside, as ScrollGT's loader keeps fibers. Both tracers saw the whole cube,
so only the scoring scale changes. Scored with ScrollGT score_tracing at tolerances 4 and 2.

Identity: the whole cube scored by the same path at tolerance 4 must reproduce finding 94's rows for both entrants, on
every cube, or the status is IDENTITY_FAILED. CPU only. Writes reports/octant_crop_rescore.json.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import tolerance4_rescore as t4  # noqa: E402

PEN = f91.PEN
SIZE = 256
CUBES = [c for c in f91.IN_SAMPLE if c.endswith("_512")]
OCTANTS = [(z, y, x) for z in (0, SIZE) for y in (0, SIZE) for x in (0, SIZE)]
TOLS = (4.0, 2.0)
HOLDS, REVERSES = 16, 8  # of 24 octants, at tolerance 4
NEURAL = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer/run")


def crop_skeleton(skel, origin, size: int = SIZE):
    """The ground truth shifted to the octant at `origin` (z, y, x), keeping fibers with at least two nodes inside
    (inside as ScrollGT's Fiber.in_bounds_mask has it: 0 <= coordinate <= size - 1 on every axis)."""
    o = np.asarray(origin, float)
    fibers = []
    for f in skel.fibers:
        c = f.coords - o
        if np.all((c >= 0) & (c <= size - 1), axis=1).sum() > 1:
            g = copy.copy(f)
            g.coords = c
            fibers.append(g)
    out = copy.copy(skel)
    out.fibers = fibers
    return out


def crop_labels(labels: np.ndarray, origin, size: int = SIZE) -> np.ndarray:
    z, y, x = origin
    return np.ascontiguousarray(labels[z : z + size, y : y + size, x : x + size])


def verdict(rows: dict) -> dict:
    """At tolerance 4, the octants where the neural tracer's ERLpen is above our tracer's."""
    keys = [
        k
        for k, r in rows.items()
        if r and r["neural"].get(4.0) and r["tracer"].get(4.0)
    ]
    leads = sum(rows[k]["neural"][4.0][PEN] > rows[k]["tracer"][4.0][PEN] for k in keys)
    n = len(keys)
    holds = leads >= HOLDS if n == len(CUBES) * len(OCTANTS) else None
    if holds is None:
        reading = None
    elif holds:
        reading = ("cropping does not reverse it: cube size, as scored, is not why the 256³ in-sample cubes trail at "
                   "tolerance 4")  # fmt: skip
    elif leads <= REVERSES:
        reading = "cropping reverses it: the 256³ cubes' deficit at tolerance 4 may be their size"
    else:
        reading = "inconclusive: cropping weakens the lead without reversing it"
    return {
        "neural_leads_at_4": [leads, n],
        "prediction_P1_leads_on_16_of_24": holds,
        "reading": reading,
    }


def outcome(identity: dict, rows: dict):
    if any(identity.values()):
        return "IDENTITY_FAILED", None
    v = verdict(rows)
    return (
        "OK" if v["prediction_P1_leads_on_16_of_24"] is not None else "INCOMPLETE"
    ), v


def _keep(row: dict) -> dict:
    return {k: row[k] for k in (PEN, "erl", "coverage", "precision", "merges", "splits", "n_gt_fibers", "gt_length",
                                "n_pred_instances", "pred_length")}  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--t94", type=Path, default=Path("reports/tolerance4_rescore.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("reports/octant_crop_rescore.json")
    )
    args = ap.parse_args()
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    t94 = json.loads(args.t94.read_text())
    rows: dict = {}
    whole: dict = {}
    identity: dict = {}
    for c in CUBES:
        skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
        labels = {
            "neural": afv_to_labels.rasterize(
                {k: afv_to_labels.to_cube_zyx(v, (0, 0, 0)) for k, v in afv_to_labels.read_afv(NEURAL / c / "fibers.afv").items()},
                (512,) * 3),
            "tracer": np.load(t4.tracer_labelling(c)),
        }  # fmt: skip
        whole[c] = {
            e: _keep(score_tracing(skel, lab, tolerance=4.0).as_row())
            for e, lab in labels.items()
        }
        for e, ref in (
            ("neural", t94["rows_neural"][c]),
            ("tracer", t94["rows_tracer"][c]),
        ):
            bad = [
                k
                for k in (PEN, "coverage", "n_pred_instances", "pred_length")
                if whole[c][e][k] != ref[k]
            ]
            if bad:
                identity[f"{e} {c}"] = bad
        for o in OCTANTS:
            sk = crop_skeleton(skel, o)
            key = f"{c}@{o[0]}_{o[1]}_{o[2]}"
            rows[key] = {e: {t: _keep(score_tracing(sk, crop_labels(lab, o), tolerance=t).as_row()) for t in TOLS}
                         for e, lab in labels.items()}  # fmt: skip
            print(
                key,
                {e: {t: rows[key][e][t][PEN] for t in TOLS} for e in labels},
                flush=True,
            )
    status, reading = outcome(identity, rows)
    out = {
        "status": status,
        "size": SIZE,
        "tolerances": list(TOLS),
        "cubes": CUBES,
        "identity_problems": identity,
        "whole_cube_tol4": whole,
        "octants": {
            k: {e: {str(t): r for t, r in v.items()} for e, v in r.items()}
            for k, r in rows.items()
        },
    }
    if reading is not None:
        out.update(reading)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {status}; wrote {args.out}")
    return 0 if status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
