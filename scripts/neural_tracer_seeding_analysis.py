"""docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md -- villa's neural fiber tracer with its seeding set
per micrometre (scripts/neural_tracer_seeding.py), in two arms:

  A: finding 92's 9.6 um cubes, seeded per micrometre as natively (spacing flags and presence smoothing / r);
  B: finding 91's native cubes, seeded per micrometre as at 9.6 um (the same * r).

Subcommands, all run by repro/fibers/run_neural_tracer_seeding_chain.sh:

  args --arm A|B        the launcher and villa flags of an arm, for the chain to pass on;
  smoke --afv --reference
                        exit 0 when the identity smoke passes: the run holding --afv was the launcher's, at villa's
                        default smoothing (smoke_check), and its .afv holds the same fibers point for point as
                        --reference, finding 91's run;
  score --work W        check the smoke's records (run.json, seeding.json) against the launcher at villa's default,
                        check every run against its arm (run.json, seeding.json) and its recorded seed dots against
                        the probe (reports/neural_tracer_seed_probe.json), score it as finding 91 or 92 did, and apply
                        the registered predictions and decision rule. Writes reports/neural_tracer_seeding.json.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_pitch_analysis as pa  # noqa: E402
import neural_tracer_pitch_funnel as fn  # noqa: E402

R = pa.R
PEN, COV = f91.PEN, f91.COV
SMOKE_CUBE = "s1_00497_01497_03997_256"
MIN_ROWS, MIN_S3_LEADS = 17, 6


def _scaled(settings: dict, f: float) -> dict:
    """An arm's villa settings: the two spacing flags and the fill-in skip moved by f, all else as the run it repeats."""
    return {
        **settings,
        "plane_spacing": settings["plane_spacing"] * f,
        "fill_spacing": settings["fill_spacing"] * f,
        "fill_skip": settings["fill_skip"] * f,
    }


ARMS = {
    "A": {"settings": _scaled(pa.SETTINGS, 1 / R), "smoothing": 1 / R, "ct": "ct_9p6", "presence": "presence_9p6",
          "grid": pa.grid_size},
    "B": {"settings": _scaled(f91.SETTINGS, R), "smoothing": R, "ct": "ct", "presence": "presence",
          "grid": f91.grid_size},
}  # fmt: skip
# The identity smoke: finding 91's settings and inputs, through the launcher at villa's own smoothing.
SMOKE_RUN = {"settings": f91.SETTINGS, "smoothing": 1.0, "ct": "ct", "presence": "presence",
             "grid": f91.grid_size}  # fmt: skip


def identity_problems(
    arm: str, record: dict, seeding: dict | None, cube: str
) -> list[str]:
    """Differences between a run's run.json and seeding.json and its registered arm ("smoke": the identity smoke's)."""
    a, bad = (SMOKE_RUN if arm == "smoke" else ARMS[arm]), []
    if record.get("checkpoint_sha256") != f91.CHECKPOINT_SHA256:
        bad.append(f"checkpoint_sha256={record.get('checkpoint_sha256')}")
    for k, v in a["settings"].items():
        if k not in record or record[k] != v:
            bad.append(f"{k}={record.get(k, '<absent>')!r}")
    n = a["grid"](cube)
    if record.get("box") != {"lo": [0.0, 0.0, 0.0], "hi": [n, n, n]}:
        bad.append(f"box={record.get('box')!r}")
    if not str(record.get("ct", "")).rstrip("/").endswith(f"/{a['ct']}/{cube}.zarr"):
        bad.append(f"ct={record.get('ct')!r}")
    if (
        not str(record.get("presence", ""))
        .rstrip("/")
        .endswith(f"/{a['presence']}/{cube}_presence.zarr/1")
    ):
        bad.append(f"presence={record.get('presence')!r}")
    if record.get("tile_workers") != 0:
        bad.append(f"tile_workers={record.get('tile_workers')!r}")
    if seeding is None:
        bad.append("no seeding.json: not run by the launcher")
    else:
        if seeding.get("presence_smoothing_sigma") != a["smoothing"]:
            bad.append(f"smoothing={seeding.get('presence_smoothing_sigma')!r}")
        if seeding.get("hessian_sigma") != 1.5:
            bad.append(f"hessian={seeding.get('hessian_sigma')!r}")
    return bad


def manipulation_problems(arm: str, cube: str, recorded: int, probe: dict) -> list[str]:
    """The registered manipulation check: the seed dots a run recorded must be the probe's count for its arm."""
    expected = probe[cube][arm]["flags_smooth"]["dots"]
    return (
        []
        if recorded == expected
        else [f"recorded {recorded} seed dots, the probe counted {expected}"]
    )


