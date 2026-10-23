"""docs/preregistration/2026-10-23_neural_tracer_ct_context.md -- villa's neural fiber tracer on the five Scroll-5
256³ cubes with real CT around each cube, its box still the cube.

Finding 96 (exploratory) found that the tracer drops any seed whose 77-voxel CT window crosses the edge of the CT it is
given, and that ScrollGT's protocol (finding 91) gave it the cube alone. Here each cube's CT is padded by MARGIN voxels
of the scan it was cut from. The source is Scroll 5's public raw volume (PHerc 172, 20241024131838, uint16), converted
as villa's fibers-dataset generator made the cube (/ 257, clipped, truncated). The padded array's core must equal
finding 85's array for the cube exactly. Everything else is finding 91's:
* the presence: finding 91's own level, placed in the padded frame with zeros outside the cube, as the tracer padded
  it before;
* the settings and the checkpoint;
* the box: the cube, at trace-grid offset MARGIN / 2.

MARGIN is 128 CT voxels, 64 trace-grid voxels: a multiple of the 64-voxel seed-plane spacing, so the cube's seed planes
stay where finding 91 had them.

  fetch     download the chunks, write CT/<cube>.zarr/0 (zarr v2 uint8, as finding 85 wrote its arrays) and check its
            core; resumable, chunks cached in CACHE
  presence  write PRESENCE/<cube>_presence.zarr/1 from finding 91's level, and check its core
  smoke     finding 91's identity smoke: its own command, re-run on SMOKE, must reproduce its .afv point for point
  score     score each padded run in the cube's frame at tolerances 2 and 4, beside finding 91's and finding 94's rows;
            the run records; the registered predictions and decision rule. Writes reports/neural_tracer_ct_context.json.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_boundary as f96  # noqa: E402

PEN, COV = f91.PEN, f91.COV
CUBES = [
    "s5_03997_01497_03997_256",
    "s5_07997_02997_05497_256",
    "s5_14997_01497_01497_256",
    "s5_13497_01497_02497_256",
    "s5_16997_03997_04497_256",
]
IN_SAMPLE = CUBES[:3]
SIZE = 256
MARGIN = 128  # CT voxels; MARGIN / 2 trace-grid voxels, a multiple of the 64-voxel seed-plane spacing
PLANE_SPACING = 64
SOURCE = "https://dl.ash2txt.org/full-scrolls/Scroll5/PHerc172.volpkg/volumes_zarr/20241024131838.zarr"
T = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer")
G = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen")
SMOKE = "s5_07997_02997_05497_256"
TOLS = (2.0, 4.0)
NO_HEADING_BELOW = 0.40  # P1, on every cube
# P2: the median, padded over finding 91, with a rise on every cube
COVERAGE_FACTOR = 1.3
PRED_OVER_GT = 0.83  # P3, on every in-sample cube: the lowest 512³ value in finding 96


def box_grid(margin: int = MARGIN, size: int = SIZE) -> tuple[int, int]:
    """The cube's box in the padded trace grid (grid scale 2): [lo, hi)."""
    if margin % (2 * PLANE_SPACING):
        raise ValueError(
            "the margin must keep the seed planes where finding 91 had them"
        )
    return margin // 2, (margin + size) // 2


def to_uint8(raw: np.ndarray) -> np.ndarray:
    """villa's fibers-dataset generator: np.clip(volume / 257, 0, 255).astype(np.uint8), from the uint16 scan."""
    return np.clip(raw.astype(np.float64) / 257, 0, 255).astype(np.uint8)


