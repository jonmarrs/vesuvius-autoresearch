"""docs/preregistration/2026-11-02_seed_heading_confirmation.md -- the queued villa fix to its neural fiber tracer's
seed heading (repro/fibers/villa_volume_seed_heading.patch, finding 100's `keep` arm), on ten hand-traced cubes that
this repository has never traced or scored.

Finding 100 traced the seed dots that villa's tracer skips where its CT axis lies more than 35 degrees from the presence
direction. Kept on villa's own axis, as the fix keeps them, coverage rose 1.11x and 1.28x on the two held-out Scroll-5
cubes, which skipped 27% and 35% of their dots. On the 19 cubes that skipped at most 9%, it moved by 0.9965-1.0124x.
villa's fiber-skeletons Dataset004 holds 31 hand-traced cubes and ScrollGT ships 21. The other ten (CUBES) were checked
on the CPU on 2026-11-02 (reports/evidence/fiber_skeletons_unshipped_checks_2026-11-02.json).

Everything else is finding 97's protocol:
* the CT, padded by MARGIN voxels of the public raw scan, whose core must equal the cube's Dataset004 image exactly;
* the presence, made from fiber_hz_vt's probability as finding 91 made it and placed in the padded frame with zeros
  outside the cube;
* the box (the cube), the checkpoint and the command.
villa's CLI runs at VILLA_SHA (`before`) and at VILLA_SHA with the patch (`after`), as the re-run of 2026-10-28 did. That
re-run reproduced findings 97 and 100 point for point.

  fetch     the padded CT of each cube (resumable, chunks cached) and its core check; writes WORK/prepared.json
  presence  fiber_hz_vt on each cube (the GPU; cached with its inference identity), then the padded presence level;
            writes WORK/presence.json
  smoke     `before` on SMOKE, with finding 97's inputs, must reproduce finding 97's run point for point
  done      exit 0 if the chain logged SIDE CUBE as DONE last and its closed outputs are there
  score     score both runs of each cube in its frame at tolerances 2 and 4; the registered predictions and decision
            rule. Writes reports/seed_heading_confirmation.json.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_tracer_presence  # noqa: E402
import neural_tracer_ct_context as cc  # noqa: E402
import villa_seed_heading_rerun as rr  # noqa: E402

f91 = cc.f91
D = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_d004/unshipped")
CUBES = (
    "s1_02494_01494_03994_512",
    "s1_08994_02494_03494_512",
    "s1_09997_02497_03497_256",
    "s5_05497_01997_02997_256",
    "s5_05497_02497_02497_256",
    "s5_08994_02994_03994_512",
    "s5_08997_02497_04997_256",
    "s5_11497_05497_03997_256",
    "s5_15494_04494_02494_512",
    "s5_16997_03497_03997_256",
)
# First released in Dataset003, so outside fiber_hz_vt's training set (Dataset002's 13 + 5); the other seven are in it.
PRESENCE_HELD_OUT = (
    "s1_08994_02494_03494_512",
    "s1_09997_02497_03497_256",
    "s5_15494_04494_02494_512",
)
SIDES = ("before", "after")
MARGIN = cc.MARGIN
VILLA_SHA = "39a8cf3a124bdd5540ee826e1cb30047c8dc8c85"
SMOKE = (
    "s5_13497_01497_02497_256"  # finding 97's inputs; its run is the smoke's reference
)
SMOKE_REFERENCE = cc.T / "ct_context_run" / "neural" / SMOKE
# The model directory finding 91 recorded in each cube's inference identity (an absolute path: the script runs frozen).
MODEL = Path(
    "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/local_data/models/fiber_hz_vt"
)
PATCH = 128
TOLS = (2.0, 4.0)
# The registered predictions (docs/preregistration/2026-11-02_seed_heading_confirmation.md). s is a cube's skip share:
# the `before` run's no_heading over its dots, as finding 100 recorded it (no_heading_share).
LOW_SKIP = 0.02  # P1 applies to cubes with s below this
P1_BAND = (0.99, 1.01)  # P1: after/before coverage at tolerance 2 on those cubes
P2_DROP = 0.03  # P2: precision at tolerance 2 at most this much lower, on every cube
HIGH_SKIP = 0.20  # P3 applies to cubes with s at least this
P3_FACTOR = (
    1.05  # P3: after/before coverage at tolerance 2 at least this, on those cubes
)
P4_RHO = 0.5  # P4: Spearman's rho between s and the coverage factor, over the ten
P5_PEN = 0.95  # P5: after/before merge-penalized ERL at tolerance 2 at least this, on every cube
EVENTS = {"TRACE", "DONE", "FAILED"}


def size_of(cube: str) -> int:
    return int(cube.rsplit("_", 1)[1])


def box(cube: str) -> str:
    """The cube in the padded trace grid (grid scale 2), as villa's --box x0,y0,z0,x1,y1,z1."""
    lo, hi = cc.box_grid(MARGIN, size_of(cube))
    return ",".join(str(v) for v in (lo,) * 3 + (hi,) * 3)


