"""Inputs for a First Letters submission image made from a band read, and the flattening check it needs.

The image itself is made by the PHerc. 343 recipe's make_submission_image.py (MIT, Nieuwlaar/pherc343-first-letters
at e8370f1f), called from its clone by make_band_submission.sh. This module supplies what that script needs from our
band reads and what it does not measure:

  ink        Studio's map of a winding (float32 [H, W], inference.py's .npy) as a float32 TIFF named the way the
             recipe's script reads it. The map of our layers 41 down to 26 (finding 124's order) is the reading side:
             <stem>__studio__L66zc33.50_reverse.tif (window centre 33.5, so depth +1, the depth the recipe's own
             image shows). The map of the reversed planes is the control: <stem>__studio__L66zc33.50.tif, which the
             recipe's script draws only with --allow-blind. Values are written unchanged (the script reads a float32
             TIFF as is); the shape must be the render's.
  isometry   how far the mesh's flattening is from isometric inside an area of the render: each grid edge's 3D length
             over its flat length (1 / scale render pixels), along rows and along columns, the angle between the two
             edge directions at each node, and the 3D area of the area's quads over their flat area. The rules ask
             for "a low-distortion isometric 2D parametrization"; the recipe's script reports only the area ratio.

Nothing here reads CT, chooses an area, or places a row or a letter.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

READING_TAG = "__studio__L66zc33.50_reverse"
CONTROL_TAG = "__studio__L66zc33.50"
WITHIN = 0.10  # the share of edges whose stretch is within 10% of 1 is reported


def ink_tiffs(
    reading: Path, control: Path, render_hw: tuple[int, int], out_dir: Path, stem: str
) -> dict:
    """Write the two Studio maps as float32 TIFFs for make_submission_image.py; refuse a shape or value problem."""
    import tifffile

    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for role, src, tag in (
        ("reading", reading, READING_TAG),
        ("control", control, CONTROL_TAG),
    ):
        values = np.load(src, allow_pickle=False)
        if values.ndim != 2 or tuple(values.shape) != tuple(render_hw):
            raise SystemExit(
                f"{src}: shape {values.shape}, the render is {tuple(render_hw)}"
            )
        if values.dtype != np.float32:
            raise SystemExit(f"{src}: {values.dtype}, Studio writes float32")
        if not np.isfinite(values).all():
            raise SystemExit(f"{src}: has values that are not finite")
        dest = out_dir / f"{stem}{tag}.tif"
        if dest.exists():
            raise SystemExit(f"{dest} exists")
        tifffile.imwrite(dest, values)
        written[role] = {
            "source": src.name,
            "file": dest.name,
            "shape": list(values.shape),
        }
    return written


def control_stats(sidecar: Path, depth: int = 1) -> dict:
    """The ink-stats the recipe's script needs to draw the control: the reading image's own numbers.

    The script draws a blind-side (here: reversed-plane) map only with the reading side's statistics, so that a
    fainter map is not stretched up to look like text. They are taken from the reading image's sidecar: its
    single-model ink stretch, mean and sd, and its CT stretch, so both images share every display number.
    """
    d = json.loads(sidecar.read_text())
    norm = d["ink"]["normalisation"]
    if norm.get("mode") != "single model" or len(norm.get("models", [])) != 1:
        raise SystemExit(
            f"{sidecar}: expected one reading-side model, not {norm.get('models')}"
        )
    (model,) = norm["models"]
    m = norm["per_model"][model]
    if d["ink"]["maps"][0]["side"] != "reading":
        raise SystemExit(f"{sidecar}: the image was not made from the reading side")
    _, h, w = d["ct"]["shape"]
    ct = d["ct"]["stretch"]
    return {
        "H": h,
        "W": w,
        "surface": d["ct"]["file"],
        "models": {
            model: {k: m[k] for k in ("p1", "p99_5", "mean", "sd")}
            | {"depths": [depth]}
        },
        "ct": {"p1": ct["lo"], "p99_5": ct["hi"]},
        "source": f"{sidecar.name}: the reading image's stretch, reused for its control",
    }


def reading_orientation(
    mesh: Path, umbilicus: Path, top_to_bottom: bool, left_handed: bool
) -> dict:
    """flip_lr and flip_ud for the recipe's script, by the band pages' rule (band_index.orientation).

    The recipe's script measures the reading orientation itself, with a rule written for PHerc. 343's volume (z bottom
    to top, right-handed coordinates). A volume whose catalog says z runs top to bottom turns both senses, and
    left-handed coordinates turn theta's: on PHerc. 211 the script's own measurement is the 180-degree turn of the
    orientation the winner's map reads in. So the flips are computed here, with the scroll's two catalog flags, and
    passed to the script explicitly.
    """
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "eligible_band" / "band_index.py"
    spec = importlib.util.spec_from_file_location("band_index_for_submission", path)
    assert spec and spec.loader
    band_index = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = band_index
    spec.loader.exec_module(band_index)
    xyz, valid, _ = _nodes(mesh)
    xyz = np.where(valid[..., None], xyz, -1.0)
    turn = band_index.orientation(
        xyz, valid, band_index.axis(umbilicus), top_to_bottom, left_handed
    )
    return {
        "mesh": mesh.name,
        "umbilicus": umbilicus.name,
        "z_direction_is_top_to_bottom": top_to_bottom,
        "left_handed_coordinates": left_handed,
        **{
            k: (bool(v) if isinstance(v, (bool, np.bool_)) else int(v))
            for k, v in turn.items()
        },
        "rule": "band_index.orientation: flip_ud = s * sign(dz/drow) > 0, flip_lr = s * t * sign(dtheta/dcolumn) > 0, "
        "s = -1 if z runs top to bottom, t = -1 if left-handed (the recipe's rule is s = t = 1)",
    }


def _nodes(mesh: Path) -> tuple[np.ndarray, np.ndarray, float]:
    """The mesh's points [rows, cols, 3] (x, y, z), its valid-node mask, and the flat length of one grid step."""
    import tifffile

    meta = json.loads((mesh / "meta.json").read_text())
    scale = meta.get("scale")
    if not (
        isinstance(scale, list)
        and len(scale) == 2
        and scale[0] == scale[1]
        and scale[0] > 0
    ):
        raise SystemExit(
            f"{mesh}: meta.json scale must be two equal positive numbers, not {scale!r}"
        )
    xyz = np.stack(
        [tifffile.imread(mesh / f"{a}.tif").astype(np.float64) for a in "xyz"], axis=-1
    )
    valid = np.all(xyz != -1, axis=-1) & np.all(np.isfinite(xyz), axis=-1)
    if (mesh / "mask.tif").exists():
        valid &= tifffile.imread(mesh / "mask.tif") > 0
    return xyz, valid, 1.0 / float(scale[0])