def chunk_ranges(lo, hi, chunk: int):
    return [
        range(a // chunk, (b - 1) // chunk + 1) for a, b in zip(lo, hi, strict=False)
    ]


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 (a fixed https URL)
        return r.read()


def read_region(lo, hi, cache: Path, source: str = SOURCE, get=_get) -> np.ndarray:
    """[lo, hi) (z, y, x) of the source's level 0, from its chunks (cached in CACHE as raw bytes)."""
    from numcodecs import get_codec

    meta = json.loads(get(f"{source}/0/.zarray"))
    c = meta["chunks"][0]
    if meta["chunks"] != [c] * 3 or meta.get("dimension_separator") != "/":
        raise ValueError(f"unexpected layout: {meta}")
    if any(a < 0 or b > s for a, b, s in zip(lo, hi, meta["shape"], strict=False)):
        raise ValueError(f"{lo}-{hi} leaves the volume {meta['shape']}")
    codec = get_codec(meta["compressor"])
    ks = chunk_ranges(lo, hi, c)
    base = np.array([k.start for k in ks]) * c
    buf = np.zeros(tuple(len(k) * c for k in ks), np.dtype(meta["dtype"]))
    cache.mkdir(parents=True, exist_ok=True)
    for i, kz in enumerate(ks[0]):
        for j, ky in enumerate(ks[1]):
            for k, kx in enumerate(ks[2]):
                f = cache / f"{kz}.{ky}.{kx}"
                if not f.exists():
                    tmp = f.with_suffix(".part")
                    tmp.write_bytes(get(f"{source}/0/{kz}/{ky}/{kx}"))
                    tmp.rename(f)
                a = np.frombuffer(codec.decode(f.read_bytes()), meta["dtype"]).reshape(
                    (c, c, c)
                )
                buf[i * c : (i + 1) * c, j * c : (j + 1) * c, k * c : (k + 1) * c] = a
    s = np.asarray(lo) - base
    e = s + (np.asarray(hi) - np.asarray(lo))
    return buf[s[0] : e[0], s[1] : e[1], s[2] : e[2]]


def padded_bounds(cube: str, margin: int = MARGIN):
    z, y, x, n = (int(v) for v in cube.split("_")[1:5])
    lo = (z - margin, y - margin, x - margin)
    return lo, tuple(v + n + 2 * margin for v in lo)


def core(volume: np.ndarray, margin: int = MARGIN, size: int = SIZE) -> np.ndarray:
    return volume[
        margin : margin + size, margin : margin + size, margin : margin + size
    ]


def _write_array(
    out: Path, level: str, data: np.ndarray, chunks, compressor=None
) -> None:
    """OUT/LEVEL as a zarr v2 uint8 array, built beside OUT and renamed; every chunk written."""
    import zarr
    from numcodecs import Blosc

    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix=f".{out.name}.building-", dir=out.parent))
    try:
        arr = zarr.open(str(build / level), mode="w-", shape=data.shape, chunks=chunks, dtype="u1",
                        compressor=compressor or Blosc(cname="lz4", clevel=5, shuffle=Blosc.SHUFFLE),
                        write_empty_chunks=True)  # fmt: skip
        arr[...] = data
        build.rename(out)
    except BaseException:
        shutil.rmtree(build, ignore_errors=True)
        raise


def fetch(work: Path, cubes=CUBES, get=_get, cache: Path | None = None) -> dict:
    import zarr

    out = {}
    for cube in cubes:
        dst = work / "ct" / f"{cube}.zarr"
        if not dst.exists():
            lo, hi = padded_bounds(cube)
            padded = to_uint8(
                read_region(lo, hi, (cache or work / "cache") / cube, get=get)
            )
            if not np.array_equal(
                core(padded), zarr.open(str(G / "zarr" / f"{cube}.zarr"), mode="r")[...]
            ):
                raise SystemExit(
                    f"{cube}: the padded CT's core differs from finding 85's array"
                )
            _write_array(dst, "0", padded, (128, 128, 128))
        arr = zarr.open(str(dst / "0"), mode="r")
        ok = bool(
            np.array_equal(
                core(arr[...]),
                zarr.open(str(G / "zarr" / f"{cube}.zarr"), mode="r")[...],
            )
        )
        out[cube] = {"shape": list(arr.shape), "core_equals_finding_85": ok}
        print(cube, out[cube], flush=True)
    return out


