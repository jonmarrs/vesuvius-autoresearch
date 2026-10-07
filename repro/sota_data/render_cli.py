"""Render a detector-ready surface volume from a segment's original.obj + a volume zarr.

Turns the open bucket's MESH-ONLY segments (obj + volume, no surface volume, no predictions)
into a 26-layer surface volume the ink detector can consume. Validated on Scroll 1 against a
released surface volume on two scrolls: Scroll 1 center-layer NCC ~0.59 (placement-correct,
resolution-limited comparison) and PHerc1667 NCC 0.78 (gate PASS; see
reports/detector/render_validation_1667.md). NO ink label is written — the render is label-free.

Examples
--------
Render a Scroll-3 (PHerc0332) mesh-only segment, auto-inferring the coordinate scale:

    uv run python -m repro.sota_data.render_cli \\
      --obj  s3://vesuvius-challenge-open-data/PHerc0332/segments/<seg>/mesh/intermediate/<seg>_original.obj \\
      --volume vesuvius-challenge-open-data/PHerc0332/volumes/<vol>.zarr \\
      --out local_data/rendered --frag-id myseg --scale auto

`--scale auto` renders a small probe at each candidate obj-level-div and keeps the one whose
surface shows real papyrus texture (teacher-free; the honest substitute for ground truth on
unread scrolls). Pass a number instead to fix it.
"""

import argparse
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.fragment import validate_fragment_id
from repro.sota_data.obj_geometry import fetch_obj as _fetch_obj_if_s3
from repro.sota_data.render_surface import (
    grid_shape,
    render_region,
    render_region_tifxyz,
    validate_level_sign,
    validate_region,
)

CANDIDATE_DIVS = [1.0, 2.0, 4.0]


