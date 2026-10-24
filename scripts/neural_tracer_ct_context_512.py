"""docs/preregistration/2026-10-24_neural_tracer_ct_context_512.md -- villa's neural fiber tracer on the eleven 512³
cubes with real CT around each cube, its box still the cube.

Finding 97's method (scripts/neural_tracer_ct_context.py, left as it ran) at 512³. Each cube's CT is padded by MARGIN
voxels of the scan it was cut from, converted as villa's fibers-dataset generator made the cube (/ 257, clipped,
truncated), and its core must equal finding 85's array exactly:
* Scroll 5 from its raw zarr (PHerc 172, 20241024131838), as finding 97;
* Scroll 3 from its raw slices (PHerc332, 20231117143551), by byte range (scripts/raw_tiff_region.py).
The presence is finding 91's own level, placed in the padded frame with zeros outside the cube. The box is the cube, at
trace-grid offset MARGIN / 2; at 256 trace-grid voxels it is one tile, as in finding 91. The two sets, S5_CUBES (in
sample) and S3_CUBES (held out), are judged apart by the same predictions.

  fetch     download, write CT/<cube>.zarr/0 (zarr v2 uint8) and check its core; resumable, cached in CACHE
  presence  write PRESENCE/<cube>_presence.zarr/1 from finding 91's level, and check its core
  smoke     finding 91's own command, re-run on SMOKE (a 512³ cube), must reproduce its .afv point for point
  score     score each padded run in the cube's frame at tolerances 2 and 4, beside finding 91's and finding 94's rows;
            the run records; the registered predictions and decision rule. Writes reports/neural_tracer_ct_context_512.json.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_ct_context as cc  # noqa: E402
import raw_tiff_region  # noqa: E402

f91, f96 = cc.f91, cc.f96
PEN, COV = cc.PEN, cc.COV
S5_CUBES = [
    "s5_06494_01994_03994_512",
    "s5_06994_00994_04994_512",
    "s5_07994_01994_05494_512",
]
S3_CUBES = [
    "s3_00994_00494_01994_512",
    "s3_00994_01994_00494_512",
    "s3_00994_02494_01494_512",
    "s3_01994_01494_00994_512",
    "s3_01994_01994_01494_512",
    "s3_02994_02494_01994_512",
    "s3_03494_01494_00494_512",
    "s3_04494_00994_01494_512",
]
ALL_CUBES = S5_CUBES + S3_CUBES  # the Scroll-5 cubes run first
SETS = {"scroll5": S5_CUBES, "scroll3": S3_CUBES}
IN_SAMPLE = S5_CUBES
SIZE = 512
MARGIN = cc.MARGIN
S3_SOURCE = raw_tiff_region.VOLUMES["s3"]["url"]
SMOKE = "s5_06494_01994_03994_512"
T, G, TOLS = cc.T, cc.G, cc.TOLS
# P1: below finding 91's share on every cube, and below IN_SAMPLE_BELOW on the in-sample ones
IN_SAMPLE_BELOW = 0.05
COVERAGE_FACTOR = 1.15  # P2: the median within each set, with a rise on every cube
# P4: below P4_BELOW on at least P4_AT_LEAST of the eight Scroll-3 cubes
P4_BELOW, P4_AT_LEAST = 0.10, 6


def box_grid() -> tuple[int, int]:
    return cc.box_grid(MARGIN, SIZE)


def core(volume: np.ndarray) -> np.ndarray:
    return cc.core(volume, MARGIN, SIZE)


def to_uint8(raw: np.ndarray, slab: int = 64) -> np.ndarray:
    """cc.to_uint8 a slab at a time: the same voxels, without float64 copies of a whole 768³ region (about 3.6 GB
    each) beside the loop."""
    out = np.empty(raw.shape, np.uint8)
    for i in range(0, raw.shape[0], slab):
        out[i : i + slab] = cc.to_uint8(raw[i : i + slab])
    return out


def read_padded(
    cube: str, cache: Path, get=cc._get, get_ranges=raw_tiff_region._get_ranges
) -> np.ndarray:
    """The cube's padded region of the raw uint16 scan it was cut from."""
    lo, hi = cc.padded_bounds(cube)
    if cube.startswith("s5_"):
        return cc.read_region(lo, hi, cache, get=get)
    if cube.startswith("s3_"):
        return raw_tiff_region.read_region("s3", lo, hi, cache, get_ranges)
    raise ValueError(f"{cube}: not one of this registration's scrolls")


