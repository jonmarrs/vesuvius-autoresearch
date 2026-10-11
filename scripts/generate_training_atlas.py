#!/usr/bin/env python3
"""Publish a bounded binary-label overview with explicit inspection limits."""

from __future__ import annotations

import argparse
import json
import stat
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from scripts.data_catalogue import (
    MAX_CANDIDATE_ENTRIES,
    MAX_FRAGMENTS,
    MAX_IMAGE_PIXELS,
    artifact_record,
    bounded_integer,
    captured_binary_png,
    default_output,
    display_name,
    fingerprint,
    fragment_snapshot,
    local_root,
    verify_png_source,
    write_verified_json,
)
from scripts.labeling.label_artifacts import new_output, publish_new

THUMBNAIL_SIZE = 512
DPI = 150


def inspect_fragment(root, entry, max_pixels):
    directory = root / entry["name"]
    labels, label_source = captured_binary_png(
        directory / "inklabels.png", max_pixels=max_pixels
    )
    record = {
        "name": entry["name"],
        "shape_yx": list(labels.shape),
        "ink_pixels": int(np.count_nonzero(labels)),
        "labels": label_source,
        "mask": None,
        "mask_status": "absent",
        "mask_pixels": None,
        "ink_inside_mask": None,
        "ink_outside_mask": None,
    }
    name = display_name(entry["name"])
    record["caption_name"] = name[:69] + "..." if len(name) > 72 else name
    record["caption_truncated"] = record["caption_name"] != name
    if entry["mask"] is not None:
        mask, source = captured_binary_png(
            directory / "mask.png", max_pixels=max_pixels, shape=labels.shape
        )
        count = int(np.count_nonzero(mask))
        if not count:
            raise ValueError(f"mask must contain positive pixels: {directory}")
        record.update(
            mask=source,
            mask_status="binary_shape_checked",
            mask_pixels=count,
            ink_inside_mask=int(np.count_nonzero(labels & mask)),
            ink_outside_mask=int(np.count_nonzero(labels & ~mask)),
        )
    # Exact counts above use the full bounded source. Thumbnails only illustrate it.
    with Image.fromarray(labels.astype(np.uint8) * 255) as preview:
        preview.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.NEAREST)
        thumbnail = np.asarray(preview).copy()
    record["thumbnail_shape_yx"] = list(thumbnail.shape)
    return record, thumbnail


def render_atlas(staging, thumbnails, report):
    rows = (len(thumbnails) + 2) // 3
    figure = Figure(figsize=(15, 4 * rows + 1), dpi=DPI, facecolor="white")
    FigureCanvasAgg(figure)
    try:
        axes = figure.subplots(rows, 3, squeeze=False).ravel()
        for axis, thumbnail, record in zip(
            axes[: len(thumbnails)], thumbnails, report["fragments"], strict=True
        ):
            axis.imshow(
                thumbnail, cmap="gray", vmin=0, vmax=255, interpolation="nearest"
            )
            caption = record["caption_name"]
            lines = [
                caption[start : start + 36] for start in range(0, len(caption), 36)
            ]
            name = "\n".join(lines + [""] * (2 - len(lines)))
            axis.set_anchor("N")
            mask_status = (
                "Mask: binary + shape checked" if record["mask"] else "Mask: absent"
            )
            axis.set_title(
                f"{name}\n{record['shape_yx']} YX; ink pixels: {record['ink_pixels']}\n"
                f"{mask_status}",
                fontsize=10,
                color="black",
                fontfamily="DejaVu Sans",
                parse_math=False,
            )
            axis.set_axis_off()
        for axis in axes[len(thumbnails) :]:
            axis.set_axis_off()
        figure.suptitle(
            "Recorded ink label overview\n"
            "Array inspection only; CT registration, ground truth and training readiness not assessed\n"
            "Nearest-neighbor previews; full names and source facts in atlas.json",
            fontsize=13,
            color="black",
            fontfamily="DejaVu Sans",
            parse_math=False,
        )
        figure.tight_layout(rect=(0, 0, 1, 0.90))
        description = json.dumps(
            {
                "scope": report["scope"],
                "metadata_sha256": report["metadata_sha256"],
                "source_root": report["source"]["root"],
                "selection": report["selection"],
                "fragments": [
                    {
                        "name": item["name"],
                        "labels": item["labels"]["sha256"],
                        "mask": item["mask"]["sha256"] if item["mask"] else None,
                    }
                    for item in report["fragments"]
                ],
            },
            sort_keys=True,
            allow_nan=False,
        )
        # Explicit bounds prevent a caller's savefig.bbox='tight' from changing canvas size.
        bounds = figure.bbox_inches.frozen()
        figure.savefig(
            staging / "atlas.png",
            dpi=DPI,
            bbox_inches=bounds,
            metadata={"Description": description},
            facecolor="white",
        )
        figure.savefig(
            staging / "atlas.svg",
            dpi=DPI,
            bbox_inches=bounds,
            metadata={"Description": description},
            facecolor="white",
        )
        canvas = [int(round(15 * DPI)), int(round((4 * rows + 1) * DPI))]
        with Image.open(staging / "atlas.png") as image:
            image.load()
            if image.format != "PNG" or list(image.size) != canvas:
                raise ValueError("atlas PNG verification failed")
            if image.info.get("Description") != description:
                raise ValueError("atlas PNG provenance verification failed")
        svg = ET.parse(staging / "atlas.svg").getroot()
        if svg.tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError("atlas SVG verification failed")
        descriptions = svg.findall(".//{http://purl.org/dc/elements/1.1/}description")
        if len(descriptions) != 1 or descriptions[0].text != description:
            raise ValueError("atlas SVG provenance verification failed")
        return canvas
    finally:
        figure.clear()