def nml_path(cube: str, nml_dir: Path = D / "nml") -> Path:
    """Dataset004's NML for the cube (Scroll 1's are named s1a)."""
    s, z, y, x, n = cube.split("_")
    found = sorted(nml_dir.glob(f"fibers_{s}*_{z}z_{y}y_{x}x_{n}_v*.nml"))
    if len(found) != 1:
        raise SystemExit(f"{cube}: expected one NML in {nml_dir}, found {[p.name for p in found]}")  # fmt: skip
    return found[0]


def ground_truth(cube: str, nml: Path | None = None):
    """The NML in the cube's frame, keeping the fibers with more than one node inside it, as ScrollGT's targets are
    scored. On two shipped cubes this gives ScrollGT's rows exactly (the checks record)."""
    if str(f91.SG / "src") not in sys.path:
        sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.skeleton_io import Skeleton, origin_from_stem, parse_nml

    shape = (size_of(cube),) * 3
    skel = parse_nml(nml or nml_path(cube), origin_zyx=origin_from_stem(cube))
    if skel.scale_um and any(abs(s - 7.91) > 1e-6 for s in skel.scale_um):
        raise SystemExit(f"{cube}: NML scale {skel.scale_um} is not 7.91 um")
    kept = [f for f in skel.fibers if f.in_bounds_mask(shape).sum() > 1]
    return Skeleton(fibers=kept, scale_um=skel.scale_um, origin_zyx=skel.origin_zyx)


def cube_image(cube: str) -> np.ndarray:
    import tifffile

    img = tifffile.imread(D / f"{cube}_image.tif")
    if img.shape != (size_of(cube),) * 3 or img.dtype != np.uint8:
        raise SystemExit(f"{cube}: image {img.shape} {img.dtype}")
    return img


def fetch(work: Path, cubes=CUBES, get=cc._get, get_ranges=None) -> dict:
    import zarr

    get_ranges = get_ranges or cc.raw_tiff_region._get_ranges
    out = {}
    for cube in cubes:
        n, img = size_of(cube), cube_image(cube)
        dst = work / "ct" / f"{cube}.zarr"
        if not dst.exists():
            padded = cc.to_uint8(
                cc.read_padded(cube, work / "cache" / cube, get, get_ranges)
            )
            if not np.array_equal(cc.core(padded, MARGIN, n), img):
                raise SystemExit(
                    f"{cube}: the padded CT's core differs from Dataset004's image"
                )
            cc._write_array(dst, "0", padded, (128, 128, 128))
        arr = zarr.open(str(dst / "0"), mode="r")
        ok = bool(
            arr.shape == (n + 2 * MARGIN,) * 3
            and np.array_equal(cc.core(arr[...], MARGIN, n), img)
        )
        out[cube] = {"shape": list(arr.shape), "core_equals_dataset004": ok}
        print(cube, out[cube], flush=True)
    return out


