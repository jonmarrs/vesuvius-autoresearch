#!/usr/bin/env python3
"""Build a visual contact sheet for Vesuvius prize candidate evidence."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def _candidate_dirs(root):
    return sorted(Path(root).glob("candidate_*"))


def _load_manifest(candidate_dir):
    path = candidate_dir / "manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _label_for(candidate_dir, manifest):
    candidate = manifest.get("candidate") or {}
    parts = [
        candidate_dir.name,
        str(candidate.get("scroll_id") or ""),
        str(candidate.get("division") or ""),
        "z={}".format(candidate.get("z", "")),
        "score={}".format(candidate.get("review_score", "")),
    ]
    return " | ".join(
        part for part in parts if part and part != "z=" and part != "score="
    )


def _prediction_image_path(candidate_dir, manifest):
    path = manifest.get("prediction_image")
    if path:
        p = Path(path)
        if p.exists():
            return p
    predictions = candidate_dir / "predictions"
    matches = sorted(predictions.glob("*.png"))
    matches = [p for p in matches if not p.name.endswith(("_ink.png", "_fiber.png"))]
    return matches[0] if matches else None


def build_contact_sheet(root, out_path, thumb_width=480, label_height=34, columns=2):
    tiles = []
    for candidate_dir in _candidate_dirs(root):
        manifest = _load_manifest(candidate_dir)
        image_path = _prediction_image_path(candidate_dir, manifest)
        if not image_path:
            continue
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            scale = thumb_width / image.width
            thumb_height = max(1, int(image.height * scale))
            thumb = image.resize((thumb_width, thumb_height))
        tile = Image.new("RGB", (thumb_width, thumb_height + label_height), "white")
        tile.paste(thumb, (0, label_height))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 8), _label_for(candidate_dir, manifest), fill="black")
        tiles.append(tile)

    if not tiles:
        raise FileNotFoundError(f"No candidate prediction images found under {root}")

    columns = max(1, columns)
    rows = (len(tiles) + columns - 1) // columns
    tile_width = max(tile.width for tile in tiles)
    tile_height = max(tile.height for tile in tiles)
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), "white")

    for index, tile in enumerate(tiles):
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        sheet.paste(tile, (x, y))

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return {"out": str(out), "candidates": len(tiles), "columns": columns, "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="reports/scroll23_evidence")
    parser.add_argument("--out", default="reports/scroll23_candidate_contact_sheet.png")
    parser.add_argument("--thumb-width", type=int, default=480)
    parser.add_argument("--columns", type=int, default=2)
    args = parser.parse_args()

    print(
        json.dumps(
            build_contact_sheet(
                args.root, args.out, args.thumb_width, columns=args.columns
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