def _summary(values: np.ndarray, ideal: float | None = None) -> dict:
    if values.size == 0:
        return {"n": 0}
    q = np.percentile(values, [5, 50, 95])
    out = {"n": int(values.size), "p5": round(float(q[0]), 4), "median": round(float(q[1]), 4),
           "p95": round(float(q[2]), 4)}  # fmt: skip
    if ideal is not None:
        out["share_within_10pct"] = round(
            float(np.mean(np.abs(values - ideal) <= WITHIN * ideal)), 4
        )
    return out


def isometry(mesh: Path, area: tuple[int, int, int, int] | None = None) -> dict:
    """Edge stretch, shear and area ratio of the mesh's nodes whose render pixel lies in area (row0, row1, col0, col1;
    ends exclusive), or of the whole mesh. Render pixel of node (i, j) = (i, j) / scale, as the renderer lays it out."""
    xyz, valid, step = _nodes(mesh)
    rows, cols = valid.shape
    inside = valid.copy()
    if area is not None:
        row0, row1, col0, col1 = area
        r = np.arange(rows)[:, None] * step
        c = np.arange(cols)[None, :] * step
        inside &= (r >= row0) & (r < row1) & (c >= col0) & (c < col1)
    along_cols = (
        inside[:, :-1] & inside[:, 1:]
    )  # edge (i, j)-(i, j+1): one step along a render row
    along_rows = (
        inside[:-1, :] & inside[1:, :]
    )  # edge (i, j)-(i+1, j): one step down a render column
    du = xyz[:, 1:] - xyz[:, :-1]
    dv = xyz[1:, :] - xyz[:-1, :]
    su = np.linalg.norm(du, axis=-1)[along_cols] / step
    sv = np.linalg.norm(dv, axis=-1)[along_rows] / step
    quad = inside[:-1, :-1] & inside[1:, :-1] & inside[:-1, 1:] & inside[1:, 1:]
    u0, v0 = du[:-1, :], dv[:, :-1]  # the two edges leaving node (i, j) of each quad
    cosang = np.sum(u0 * v0, axis=-1) / np.maximum(
        np.linalg.norm(u0, axis=-1) * np.linalg.norm(v0, axis=-1), 1e-12
    )
    shear = np.abs(90.0 - np.degrees(np.arccos(np.clip(cosang[quad], -1, 1))))
    p00, p01, p10, p11 = xyz[:-1, :-1], xyz[:-1, 1:], xyz[1:, :-1], xyz[1:, 1:]
    tri = 0.5 * (
        np.linalg.norm(np.cross(p01 - p00, p10 - p00), axis=-1)
        + np.linalg.norm(np.cross(p01 - p11, p10 - p11), axis=-1)
    )
    n_quads = int(quad.sum())
    return {
        "mesh": mesh.name,
        "area_raw_render_px": None
        if area is None
        else dict(zip(("row0", "row1", "col0", "col1"), area, strict=False)),
        "flat_step_px": step,
        "nodes": int(inside.sum()),
        "stretch_along_render_rows": _summary(su, 1.0),
        "stretch_along_render_columns": _summary(sv, 1.0),
        "shear_deg": _summary(shear),
        "quads": n_quads,
        "area_ratio_3d_to_flat": round(
            float(tri[quad].sum() / (n_quads * step * step)), 4
        )
        if n_quads
        else None,
        "rule": "stretch = 3D edge length / (1 / scale); shear = |90 - angle between the two edges at a node|; "
        "area ratio = sum of the quads' 3D area (two triangles) / (quads x step^2)",
    }


