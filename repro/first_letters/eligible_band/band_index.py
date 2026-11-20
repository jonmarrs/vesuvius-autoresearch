"""An inspection page for a Studio band read (finding 125): SUMMARY_DIR/index.html, on this machine only.

The windings in order of their largest tile ink share (only an order of inspection: it decides nothing), each with
a thumbnail at one eighth and a link to its full-resolution image, beside its numbers and its fit's excess score.

Each image is turned into reading orientation, per winding, from its mesh, the scroll axis and the scroll's two
orientation flags in the open-data catalog. This is the PHerc. 343 recipe's rule (`make_submission_image.py`,
`measure_orientation`): flip top to bottom when z increases with row, so that high z is at the top; mirror left to
right when theta increases with column, so that theta decreases to the right. It is written for a scroll whose z
runs bottom to top in right-handed coordinates, as PHerc. 343's volume does. A z that runs top to bottom
(`z_direction_is_top_to_bottom`) reverses both senses, and left-handed coordinates reverse the sense of theta.

Checked on PHerc. 211 (z top to bottom, right-handed), against the winner's map, which reads as published:
- the winner's own surface needs neither flip;
- our fit's w035 needs the mirror only, and mirrored its Studio map reads as the winner's does;
- its rows run with the winner's (r 0.999) and its columns against them (r -0.996).
"as rendered" links the unturned image.

usage: band_index.py SUMMARY_DIR --finals DIR --umbilicus JSON --top-to-bottom true|false --left-handed true|false
       [--quality QUALITY_JSON]
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))

import mesh_step_analysis as analysis  # noqa: E402

THUMB = 8  # one pixel per 8


def order(summary: dict) -> list[str]:
    """Largest tile ink share first; windings with no scored tile last, by name."""

    def key(name: str) -> tuple:
        share = summary[name]["largest_tile_ink_share"]
        return (share is None, -(share or 0.0), name)

    return sorted(summary, key=key)


def axis(path: Path) -> np.ndarray:
    """The scroll axis as rows z, x, y, sorted by z, from a published umbilicus file."""
    points = sorted(
        json.loads(Path(path).read_text())["control_points"], key=lambda p: p["z"]
    )
    return np.array([[p["z"], p["x"], p["y"]] for p in points], dtype=np.float64).T


def orientation(xyz: np.ndarray, valid: np.ndarray, umbilicus: np.ndarray, top_to_bottom: bool,
                left_handed: bool) -> dict:  # fmt: skip
    """flip_ud and flip_lr that turn this mesh's render into reading orientation (the module's rule)."""
    x, y, z = (np.where(valid, xyz[..., i], np.nan) for i in range(3))
    cx = np.interp(z, umbilicus[0], umbilicus[1])
    cy = np.interp(z, umbilicus[0], umbilicus[2])
    theta = np.arctan2(y - cy, x - cx)
    unwrapped = np.unwrap(np.nan_to_num(theta), axis=1)
    step = np.diff(unwrapped, axis=1)[valid[:, 1:] & valid[:, :-1]]
    rows_z = np.array([np.nanmedian(r) if np.isfinite(r).any() else np.nan for r in z])
    dz = np.diff(rows_z)
    sign_theta = int(np.sign(np.median(step))) if step.size else 0
    sign_z = int(np.sign(np.nanmedian(dz))) if np.isfinite(dz).any() else 0
    s = -1 if top_to_bottom else 1
    t = -1 if left_handed else 1
    return {
        "sign_dtheta_per_column": sign_theta,
        "sign_dz_per_row": sign_z,
        "flip_ud": s * sign_z > 0,
        "flip_lr": s * t * sign_theta > 0,
    }


def build(out: Path, finals: Path, umbilicus: Path, top_to_bottom: bool, left_handed: bool,
          quality: dict | None = None) -> Path:  # fmt: skip
    import cv2

    summary = json.loads((out / "summary.json").read_text())["windings"]
    quality = quality or {}
    centre = axis(umbilicus)
    (out / "thumbs").mkdir(exist_ok=True)
    (out / "images_reading").mkdir(exist_ok=True)
    turns = {}
    rows = []
    for rank, name in enumerate(order(summary), 1):
        s = summary[name]
        xyz, valid = analysis.load_tifxyz(finals / f"{name}.tifxyz")
        turn = orientation(xyz, valid, centre, top_to_bottom, left_handed)
        turns[name] = turn
        image = cv2.imread(str(out / "images" / f"{name}.png"), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise SystemExit(f"no image for {name}")
        if turn["flip_ud"]:
            image = image[::-1]
        if turn["flip_lr"]:
            image = image[:, ::-1]
        cv2.imwrite(
            str(out / "images_reading" / f"{name}.png"), np.ascontiguousarray(image)
        )
        small = cv2.resize(image, (max(1, image.shape[1] // THUMB), max(1, image.shape[0] // THUMB)),
                           interpolation=cv2.INTER_AREA)  # fmt: skip
        cv2.imwrite(str(out / "thumbs" / f"{name}.png"), small)
        excess = (quality.get(name) or {}).get("excess")
        flips = ", ".join(
            f
            for f, on in (
                ("mirrored", turn["flip_lr"]),
                ("upside down", turn["flip_ud"]),
            )
            if on
        )
        rows.append(
            f"<tr><td>{rank}</td><td><a href='images_reading/{name}.png'>{html.escape(name)}</a> "
            f"(<a href='images/{name}.png'>as rendered</a>; {flips or 'unturned'})</td>"
            f"<td>{s['ink_share']}</td><td>{s['largest_tile_ink_share']}</td><td>{s['tiles_scored']}</td>"
            f"<td>{'' if excess is None else round(excess, 3)}</td>"
            f"<td><a href='images_reading/{name}.png'><img src='thumbs/{name}.png'></a></td></tr>"
        )
    (out / "orientation.json").write_text(json.dumps(turns, indent=1) + "\n")
    page = f"""<!doctype html><meta charset="utf-8"><title>Studio band read</title>
<style>body{{font:14px sans-serif;background:#111;color:#ddd}}td{{padding:4px;vertical-align:top}}
img{{max-width:900px}}a{{color:#8cf}}</style>
<p>Studio probability (white = ink). Order: largest tile ink share; it decides nothing. Click for full resolution.</p>
<p>Each image is turned into reading orientation from its mesh, the scroll axis and the catalog's orientation flags
(the PHerc. 343 recipe's rule, checked on PHerc. 211 against the winner's map). "as rendered" links the unturned
image.</p>
<table><tr><th>#</th><th>winding</th><th>ink share</th><th>largest tile</th><th>tiles</th><th>fit excess</th>
<th>map</th></tr>
{"".join(rows)}</table>
"""
    (out / "index.html").write_text(page)
    return out / "index.html"


def _flag(text: str) -> bool:
    if text not in ("true", "false"):
        raise argparse.ArgumentTypeError("true or false")
    return text == "true"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("summary", type=Path)
    ap.add_argument("--finals", required=True, type=Path)
    ap.add_argument("--umbilicus", required=True, type=Path)
    ap.add_argument("--top-to-bottom", required=True, type=_flag)
    ap.add_argument("--left-handed", required=True, type=_flag)
    ap.add_argument("--quality", type=Path)
    args = ap.parse_args(argv)
    quality = json.loads(args.quality.read_text())["windings"] if args.quality else None
    print(
        build(
            args.summary,
            args.finals,
            args.umbilicus,
            args.top_to_bottom,
            args.left_handed,
            quality,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
