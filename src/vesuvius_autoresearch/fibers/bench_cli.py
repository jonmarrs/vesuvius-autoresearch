"""Fiber tracing benchmark CLI: score any instance labelling against hand traces.

The point of this tool is that a fiber tracer cannot be ranked by coverage or
precision. Measured on a real cube, five different labellings -- the correct one,
one instance for everything, one instance per voxel, 50 random instances, and
connected components -- all scored **identical** coverage (0.960) and precision
(0.229), because those depend on the shared fiber mask rather than on the
labelling. Only expected run length and the merge count separate them.

So this scores connectivity, publishes anti-gaming floors next to any result, and
refuses to report a single headline number.

Typical use:

    # score your own instance labelling (int labels, 0 = background)
    python -m vesuvius_autoresearch.fibers.bench_cli score \\
        --instances my_pred.npy --cube s1_00497_01497_03997_256

    # reproduce the published floors on a cube
    python -m vesuvius_autoresearch.fibers.bench_cli floors \\
        --cube s1_00497_01497_03997_256

    # run our tracer end to end and score it
    python -m vesuvius_autoresearch.fibers.bench_cli trace \\
        --cube s1_00497_01497_03997_256 --model local_data/models/fiber_hz_vt

Ground truth is the public `fiber-skeletons` dataset
(dl.ash2txt.org/datasets/fiber-skeletons/). `fetch` downloads a cube.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.request

import numpy as np

DATA_URL = (
    "https://dl.ash2txt.org/datasets/fiber-skeletons/Dataset001_sk-fibers-20250124/"
)
DEFAULT_DATA = pathlib.Path("local_data/fiber_skeletons")
DEFAULT_TOL = 2.0

# The six full 256^3 cubes every published number (README, BASELINES.md,
# ScrollGT) draws from. No 128^3 sub-volume figure is carried downstream.
CUBES = [
    "s1_00497_01497_03997_256",
    "s1_00497_02497_02997_256",
    "s1_00997_02497_02997_256",
    "s1_08997_02997_02497_256",
    "s1_10997_02997_02997_256",
    "s5_03997_01497_03997_256",
]


def _load_cube(data_dir: pathlib.Path, cube: str):
    import tifffile

    from vesuvius_autoresearch.fibers.skeleton_io import Skeleton, load_cube_skeleton

    img = tifffile.imread(data_dir / f"{cube}_image.tif")
    full = load_cube_skeleton(data_dir, cube)
    gt = Skeleton(
        fibers=[f for f in full.fibers if f.in_bounds_mask(img.shape).sum() > 1],
        scale_um=full.scale_um,
        origin_zyx=full.origin_zyx,
    )
    return img, gt


def _fiber_prob(data_dir: pathlib.Path, cube: str, img, model_dir, patch: int):
    """Cached `fiber_hz_vt` probability for a cube."""
    from vesuvius_autoresearch.fibers.semantic import (
        fiber_probability,
        load_model,
        predict_volume,
    )

    cache = data_dir / f"{cube}_fiberprob.npy"
    if cache.exists():
        fp = np.load(cache)
        if fp.shape == img.shape:
            return fp.astype(float)
    model = load_model(model_dir)
    prob = predict_volume(model, img, patch_size=(patch, patch, patch))
    fp = fiber_probability(prob).astype(np.float32)
    np.save(cache, fp)
    return fp.astype(float)


def _print_rows(rows: dict[str, dict]) -> None:
    hdr = f"{'row':34s} {'ERL':>7s} {'ERLpen':>7s} {'cov':>6s} {'splits':>7s} {'merges':>7s} {'ninst':>7s}"
    print(hdr)
    print("-" * len(hdr))
    for name, r in rows.items():
        print(
            f"{name:34s} {r['erl']:7.2f} {r['erl_merge_penalized']:7.2f} "
            f"{r['coverage']:6.3f} {r['splits']:7d} {r['merges']:7d} "
            f"{r['n_pred_instances']:7d}"
        )


def cmd_fetch(args) -> int:
    out = pathlib.Path(args.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    import re

    nmls = [
        n
        for n in re.findall(
            r'href="([^"]+)"',
            urllib.request.urlopen(DATA_URL + "nml/", timeout=60).read().decode(),
        )
        if n.endswith(".nml")
    ]
    want = None
    if args.cube:
        m = args.cube.split("_")
        want = f"_{m[1]}z_{m[2]}y_{m[3]}x_{m[4]}_"
    for nm in nmls:
        if want and want not in nm:
            continue
        mm = __import__("re").match(
            r"fibers_(s\d)a?_(\d+)z_(\d+)y_(\d+)x_(\d+)_v\d+\.nml", nm
        )
        if not mm:
            continue
        s, z, y, x, sz = mm.groups()
        stem = f"{s}_{z}_{y}_{x}_{sz}"
        for rel, dst in [
            (f"nml/{nm}", f"{stem}.nml"),
            (f"imagesTr/{stem}_0000.tif", f"{stem}_image.tif"),
            (f"labelsTr/{stem}.tif", f"{stem}_semantic.tif"),
        ]:
            p = out / dst
            if p.exists() and p.stat().st_size > 0:
                continue
            t = time.time()
            urllib.request.urlretrieve(DATA_URL + rel, p)
            print(f"  {dst}  {p.stat().st_size / 1e6:.0f} MB  {time.time() - t:.0f}s")
    print(f"data in {out}")
    return 0


def _floor_rows(ev, gt, img, mask, tolerance: float) -> dict[str, dict]:
    """Oracle + all four anti-gaming floors for one cube, canonical row keys."""
    return {
        "oracle": ev.score_tracing(
            gt, ev.oracle_from_skeleton(gt, img.shape, 1.0), tolerance=tolerance
        ).as_row(),
        "floor_single_instance": ev.score_tracing(
            gt, ev.floor_single_instance(mask), tolerance=tolerance
        ).as_row(),
        "floor_connected_components": ev.score_tracing(
            gt, ev.floor_connected_components(mask), tolerance=tolerance
        ).as_row(),
        "floor_voxel_instances": ev.score_tracing(
            gt, ev.floor_voxel_instances(mask), tolerance=tolerance
        ).as_row(),
        "floor_random_instances": ev.score_tracing(
            gt, ev.floor_random_instances(mask, 50, 0), tolerance=tolerance
        ).as_row(),
    }


def _floors_all_cubes(args) -> int:
    """Run oracle + all four floors on every published cube, refreshing the
    all-cubes report. `tracer_strict_relink` (produced separately by `trace`)
    is carried over from any prior report at the same --json-out path rather
    than recomputed here, since this command only owns the floors."""
    from vesuvius_autoresearch.fibers import eval_trace as ev
    from vesuvius_autoresearch.fibers.semantic import FIBER_HZ_VT_REPO

    data_dir = pathlib.Path(args.data_dir)
    out_path = pathlib.Path(args.json_out) if args.json_out else None
    prior_cubes: dict = {}
    if out_path and out_path.exists():
        prior_cubes = json.loads(out_path.read_text()).get("cubes", {})

    report = {"tolerance": args.tolerance, "model": FIBER_HZ_VT_REPO, "cubes": {}}
    for cube in CUBES:
        t0 = time.time()
        img, gt = _load_cube(data_dir, cube)
        fp = _fiber_prob(data_dir, cube, img, args.model, args.patch)
        infer_s = round(time.time() - t0, 1)
        mask = fp >= args.mask_threshold

        rows = _floor_rows(ev, gt, img, mask, args.tolerance)
        prior_rows = prior_cubes.get(cube, {}).get("rows", {})
        if "tracer_strict_relink" in prior_rows:
            rows["tracer_strict_relink"] = prior_rows["tracer_strict_relink"]

        dt = time.time() - t0
        print(
            f"cube={cube}  gt_fibers={len(gt)}  tolerance={args.tolerance}  {dt:.0f}s"
        )
        _print_rows(rows)
        print()

        report["cubes"][cube] = {
            "shape": list(img.shape),
            "n_gt": len(gt),
            "infer_s": infer_s,
            "rows": rows,
        }

    if out_path:
        out_path.write_text(json.dumps(report, indent=1))
        print(f"report -> {out_path}")
    return 0


def cmd_floors(args) -> int:
    if args.all_cubes:
        return _floors_all_cubes(args)
    if not args.cube:
        print("ERROR: --cube is required unless --all-cubes is given", file=sys.stderr)
        return 2

    from vesuvius_autoresearch.fibers import eval_trace as ev

    data_dir = pathlib.Path(args.data_dir)
    img, gt = _load_cube(data_dir, args.cube)
    fp = _fiber_prob(data_dir, args.cube, img, args.model, args.patch)
    mask = fp >= args.mask_threshold

    rows = _floor_rows(ev, gt, img, mask, args.tolerance)
    print(f"cube={args.cube}  gt_fibers={len(gt)}  tolerance={args.tolerance}")
    _print_rows(rows)
    print(
        "\nNote: coverage is identical across floors because it depends on the "
        "mask, not the labelling. Rank on ERL and merges."
    )
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(rows, indent=1))
    return 0


def cmd_score(args) -> int:
    from vesuvius_autoresearch.fibers import eval_trace as ev

    data_dir = pathlib.Path(args.data_dir)
    img, gt = _load_cube(data_dir, args.cube)
    inst = np.load(args.instances)
    if inst.shape != img.shape:
        print(f"ERROR: instances {inst.shape} != cube {img.shape}", file=sys.stderr)
        return 2
    s = ev.score_tracing(gt, inst.astype(np.int32), tolerance=args.tolerance)
    row = s.as_row()
    print(f"cube={args.cube}  gt_fibers={len(gt)}  tolerance={args.tolerance}")
    _print_rows({pathlib.Path(args.instances).stem: row})
    if args.with_floors:
        fp = _fiber_prob(data_dir, args.cube, img, args.model, args.patch)
        mask = fp >= args.mask_threshold
        _print_rows(
            {
                "floor: connected components": ev.score_tracing(
                    gt, ev.floor_connected_components(mask), tolerance=args.tolerance
                ).as_row()
            }
        )
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(row, indent=1))
    return 0


def cmd_trace(args) -> int:
    from vesuvius_autoresearch.fibers import eval_trace as ev
    from vesuvius_autoresearch.fibers.detection import (
        detect_vesselness,
        fiber_direction,
        hessian,
    )
    from vesuvius_autoresearch.fibers.trace import (
        RelinkParams,
        TraceParams,
        relink_fragments,
        trace_fibers,
    )

    data_dir = pathlib.Path(args.data_dir)
    img, gt = _load_cube(data_dir, args.cube)
    fp = _fiber_prob(data_dir, args.cube, img, args.model, args.patch)

    # Orientation from the probability field, not raw CT: measured 5x coverage.
    J, _ = hessian(fp.copy(), gauss_sigma=2, sigma=3)
    dirs, valid = fiber_direction(J)
    ves = np.asarray(detect_vesselness(fp.copy(), gauss_sigma=1, sigma=2), dtype=float)
    ves = ves / max(float(ves.max()), 1e-9)

    t = time.time()
    res = trace_fibers(
        response=fp,
        seed_response=ves,
        directions=np.asarray(dirs),
        valid=np.asarray(valid),
        params=TraceParams(
            seed_percentile=args.seed_percentile,
            continue_threshold=args.continue_threshold,
            min_length=args.min_length,
            seed_stride=2,
            max_angle_deg=args.max_angle,
            claim_radius=args.claim_radius,
            tangent_window=args.tangent_window,
            max_skip_steps=args.max_skip_steps,
            seed_nms_radius=args.seed_nms_radius,
        ),
    )
    if args.relink:
        res = relink_fragments(
            res,
            RelinkParams(
                max_gap=args.relink_gap,
                max_link_angle_deg=args.relink_angle,
                max_tangent_angle_deg=args.relink_angle + 5,
            ),
        )
    inst = res.to_instances(radius=1.0)
    dt = time.time() - t

    rows = {
        "tracer": ev.score_tracing(gt, inst, tolerance=args.tolerance).as_row(),
        "floor: connected components": ev.score_tracing(
            gt,
            ev.floor_connected_components(fp >= args.mask_threshold),
            tolerance=args.tolerance,
        ).as_row(),
    }
    print(
        f"cube={args.cube}  gt_fibers={len(gt)}  tolerance={args.tolerance}  "
        f"trace={dt:.0f}s  stops={res.stop_counts}"
    )
    _print_rows(rows)
    if args.save_instances:
        np.save(args.save_instances, inst)
        print(f"instances -> {args.save_instances}")
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(rows, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Fiber tracing connectivity benchmark (ERL / splits / merges)."
    )
    ap.add_argument("--data-dir", default=str(DEFAULT_DATA))
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="download cube(s) from the public dataset")
    f.add_argument("--cube", help="stem, e.g. s1_00497_01497_03997_256; omit for all")
    f.set_defaults(func=cmd_fetch)

    for name, fn, helptext in [
        ("floors", cmd_floors, "reproduce the anti-gaming floors on a cube"),
        ("score", cmd_score, "score your own instance labelling (.npy)"),
        ("trace", cmd_trace, "run our tracer and score it"),
    ]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--cube", required=(name != "floors"))
        p.add_argument("--tolerance", type=float, default=DEFAULT_TOL)
        p.add_argument("--model", default="local_data/models/fiber_hz_vt")
        p.add_argument("--patch", type=int, default=128)
        p.add_argument("--mask-threshold", type=float, default=0.5)
        p.add_argument("--json-out")
        p.set_defaults(func=fn)
        if name == "floors":
            p.add_argument(
                "--all-cubes",
                action="store_true",
                help="run every published cube (ignores --cube) and refresh --json-out",
            )
        if name == "score":
            p.add_argument("--instances", required=True, help=".npy int labels")
            p.add_argument("--with-floors", action="store_true")
        if name == "trace":
            p.add_argument("--seed-percentile", type=float, default=85.0)
            p.add_argument("--continue-threshold", type=float, default=0.5)
            p.add_argument("--min-length", type=float, default=15.0)
            p.add_argument("--max-angle", type=float, default=25.0)
            p.add_argument("--claim-radius", type=float, default=3.5)
            p.add_argument(
                "--tangent-window",
                type=int,
                default=1,
                help="compare each step against the mean of the last N "
                "directions (1 = published baseline behaviour; 5 measured "
                "best on both dev cubes and is the frozen, shipped-"
                "improvement configuration -- see fiber_tracer_improvement.md)",
            )
            p.add_argument(
                "--max-skip-steps",
                type=int,
                default=0,
                help="coast through this many consecutive curvature "
                "rejections before stopping (0 = baseline; measured and "
                "REJECTED -- regressed merge-penalized ERL and raised merges "
                "in same-window isolation on both dev cubes, ships disabled)",
            )
            p.add_argument(
                "--seed-nms-radius",
                type=float,
                default=0.0,
                help="suppress seeds within this perpendicular distance "
                "of an accepted seed (0 = disabled; measured and REJECTED "
                "-- no distinguishable ERLpen change and a double regression "
                "on one dev cube, ships disabled)",
            )
            p.add_argument("--relink", action="store_true", default=True)
            p.add_argument("--no-relink", dest="relink", action="store_false")
            p.add_argument("--relink-gap", type=float, default=10.0)
            p.add_argument("--relink-angle", type=float, default=30.0)
            p.add_argument("--save-instances")

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
