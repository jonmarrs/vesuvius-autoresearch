"""docs/preregistration/2026-10-20_tolerance4_rescore.md -- our tracer and connected components re-scored at tolerance 4
on ScrollGT's 21 fiber cubes, beside villa's neural tracer's tolerance-4 rows (finding 91's descriptive scores).

Each labelling must first reproduce its published row's tolerance-independent fields (instance count, predicted and
ground-truth length, ground-truth fibers), or the status is IDENTITY_FAILED. CPU only. Writes
reports/tolerance4_rescore.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_analysis as f91  # noqa: E402

TOL4 = 4.0
PEN = f91.PEN
SAME = ("n_pred_instances", "pred_length", "gt_length", "n_gt_fibers")
RESCORE = Path(
    "/home/jon/openclaw-workspace/Neo-VM/spiral_out/tracer_rescore"
)  # finding 80, in sample
HELDOUT = Path(
    "/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_heldout/run"
)  # finding 83, held out
MIN_S3, MIN_INS = 6, 9


def tracer_labelling(cube: str) -> Path:
    return (RESCORE if cube in f91.IN_SAMPLE else HELDOUT) / f"{cube}_instances.npy"


def identity_problems(published: dict, row: dict) -> list[str]:
    """Fields of a labelling's tolerance-4 row that differ from its published row where the tolerance cannot move them."""
    return [
        f"{k}={row.get(k)!r}, published {published.get(k)!r}"
        for k in SAME
        if row.get(k) != published.get(k)
    ]


def verdict(neural: dict, tracer: dict) -> dict:
    """The registered predictions from the neural tracer's and our tracer's tolerance-4 rows (None: not scored)."""
    s3 = [c for c in f91.S3 if neural.get(c) and tracer.get(c)]
    ins = [c for c in f91.IN_SAMPLE if neural.get(c) and tracer.get(c)]
    leads = sum(neural[c][PEN] > tracer[c][PEN] for c in s3)
    trails = sum(neural[c][PEN] < tracer[c][PEN] for c in ins)
    p1 = leads >= MIN_S3 if len(s3) >= MIN_S3 else None
    p2 = trails >= MIN_INS if len(ins) >= MIN_INS else None
    readings = []
    if p1 is not None:
        readings.append("the Scroll-3 lead holds at tolerance 4" if p1 else
                        "the Scroll-3 lead is tolerance-dependent: recommend a ScrollGT note where the lead is claimed")  # fmt: skip
    if p2 is not None:
        readings.append("the in-sample deficit holds at tolerance 4" if p2 else
                        "the in-sample deficit is tolerance-dependent: recommend a ScrollGT note where the deficit is "
                        "claimed")  # fmt: skip
    return {
        "predictions": {
            "P1_s3_leads_tracer_on_6_of_8": p1,
            "P2_in_sample_trails_tracer_on_9_of_11": p2,
        },
        "s3_leading_tracer": [leads, len(s3)],
        "in_sample_trailing_tracer": [trails, len(ins)],
        "readings": readings,
    }


def outcome(identity: dict, neural: dict, tracer: dict):
    if any(identity.values()):
        return "IDENTITY_FAILED", None
    reading = verdict(neural, tracer)
    return (
        "OK"
        if all(v is not None for v in reading["predictions"].values())
        else "INCOMPLETE"
    ), reading


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--entrant", type=Path, default=Path("reports/neural_tracer_entrant.json")
    )
    ap.add_argument("--out", type=Path, default=Path("reports/tolerance4_rescore.json"))
    args = ap.parse_args()
    import numpy as np

    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import (
        SCORING_VERSION,
        floor_connected_components,
        score_tracing,
    )
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    entrant = json.loads(args.entrant.read_text())
    neural = {c: entrant["descriptive_tolerance_4"][c]["tracer"] for c in f91.ALL}
    rows: dict[str, dict] = {"tracer": {}, "cc": {}}
    published: dict[str, dict] = {"tracer": {}, "cc": {}}
    identity: dict[str, list[str]] = {}
    for c in f91.ALL:
        target = f91.SG / "data" / f"fibers_{c}"
        skel, mask, meta = load_fiber_target(target)
        published["tracer"][c] = meta["floors"][f91.TRACER]
        published["cc"][c] = meta["floors"][f91.CC]
        for name, labels in (
            ("tracer", np.load(tracer_labelling(c))),
            ("cc", floor_connected_components(mask)),
        ):
            row = score_tracing(skel, labels, tolerance=TOL4).as_row()
            if bad := identity_problems(published[name][c], row):
                identity[f"{name} {c}"] = bad
            rows[name][c] = row
        print(
            c,
            "tracer",
            rows["tracer"][c][PEN],
            "cc",
            rows["cc"][c][PEN],
            "neural",
            neural[c][PEN],
            flush=True,
        )
    status, reading = outcome(identity, neural, rows["tracer"])
    out = {
        "status": status,
        "tolerance": TOL4,
        "scoring_version": SCORING_VERSION,
        "identity_problems": identity,
        "rows_tracer": rows["tracer"],
        "rows_cc": rows["cc"],
        "rows_neural": neural,
        "published_tracer": published["tracer"],
        "published_cc": published["cc"],
        "published_neural": {c: entrant["neural_rows"][c] for c in f91.ALL},
        "groups": {
            "in_sample": f91.IN_SAMPLE,
            "s3": f91.S3,
            "s5_held_out": f91.S5_HELDOUT,
        },
    }
    if reading is not None:
        out.update(reading)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {status}; wrote {args.out}")
    return 0 if status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