def infer_scale(
    seg, obj, volume, out_root, y0, x0, size, level, sign, obj_grid_size=None
):
    """Render a probe at each candidate obj-level-div; return the div with the most
    papyrus-like surface structure (and reject empties)."""
    import glob

    import cv2

    from repro.sota_data.render_surface import surface_structure

    h, w = grid_shape(size)
    full_shape = grid_shape(obj_grid_size if obj_grid_size is not None else size)
    validate_region(y0, x0, size, full_shape)
    probe_size = (min(h, 1024), min(w, 1024))
    py, px = y0 + (h - probe_size[0]) // 2, x0 + (w - probe_size[1]) // 2
    best = (None, 0.0)
    os.makedirs(out_root, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".scale-probes-", dir=out_root
    ) as probe_root:
        for div in CANDIDATE_DIVS:
            fid = f"{seg}_probe_div{int(div)}"
            try:
                out_seg, _ = render_region(
                    seg,
                    obj,
                    volume,
                    py,
                    px,
                    probe_size,
                    level,
                    sign,
                    probe_root,
                    frag_id=fid,
                    obj_level_div=div,
                    obj_grid_size=full_shape,
                )
                mid = sorted(glob.glob(f"{out_seg}/layers/*.tif"))[13]
                mask = cv2.imread(f"{out_seg}/{fid}_mask.png", 0)
                s = surface_structure(cv2.imread(mid, 0), mask > 127)
                print(f"  scale probe div={div}: surface structure={s:.3f}", flush=True)
                if math.isfinite(s) and s > max(best[1], 1e-6):
                    best = (div, s)
            except ValueError as e:
                print(f"  scale probe div={div}: rejected ({e})", flush=True)
    if best[0] is None:
        raise SystemExit(
            "all candidate scales failed or were flat — check --obj / --volume / --level"
        )
    print(f"  chosen obj-level-div = {best[0]} (structure {best[1]:.3f})", flush=True)
    return best[0]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--obj", help="original.obj (local path or S3 key/url)")
    src.add_argument(
        "--tifxyz",
        help="tifxyz geometry dir (local or S3) — the released "
        "grid format most bucket segments ship; region is in grid px and "
        "--scale is ignored (tifxyz coords are level-0 voxels by convention)",
    )
    ap.add_argument("--volume", required=True, help="volume zarr (S3 key, anonymous)")
    ap.add_argument("--out", default="local_data/rendered", help="output root dir")
    ap.add_argument(
        "--obj-grid-size",
        nargs=2,
        type=int,
        metavar=("H", "W"),
        help="full OBJ UV-grid resolution; required for nonzero region origins",
    )
    ap.add_argument(
        "--frag-id", default=None, help="fragment id (default: obj basename)"
    )
    ap.add_argument(
        "--region",
        nargs="+",
        type=int,
        metavar="N",
        default=[0, 0, 2048],
        help="render region: Y0 X0 SIZE (square) or Y0 X0 H W (default 0 0 2048)",
    )
    ap.add_argument(
        "--level", type=int, default=2, help="volume pyramid level (default 2)"
    )
    ap.add_argument("--sign", type=float, default=1.0, help="normal sign (default 1)")
    ap.add_argument(
        "--scale",
        default="auto",
        help="obj level-div: a number, or 'auto' to infer teacher-free (default)",
    )
    args = ap.parse_args(argv)
    if len(args.region) == 3:
        y0, x0, size = args.region
    elif len(args.region) == 4:
        y0, x0 = args.region[:2]
        size = (args.region[2], args.region[3])
    else:
        ap.error("--region takes 3 (Y0 X0 SIZE) or 4 (Y0 X0 H W) integers")

    basename = os.path.basename((args.tifxyz or args.obj).rstrip("/"))
    seg = args.frag_id or (
        basename.replace(".tifxyz", "")
        if args.tifxyz
        else basename.replace("_original.obj", "").replace(".obj", "")
    )
    try:
        validate_level_sign(args.level, args.sign)
        if y0 < 0 or x0 < 0:
            raise ValueError("region origins must be nonnegative")
        if args.tifxyz and size == 0:
            if y0 or x0:
                raise ValueError("whole-grid region requires zero origins")
        else:
            grid_shape(size)
        if args.obj_grid_size:
            if args.tifxyz:
                raise ValueError("--obj-grid-size applies to --obj only")
            validate_region(y0, x0, size, grid_shape(args.obj_grid_size))
        elif args.obj and (y0 or x0):
            raise ValueError("OBJ region offsets require --obj-grid-size H W")
        if args.obj and args.scale != "auto":
            div = float(args.scale)
            if not math.isfinite(div) or div <= 0:
                raise ValueError("--scale must be a positive finite number or auto")
        validate_fragment_id(seg)
        if os.path.lexists(os.path.join(args.out, seg)):
            raise FileExistsError(
                "fragment already exists; use a fresh --frag-id/--out"
            )
    except (ValueError, TypeError, FileExistsError) as exc:
        ap.error(str(exc))

    if args.tifxyz:
        out_seg, stats = render_region_tifxyz(
            seg,
            args.tifxyz,
            args.volume,
            y0,
            x0,
            size,
            args.level,
            args.sign,
            args.out,
            frag_id=seg,
            extra_prov={"cli": True},
        )
        print(f"\nRendered {out_seg}")
        print(
            f"  layers: 26  valid_frac={stats['valid_frac']:.3f}  "
            f"clamped_frac={stats['clamped_frac']:.3f}  (tifxyz geometry, level-0 "
            f"coords / {2**args.level})"
        )
        print(
            "  label-free. See docs/SURFACE_RENDERER.md for historical validation "
            "and the current rendering contract."
        )
        return 0

    obj = _fetch_obj_if_s3(args.obj)

    if args.scale == "auto":
        print(
            "Inferring obj coordinate scale (teacher-free surface-structure probe)...",
            flush=True,
        )
        div = infer_scale(
            seg,
            obj,
            args.volume,
            args.out,
            y0,
            x0,
            size,
            args.level,
            args.sign,
            obj_grid_size=args.obj_grid_size,
        )
    else:
        div = float(args.scale)

    grid_kwargs = {"obj_grid_size": args.obj_grid_size} if args.obj_grid_size else {}
    out_seg, stats = render_region(
        seg,
        obj,
        args.volume,
        y0,
        x0,
        size,
        args.level,
        args.sign,
        args.out,
        frag_id=seg,
        obj_level_div=div,
        extra_prov={"cli": True, "obj_source": args.obj, "scale_selection": args.scale},
        **grid_kwargs,
    )
    print(f"\nRendered {out_seg}")
    print(
        f"  layers: 26  valid_frac={stats['valid_frac']:.3f}  "
        f"clamped_frac={stats['clamped_frac']:.3f}  obj_level_div={div}"
    )
    print(
        "  label-free. See docs/SURFACE_RENDERER.md for historical validation "
        "and the current rendering contract."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