def fetch(
    work: Path,
    cubes=ALL_CUBES,
    get=cc._get,
    cache: Path | None = None,
    get_ranges=raw_tiff_region._get_ranges,
) -> dict:
    import zarr

    out = {}
    for cube in cubes:
        dst = work / "ct" / f"{cube}.zarr"
        ref = G / "zarr" / f"{cube}.zarr"
        if not dst.exists():
            padded = to_uint8(
                read_padded(cube, (cache or work / "cache") / cube, get, get_ranges)
            )
            if not np.array_equal(core(padded), zarr.open(str(ref), mode="r")[...]):
                raise SystemExit(
                    f"{cube}: the padded CT's core differs from finding 85's array"
                )
            cc._write_array(dst, "0", padded, (128, 128, 128))
        arr = zarr.open(str(dst / "0"), mode="r")
        ok = bool(np.array_equal(core(arr[...]), zarr.open(str(ref), mode="r")[...]))
        out[cube] = {"shape": list(arr.shape), "core_equals_finding_85": ok}
        print(cube, out[cube], flush=True)
    return out


def presence(work: Path, cubes=ALL_CUBES) -> dict:
    import zarr

    lo, hi = box_grid()
    out = {}
    for cube in cubes:
        src = zarr.open(str(T / "presence" / f"{cube}_presence.zarr" / "1"), mode="r")
        dst = work / "presence" / f"{cube}_presence.zarr"
        if not dst.exists():
            level = np.zeros(((SIZE + 2 * MARGIN) // 2,) * 3, np.uint8)
            level[lo:hi, lo:hi, lo:hi] = src[...]
            cc._write_array(dst, "1", level, src.chunks, src.compressor)
        got = zarr.open(str(dst / "1"), mode="r")[...]
        ok = bool(
            np.array_equal(got[lo:hi, lo:hi, lo:hi], src[...])
            and not got.sum() - got[lo:hi, lo:hi, lo:hi].sum()
        )
        out[cube] = {"shape": list(got.shape), "core_equals_finding_91": ok}
        print(cube, out[cube], flush=True)
    return out


def run_record(run: Path) -> dict:
    """tiles.jsonl counts and the closest traced seed to a face of the cube (trace-grid voxels)."""
    tiles = [
        json.loads(line)
        for line in (run / "tiles.jsonl").read_text().splitlines()
        if line.strip()
    ]
    keys = ("dots", "owned_dots", "no_heading", "traced", "fibers", "traced_vox", "kept_vox")  # fmt: skip
    out = {k: int(sum(t.get(k, 0) for t in tiles)) for k in keys}
    out["seconds"] = float(sum(t.get("seconds", 0.0) for t in tiles))
    seeds = np.concatenate(
        [np.load(p)["seed"].reshape(-1, 3) for p in sorted((run / "tiles").glob("*.npz")) if not p.name.endswith(".partial.npz")]
    )  # fmt: skip
    lo, hi = box_grid()
    local = seeds - lo
    out["min_seed_face_distance_grid"] = float(
        np.minimum(local, (hi - lo) - local).min()
    )
    out["no_heading_share"] = out["no_heading"] / out["dots"] if out["dots"] else None
    return out


def labels_in_cube(afv: Path) -> np.ndarray:
    return cc.labels_in_cube(afv, MARGIN, SIZE)


def verdict(
    cubes,
    rows: dict,
    rows4: dict,
    f91_rows: dict,
    f91_records: dict,
    records: dict,
    ours2: dict,
    ours4: dict,
) -> dict:
    """One set. rows / f91_rows / ours2: cube -> row at tolerance 2; rows4 / ours4 at tolerance 4; records and
    f91_records: cube -> run counts (finding 96's for finding 91's runs)."""
    want = list(cubes)
    cubes = [c for c in want if c in rows and c in records]
    out: dict = {"scored": len(cubes)}
    if len(cubes) < len(want):
        out.update(prediction_P1=None, prediction_P2=None, prediction_P3=None, prediction_P4=None, reading=None)  # fmt: skip
        return out
    if zero := [
        c for c in cubes if f91_rows[c][COV] <= 0 or not f91_records[c]["dots"]
    ]:
        raise ValueError(f"no ratio over a coverage or a seed count of 0: {zero}")
    nh = {c: records[c]["no_heading_share"] for c in cubes}
    nh91 = {c: f91_records[c]["no_heading"] / f91_records[c]["dots"] for c in cubes}
    factor = {c: rows[c][COV] / f91_rows[c][COV] for c in cubes}
    leads2 = {c: rows[c][PEN] > ours2[c][PEN] for c in cubes}
    leads4 = {c: rows4[c][PEN] > ours4[c][PEN] for c in cubes}
    out.update(
        no_heading_share=nh,
        finding_91_no_heading_share=nh91,
        coverage_factor=factor,
        median_coverage_factor=statistics.median(factor.values()),
        leads_tol2=leads2,
        leads_tol4=leads4,
        pred_over_gt={c: rows[c]["pred_length"] / rows[c]["gt_length"] for c in cubes},
        manipulation_seed_inside_19=any(
            records[c]["min_seed_face_distance_grid"] < 19 for c in cubes
        ),
    )
    out["prediction_P1"] = all(nh[c] < nh91[c] for c in cubes) and all(
        nh[c] < IN_SAMPLE_BELOW for c in cubes if c in IN_SAMPLE
    )
    out["prediction_P2"] = (
        all(v > 1 for v in factor.values())
        and out["median_coverage_factor"] >= COVERAGE_FACTOR
    )
    # finding 91's ranking at tolerance 2: ahead on Scroll 3, behind on Scroll 5; ahead on all eleven at tolerance 4
    out["prediction_P3"] = all(leads4.values()) and all(
        leads2[c] == c.startswith("s3_") for c in cubes
    )
    s3 = [c for c in cubes if c.startswith("s3_")]
    out["prediction_P4"] = (
        sum(nh[c] < P4_BELOW for c in s3) >= P4_AT_LEAST if s3 else None
    )
    if not out["manipulation_seed_inside_19"]:
        out["reading"] = (
            "manipulation failed: no seed came closer to a face than finding 91's rule allowed"
        )
    elif out["prediction_P1"] and out["prediction_P2"]:
        out["reading"] = ("on the 512³ cubes too the cube-only protocol held it back, by less: with real CT around "
                          "the cube it drops fewer seeds and covers more")  # fmt: skip
    elif out["prediction_P1"]:
        out["reading"] = (
            "the rule binds, but on the 512³ cubes the scan around the cube adds little coverage"
        )
    else:
        out["reading"] = ("with CT around the cube it still drops as many seeds: the window rule is not the main "
                          "reason on the 512³ cubes")  # fmt: skip
    return out


def outcome(
    cubes,
    identity: dict,
    smoke_ok: bool | None,
    rows,
    rows4,
    f91_rows,
    f91_records,
    records,
    ours2,
    ours4,
):
    if smoke_ok is False:
        return "SMOKE_FAILED", None
    if any(identity.get(c) for c in cubes):
        return "IDENTITY_FAILED", None
    v = verdict(cubes, rows, rows4, f91_rows, f91_records, records, ours2, ours4)
    if v["prediction_P1"] is None:
        return "INCOMPLETE", v
    return ("MANIPULATION_FAILED" if not v["manipulation_seed_inside_19"] else "OK"), v


def cmd_score(work: Path, out_path: Path) -> int:
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    rep = json.loads(Path("reports/neural_tracer_entrant.json").read_text())
    t94 = json.loads(Path("reports/tolerance4_rescore.json").read_text())
    prep = json.loads((work / "prepared.json").read_text())
    identity = {c: [k for k in ("ct", "presence") if not prep[k][c][f"core_equals_finding_{85 if k == 'ct' else 91}"]]
                for c in ALL_CUBES}  # fmt: skip
    smoke = (
        json.loads((work / "smoke.json").read_text())["identical"]
        if (work / "smoke.json").exists()
        else None
    )
    rows: dict = {}
    rows4: dict = {}
    records: dict = {}
    failed = []
    for c in ALL_CUBES:
        run = work / "neural" / c
        if not (run / "fibers.afv").exists():
            failed.append(c)
            continue
        skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
        lab = labels_in_cube(run / "fibers.afv")
        r = {t: score_tracing(skel, lab, tolerance=t).as_row() for t in TOLS}
        rows[c], rows4[c], records[c] = r[2.0], r[4.0], run_record(run)
    f91_rows = {c: rep["neural_rows"][c] for c in ALL_CUBES}
    f91_records = {c: f96.run_counts(c) for c in ALL_CUBES}
    ours2 = {c: rep["comparators"][c]["tracer"] for c in ALL_CUBES}
    ours4 = {c: t94["rows_tracer"][c] for c in ALL_CUBES}
    out: dict = {
        "margin_ct_voxels": MARGIN,
        "box_grid": list(box_grid()),
        "source_scroll5": cc.SOURCE,
        "source_scroll3": S3_SOURCE,
        "identity_problems": {c: p for c, p in identity.items() if p},
        "smoke_cube": SMOKE,
        "smoke_identical": smoke,
        "failed": failed,
        "rows_tol2": rows,
        "rows_tol4": rows4,
        "finding_91_rows_tol2": f91_rows,
        "finding_94_rows_tol4": {c: t94["rows_neural"][c] for c in ALL_CUBES},
        "our_tracer_tol2": ours2,
        "our_tracer_tol4": ours4,
        "records": records,
        "finding_96_records": f91_records,
    }
    statuses = {}
    for name, cubes in SETS.items():
        status, v = outcome(cubes, identity, smoke, rows, rows4, f91_rows, f91_records, records, ours2, ours4)  # fmt: skip
        statuses[name] = status
        out[f"status_{name}"] = status
        out[name] = v
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {statuses}; wrote {out_path}")
    return 0 if all(s == "OK" for s in statuses.values()) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "presence", "smoke", "score"):
        p = sub.add_parser(name)
        p.add_argument("--work", type=Path, required=True)
        if name == "score":
            p.add_argument(
                "--out",
                type=Path,
                default=Path("reports/neural_tracer_ct_context_512.json"),
            )
    args = ap.parse_args(argv)
    if args.cmd in ("fetch", "presence"):
        res = fetch(args.work) if args.cmd == "fetch" else presence(args.work)
        prep_path = args.work / "prepared.json"
        prep = json.loads(prep_path.read_text()) if prep_path.exists() else {}
        prep["ct" if args.cmd == "fetch" else "presence"] = res
        prep_path.write_text(json.dumps(prep, indent=1) + "\n")
        key = (
            "core_equals_finding_85"
            if args.cmd == "fetch"
            else "core_equals_finding_91"
        )
        return 0 if all(r[key] for r in res.values()) else 1
    if args.cmd == "smoke":
        same = cc.f96_afv_identical(
            args.work / "smoke" / SMOKE / "fibers.afv", T / "run" / SMOKE / "fibers.afv"
        )
        (args.work / "smoke.json").write_text(
            json.dumps({"cube": SMOKE, "identical": same}) + "\n"
        )
        print("SMOKE_OK" if same else "SMOKE_FAILED")
        return 0 if same else 1
    return cmd_score(args.work, args.out)


if __name__ == "__main__":
    sys.exit(main())
