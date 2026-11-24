"""A look-first page for a Studio band read: its windows in the glyph network's order, the first 10 first (finding 138).

Finding 138 found that at PHerc. 211's prize place the PHerc. 306B team's glyph network ranks a window on the known
text 2nd of 467 in a Studio band read, and that the windows around it are mostly texture. Its registered consequence,
approved by the owner on 2026-11-23: the eligible bands' pages get their windows in glyph order, the first 10 first.
This orders the owner's look; it drops nothing and says nothing about where text is.

usage: look_first.py SUMMARY_DIR GLYPH.json [--first 10]

Reads `glyph.py score`'s record (one entry per window: x0 in render pixels, its share on the sheet, glyph score) and,
in SUMMARY_DIR, `band_index.py`'s images in reading orientation (images_reading/wNNN.png, the map's pixels turned as
orientation.json says). Writes, in SUMMARY_DIR and nowhere else:
- look_first.html: the first windows as crops, then every scored window by rank, each linked to its winding's image;
- look_first/: the crops;
- look_first.json: the order (rank, winding, x0, columns in the reading image, glyph score).
Eligible scrolls' images stay on this machine; nothing here is uploaded.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import glyph  # noqa: E402  (glyph.WIN, glyph.rank: the order finding 138 tested)


def reading_columns(x0: int, width: int, flip_lr: bool) -> tuple[int, int]:
    """The window's columns [a, b) in the reading image: the map's columns, mirrored when the image is."""
    a, b = x0, min(x0 + glyph.WIN, width)
    return (width - b, width - a) if flip_lr else (a, b)


def order(record: dict) -> list[dict]:
    flat = [{"winding": w, **x} for w, xs in record["windings"].items() for x in xs]
    return glyph.rank(flat, "glyph")


def build(summary: Path, record: dict, first: int = 10) -> dict:
    from PIL import Image

    turns = json.loads((summary / "orientation.json").read_text())
    out_dir = summary / "look_first"
    out_dir.mkdir(exist_ok=True)
    rows = []
    for rank, x in enumerate(order(record), start=1):
        w = x["winding"]
        image = summary / "images_reading" / f"{w}.png"
        with Image.open(image) as im:
            width = im.size[0]
            a, b = reading_columns(x["x0"], width, bool(turns[w]["flip_lr"]))
            crop = None
            if rank <= first:
                crop = f"look_first/{rank:03d}_{w}_x{x['x0']}.png"
                im.crop((a, 0, b, im.size[1])).save(summary / crop)
        rows.append({"rank": rank, "winding": w, "x0": x["x0"], "columns_in_reading_image": [a, b],
                     "glyph": x["glyph"], "crop": crop})  # fmt: skip
    record_out = {"first": first, "windows": len(rows), "order": rows}
    (summary / "look_first.json").write_text(json.dumps(record_out, indent=1) + "\n")
    (summary / "look_first.html").write_text(page(rows, first))
    return record_out


def page(rows: list[dict], first: int) -> str:
    e = html.escape
    head = (
        "<!doctype html><meta charset='utf-8'><title>Look first</title>"
        "<style>body{font:14px sans-serif;margin:16px;background:#fff;color:#111}"
        "img{max-width:100%;border:1px solid #999}figure{margin:0 0 24px}td,th{padding:2px 8px;text-align:left}</style>"
        "<h1>Look first: windows in the glyph network's order</h1>"
        "<p>Finding 138: at PHerc. 211's prize place this order put a window on the known text 2nd of 467, among "
        "windows of texture. It orders the look and says nothing about where text is; every winding is still on "
        "<a href='index.html'>the main page</a>. Columns are in the reading image's pixels.</p>"
    )
    figs = "".join(
        f"<figure><img src='{e(r['crop'])}' alt='{e(r['winding'])}'><figcaption>{r['rank']}. "
        f"<a href='images_reading/{e(r['winding'])}.png'>{e(r['winding'])}</a>, columns "
        f"{r['columns_in_reading_image'][0]} to {r['columns_in_reading_image'][1]}</figcaption></figure>"
        for r in rows[:first]
    )
    table = "".join(
        f"<tr><td>{r['rank']}</td><td><a href='images_reading/{e(r['winding'])}.png'>{e(r['winding'])}</a></td>"
        f"<td>{r['columns_in_reading_image'][0]} to {r['columns_in_reading_image'][1]}</td></tr>"
        for r in rows
    )
    return (
        head + f"<h2>The first {first}</h2>" + figs
        + "<h2>Every window, by rank</h2><table><tr><th>rank</th><th>winding</th><th>columns</th></tr>"
        + table + "</table>\n"
    )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("summary", type=Path)
    ap.add_argument("glyph_record", type=Path)
    ap.add_argument("--first", type=int, default=10)
    args = ap.parse_args(argv)
    out = build(args.summary, json.loads(args.glyph_record.read_text()), args.first)
    print(
        f"{args.summary / 'look_first.html'}: {out['windows']} windows, the first {out['first']} as crops"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
