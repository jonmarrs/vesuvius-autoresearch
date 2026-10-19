"""docs/preregistration/2026-10-19_neural_tracer_training_pitch.md -- villa's neural fiber tracer re-run on each
ScrollGT cube resampled to 9.6 um, scored in the cube's own 7.91 um frame and set beside finding 91's native rows.

Each `.afv` from repro/fibers/run_neural_tracer_pitch_chain.sh is in resampled voxels: scale_back multiplies by
r = 9.6 / 7.91 into the cube's frame, then it is rasterised and scored exactly as finding 91 did. Writes
reports/neural_tracer_pitch.json.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import resample_cube_pitch as rcp  # noqa: E402

TO_UM = 9.6
R = TO_UM / rcp.FROM_UM
SETTINGS = {
    **f91.SETTINGS,
    "base_um": TO_UM,
}  # reported lengths only; everything else as finding 91
PEN, COV = f91.PEN, f91.COV
MATERIAL = math.log(
    1.15
)  # |median log ratio| beyond this, or 2+ flips against our tracer: the published row moves


def grid_size(cube: str) -> float:
    return rcp.resampled_length(int(cube.rsplit("_", 1)[1]), R) / SETTINGS["grid_scale"]


def identity_problems(record: dict, cube: str) -> list[str]:
    """Differences between a run's run.json and the registered pitch-matched entrant for this cube."""
    bad = []
    if record.get("checkpoint_sha256") != f91.CHECKPOINT_SHA256:
        bad.append(f"checkpoint_sha256={record.get('checkpoint_sha256')}")
    for k, v in SETTINGS.items():
        if k not in record or record[k] != v:
            bad.append(f"{k}={record.get(k, '<absent>')!r}")
    n = grid_size(cube)
    if record.get("box") != {"lo": [0.0, 0.0, 0.0], "hi": [n, n, n]}:
        bad.append(f"box={record.get('box')!r}")
    if not str(record.get("ct", "")).rstrip("/").endswith(f"/ct_9p6/{cube}.zarr"):
        bad.append(f"ct={record.get('ct')!r}")
    if (
        not str(record.get("presence", ""))
        .rstrip("/")
        .endswith(f"/presence_9p6/{cube}_presence.zarr/1")
    ):
        bad.append(f"presence={record.get('presence')!r}")
    return bad


def scale_back(fibers: dict, cube: str) -> dict:
    """Resampled-voxel xyz polylines -> the cube's own zyx."""
    return {
        k: afv_to_labels.to_cube_zyx(rcp.to_source(v, R), (0, 0, 0))
        for k, v in fibers.items()
    }


def verdict(rows: dict, native: dict, comp: dict) -> dict:
    """The registered predictions and reading, from the pitch-matched rows, finding 91's rows and our tracer's."""
    ins = [c for c in f91.IN_SAMPLE if rows.get(c)]
    s3 = [c for c in f91.S3 if rows.get(c)]
    every = [c for c in f91.ALL if rows.get(c)]
    trails = sum(rows[c][PEN] < comp[c]["tracer"][PEN] for c in ins)
    leads = sum(rows[c][PEN] > comp[c]["tracer"][PEN] for c in s3)
    logs = [
        math.log(rows[c][PEN] / native[c][PEN])
        for c in every
        if rows[c][PEN] > 0 and native[c][PEN] > 0
    ]
    flips = sum(
        (rows[c][PEN] > comp[c]["tracer"][PEN])
        != (native[c][PEN] > comp[c]["tracer"][PEN])
        for c in every
    )
    median_ratio = math.exp(statistics.median(logs)) if logs else None
    p = {
        "P1_in_sample_trails_tracer_on_9_of_11": trails >= 9 if len(ins) >= 9 else None,
        "P2_s3_leads_tracer_on_6_of_8": leads >= 6 if len(s3) >= 6 else None,
        "P3_median_pen_ratio_within_0.85_1.15": (0.85 <= median_ratio <= 1.15)
        if len(logs) >= 17
        else None,
    }
    material = None
    if len(logs) >= 17:
        material = abs(statistics.median(logs)) > MATERIAL or flips >= 2
    if p["P1_in_sample_trails_tracer_on_9_of_11"] is None:
        cause = None
    elif ins and len(ins) - trails >= 3:
        cause = "pitch is a material cause of the in-sample deficit"
    else:
        cause = "pitch is not the main cause of the in-sample deficit"
    return {
        "predictions": p,
        "in_sample_trailing_tracer": [trails, len(ins)],
        "s3_leading_tracer": [leads, len(s3)],
        "median_pen_ratio_pitch_over_native": median_ratio,
        "flips_against_tracer": flips,
        "published_row_moves_materially": material,
        "in_sample_reading": cause,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument(
        "--native", type=Path, default=Path("reports/neural_tracer_entrant.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_pitch.json")
    )
    args = ap.parse_args()
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    native = json.loads(args.native.read_text())["neural_rows"]
    rows: dict[str, dict | None] = {}
    comp: dict[str, dict] = {}
    identity: dict[str, list[str]] = {}
    failed = []
    for c in f91.ALL:
        target = f91.SG / "data" / f"fibers_{c}"
        meta = json.loads((target / "meta.json").read_text())
        comp[c] = {"tracer": meta["floors"][f91.TRACER], "cc": meta["floors"][f91.CC]}
        run = args.work / c
        if not (run / "fibers.afv").exists():
            rows[c] = None
            failed.append(c)
            continue
        problems = identity_problems(json.loads((run / "run.json").read_text()), c)
        if problems:
            identity[c] = problems
        skel, _, _ = load_fiber_target(target)
        size = int(c.rsplit("_", 1)[1])
        labels = afv_to_labels.rasterize(
            scale_back(afv_to_labels.read_afv(run / "fibers.afv"), c), (size,) * 3
        )
        row = score_tracing(skel, labels, tolerance=f91.TOL).as_row()
        row["stop_reasons"] = f91.stop_reasons(run / "fibers.afv")
        rows[c] = row
        print(
            f"{c}: pen {row[PEN]} (native {native[c][PEN]}) cov {row[COV]} (native {native[c][COV]})",
            flush=True,
        )
    status = "IDENTITY_FAILED" if identity else ("INCOMPLETE" if failed else "OK")
    out = {
        "status": status,
        "to_um": TO_UM,
        "ratio": R,
        "settings": SETTINGS,
        "failed_runs": failed,
        "identity_problems": identity,
        "pitch_rows": rows,
        "native_rows": {
            c: {k: v for k, v in native[c].items() if k != "stop_reasons"}
            for c in f91.ALL
        },
        "comparators": comp,
        "groups": {
            "in_sample": f91.IN_SAMPLE,
            "s3": f91.S3,
            "s5_held_out": f91.S5_HELDOUT,
        },
    }
    if status != "IDENTITY_FAILED":
        out.update(verdict({c: r for c, r in rows.items() if r}, native, comp))
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {status}; wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
