"""The seam trim at villa's default block size: one 1024³ zone of Scroll 3 in 8 blocks of 512 (finding 107's run).

Finding 106 measured the trim on 512³ cubes in blocks of 256, because a hand-traced cube allows no smaller face count.
This runs villa's generator as VC3D would on a zone larger than its default block: a 1024³ zone of the public Scroll-3
scan at --block-size 512 (the default), each block predicted from its own crop with the 32-voxel margin. The zone is
centred on a held-out hand-traced cube, so its three inner faces cross the cube at cube coordinate 256 on each axis.

Each zone runs with villa main's stitching (`main`) and with the amended patch (`patched`), whose `trim_cut_ends` keeps
the ends at the border of the box the zone's blocks read; that is the patch the villa PR proposes. The prediction,
spline and stitching code is the #1934 head, as in finding 106 (`afv_generator_block_seams.identity()`).

Per variant: over the whole zone (no ground truth needed) the fibers written, their length and the share of it within
1.5 voxels of a different fiber of the same family; inside the cube, ScrollGT `score_tracing` at τ = 2 and 4 of the
written fibers clipped to the cube, and the same duplicated share counted on the cube's samples.

Usage (the generator's venv; CPU unless --device says otherwise):
  python -I scripts/afv_generator_default_zone.py fetch --out CONTEXT.npy --cache DIR
  python -I scripts/afv_generator_default_zone.py run --context CONTEXT.npy --work DIR --pr PR_SRC --villa VILLA \
      --main REV --patched-stitch PATH [--device cpu]
  python -I scripts/afv_generator_default_zone.py verdict --work DIR --out RECORD
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_generator_block_seams as bs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD_106 = ROOT / "reports/afv_generator_block_seams.json"
CUBE = "s3_04494_00994_01494_512"  # the held-out cube with the lower of finding 106's two middle gains at τ = 4
SIZE = 512  # the cube's side
ZONE = 1024
BLOCK = 512  # villa's default --block-size
MARGIN = 32  # villa's BLOCK_MARGIN
# the scan read around the cube: the zone and its blocks' margin
PAD = (ZONE - SIZE) // 2 + MARGIN
SIDE = SIZE + 2 * PAD
# the amended patch's stitch.py (villa 7e6b82164 + repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch)
PATCHED_STITCH_SHA256 = (
    "362b78b12b2abf1b887f173cf658a6480692bc4a37e7e20cb81ff1ca85be0a6a"
)
CONTEXT_CT = bs.SG / "tools/context_ct.py"


def lower_middle_cube(record: dict) -> str:
    """The held-out cube with the lower of the two middle arm-real gains at τ = 4 (the eight's median is their mean)."""
    g = {c: bs.gain(record["cubes"][c]["rows"], "real", "tol4") for c in bs.HELD_OUT}
    return sorted(bs.HELD_OUT, key=g.get)[len(g) // 2 - 1]


def zone_box() -> tuple[np.ndarray, np.ndarray]:
    """The zone's origin and size, x, y, z, in the fetched array's voxels."""
    return np.full(3, MARGIN), np.full(3, ZONE)


def read_box(shape_xyz) -> tuple[np.ndarray, np.ndarray]:
    """The box the zone's blocks read together (cli: zone ± BLOCK_MARGIN, clipped to the volume)."""
    origin, size = zone_box()
    return np.maximum(origin - MARGIN, 0), np.minimum(origin + size + MARGIN, shape_xyz)


def block_crops(
    cli, shape_xyz
) -> list[tuple[list[int], list[int], np.ndarray, np.ndarray]]:
    """(origin, size, low, high) per block, as cli.generate reads them."""
    origin, size = zone_box()
    out = []
    for o, s in cli.zone_blocks(origin.tolist(), size.tolist(), BLOCK):
        low = np.maximum(np.asarray(o) - MARGIN, 0)
        high = np.minimum(np.asarray(o) + np.asarray(s) + MARGIN, shape_xyz)
        out.append((o, s, low, high))
    return out


def duplicated_share_in(
    fibers: list[np.ndarray], families: list[int], lo_xyz, hi_xyz
) -> float:
    """bs.duplicated_share, counting only the samples inside [lo, hi) (x, y, z); neighbours may lie anywhere."""
    from scipy.spatial import cKDTree

    lo, hi = np.asarray(lo_xyz, float), np.asarray(hi_xyz, float)
    dup = total = 0
    for fam in set(families):
        idx = [i for i, f in enumerate(families) if f == fam]
        pts = [bs.dense(fibers[i])[0] for i in idx]
        allp = np.concatenate(pts)
        own = np.concatenate([np.full(len(p), k) for k, p in enumerate(pts)])
        tree = cKDTree(allp)
        for k, p in enumerate(pts):
            p = p[np.all((p >= lo) & (p < hi), axis=1)]
            if len(p):
                dup += sum(
                    bool(np.any(own[n] != k))
                    for n in tree.query_ball_point(p, bs.DUPLICATE)
                )
                total += len(p)
    return dup / total if total else 0.0


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(args) -> None:
    import zarr

    spec = importlib.util.spec_from_file_location("context_ct", CONTEXT_CT)
    cc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cc)
    t = time.time()
    padded = cc.to_uint8(cc.read_padded(CUBE, args.cache / CUBE, PAD))
    own = np.asarray(zarr.open(str(bs.CT / f"{CUBE}.zarr"), mode="r")[:])
    assert padded.shape == (SIDE,) * 3, padded.shape
    if not np.array_equal(cc.core(padded, PAD), own):
        raise SystemExit("the fetched scan's core is not the cube's own CT")
    np.save(args.out, padded)
    print(f"wrote {args.out}: {padded.shape} uint8, the cube at [{PAD}, {PAD + SIZE}), its core equal to the cube's CT; "
          f"{time.time() - t:.0f} s", flush=True)  # fmt: skip


def run(args) -> None:
    import torch
    import zarr

    trim_cut_ends, cut_end = bs.load(args.pr, args.patched_stitch)
    import afv_to_labels
    from scrollgt.fibers.eval_trace import score_tracing
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack, clean
    from vesuvius.afv_spline_generator.extend.stitch import Stitcher
    from vesuvius.afv_spline_generator.predict import predict_fibers
    from vesuvius.afv_spline_generator.splines import extract_splines, threshold_to_u8

    work = args.work
    work.mkdir(parents=True, exist_ok=True)
    problems = bs.identity(args.pr, args.villa, args.main, args.patched_stitch)
    if (
        hashlib.sha256(args.patched_stitch.read_bytes()).hexdigest()
        != PATCHED_STITCH_SHA256
    ):
        problems.append("the patched stitch.py is not the amended patch's")
    ct = np.load(args.context, mmap_mode="r")
    own = np.asarray(zarr.open(str(bs.CT / f"{CUBE}.zarr"), mode="r")[:])
    if ct.shape != (SIDE,) * 3 or not np.array_equal(
        ct[PAD : PAD + SIZE, PAD : PAD + SIZE, PAD : PAD + SIZE], own
    ):
        problems.append("the context's core is not the cube's own CT")
    shape_xyz = np.asarray(ct.shape[::-1])
    crops = block_crops(cli, shape_xyz)
    if len(crops) != 8 or any(
        not np.array_equal(h - lo, np.full(3, BLOCK + 2 * MARGIN))
        for _, _, lo, h in crops
    ):
        problems.append("the zone is not 8 blocks each read as 576³")
    reach_low, reach_high = read_box(shape_xyz)
    device = torch.device(args.device)
    folder, provenance = cli.resolve_model(cli.DEFAULT_MODEL)
    if provenance.get("revision", bs.REVISION) != bs.REVISION:
        problems.append(
            f"model revision {provenance.get('revision')} is not {bs.REVISION}"
        )
    # A failed check means no verdict whatever the run gives: stop before the fields are predicted.
    if problems:
        raise SystemExit(f"gate failed: {problems}")
    network, patch = cli.load_network(folder, device)
    threshold = threshold_to_u8(bs.THRESHOLD)
    timing = {}

    def predicted(i: int, sl) -> np.ndarray:
        f = work / f"prob_block_{i}.npy"
        if f.exists():
            return np.load(f)
        t = time.time()
        p = predict_fibers(
            network, np.asarray(ct[sl]), patch, device=device, mirror=False
        )
        timing[f"block_{i}"] = round(time.time() - t, 1)
        tmp = f.with_suffix(".part.npy")
        np.save(tmp, p)
        tmp.rename(f)
        print(f"block {i} predicted in {timing[f'block_{i}']} s", flush=True)
        return p

    def generate(variant: str) -> list[dict]:
        black = ExteriorBlack(reach_low, reach_high)
        with tempfile.TemporaryDirectory(prefix="afv-stitch-") as scratch:
            st = Stitcher(scratch)
            try:
                for i, (origin, size, low, high) in enumerate(crops):
                    sl = tuple(
                        slice(int(a), int(b))
                        for a, b in zip(low[::-1], high[::-1], strict=True)
                    )
                    black.add(np.asarray(ct[sl]), low)
                    traces = extract_splines(predicted(i, sl), threshold)
                    if variant == "patched":
                        traces = trim_cut_ends(
                            traces,
                            low[::-1],
                            high[::-1],
                            reach_low[::-1],
                            reach_high[::-1],
                        )
                    st.add_block(f"block-{i}", low.tolist(), (high - low).tolist(), traces,
                                 (np.asarray(origin), np.asarray(origin) + np.asarray(size)))  # fmt: skip
                traces = st.stitched()
            finally:
                st.close()
        return clean(traces, bs.MAX_JOIN_ANGLE, bs.MIN_LENGTH, black, bs.BLACK_DISTANCE)

    skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{CUBE}")
    lo, hi = np.full(3, PAD), np.full(3, PAD + SIZE)
    out = {"cube": CUBE, "zone": ZONE, "block": BLOCK, "pad": PAD, "cut_end": cut_end, "identity_problems": problems,
           "context_sha256": file_sha256(args.context), "rows": {}}  # fmt: skip
    for variant in bs.VARIANTS:
        traces = generate(variant)
        fibers = [np.asarray(t["points"], np.float64) for t in traces]
        families = [int(t["family"]) for t in traces]
        np.savez(work / f"{variant}_fibers.npz", points=np.concatenate(fibers),
                 offsets=np.r_[0, np.cumsum([len(f) for f in fibers])], family=np.array(families))  # fmt: skip
        labels = afv_to_labels.rasterize(
            {k: afv_to_labels.to_cube_zyx(v, (PAD,) * 3) for k, v in enumerate(fibers)},
            (SIZE,) * 3,
        )
        inside = [bs.dense(f)[0] for f in fibers]
        inside = [p[np.all((p >= lo) & (p < hi), axis=1)] for p in inside]
        row = {
            "zone": {
                "written": len(fibers),
                "length": round(float(sum(bs.dense(f)[1][-1] for f in fibers)), 1),
                "duplicated_share": round(bs.duplicated_share(fibers, families), 4),
            },
            "cube": {
                "written_inside": sum(len(p) > 0 for p in inside),
                "duplicated_share": round(
                    duplicated_share_in(fibers, families, lo, hi), 4
                ),
                **{
                    f"tol{int(t)}": score_tracing(skel, labels, tolerance=t).as_row()
                    for t in bs.TOLS
                },
            },
        }
        out["rows"][variant] = row
        z, c = row["zone"], row["cube"]
        print(f"{variant:7s} zone written {z['written']} dup {z['duplicated_share']:.3f} | cube dup "
              f"{c['duplicated_share']:.3f} t2 {c['tol2']['erl_merge_penalized']} m{c['tol2']['merges']} "
              f"t4 {c['tol4']['erl_merge_penalized']} m{c['tol4']['merges']}", flush=True)  # fmt: skip
    out["patched_stitch_sha256"] = hashlib.sha256(
        args.patched_stitch.read_bytes()
    ).hexdigest()
    out["timing_s"] = timing
    out["settings"] = {"threshold": bs.THRESHOLD, "margin": cli.BLOCK_MARGIN, "mirror": False, "extend": False,
                       "max_join_angle": bs.MAX_JOIN_ANGLE, "min_length": bs.MIN_LENGTH,
                       "black_distance": bs.BLACK_DISTANCE, "model": cli.DEFAULT_MODEL, "revision": bs.REVISION,
                       "pr_head": bs.PR_HEAD, "villa_main": args.main, "device": args.device}  # fmt: skip
    (work / "result.json").write_text(json.dumps(out, indent=1))
    print(f"identity problems {problems or 'none'}", flush=True)


def verdict(r: dict) -> dict:
    """The registered decision rule, applied to one result."""
    m, p = r["rows"]["main"], r["rows"]["patched"]
    checks = {
        "P1_main_zone_duplicated_share": [m["zone"]["duplicated_share"], m["zone"]["duplicated_share"] >= 0.05],
        "P2_patched_over_main_duplicated": [
            round(p["zone"]["duplicated_share"] / m["zone"]["duplicated_share"], 4) if m["zone"]["duplicated_share"] else None,
            p["zone"]["duplicated_share"] <= 0.6 * m["zone"]["duplicated_share"],
        ],
        "P3_gain_tol4": [
            round(p["cube"]["tol4"]["erl_merge_penalized"] / m["cube"]["tol4"]["erl_merge_penalized"] - 1, 4),
            p["cube"]["tol4"]["erl_merge_penalized"] > m["cube"]["tol4"]["erl_merge_penalized"],
        ],
        "P4_merges_tol2": [
            [m["cube"]["tol2"]["merges"], p["cube"]["tol2"]["merges"]],
            p["cube"]["tol2"]["merges"] <= 1.05 * m["cube"]["tol2"]["merges"],
        ],
    }  # fmt: skip
    held = {k: v[1] for k, v in checks.items()}
    if r["identity_problems"]:
        decision = "NO_VERDICT"
    elif not held["P1_main_zone_duplicated_share"]:
        decision = "NO_DOUBLING_AT_DEFAULTS"
    elif not (held["P3_gain_tol4"] and held["P4_merges_tol2"]):
        decision = "COSTS_AT_DEFAULTS"
    elif not held["P2_patched_over_main_duplicated"]:
        decision = "PARTIAL"
    else:
        decision = "BITES_AT_DEFAULTS"
    return {"decision": decision, **checks}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--out", type=Path, required=True)
    f.add_argument("--cache", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--context", type=Path, required=True)
    r.add_argument("--work", type=Path, required=True)
    r.add_argument("--pr", type=Path, required=True)
    r.add_argument("--villa", type=Path, required=True)
    r.add_argument("--main", required=True)
    r.add_argument("--patched-stitch", type=Path, required=True)
    r.add_argument("--device", default="cpu")
    v = sub.add_parser("verdict")
    v.add_argument("--work", type=Path, required=True)
    v.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "fetch":
        fetch(args)
    elif args.cmd == "run":
        run(args)
    else:
        if args.out.exists():
            raise SystemExit(f"{args.out} exists: the record is written once")
        r = json.loads((args.work / "result.json").read_text())
        args.out.write_text(
            json.dumps({"verdict": verdict(r), "result": r}, indent=1) + "\n"
        )
        print(json.dumps(verdict(r), indent=1))


if __name__ == "__main__":
    main()
