"""Render a detector-ready surface volume from a segment's original.obj + a volume zarr.

Turns the open bucket's MESH-ONLY segments (obj + volume, no surface volume, no predictions)
into a 26-layer surface volume the ink detector can consume. Validated on Scroll 1 against a
released surface volume (center-layer NCC ~0.59 — placement-correct, not pixel-perfect; see
reports/detector/render_validation.md). NO ink label is written — the render is label-free.

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
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.render_surface import render_region, render_region_tifxyz

CANDIDATE_DIVS = [1.0, 2.0, 4.0]


def _fetch_obj_if_s3(obj):
    if not obj.startswith("s3://") and not obj.startswith("vesuvius-challenge"):
        return obj
    import s3fs

    key = obj.replace("s3://", "")
    dst = os.path.join("local_data/rendered_obj", os.path.basename(key))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        s3fs.S3FileSystem(anon=True).get(key, dst)
    return dst


def infer_scale(seg, obj, volume, out_root, y0, x0, size, level, sign):
    """Render a probe at each candidate obj-level-div; return the div with the most
    papyrus-like surface structure (and reject empties)."""
    import glob

    import cv2

    from repro.sota_data.render_surface import surface_structure

    best = (None, -1.0)
    for div in CANDIDATE_DIVS:
        fid = f"{seg}_probe_div{int(div)}"
        try:
            out_seg, _ = render_region(
                seg,
                obj,
                volume,
                y0,
                x0,
                min(size, 1024),
                level,
                sign,
                out_root,
                frag_id=fid,
                obj_level_div=div,
            )
            mid = sorted(glob.glob(f"{out_seg}/layers/*.tif"))[13]
            mask = cv2.imread(glob.glob(f"{out_seg}/*_mask.png")[0], 0)
            s = surface_structure(cv2.imread(mid, 0), mask > 127)
            print(f"  scale probe div={div}: surface structure={s:.3f}", flush=True)
            if s > best[1]:
                best = (div, s)
        except Exception as e:
            print(f"  scale probe div={div}: failed ({type(e).__name__})", flush=True)
    if best[0] is None:
        raise SystemExit(
            "all candidate scales failed — check --obj / --volume / --level"
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
        "--frag-id", default=None, help="fragment id (default: obj basename)"
    )
    ap.add_argument(
        "--region",
        nargs=3,
        type=int,
        metavar=("Y0", "X0", "SIZE"),
        default=[0, 0, 2048],
        help="render region + grid size (default 0 0 2048)",
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
    y0, x0, size = args.region

    if args.tifxyz:
        seg = args.frag_id or os.path.basename(args.tifxyz.rstrip("/")).replace(
            ".tifxyz", ""
        )
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
            "  label-free (no ink GT fabricated). Renderer is placement-validated on "
            "Scroll 1 (NCC ~0.59), NOT pixel-perfect — treat outputs qualitatively."
        )
        return 0

    obj = _fetch_obj_if_s3(args.obj)
    seg = args.frag_id or os.path.basename(obj).replace("_original.obj", "").replace(
        ".obj", ""
    )

    if args.scale == "auto":
        print(
            "Inferring obj coordinate scale (teacher-free surface-structure probe)...",
            flush=True,
        )
        div = infer_scale(
            seg, obj, args.volume, args.out, y0, x0, size, args.level, args.sign
        )
    else:
        div = float(args.scale)

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
        extra_prov={"cli": True},
    )
    print(f"\nRendered {out_seg}")
    print(
        f"  layers: 26  valid_frac={stats['valid_frac']:.3f}  "
        f"clamped_frac={stats['clamped_frac']:.3f}  obj_level_div={div}"
    )
    print(
        "  label-free (no ink GT fabricated). Renderer is placement-validated on Scroll 1 "
        "(NCC ~0.59), NOT pixel-perfect — treat outputs qualitatively."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