def generate_atlas(
    root="local_data",
    output=None,
    *,
    limit=12,
    max_pixels=2048**2,
    max_entries=MAX_CANDIDATE_ENTRIES,
):
    limit = bounded_integer(limit, "limit", MAX_FRAGMENTS)
    max_pixels = bounded_integer(max_pixels, "max_pixels", MAX_IMAGE_PIXELS)
    max_entries = bounded_integer(max_entries, "max_entries", MAX_CANDIDATE_ENTRIES)
    root = local_root(root)
    output = new_output(
        output if output is not None else default_output("label_atlas"), root
    )
    snapshot = fragment_snapshot(root, max_entries)
    candidates = [
        entry
        for entry in snapshot["entries"]
        if stat.S_ISDIR(entry["mode"]) and entry["labels"] is not None
    ]
    if not candidates:
        raise ValueError("no inklabels.png candidates found")
    records, thumbnails = [], []
    for entry in candidates[:limit]:
        record, thumbnail = inspect_fragment(root, entry, max_pixels)
        records.append(record)
        thumbnails.append(thumbnail)
    report = {
        "contract": 1,
        "scope": "binary arrays and optional mask shapes only; CT registration, ground truth "
        "and training readiness not assessed",
        "source": snapshot,
        "metadata_sha256": fingerprint(snapshot),
        "selection": {
            "rule": "first directory names with inklabels.png entries, sorted lexicographically",
            "candidate_count": len(candidates),
            "selected_count": len(records),
            "uninspected_candidates": len(candidates) - len(records),
        },
        "limits": {
            "limit": limit,
            "max_pixels": max_pixels,
            "max_entries": max_entries,
        },
        "thumbnail": {
            "method": "nearest",
            "max_side": THUMBNAIL_SIZE,
            "scope": "illustration only; resampling can omit features",
        },
        "fragments": records,
    }
    with publish_new(output) as staging:
        report["canvas_wh"] = render_atlas(staging, thumbnails, report)
        report["artifacts"] = {
            name: artifact_record(staging / name) for name in ("atlas.png", "atlas.svg")
        }
        write_verified_json(staging / "atlas.json", report)
        for record in records:
            verify_png_source(record["labels"])
            if record["mask"] is not None:
                verify_png_source(record["mask"])
        if fragment_snapshot(root, max_entries) != snapshot:
            raise ValueError("atlas source listing changed before publication")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("local_data"))
    parser.add_argument("--out", type=Path, help="new, separate output directory")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--max-pixels", type=int, default=2048**2)
    parser.add_argument("--max-entries", type=int, default=MAX_CANDIDATE_ENTRIES)
    args = parser.parse_args(argv)
    try:
        output = generate_atlas(
            args.root,
            args.out,
            limit=args.limit,
            max_pixels=args.max_pixels,
            max_entries=args.max_entries,
        )
    except (OSError, ValueError) as exc:
        print(f"Atlas failed: {exc}", file=sys.stderr)
        return 1
    print(f"Label atlas saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
