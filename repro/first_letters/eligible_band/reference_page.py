"""A reference page for the owner's look at a Studio band read, on this machine only: Studio's maps where letters
are known, each beside the same reader's map with its planes reversed, drawn as the band pages draw theirs.

PHerc. 211's First Letters prize was awarded on 2026-11-15, and PHerc. 343's letters are published by the recipe,
so these images may be looked at. No eligible scroll is read here.

- PHerc. 211: our own fit's windings w033 to w036, snapped, flattened, rendered and read by Studio (finding 124:
  r 0.82 against the winner's map). Beside each, the same render read with Studio's planes in reverse order
  (r -0.05): the same reader on the same papyrus, drawing ink-like marks but not the winner's letters.
- PHerc. 343: the recipe's published surface read by Studio (finding 127: r 0.62 against the recipe's ensemble),
  and reversed (r 0.10).

Each image is Studio's probability times 255, white = ink, the band pages' encoding, in reading orientation.
PHerc. 211's is turned by band_index's rule from the winding's mesh, the axis and the catalog's flags; PHerc. 343's
by the recipe's sidecar. Thumbnails are at one eighth, as on the band pages, each with a 1 cm bar at its scan's
voxel size. Beside each image are studio_band's numbers: the share of the rendered area at 0.5 or more, and the
largest share over one 380-pixel tile, which orders the band pages.

usage: reference_page.py OUT_DIR [--fl-root DIR]
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))

import band_index  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import studio_band  # noqa: E402
from render_frame import frame_index  # noqa: E402

FL_ROOT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters")
THUMB = band_index.THUMB
UM_PER_CM = 10_000.0
BAND_PAGES = (  # relative to OUT_DIR's parent, the first-letters root
    (
        "PHerc. 0826, finding 125",
        "pherc0826_band/work/studio_outer80/summary/index.html",
    ),
    (
        "PHerc. 0358, finding 126",
        "pherc0358_band/work/studio_fulldense/summary/index.html",
    ),
)


@dataclass(frozen=True)
class Panel:
    key: str  # file stem on the page
    scroll: str
    what: str
    studio_map: Path  # Studio's probability, float, in the render's frame
    render: (
        Path  # the render it was read from: its surface layer marks the rendered area
    )
    flip_ud: bool
    flip_lr: bool
    voxel_um: float


def rendered_area(render: Path) -> np.ndarray:
    """Where the winding was rendered: its surface layer (33 of the 66-layer frame) above zero, as studio_band."""
    import zarr

    level0 = zarr.open(str(render), mode="r")["0"]
    return np.asarray(level0[frame_index(level0.shape[0], 33)]) > 0


def draw(panel: Panel, out: Path) -> dict:
    """Write the panel's image and thumbnail in reading orientation; return studio_band's numbers for it."""
    import cv2

    prob = np.load(panel.studio_map, allow_pickle=False).astype(np.float32)
    rendered = rendered_area(panel.render)
    if rendered.shape != prob.shape:
        raise SystemExit(
            f"{panel.studio_map} is {prob.shape}, its render {rendered.shape}"
        )
    tiles = studio_band.tile_shares(prob, rendered)
    area = int(rendered.sum())
    image = np.clip(np.round(prob * 255), 0, 255).astype(np.uint8)
    if panel.flip_ud:
        image = image[::-1]
    if panel.flip_lr:
        image = image[:, ::-1]
    image = np.ascontiguousarray(image)
    cv2.imwrite(str(out / "images" / f"{panel.key}.png"), image)
    small = cv2.resize(image, (max(1, image.shape[1] // THUMB), max(1, image.shape[0] // THUMB)),
                       interpolation=cv2.INTER_AREA)  # fmt: skip
    bar = int(round(UM_PER_CM / panel.voxel_um / THUMB))
    y = small.shape[0] - 8
    if bar + 8 <= small.shape[1] and y >= 4:
        small[y - 3 : y, 6 : 6 + bar] = 255  # the 1 cm bar, bottom left
    cv2.imwrite(str(out / "thumbs" / f"{panel.key}.png"), small)
    return {
        "shape": list(prob.shape),
        "rendered_pixels": area,
        "ink_share": round(float((prob[rendered] >= studio_band.INK).mean()), 4)
        if area
        else None,
        "largest_tile_ink_share": max((t["ink_share"] for t in tiles), default=None),
        "tiles_scored": len(tiles),
        "bar_px_on_thumbnail": bar,
    }


def letter_heights(sizes_csv: Path) -> dict:
    """The recipe's measured letter heights (mm) on PHerc. 343: median, min and max."""
    with open(sizes_csv, newline="") as f:
        heights = [float(r["height_mm"]) for r in csv.DictReader(f)]
    return {
        "letters": len(heights),
        "median_mm": round(statistics.median(heights), 2),
        "min_mm": min(heights),
        "max_mm": max(heights),
    }


