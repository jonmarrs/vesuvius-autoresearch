"""Finding 125: Studio reads every winding of a fitted band, as images for the owner to inspect.

Registration: docs/preregistration/2026-11-20_first_letters_0826_studio_band.md.

    orient     OUT.json FINAL_TIFXYZ... [--umbilicus JSON]
               per winding, the share of its normals that point toward the band's centre (the mean of every listed
               winding's nodes) in the x-y plane, and "flip" when that share is above one half, as on PHerc. 211,
               where our fit's windings point inward on 99% of their nodes and were rendered flipped (findings 121
               and 124). Decided from the geometry, before any ink. With --umbilicus the centre is the published
               scroll axis at each node's z instead: on PHerc. 0826's read the band's mean lay off the axis, and two
               windings that point inward on 90% of their nodes against the axis scored 49% against it.
    summarise  OUT_DIR MAPS_DIR PLANES_OR_RENDERS_DIR
               for each Studio map MAPS_DIR/<winding>.npy: an 8-bit image of it (OUT_DIR/images/<winding>.png),
               a contact sheet of all of them at one eighth (OUT_DIR/contact_sheet.png), and the numbers in
               OUT_DIR/summary.json: the share of the winding's rendered area at probability 0.5 or more, and the
               same over each tile of 380 pixels (finding 117's 19 nodes), with the largest tile share.
    select     QUALITY_JSON OUT.txt
               the windings whose sheet-following excess (run_quality.sh) is above zero: nearer a predicted sheet
               than six voxels off it. Chosen from the geometry, before any ink (finding 126).
    stacked    OUT.json SNAP_DIR
               for each pair of consecutive snapped windings, the share of the inner one's nodes within 2 voxels of
               the outer one (finding 110's surface_distance): the strategy's stacked-winding check. Described: a
               pair at or above STACKED renders the same papyrus twice.

Nothing here decides whether there are letters; that is the owner's reading of the images.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))

import mesh_step_analysis as analysis  # noqa: E402

TILE = 380  # pixels: 19 nodes of 20, finding 117's tile
INK = 0.5
MIN_TILE_COVER = 0.9  # share of a tile that must be rendered for it to be scored
STACKED = 0.30  # finding 113's line for two windings on one surface
SHEET_SCALE = 8  # contact sheet: one pixel per 8


def axis_xy(umbilicus: Path, z: np.ndarray) -> np.ndarray:
    """The published scroll axis (control points x, y, z) at each z, as (N, 2) x, y."""
    points = sorted(
        json.loads(Path(umbilicus).read_text())["control_points"], key=lambda p: p["z"]
    )
    zs = np.array([p["z"] for p in points], dtype=np.float64)
    return np.stack(
        [
            np.interp(z, zs, [p["x"] for p in points]),
            np.interp(z, zs, [p["y"] for p in points]),
        ],
        1,
    )


def orientation(finals: list[Path], umbilicus: Path | None = None) -> dict:
    loaded = {
        Path(f).name.removesuffix(".tifxyz"): analysis.load_tifxyz(f) for f in finals
    }
    centre = np.concatenate([xyz[v] for xyz, v in loaded.values()]).mean(0)
    out: dict = {
        "centre_xyz": [round(float(c), 1) for c in centre],
        "reference": "band_centre" if umbilicus is None else "scroll_axis",
        "windings": {},
    }
    for name, (xyz, valid) in loaded.items():
        normals, ok = analysis.grid_normals(xyz, valid)
        keep = valid & ok
        points = xyz[keep]
        radial = points[:, :2] - (
            centre[:2] if umbilicus is None else axis_xy(umbilicus, points[:, 2])
        )
        length = np.linalg.norm(radial, axis=1)
        good = length > 0
        dot = np.einsum(
            "ij,ij->i", normals[keep][good][:, :2], radial[good] / length[good, None]
        )
        inward = float((dot < 0).mean()) if dot.size else None
        out["windings"][name] = {
            "share_of_normals_pointing_inward": None
            if inward is None
            else round(inward, 4),
            "render": None
            if inward is None or inward == 0.5
            else ("flip" if inward > 0.5 else "keep"),
        }
    return out


def tile_shares(prob: np.ndarray, rendered: np.ndarray) -> list[dict]:
    h, w = prob.shape
    tiles = []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            cover = rendered[y : y + TILE, x : x + TILE]
            if cover.mean() < MIN_TILE_COVER:
                continue
            share = float((prob[y : y + TILE, x : x + TILE][cover] >= INK).mean())
            tiles.append(
                {"row": y // TILE, "col": x // TILE, "ink_share": round(share, 4)}
            )
    return tiles


def summarise(out: Path, maps: Path, renders: Path) -> dict:
    import cv2
    import zarr

    (out / "images").mkdir(parents=True, exist_ok=False)
    summary: dict = {"windings": {}}
    thumbs = []
    for path in sorted(maps.glob("w*.npy")):
        name = path.stem
        prob = np.load(path, allow_pickle=False).astype(np.float32)
        level0 = zarr.open(str(renders / f"{name}_66.zarr"), mode="r")["0"]
        rendered = (
            np.asarray(level0[33]) > 0
        )  # the surface layer: where the winding was rendered
        if rendered.shape != prob.shape:
            raise SystemExit(f"{path} is {prob.shape}, its render {rendered.shape}")
        image = np.clip(np.round(prob * 255), 0, 255).astype(np.uint8)
        cv2.imwrite(str(out / "images" / f"{name}.png"), image)
        tiles = tile_shares(prob, rendered)
        area = int(rendered.sum())
        summary["windings"][name] = {
            "shape": list(prob.shape),
            "rendered_pixels": area,
            "ink_share": round(float((prob[rendered] >= INK).mean()), 4)
            if area
            else None,
            "tiles_scored": len(tiles),
            "largest_tile_ink_share": max(
                (t["ink_share"] for t in tiles), default=None
            ),
            "tiles": tiles,
        }
        thumbs.append((name, cv2.resize(image, (image.shape[1] // SHEET_SCALE, image.shape[0] // SHEET_SCALE),
                                        interpolation=cv2.INTER_AREA)))  # fmt: skip
    if thumbs:
        width = max(t.shape[1] for _, t in thumbs)
        rows = [np.pad(t, ((0, 4), (0, width - t.shape[1]))) for _, t in thumbs]
        cv2.imwrite(str(out / "contact_sheet.png"), np.vstack(rows))
        summary["contact_sheet_order"] = [n for n, _ in thumbs]
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def select(quality: dict) -> list[str]:
    """Windings with a sheet-following excess above zero, in index order."""
    chosen = []
    for name, entry in quality["windings"].items():
        excess = entry.get("excess") if isinstance(entry, dict) else None
        if excess is not None and excess > 0:
            chosen.append(name)
    return sorted(chosen, key=lambda n: int(n[1:]))


def stacked(snap: Path) -> dict:
    names = sorted(
        (p.name for p in snap.iterdir() if p.is_dir() and (p / "x.tif").exists()),
        key=lambda n: int(n[1:]),
    )
    loaded = {n: analysis.load_tifxyz(snap / n) for n in names}
    pairs = {}
    for inner, outer in zip(names, names[1:], strict=False):
        if int(outer[1:]) != int(inner[1:]) + 1:
            continue
        share = analysis.surface_distance(*loaded[inner], *loaded[outer])[
            "fraction_within"
        ]["2"]
        pairs[f"{inner}-{outer}"] = share
    return {
        "line": STACKED,
        "pairs": pairs,
        "stacked": sorted(k for k, v in pairs.items() if v >= STACKED),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    o = sub.add_parser("orient")
    o.add_argument("out", type=Path)
    o.add_argument("finals", nargs="+", type=Path)
    o.add_argument("--umbilicus", type=Path)
    s = sub.add_parser("summarise")
    s.add_argument("out", type=Path)
    s.add_argument("maps", type=Path)
    s.add_argument("renders", type=Path)
    c = sub.add_parser("select")
    c.add_argument("quality", type=Path)
    c.add_argument("out", type=Path)
    k = sub.add_parser("stacked")
    k.add_argument("out", type=Path)
    k.add_argument("snap", type=Path)
    args = ap.parse_args(argv)
    if args.command == "select":
        chosen = select(json.loads(args.quality.read_text()))
        args.out.write_text("".join(f"{n}\n" for n in chosen))
        print(f"{len(chosen)} windings with positive excess")
        return 0 if chosen else 1
    if args.command == "stacked":
        result = stacked(args.snap)
        args.out.write_text(json.dumps(result, indent=1) + "\n")
        print(json.dumps({"pairs": len(result["pairs"]), "stacked": result["stacked"]}))
        return 0
    if args.command == "orient":
        if args.out.exists():
            print(f"{args.out} exists", file=sys.stderr)
            return 2
        result = orientation(args.finals, args.umbilicus)
        args.out.write_text(json.dumps(result, indent=1) + "\n")
        for name, entry in result["windings"].items():
            print(f"{name} {entry['render']}")
        return 0 if all(e["render"] for e in result["windings"].values()) else 1
    summary = summarise(args.out, args.maps, args.renders)
    print(
        json.dumps(
            {
                n: {k: v for k, v in s.items() if k != "tiles"}
                for n, s in summary["windings"].items()
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