def _area(text: str | None) -> tuple[int, int, int, int] | None:
    if text is None:
        return None
    if text.endswith(".json"):
        d = json.loads(Path(text).read_text())
        d = d.get("area", d).get("raw_render_px", d)
        return tuple(int(d[k]) for k in ("row0", "row1", "col0", "col1"))  # type: ignore[return-value]
    parts = [int(v) for v in text.split(",")]
    if len(parts) != 4:
        raise SystemExit("--area is row0,row1,col0,col1 or a JSON with raw_render_px")
    return tuple(parts)  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser(
        "ink", help="Studio maps as the recipe script's float32 TIFF inputs"
    )
    a.add_argument("reading", type=Path, help="Studio's map of layers 41 down to 26")
    a.add_argument(
        "control", type=Path, help="Studio's map of the same layers reversed"
    )
    a.add_argument("--render-hw", type=int, nargs=2, required=True, metavar=("H", "W"))
    a.add_argument("--out-dir", type=Path, required=True)
    a.add_argument("--stem", required=True, help="the mesh folder name without .tifxyz")
    b = sub.add_parser("isometry", help="the flattening's distortion inside an area")
    b.add_argument("mesh", type=Path)
    b.add_argument(
        "--area",
        help="row0,row1,col0,col1 in raw render pixels, or a JSON with raw_render_px",
    )
    b.add_argument("--out", type=Path)
    c = sub.add_parser(
        "stats", help="the control's ink-stats, from the reading image's sidecar"
    )
    c.add_argument("sidecar", type=Path)
    c.add_argument("--out", type=Path, required=True)
    o = sub.add_parser(
        "orient",
        help="flip_lr and flip_ud from the mesh, the axis and the catalog's two flags",
    )
    o.add_argument("mesh", type=Path)
    o.add_argument("--umbilicus", type=Path, required=True)
    o.add_argument("--top-to-bottom", choices=("true", "false"), required=True)
    o.add_argument("--left-handed", choices=("true", "false"), required=True)
    o.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "ink":
        result = ink_tiffs(
            args.reading, args.control, tuple(args.render_hw), args.out_dir, args.stem
        )
    elif args.cmd == "stats":
        result = control_stats(args.sidecar)
    elif args.cmd == "orient":
        result = reading_orientation(
            args.mesh,
            args.umbilicus,
            args.top_to_bottom == "true",
            args.left_handed == "true",
        )
    else:
        result = isometry(args.mesh, _area(args.area))
    text = json.dumps(result, indent=1)
    if getattr(args, "out", None):
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