def smoke_check(run: Path, reference: Path) -> dict:
    """The registered identity smoke: the launcher at villa's default smoothing, with --tile-workers 0, reproduces
    finding 91's fibers.afv. Villa's tool alone reproduces it too, so its records are checked as an arm's are:
    seeding.json, which only the launcher writes, shows that the launcher ran, and run.json that it ran on finding
    91's settings and inputs with --tile-workers 0."""
    afv, record, seeding = run / "fibers.afv", run / "run.json", run / "seeding.json"
    identical = afv.exists() and afv_identical(afv, reference)
    problems = (
        identity_problems(
            "smoke",
            json.loads(record.read_text()),
            json.loads(seeding.read_text()) if seeding.exists() else None,
            SMOKE_CUBE,
        )
        if record.exists()
        else ["no run.json"]
    )
    return {
        "cube": SMOKE_CUBE,
        "identical_to_finding_91": identical,
        "launcher_problems": problems,
        "ok": identical and not problems,
    }


def afv_identical(a: Path, b: Path) -> bool:
    """The same fibers point for point, whatever their ids."""

    def fibers(p):
        return sorted(
            np.ascontiguousarray(v, "<f8").tobytes()
            for v in afv_to_labels.read_afv(p).values()
        )

    return fibers(a) == fibers(b)


def verdict(rows_a: dict, rows_b: dict, native: dict, comp: dict) -> dict:
    """The registered predictions and decision rule, from each arm's scored rows (None: not scored)."""
    a = [c for c in f91.ALL if rows_a.get(c)]
    b = [c for c in f91.ALL if rows_b.get(c)]
    s3 = [c for c in f91.S3 if rows_a.get(c)]
    if zero := [c for c in a + b if native[c][PEN] <= 0]:
        raise ValueError(f"no ratio over a native score of 0: {zero}")
    ratio_a = (
        statistics.median(rows_a[c][PEN] / native[c][PEN] for c in a) if a else None
    )
    ratio_b = (
        statistics.median(rows_b[c][PEN] / native[c][PEN] for c in b) if b else None
    )
    leads = sum(rows_a[c][PEN] > comp[c]["tracer"][PEN] for c in s3)
    p1 = ratio_a >= 0.85 if len(a) >= MIN_ROWS else None
    p2 = leads >= MIN_S3_LEADS if len(a) >= MIN_ROWS else None
    p3 = ratio_b <= 0.80 if len(b) >= MIN_ROWS else None
    if p1 is None or p3 is None:
        conclusion = None
    elif p1 and p3:
        conclusion = ("the seeding scale, fixed in grid voxels, explains most of finding 92's drop: recommend revising "
                      "ScrollGT 0.8.1's note to say so, with P2's result")  # fmt: skip
    elif p3:
        conclusion = ("seeding density moves the score, but restoring it at 9.6 µm does not recover it: the note "
                      "stands, with the seeding sensitivity added")  # fmt: skip
    elif not p1:
        conclusion = "the seeding scale is not the cause: the note stands"
    else:
        conclusion = "inconsistent: both reported, no recommendation"
    return {
        "predictions": {
            "P1_A_median_pen_ratio_at_least_0.85": p1,
            "P2_A_leads_tracer_on_6_of_8_s3": p2,
            "P3_B_median_pen_ratio_at_most_0.80": p3,
        },
        "median_pen_ratio_A": ratio_a,
        "median_pen_ratio_B": ratio_b,
        "scored": {"A": len(a), "B": len(b)},
        "s3_leading_tracer_A": [leads, len(s3)],
        "conclusion": conclusion,
    }


def outcome(
    smoke_ok: bool, identity: dict, rows_a: dict, rows_b: dict, native: dict, comp: dict
):
    """SMOKE_FAILED or IDENTITY_FAILED (no verdict); else INCOMPLETE when a prediction is unevaluated; else OK."""
    if not smoke_ok:
        return "SMOKE_FAILED", None
    if any(identity.values()):
        return "IDENTITY_FAILED", None
    reading = verdict(rows_a, rows_b, native, comp)
    complete = all(v is not None for v in reading["predictions"].values())
    return ("OK" if complete else "INCOMPLETE"), reading


def launch_args(arm: str) -> str:
    """The launcher's --smoothing and villa's arm flags, exactly as the arm's settings hold them."""
    a = ARMS[arm]
    s = a["settings"]
    return (f"--smoothing {a['smoothing']!r} --plane-spacing {s['plane_spacing']!r} --fill-spacing "
            f"{s['fill_spacing']!r} --fill-skip {s['fill_skip']!r} --base-um {s['base_um']!r}")  # fmt: skip


