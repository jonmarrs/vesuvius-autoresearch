"""docs/preregistration/2026-10-16_neural_fiber_tracer_entrant.md -- villa's neural fiber tracer (villa #2045,
scrollprize/fiber_single_small) traced each ScrollGT fiber cube in volume mode at its defaults. ScrollGT scores it
(fiber scoring version 3, tolerance 2.0) beside connected components, our tracer, and villa PR #1934's generator.

Each cube's run.json must record the registered checkpoint (by sha256) and settings, or there is no verdict. The
.afv it exported is rasterised as thin centrelines (afv_to_labels.py). #1934's generator is re-scored from finding
85's .afv files under the same scorer, after its own identity check.

Usage: .venv/bin/python scripts/neural_tracer_analysis.py --work DIR --generator-work DIR [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_generator_analysis as gen85  # noqa: E402
import afv_to_labels  # noqa: E402

SG = Path("/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt")
TOL = 2.0
LOOSE_TOL = 4.0  # descriptive only: the tracer's own label tolerance, 2 grid voxels, is 4 CT voxels here
REPO_ID = "scrollprize/fiber_single_small"
REVISION = "451182558cb3270cfc2ddf967acbd4f36b9b816b"
CHECKPOINT_SHA256 = "3268a0ac1807debdeaded05fa7bc90b82d3ca8102125247e5cba688a10a4811f"
# Every setting tracing/volume.py records that changes the fibers (its own resume check exempts the rest as speed
# or location), at its villa ccb431818 default, except the four that point it at a 7.91 um cube.
SETTINGS = {
    "checkpoint": f"{REPO_ID}@{REVISION}",
    "ct_level": 0,
    "ct_grid_scale": 1.0,
    "grid_scale": 2.0,
    "base_um": 7.91,  # reported lengths only
    "ct_z": None,
    "prefix": "fiber_",
    "tile": 256.0,
    "plane_spacing": 64.0,
    "threshold": 128.0,
    "dot_radius": 2.0,
    "fill_spacing": 4.0,
    "fill_skip": 4.0,
    "batch_spread": 16.0,
    "dedupe": 2.0,
    "stop_decisions": 3,
    "outside_decisions": 2,
    "outside_gap": 16,
    "overlap": 16,
    "trim_run": 24,
    "min_length": 48,
    "max_len": 8000.0,
    "confidence": 0.5,
    "n_commit": None,
    "gate": None,
    "precision": "bf16",
    "crops": "gpu",
    "sampling_seed": 0,
}
IN_SAMPLE = gen85.IN_SAMPLE  # fiber_hz_vt (the presence) trained on these 11
S3 = gen85.S3  # held out for the presence, the tracer and the generator
S5_HELDOUT = gen85.S5_HELDOUT
ALL = IN_SAMPLE + S3 + S5_HELDOUT
REPEAT = [
    "s3_00994_00494_01994_512",
    "s1_00497_01497_03997_256",
]  # traced twice: run-to-run variation, descriptive
CC, TRACER = "floor_connected_components", "tracer_strict_relink"
PEN, COV = "erl_merge_penalized", "coverage"


def grid_size(cube: str) -> float:
    return int(cube.rsplit("_", 1)[1]) / SETTINGS["grid_scale"]


def identity_problems(record: dict, cube: str) -> list[str]:
    """Differences between a run's run.json and the registered entrant for this cube."""
    bad = []
    if record.get("checkpoint_sha256") != CHECKPOINT_SHA256:
        bad.append(f"checkpoint_sha256={record.get('checkpoint_sha256')}")
    for k, v in SETTINGS.items():
        if k not in record or record[k] != v:
            bad.append(f"{k}={record.get(k, '<absent>')!r}")
    n = grid_size(cube)
    if record.get("box") != {"lo": [0.0, 0.0, 0.0], "hi": [n, n, n]}:
        bad.append(f"box={record.get('box')!r}")
    if not str(record.get("ct", "")).rstrip("/").endswith(f"/{cube}.zarr"):
        bad.append(f"ct={record.get('ct')!r}")
    if (
        not str(record.get("presence", ""))
        .rstrip("/")
        .endswith(f"/{cube}_presence.zarr/1")
    ):
        bad.append(f"presence={record.get('presence')!r}")
    return bad


def _share(cubes, holds) -> float:
    return sum(holds(c) for c in cubes) / len(cubes)


