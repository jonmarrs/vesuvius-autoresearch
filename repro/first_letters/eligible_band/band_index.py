"""An inspection page for a Studio band read (finding 125): SUMMARY_DIR/index.html, on this machine only.

The windings in order of their largest tile ink share (only an order of inspection: it decides nothing), each with
a thumbnail at one eighth and a link to its full-resolution image, beside its numbers and its fit's excess score.

Images are shown mirrored left to right, in reading orientation. On PHerc. 211 this fitter's windings, rendered
flipped, run against the winner's reading direction: columns correlate at -0.996 and rows at +0.999 (w035 against
the winner's surface). Mirrored, the Studio map of w035 reads as the winner's map does. "as rendered" links the
unmirrored image.

usage: band_index.py SUMMARY_DIR [QUALITY_JSON]
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

THUMB = 8  # one pixel per 8


def order(summary: dict) -> list[str]:
    """Largest tile ink share first; windings with no scored tile last, by name."""

    def key(name: str) -> tuple:
        share = summary[name]["largest_tile_ink_share"]
        return (share is None, -(share or 0.0), name)

    return sorted(summary, key=key)


def build(out: Path, quality: dict | None = None) -> Path:
    import cv2

    summary = json.loads((out / "summary.json").read_text())["windings"]
    quality = quality or {}
    (out / "thumbs").mkdir(exist_ok=True)
    (out / "images_mirrored").mkdir(exist_ok=True)
    rows = []
    for rank, name in enumerate(order(summary), 1):
        s = summary[name]
        image = cv2.imread(str(out / "images" / f"{name}.png"), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise SystemExit(f"no image for {name}")
        image = image[:, ::-1]
        cv2.imwrite(str(out / "images_mirrored" / f"{name}.png"), image)
        small = cv2.resize(image, (max(1, image.shape[1] // THUMB), max(1, image.shape[0] // THUMB)),
                           interpolation=cv2.INTER_AREA)  # fmt: skip
        cv2.imwrite(str(out / "thumbs" / f"{name}.png"), small)
        excess = (quality.get(name) or {}).get("excess")
        rows.append(
            f"<tr><td>{rank}</td><td><a href='images_mirrored/{name}.png'>{html.escape(name)}</a> "
            f"(<a href='images/{name}.png'>as rendered</a>)</td>"
            f"<td>{s['ink_share']}</td><td>{s['largest_tile_ink_share']}</td><td>{s['tiles_scored']}</td>"
            f"<td>{'' if excess is None else round(excess, 3)}</td>"
            f"<td><a href='images_mirrored/{name}.png'><img src='thumbs/{name}.png'></a></td></tr>"
        )
    page = f"""<!doctype html><meta charset="utf-8"><title>Studio band read</title>
<style>body{{font:14px sans-serif;background:#111;color:#ddd}}td{{padding:4px;vertical-align:top}}
img{{max-width:900px}}a{{color:#8cf}}</style>
<p>Studio probability (white = ink). Order: largest tile ink share; it decides nothing. Click for full resolution.</p>
<p>Images are mirrored left to right from the render, into reading orientation: on PHerc. 211 this fitter's flipped
renders run against the winner's reading direction (column correlation -0.996), and mirrored they read as the
winner's map does. "as rendered" links the unmirrored image.</p>
<table><tr><th>#</th><th>winding</th><th>ink share</th><th>largest tile</th><th>tiles</th><th>fit excess</th>
<th>map</th></tr>
{"".join(rows)}</table>
"""
    (out / "index.html").write_text(page)
    return out / "index.html"


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) not in (1, 2):
        print(__doc__, file=sys.stderr)
        return 2
    quality = (
        json.loads(Path(args[1]).read_text())["windings"] if len(args) == 2 else None
    )
    print(build(Path(args[0]), quality))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
