"""Bounded 2D hole-fill proposals. Morphology does not establish ink ground truth."""

from __future__ import annotations

import hashlib
import io
import json
import platform
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, __version__ as pillow_version

from scripts.data_catalogue import (
    MAX_IMAGE_BYTES,
    artifact_record,
    bounded_integer,
    captured_binary_png,
    markdown_name,
    verify_png_source,
    write_verified_json,
)
from scripts.labeling.label_artifacts import new_output, publish_new
from scripts.text_snapshot import Snapshot

MAX_PIXELS = 2048**2
MAX_HOLES = 256


def settings(max_hole_pixels, max_added_pixels, connectivity, max_pixels):
    pixels = bounded_integer(max_pixels, "max_pixels", MAX_PIXELS)
    hole = bounded_integer(max_hole_pixels, "max_hole_pixels", MAX_PIXELS)
    added = bounded_integer(max_added_pixels, "max_added_pixels", MAX_PIXELS)
    if type(connectivity) is not int or connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8")
    return {
        "max_pixels": pixels,
        "max_hole_pixels": hole,
        "max_added_pixels": added,
        "connectivity": connectivity,
        "max_selected_holes": MAX_HOLES,
    }


def propose_holes(original, region, options):
    """Select whole enclosed background components, never the exterior background.

    The region declares pixels eligible for a proposal. A hole touching unknown
    pixels is rejected in its entirety; the mask never clips or creates a hole.
    """
    original, region = np.asarray(original), np.asarray(region)
    if (
        original.ndim != 2
        or not original.size
        or original.dtype != np.bool_
        or region.dtype != np.bool_
        or region.shape != original.shape
        or original.size > options["max_pixels"]
    ):
        raise ValueError("expected aligned, bounded, nonempty 2D binary arrays")
    count, components, stats, _ = cv2.connectedComponentsWithStats(
        (~original).astype(np.uint8), connectivity=options["connectivity"]
    )
    unknown = np.bincount(components[~region], minlength=count)
    selected: list[int] = []
    holes: list[dict] = []
    rejected = {"border_components": 0, "oversize_holes": 0, "outside_region_holes": 0}
    total = 0
    height, width = original.shape
    for index in range(1, count):
        x, y, w, h, area = map(int, stats[index])
        if x == 0 or y == 0 or x + w == width or y + h == height:
            rejected["border_components"] += 1
            continue
        if area > options["max_hole_pixels"]:
            rejected["oversize_holes"] += 1
            continue
        if unknown[index]:
            rejected["outside_region_holes"] += 1
            continue
        total += area
        if total > options["max_added_pixels"]:
            raise ValueError(
                "proposal exceeds max_added_pixels; choose smaller limits or input"
            )
        if len(selected) >= MAX_HOLES:
            raise ValueError(
                f"proposal exceeds {MAX_HOLES} holes; use an explicit smaller input"
            )
        selected.append(index)
        holes.append({"pixels": area, "bbox_yx": [y, y + h, x, x + w]})
    added = np.isin(components, selected)
    proposal = original | added
    return (
        proposal,
        added,
        {
            "original_positive_pixels": int(original.sum()),
            "proposed_positive_pixels": int(proposal.sum()),
            "added_pixels": int(added.sum()),
            "removed_pixels": 0,
            "eligible_pixels": int(region.sum()),
            "selected_holes": sorted(holes, key=lambda item: item["bbox_yx"]),
            **rejected,
        },
    )


def _write_png(path, values):
    Image.fromarray(values).save(path, format="PNG")
    with Image.open(path) as image:
        if image.format != "PNG" or not np.array_equal(np.asarray(image), values):
            raise ValueError(f"PNG output readback failed: {path}")


def _captured_png(path, *, max_pixels, shape=None):
    values, record = captured_binary_png(path, max_pixels=max_pixels, shape=shape)
    # Bind archival bytes to the same capture the shared decoder hashed.
    path = Path(record["path"])
    with path.open("rb") as stream:
        data = stream.read(MAX_IMAGE_BYTES + 1)
    if (
        len(data) != record["bytes"]
        or hashlib.sha256(data).hexdigest() != record["sha256"]
    ):
        raise ValueError(f"source changed before copying: {path}")
    with Image.open(io.BytesIO(data)) as image:
        if image.n_frames != 1 or "transparency" in image.info:
            raise ValueError("labels must be a single-frame PNG without transparency")
    return values, record, data


def _copy_source(record, data, staging, name):
    target = staging / "sources" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    if artifact_record(target) != {
        "bytes": record["bytes"],
        "sha256": record["sha256"],
    }:
        raise ValueError("source PNG copy verification failed")