def presence(work: Path, cubes=CUBES) -> dict:
    import zarr

    lo, hi = box_grid()
    out = {}
    for cube in cubes:
        src = zarr.open(str(T / "presence" / f"{cube}_presence.zarr" / "1"), mode="r")
        dst = work / "presence" / f"{cube}_presence.zarr"
        if not dst.exists():
            level = np.zeros(((SIZE + 2 * MARGIN) // 2,) * 3, np.uint8)
            level[lo:hi, lo:hi, lo:hi] = src[...]
            _write_array(dst, "1", level, src.chunks, src.compressor)
        got = zarr.open(str(dst / "1"), mode="r")[...]
        ok = bool(
            np.array_equal(got[lo:hi, lo:hi, lo:hi], src[...])
            and not got.sum() - got[lo:hi, lo:hi, lo:hi].sum()
        )
        out[cube] = {"shape": list(got.shape), "core_equals_finding_91": ok}
        print(cube, out[cube], flush=True)
    return out


def run_record(run: Path, margin: int = MARGIN) -> dict:
    """tiles.jsonl counts and the closest traced seed to a face of the cube (trace-grid voxels)."""
    tiles = [
        json.loads(line)
        for line in (run / "tiles.jsonl").read_text().splitlines()
        if line.strip()
    ]
    keys = (
        "dots",
        "owned_dots",
        "no_heading",
        "traced",
        "fibers",
        "traced_vox",
        "kept_vox",
    )
    out = {k: int(sum(t.get(k, 0) for t in tiles)) for k in keys}
    seeds = np.concatenate(
        [np.load(p)["seed"].reshape(-1, 3) for p in sorted((run / "tiles").glob("*.npz")) if not p.name.endswith(".partial.npz")]
    )  # fmt: skip
    lo, hi = box_grid(margin)
    local = seeds - lo
    out["min_seed_face_distance_grid"] = float(
        np.minimum(local, (hi - lo) - local).min()
    )
    out["no_heading_share"] = out["no_heading"] / out["dots"] if out["dots"] else None
    return out


def labels_in_cube(afv: Path, margin: int = MARGIN, size: int = SIZE) -> np.ndarray:
    """The run's fibers (padded-frame voxels) shifted to the cube's frame and rasterised as finding 91 did."""
    fibers = {
        k: afv_to_labels.to_cube_zyx(v, (margin,) * 3)
        for k, v in afv_to_labels.read_afv(afv).items()
    }
    return afv_to_labels.rasterize(fibers, (size,) * 3)


def verdict(rows: dict, f91_rows: dict, records: dict) -> dict:
    """rows / f91_rows: cube -> row at tolerance 2; records: cube -> run_record."""
    cubes = [c for c in CUBES if c in rows and c in records]
    out: dict = {"scored": len(cubes)}
    if len(cubes) < len(CUBES):
        out.update(
            prediction_P1=None, prediction_P2=None, prediction_P3=None, reading=None
        )
        return out
    if zero := [c for c in cubes if f91_rows[c][COV] <= 0]:
        raise ValueError(f"no ratio over a coverage of 0: {zero}")
    nh = {c: records[c]["no_heading_share"] for c in cubes}
    factor = {c: rows[c][COV] / f91_rows[c][COV] for c in cubes}
    pred = {c: rows[c]["pred_length"] / rows[c]["gt_length"] for c in IN_SAMPLE}
    out.update(
        no_heading_share=nh,
        coverage_factor=factor,
        median_coverage_factor=statistics.median(factor.values()),
        pred_over_gt_in_sample=pred,
        manipulation_seed_inside_19=any(
            records[c]["min_seed_face_distance_grid"] < 19 for c in cubes
        ),
    )
    out["prediction_P1"] = all(v < NO_HEADING_BELOW for v in nh.values())
    out["prediction_P2"] = (
        all(v > 1 for v in factor.values())
        and out["median_coverage_factor"] >= COVERAGE_FACTOR
    )
    out["prediction_P3"] = all(v >= PRED_OVER_GT for v in pred.values())
    if not out["manipulation_seed_inside_19"]:
        out["reading"] = (
            "manipulation failed: no seed came closer to a face than finding 91's rule allowed"
        )
    elif out["prediction_P1"] and out["prediction_P2"]:
        out["reading"] = ("the cube-only protocol held the neural tracer back on these cubes: with real CT around the "
                          "cube it drops fewer seeds and covers more")  # fmt: skip
    elif out["prediction_P1"]:
        out["reading"] = (
            "the rule binds, but coverage did not rise as predicted: the gap has another cause too"
        )
    else:
        out["reading"] = (
            "with CT around the cube it still drops as many seeds: the window rule is not the main reason"
        )
    return out


def outcome(
    identity: dict, smoke_ok: bool | None, rows: dict, f91_rows: dict, records: dict
):
    if smoke_ok is False:
        return "SMOKE_FAILED", None
    if any(identity.values()):
        return "IDENTITY_FAILED", None
    v = verdict(rows, f91_rows, records)
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
                for c in CUBES}  # fmt: skip
    smoke = (
        json.loads((work / "smoke.json").read_text())["identical"]
        if (work / "smoke.json").exists()
        else None
    )
    rows: dict = {}
    rows4: dict = {}
    records: dict = {}
    failed = []
    for c in CUBES:
        run = work / "neural" / c
        if not (run / "fibers.afv").exists():
            failed.append(c)
            continue
        skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
        lab = labels_in_cube(run / "fibers.afv")
        r = {t: score_tracing(skel, lab, tolerance=t).as_row() for t in TOLS}
        rows[c], rows4[c], records[c] = r[2.0], r[4.0], run_record(run)
    f91_rows = {c: rep["neural_rows"][c] for c in CUBES}
    status, v = outcome(identity, smoke, rows, f91_rows, records)
    out = {
        "status": status,
        "margin_ct_voxels": MARGIN,
        "box_grid": list(box_grid()),
        "source": SOURCE,
        "identity_problems": {c: p for c, p in identity.items() if p},
        "smoke_identical": smoke,
        "failed": failed,
        "rows_tol2": rows,
        "rows_tol4": rows4,
        "finding_91_rows_tol2": f91_rows,
        "finding_94_rows_tol4": {c: t94["rows_neural"][c] for c in CUBES},
        "our_tracer_tol2": {c: rep["comparators"][c]["tracer"] for c in CUBES},
        "our_tracer_tol4": {c: t94["rows_tracer"][c] for c in CUBES},
        "records": records,
        "finding_96_records": {c: f96.run_counts(c) for c in CUBES},
    }
    if v is not None:
        out.update(v)
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {status}; wrote {out_path}")
    return 0 if status == "OK" else 1


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
                default=Path("reports/neural_tracer_ct_context.json"),
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
        same = f96_afv_identical(
            args.work / "smoke" / SMOKE / "fibers.afv", T / "run" / SMOKE / "fibers.afv"
        )
        (args.work / "smoke.json").write_text(
            json.dumps({"cube": SMOKE, "identical": same}) + "\n"
        )
        print("SMOKE_OK" if same else "SMOKE_FAILED")
        return 0 if same else 1
    return cmd_score(args.work, args.out)


def f96_afv_identical(a: Path, b: Path) -> bool:
    """The same fibers point for point, whatever their ids (finding 93's smoke comparison)."""

    def fibers(p):
        return sorted(
            np.ascontiguousarray(v, "<f8").tobytes()
            for v in afv_to_labels.read_afv(p).values()
        )

    return fibers(a) == fibers(b)


if __name__ == "__main__":
    sys.exit(main())