def score(args) -> int:
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    native = json.loads(args.native.read_text())["neural_rows"]
    pitch = json.loads(args.pitch.read_text())["pitch_rows"]
    probe = json.loads(args.probe.read_text())["cubes"]
    smoke = smoke_check(
        args.work / "identity" / SMOKE_CUBE,
        args.native_work / SMOKE_CUBE / "fibers.afv",
    )
    rows: dict[str, dict] = {"A": {}, "B": {}}
    identity: dict[str, dict] = {"A": {}, "B": {}}
    manipulation: dict[str, dict] = {"A": {}, "B": {}}
    failed: dict[str, list] = {"A": [], "B": []}
    funnel: dict[str, dict] = {"A": {}, "B": {}}
    comp = {}
    for c in f91.ALL:
        target = f91.SG / "data" / f"fibers_{c}"
        meta = json.loads((target / "meta.json").read_text())
        comp[c] = {"tracer": meta["floors"][f91.TRACER], "cc": meta["floors"][f91.CC]}
        skel, _, _ = load_fiber_target(target)
        size = int(c.rsplit("_", 1)[1])
        for arm in "AB":
            run = args.work / arm / c
            if not (run / "fibers.afv").exists():
                rows[arm][c] = None
                failed[arm].append(c)
                continue
            seeding = (
                json.loads((run / "seeding.json").read_text())
                if (run / "seeding.json").exists()
                else None
            )
            if bad := identity_problems(
                arm, json.loads((run / "run.json").read_text()), seeding, c
            ):
                identity[arm][c] = bad
            funnel[arm][c] = fn.tile_totals(run)
            if m := manipulation_problems(arm, c, funnel[arm][c]["dots"], probe):
                manipulation[arm][c] = m
                rows[arm][c] = None
                continue
            fibers = afv_to_labels.read_afv(run / "fibers.afv")
            cube_zyx = pa.scale_back(fibers, c) if arm == "A" else {
                k: afv_to_labels.to_cube_zyx(v, (0, 0, 0)) for k, v in fibers.items()}  # fmt: skip
            row = score_tracing(
                skel, afv_to_labels.rasterize(cube_zyx, (size,) * 3), tolerance=f91.TOL
            ).as_row()
            row["stop_reasons"] = f91.stop_reasons(run / "fibers.afv")
            rows[arm][c] = row
            print(
                f"{arm} {c}: pen {row[PEN]} (native {native[c][PEN]}) cov {row[COV]}",
                flush=True,
            )
    status, reading = outcome(smoke["ok"], identity, rows["A"], rows["B"], native, comp)
    out = {
        "status": status,
        "ratio": R,
        "arms": {
            k: {"settings": v["settings"], "smoothing": v["smoothing"]}
            for k, v in ARMS.items()
        },
        "smoke": smoke,
        "failed_runs": failed,
        "identity_problems": identity,
        "manipulation_problems": manipulation,
        "rows_A": rows["A"],
        "rows_B": rows["B"],
        "native_rows": {
            c: {k: v for k, v in native[c].items() if k != "stop_reasons"}
            for c in f91.ALL
        },
        "pitch_rows": pitch,
        "comparators": comp,
        "funnel": funnel,
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("args")
    a.add_argument("--arm", choices=sorted(ARMS), required=True)
    s = sub.add_parser("smoke")
    s.add_argument("--afv", type=Path, required=True)
    s.add_argument("--reference", type=Path, required=True)
    sc = sub.add_parser("score")
    sc.add_argument("--work", type=Path, required=True)
    sc.add_argument(
        "--native-work",
        type=Path,
        default=Path(
            "/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer/run"
        ),
    )
    sc.add_argument(
        "--native", type=Path, default=Path("reports/neural_tracer_entrant.json")
    )
    sc.add_argument(
        "--pitch", type=Path, default=Path("reports/neural_tracer_pitch.json")
    )
    sc.add_argument(
        "--probe", type=Path, default=Path("reports/neural_tracer_seed_probe.json")
    )
    sc.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_seeding.json")
    )
    args = ap.parse_args(argv)
    if args.cmd == "args":
        print(launch_args(args.arm))
        return 0
    if args.cmd == "smoke":
        smoke = smoke_check(args.afv.parent, args.reference)
        print("identical" if smoke["identical_to_finding_91"] else "differs")
        for problem in smoke["launcher_problems"]:
            print(f"not the launcher at villa's default: {problem}")
        return 0 if smoke["ok"] else 1
    return score(args)


if __name__ == "__main__":
    sys.exit(main())