def padded_level(level: np.ndarray, cube: str) -> np.ndarray:
    """The presence level in the padded trace grid, zero outside the cube."""
    lo, hi = cc.box_grid(MARGIN, size_of(cube))
    if level.shape != (hi - lo,) * 3:
        raise ValueError(f"{cube}: presence level {level.shape} is not the cube's grid")
    out = np.zeros(((size_of(cube) + 2 * MARGIN) // 2,) * 3, np.uint8)
    out[lo:hi, lo:hi, lo:hi] = level
    return out


def presence(work: Path, device: str, cubes=CUBES) -> dict:
    import zarr

    from vesuvius_autoresearch.fibers.bench_cli import _fiber_prob

    out = {}
    for cube in cubes:
        dst = work / "presence" / f"{cube}_presence.zarr"
        prob = _fiber_prob(D, cube, cube_image(cube), MODEL, PATCH, device)
        level = make_tracer_presence.presence_level(prob)
        if not dst.exists():
            cc._write_array(dst, "1", padded_level(level, cube), (64, 64, 64))
        got = zarr.open(str(dst / "1"), mode="r")[...]
        ok = bool(np.array_equal(got, padded_level(level, cube)))
        record = json.loads((D / f"{cube}_fiberprob.json").read_text())
        out[cube] = {"shape": list(got.shape), "core_equals_level": ok, "inference_device": record["inference"]["recipe"]["device"],
                     "probability_sha256": record["probability_sha256"]}  # fmt: skip
        print(cube, out[cube], flush=True)
    return out


def counts(run: Path) -> dict:
    """tiles.jsonl's seed counts, summed over each tile's last line."""
    lines = [json.loads(s) for s in (run / "tiles.jsonl").read_text().splitlines() if s.strip()]  # fmt: skip
    tiles = {t["tile"]: t for t in lines}
    keys = ("dots", "owned_dots", "no_heading", "traced", "fibers")
    return {k: int(sum(t.get(k, 0) for t in tiles.values())) for k in keys}


def skip_share(record: dict) -> float:
    return record["no_heading"] / record["dots"]


def last_event(work: Path, side: str, cube: str) -> str | None:
    """A later TRACE or FAILED replaces an earlier DONE."""
    log = work / "chain.log"
    event = None
    for line in log.read_text().splitlines() if log.exists() else []:
        f = line.split()
        if len(f) >= 3 and f[0] in EVENTS and f[1] == side and f[2] == cube:
            event = f[0]
    return event


def outputs_ok(run: Path) -> bool:
    tiles = sorted((run / "tiles").glob("*.npz")) if (run / "tiles").is_dir() else []
    return (all((run / n).is_file() and (run / n).stat().st_size for n in ("run.json", "tiles.jsonl"))
            and bool(tiles) and not any(t.name.endswith(".partial.npz") for t in tiles))  # fmt: skip


def done(work: Path, side: str, cube: str) -> bool:
    return last_event(work, side, cube) == "DONE" and outputs_ok(work / side / cube)


def spearman(a: list, b: list) -> float | None:
    from scipy.stats import spearmanr

    if len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return float(spearmanr(a, b).statistic)


def verdict(rows: dict, records: dict) -> dict:
    """rows / records: side -> cube -> row at tolerance 2 / counts."""
    if any(
        c not in rows.get(s, {}) or c not in records.get(s, {})
        for s in SIDES
        for c in CUBES
    ):
        return {f"prediction_P{i}": None for i in range(1, 6)} | {"reading": None, "decision": None}  # fmt: skip
    b, a = rows["before"], rows["after"]
    if zero := [
        c for c in CUBES if b[c]["coverage"] <= 0 or b[c]["erl_merge_penalized"] <= 0
    ]:
        raise ValueError(f"no factor over a baseline of 0: {zero}")
    s = {c: skip_share(records["before"][c]) for c in CUBES}
    cov = {c: a[c]["coverage"] / b[c]["coverage"] for c in CUBES}
    prec = {c: a[c]["precision"] - b[c]["precision"] for c in CUBES}
    pen = {c: a[c]["erl_merge_penalized"] / b[c]["erl_merge_penalized"] for c in CUBES}
    low = [c for c in CUBES if s[c] < LOW_SKIP]
    high = [c for c in CUBES if s[c] >= HIGH_SKIP]
    rho = spearman([s[c] for c in CUBES], [cov[c] for c in CUBES])
    out = {
        "skip_share": s, "coverage_factor": cov, "precision_change": prec, "erl_merge_penalized_factor": pen,
        "merges_change": {c: a[c]["merges"] - b[c]["merges"] for c in CUBES},
        "low_skip_cubes": low, "high_skip_cubes": high, "spearman_rho": rho,
        "manipulation": {c: records["after"][c]["no_heading"] == 0 for c in CUBES},
        "median_coverage_factor": statistics.median(cov.values()),
        "prediction_P1": all(P1_BAND[0] <= cov[c] <= P1_BAND[1] for c in low) if low else None,
        "prediction_P2": all(prec[c] >= -P2_DROP for c in CUBES),
        "prediction_P3": all(cov[c] >= P3_FACTOR for c in high) if high else None,
        "prediction_P4": rho >= P4_RHO if rho is not None else None,
        "prediction_P5": all(pen[c] >= P5_PEN for c in CUBES),
    }  # fmt: skip
    out["manipulation_ok"] = all(out["manipulation"].values())
    out["decision"] = decision(out)
    out["reading"] = reading(out)
    return out


def decision(v: dict) -> str:
    """The registered decision rule, for the villa draft (docs/VILLA_DRAFT_volume_seed_heading.md)."""
    if not (v["prediction_P2"] and v["prediction_P5"]):
        return "HOLD"  # the fix costs precision or merge-penalized ERL on a cube it was never measured on
    return {True: "REPLICATED", False: "NOT_REPLICATED", None: "NO_HIGH_SKIP_CUBE"}[
        v["prediction_P3"]
    ]


def reading(v: dict) -> str:
    n = len(v["high_skip_cubes"])
    head = {
        "HOLD": "on cubes never traced here, the fix costs " + " and ".join(
            s for s, ok in (("precision", v["prediction_P2"]), ("merge-penalized ERL", v["prediction_P5"])) if not ok)
            + ": hold the villa draft",
        "REPLICATED": f"the coverage gain replicates on the {n} unseen cube{'s' * (n != 1)} that skip at least "
                      f"{HIGH_SKIP:.2f} of their dots, at the same precision and merge-penalized ERL",
        "NOT_REPLICATED": f"the coverage gain does not replicate on the {n} unseen cube{'s' * (n != 1)} that skip at "
                          f"least {HIGH_SKIP:.2f} of their dots: the draft's gain rests on finding 100's two cubes and "
                          "must say it did not replicate",
        "NO_HIGH_SKIP_CUBE": f"no unseen cube skips {HIGH_SKIP:.2f} of its dots, so the gain is not tested: it rests on "
                             "finding 100's two cubes; the fix costs neither precision nor merge-penalized ERL here",
    }[v["decision"]]  # fmt: skip
    if v["prediction_P1"] is False:
        head += (
            "; coverage moves by more than 1% on a cube that skips under 2% of its dots"
        )
    return head


def status(smoke_ok: bool | None, failed: list, v: dict) -> str:
    if smoke_ok is False:
        return "SMOKE_FAILED"
    if smoke_ok is None or failed or v["prediction_P2"] is None:
        return "INCOMPLETE"
    return "OK" if v["manipulation_ok"] else "MANIPULATION_FAILED"


def villa_commit(work: Path) -> str | None:
    m = re.findall(r"^CHAIN_START repo \S+ villa (\w+)", (work / "chain.log").read_text(), re.M)  # fmt: skip
    return m[0] if len(set(m)) == 1 else None


def cmd_score(work: Path, out_path: Path) -> int:
    if str(f91.SG / "src") not in sys.path:
        sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing

    if SCORING_VERSION != 3:
        raise SystemExit(f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}")  # fmt: skip
    smoke = json.loads((work / "smoke.json").read_text())["identical"] if (work / "smoke.json").exists() else None  # fmt: skip
    rows: dict = {s: {} for s in SIDES}
    rows4: dict = {s: {} for s in SIDES}
    records: dict = {s: {} for s in SIDES}
    fibers: dict = {}
    failed = []
    for s in SIDES:
        for c in CUBES:
            run = work / s / c
            if not done(work, s, c):
                failed.append(f"{s}/{c}")
                continue
            fibers[s, c] = rr.tile_fibers(run)
            lab = cc.labels_of_fibers(fibers[s, c], MARGIN, size_of(c))
            gt = ground_truth(c)
            r = {t: score_tracing(gt, lab, tolerance=t).as_row() for t in TOLS}
            rows[s][c], rows4[s][c], records[s][c] = r[2.0], r[4.0], counts(run)
            print(s, c, f"coverage {r[2.0]['coverage']:.3f}", flush=True)
    v = verdict(rows, records)
    out = {
        "registration": "docs/preregistration/2026-11-02_seed_heading_confirmation.md",
        "status": status(smoke, failed, v),
        "villa": villa_commit(work),
        "smoke_cube": SMOKE,
        "smoke_identical": smoke,
        "failed": failed,
        "presence_held_out": list(PRESENCE_HELD_OUT),
        "before_identical_to_after": {c: rr.same_fibers(fibers["before", c], fibers["after", c])
                                      for c in CUBES if ("before", c) in fibers and ("after", c) in fibers},
        "rows_tol2": rows,
        "rows_tol4": rows4,
        "records": records,
        "scoring_version": SCORING_VERSION,
        "verdict": v,
    }  # fmt: skip
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {out['status']}; reading {v['reading']}; wrote {out_path}")
    return 0 if out["status"] == "OK" else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "presence", "smoke", "done", "score"):
        p = sub.add_parser(name)
        p.add_argument("--work", type=Path, required=True)
        if name == "presence":
            p.add_argument("--device", choices=("cuda", "cpu"), required=True)
        if name == "done":
            p.add_argument("--side", choices=SIDES, required=True)
            p.add_argument("--cube", choices=CUBES, required=True)
        if name == "score":
            p.add_argument("--out", type=Path, default=Path("reports/seed_heading_confirmation.json"))  # fmt: skip
    a = ap.parse_args(argv)
    if a.cmd == "done":
        return 0 if done(a.work, a.side, a.cube) else 1
    if a.cmd in ("fetch", "presence"):
        got = fetch(a.work) if a.cmd == "fetch" else presence(a.work, a.device)
        key = "core_equals_dataset004" if a.cmd == "fetch" else "core_equals_level"
        ok = len(got) == len(CUBES) and all(r[key] for r in got.values())
        (a.work / ("prepared.json" if a.cmd == "fetch" else "presence.json")).write_text(json.dumps(got, indent=1) + "\n")  # fmt: skip
        return 0 if ok else 1
    if a.cmd == "smoke":
        same = rr.same_fibers(
            rr.tile_fibers(a.work / "smoke" / SMOKE), rr.tile_fibers(SMOKE_REFERENCE)
        )
        (a.work / "smoke.json").write_text(
            json.dumps({"cube": SMOKE, "identical": same}) + "\n"
        )
        print("SMOKE_OK" if same else "SMOKE_FAILED")
        return 0 if same else 1
    return cmd_score(a.work, a.out)


if __name__ == "__main__":
    sys.exit(main())