def default_panels(fl: Path) -> list[Panel]:
    panels = []
    band = fl / "pherc0211_band_z7650"
    maps = fl / "pherc0211_control" / "work" / "studio_e2e" / "maps"
    umbilicus = band_index.axis(band / "dataset" / "umbilicus.json")
    for w in ("w033", "w034", "w035", "w036"):
        xyz, valid = analysis.load_tifxyz(band / "work" / "final_e2e" / f"{w}.tifxyz")
        # PHerc. 211's catalog flags: z runs top to bottom, right-handed (band_index's docstring; checked there
        # against the winner's map)
        turn = band_index.orientation(xyz, valid, umbilicus, True, False)
        render = band / "work" / "render_e2e" / f"{w}_66.zarr"
        for suffix, what in (("", "Studio, our fit (finding 124)"),
                             ("_reversed", "Studio, planes reversed: no letters")):  # fmt: skip
            panels.append(Panel(f"0211_{w}{suffix}", "PHerc. 211", what, maps / f"{w}{suffix}.npy", render,
                                turn["flip_ud"], turn["flip_lr"], 9.362))  # fmt: skip
    work = fl / "pherc343_repro" / "work"
    sidecar = json.loads(
        (
            work / "studio_343" / "reference" / "concat_w047-w048_R5B2_z9500-11000.json"
        ).read_text()
    )
    o = sidecar["orientation"]
    render = work / "concat_w047-w048_R5B2_z9500-11000_66.zarr"
    for stem, what in (("forward", "Studio, the recipe's surface (finding 127)"),
                       ("reversed", "Studio, planes reversed: no letters")):  # fmt: skip
        panels.append(Panel(f"0343_{stem}", "PHerc. 343", what, work / "studio_343" / "maps" / f"{stem}.npy",
                            render, o["flip_ud"], o["flip_lr"], float(sidecar["voxel_size_um"])))  # fmt: skip
    return panels


def build(
    out: Path, panels: list[Panel], letters: dict | None = None, band_pages=()
) -> Path:
    for sub in ("images", "thumbs"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    record = {}
    rows = []
    for p in panels:
        n = draw(p, out)
        record[p.key] = {"scroll": p.scroll, "what": p.what, "flip_ud": p.flip_ud, "flip_lr": p.flip_lr,
                         "voxel_um": p.voxel_um, **n}  # fmt: skip
        flips = ", ".join(
            f for f, on in (("mirrored", p.flip_lr), ("upside down", p.flip_ud)) if on
        )
        rows.append(
            f"<tr><td>{html.escape(p.scroll)}</td><td><a href='images/{p.key}.png'>{html.escape(p.key)}</a>"
            f" ({flips or 'unturned'})<br>{html.escape(p.what)}</td>"
            f"<td>{n['ink_share']}</td><td>{n['largest_tile_ink_share']}</td><td>{n['tiles_scored']}</td>"
            f"<td><a href='images/{p.key}.png'><img src='thumbs/{p.key}.png'></a></td></tr>"
        )
    (out / "reference.json").write_text(
        json.dumps({"panels": record, "letters_343": letters}, indent=1) + "\n"
    )
    size = ""
    if letters:
        mid = letters["median_mm"] * 1000 / 9.362
        size = (
            f"<p>Letter size: the recipe measured {letters['letters']} letters on PHerc. 343, {letters['min_mm']} to "
            f"{letters['max_mm']} mm tall (median {letters['median_mm']} mm). On a band read at 9.362 um that median "
            f"is about {mid:.0f} pixels at full resolution and {mid / THUMB:.0f} on a thumbnail.</p>"
        )
    links = "".join(
        f"<li><a href='../{html.escape(path)}'>{html.escape(label)}</a></li>"
        for label, path in band_pages
    )
    page = f"""<!doctype html><meta charset="utf-8"><title>Studio reference</title>
<style>body{{font:14px sans-serif;background:#111;color:#ddd}}td{{padding:4px;vertical-align:top}}
img{{max-width:900px}}a{{color:#8cf}}</style>
<p>Studio probability (white = ink) where letters are known, drawn as the band pages draw theirs: the same encoding,
reading orientation, thumbnails at one eighth and the same numbers. The bar at the bottom left of each thumbnail is
1 cm. Click for full resolution.</p>
<p>Each "planes reversed" map is the same reader on the same render with its planes in reverse order. It draws
ink-like marks, often over much of a tile, but not the letters: so a high ink share or a high tile share is not
text. Where letters are, they are strokes in rows; in the reversed maps the marks are rounded blobs with no rows.</p>
{size}
{"<p>Band pages:</p><ul>" + links + "</ul>" if links else ""}
<table><tr><th>scroll</th><th>image</th><th>ink share</th><th>largest tile</th><th>tiles</th><th>map</th></tr>
{"".join(rows)}</table>
"""
    (out / "index.html").write_text(page)
    return out / "index.html"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--fl-root", type=Path, default=FL_ROOT)
    args = ap.parse_args(argv)
    letters = letter_heights(args.fl_root / "pherc343_repro" / "work" / "studio_343" / "reference"
                             / "concat_w047-w048_R5B2_z9500-11000_letter_sizes.csv")  # fmt: skip
    pages = [
        (label, path) for label, path in BAND_PAGES if (args.fl_root / path).exists()
    ]
    print(build(args.out, default_panels(args.fl_root), letters, pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