def verdict(rows: dict, comp: dict) -> dict:
    """rows: cube -> the tracer's row, or None if its run failed. comp: cube -> {"cc", "tracer", "generator"} rows
    (the generator's may be None).

    P1-P3 need at least 6 Scroll-3 cubes with the rows they compare; P4 needs both held-out Scroll-5 rows as well.
    """
    s3 = [c for c in S3 if rows.get(c) is not None]
    s3_gen = [c for c in s3 if comp[c].get("generator") is not None]
    t = {c: comp[c]["tracer"] for c in comp}
    g = {c: comp[c].get("generator") for c in comp}
    s5 = [c for c in S5_HELDOUT if rows.get(c) is not None]
    pred = {
        "P1_s3_pen_above_generator_on_75pct": (
            _share(s3_gen, lambda c: rows[c][PEN] > g[c][PEN]) >= 0.75 if len(s3_gen) >= 6 else None),
        "P2_s3_pen_above_tracer_on_60pct": (
            _share(s3, lambda c: rows[c][PEN] > t[c][PEN]) >= 0.60 if len(s3) >= 6 else None),
        "P3_s3_coverage_below_tracer_on_75pct": (
            _share(s3, lambda c: rows[c][COV] < t[c][COV]) >= 0.75 if len(s3) >= 6 else None),
        "P4_heldout_s5_coverage_below_s3_median": (
            all(rows[c][COV] < statistics.median(rows[s][COV] for s in s3) for c in s5)
            if len(s3) >= 6 and len(s5) == len(S5_HELDOUT) else None),
    }  # fmt: skip
    failed = sorted(c for c in ALL if rows.get(c) is None)
    status = "OK" if all(v is not None for v in pred.values()) else "INCOMPLETE"
    return {
        "status": status,
        "failed_runs": failed,
        "s3_cubes": s3,
        "s3_cubes_with_generator": s3_gen,
        "predictions": pred,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--generator-work", type=Path, required=True)
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_entrant.json")
    )
    args = ap.parse_args()
    sys.path.insert(0, str(SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )

    def score(afv: Path, cube: str, skel, tolerance: float) -> dict:
        size = int(cube.rsplit("_", 1)[1])
        fibers = afv_to_labels.read_afv(afv)
        labels = afv_to_labels.rasterize(
            {k: afv_to_labels.to_cube_zyx(v, (0, 0, 0)) for k, v in fibers.items()},
            (size,) * 3,
        )
        row = score_tracing(skel, labels, tolerance=tolerance).as_row()
        row["n_fibers_in_afv"] = len(fibers)
        return row

    comp: dict[str, dict] = {}
    rows: dict[str, dict | None] = {}
    loose: dict[str, dict] = {}
    identity: dict[str, list[str]] = {}
    for c in ALL:
        target = SG / "data" / f"fibers_{c}"
        meta = json.loads((target / "meta.json").read_text())
        skel, _, _ = load_fiber_target(target)
        comp[c] = {
            "cc": meta["floors"][CC],
            "tracer": meta["floors"][TRACER],
            "generator": None,
        }
        for name in ("cc", "tracer"):
            if comp[c][name].get("scoring_version") != SCORING_VERSION:
                raise SystemExit(
                    f"{c}: ScrollGT's {name} row is not scoring version {SCORING_VERSION}"
                )
        gafv = args.generator_work / f"{c}.afv"
        if gafv.exists() and not gen85.identity_problems(
            gen85.afv_generator_metadata(gafv), int(c.rsplit("_", 1)[1])
        ):
            comp[c]["generator"] = score(gafv, c, skel, TOL)
        run = args.work / c
        afv = run / "fibers.afv"
        if not (run / "run.json").exists() or not afv.exists():
            rows[c] = None
            print(f"{c}: no finished run (failed or missing)", flush=True)
            continue
        bad = identity_problems(json.loads((run / "run.json").read_text()), c)
        if bad:
            identity[c] = bad
            continue
        rows[c] = score(afv, c, skel, TOL)
        loose[c] = {"tracer": score(afv, c, skel, LOOSE_TOL)}
        if comp[c]["generator"] is not None:
            loose[c]["generator"] = score(gafv, c, skel, LOOSE_TOL)
        r, t, gr = rows[c], comp[c]["tracer"], comp[c]["generator"]
        print(f"{c}: neural ERL {r['erl']} pen {r[PEN]} cov {r[COV]} merges {r['merges']} inst "
              f"{r['n_pred_instances']} | our tracer pen {t[PEN]} cov {t[COV]}"
              + (f" | generator pen {gr[PEN]} cov {gr[COV]}" if gr else ""), flush=True)  # fmt: skip
    repeat: dict[str, dict] = {}
    for c in REPEAT:
        run = args.work / "repeat" / c
        if rows.get(c) is None or not (run / "fibers.afv").exists():
            continue
        bad = identity_problems(json.loads((run / "run.json").read_text()), c)
        if bad:
            identity[f"repeat/{c}"] = bad
            continue
        skel, _, _ = load_fiber_target(SG / "data" / f"fibers_{c}")
        second = score(run / "fibers.afv", c, skel, TOL)
        repeat[c] = {"second_run": second, "abs_difference": {
            k: abs(second[k] - rows[c][k]) for k in ("erl", PEN, COV, "merges", "n_pred_instances")}}  # fmt: skip
    if identity:
        v = {"status": "IDENTITY_FAILED", "identity_problems": identity}
    else:
        v = verdict(rows, comp)
    out = {"scoring_version": SCORING_VERSION, "tolerance": TOL, "checkpoint": f"{REPO_ID}@{REVISION}",
           "checkpoint_sha256": CHECKPOINT_SHA256, "settings": SETTINGS, "neural_rows": rows,
           "comparators": comp, "descriptive_tolerance_4": loose, "descriptive_repeat": repeat, **v}  # fmt: skip
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(v, indent=1))
    return 0 if v["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