def proposal_markdown(report):
    counts = report["counts"]
    lines = [
        "# Label edit proposal — review required",
        "",
        "Status: PROPOSAL_ONLY. This has not been approved or adopted for training.",
        "Enclosed spaces can be valid letter counters. Review the source and each change;",
        "a small hole is not evidence of missing ink. No CT or independent annotation was used.",
        "",
        f"Source: {markdown_name(report['source']['path'])}",
        "",
        f"Positive pixels: {counts['original_positive_pixels']} → {counts['proposed_positive_pixels']}. "
        f"Added: {counts['added_pixels']}; removed: 0; holes: {len(counts['selected_holes'])}.",
        "",
        "Preview: white = original positives, orange = proposed additions, black = background.",
        "Images use the complete source grid; no thumbnail resampling was applied.",
        "",
        "![Original binary labels](original.png)",
        "",
        "![Proposed additions in orange](preview.png)",
        "",
        "[Proposed binary image](proposed.png) · [Added pixels only](added.png)",
        "",
        "| Hole | Added pixels | Bounding box: y0, y1, x0, x1 (exclusive stops) |",
        "|---|---:|---|",
    ]
    for index, hole in enumerate(counts["selected_holes"], 1):
        lines.append(f"| {index} | {hole['pixels']} | {hole['bbox_yx']} |")
    lines.extend(
        [
            "",
            "The JSON records thresholds, background connectivity, rejected components,",
            "runtime versions, source/code captures and output hashes. No file here is named",
            "inklabels_refined.png or inklabels_filled.png. Adoption needs a separate reviewed",
            "data change and, if validation targets change, an incumbent re-score.",
            "",
        ]
    )
    return "\n".join(lines)


def create_proposal(
    input_path,
    output,
    *,
    region_mask=None,
    max_hole_pixels=16,
    max_added_pixels=4096,
    connectivity=8,
    max_pixels=MAX_PIXELS,
    dry_run=False,
):
    options = settings(max_hole_pixels, max_added_pixels, connectivity, max_pixels)
    input_path = Path(input_path).absolute()
    masks = [input_path] + (
        [Path(region_mask).absolute()] if region_mask is not None else []
    )
    # Prevent both overwrites and new automatically preferred training paths.
    output = new_output(output, *(path.resolve().parent for path in masks))
    if output.suffix.lower() in {".png", ".tif", ".tiff", ".zarr"}:
        raise ValueError(
            "output must be a new review directory, not an image or dataset path"
        )
    original, source, source_bytes = _captured_png(
        input_path, max_pixels=options["max_pixels"]
    )
    region_record = None
    region_bytes = None
    region = np.ones_like(original)
    if region_mask is not None:
        region, region_record, region_bytes = _captured_png(
            masks[1], max_pixels=options["max_pixels"], shape=original.shape
        )
        if not region.any():
            raise ValueError("region mask must contain eligible pixels")
    code = {
        name: Snapshot.read(Path(__file__).with_name(name), 256 * 1024)
        for name in (
            "label_edit_proposals.py",
            "preprocess_labels.py",
            "refine_labels_villa.py",
        )
    }
    proposal, added, counts = propose_holes(original, region, options)
    report = {
        "contract": 1,
        "status": "DRY_RUN" if dry_run else "PROPOSAL_ONLY",
        "approved": False,
        "training_ready": False,
        "annotation_quality_verified": False,
        "ct_alignment_verified": False,
        "scope": "2D enclosed-background edit proposal; no CT or independent annotation",
        "shape_yx": list(original.shape),
        "source": source,
        "region_mask": region_record,
        "region_policy": "whole hole must be eligible; omitted region means the full image",
        "settings": options,
        "counts": counts,
        "algorithm": "enclosed background components, filtered by size and eligibility; adds only",
        "code": {name: item.provenance() for name, item in code.items()},
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "opencv": cv2.__version__,
            "pillow": pillow_version,
        },
        "artifacts": {},
    }

    def verify():
        verify_png_source(source)
        if region_record is not None:
            verify_png_source(region_record)
        for snapshot in code.values():
            snapshot.verify()

    if dry_run:
        verify()
        return report
    with publish_new(output) as staging:
        _copy_source(source, source_bytes, staging, "input.png")
        if region_record is not None:
            _copy_source(region_record, region_bytes, staging, "region.png")
        for name, snapshot in code.items():
            snapshot.copy_into(staging, name)
        preview = np.repeat((original.astype(np.uint8) * 255)[..., None], 3, axis=2)
        preview[added] = [255, 128, 0]
        for name, values in {
            "original.png": original,
            "proposed.png": proposal,
            "added.png": added,
        }.items():
            _write_png(staging / name, values.astype(np.uint8) * 255)
        _write_png(staging / "preview.png", preview)
        markdown = proposal_markdown(report)
        (staging / "review.md").write_text(markdown, encoding="utf-8")
        if (staging / "review.md").read_text(encoding="utf-8") != markdown:
            raise ValueError("review Markdown readback failed")
        report["artifacts"] = {
            path.relative_to(staging).as_posix(): artifact_record(path)
            for path in sorted(staging.rglob("*"))
            if path.is_file()
        }
        verify()
        for name, expected in report["artifacts"].items():
            if artifact_record(staging / name) != expected:
                raise ValueError(
                    f"proposal artifact changed before publication: {name}"
                )
        # A killed build before the rechecks must not leave a completion report.
        write_verified_json(staging / "proposal.json", report)
    return report
