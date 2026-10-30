"""Captured selection inputs and new, staged symlink datasets (stdlib only)."""

import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

from scripts.text_snapshot import Snapshot

MANIFEST = ".autoresearch-selection.json"
MAX_PATCHES = 100_000
MAX_REFERENCE_BYTES = 64 * 1024**2
MAX_META_BYTES = 256 * 1024


def number(value, name, lower=0, upper=None):
    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError):
        finite = False
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not finite
        or (lower is not None and value < lower)
        or (upper is not None and value > upper)
    ):
        raise ValueError(f"{name} must be finite and in the supported range")
    return value


def patch_id(value):
    if (
        not isinstance(value, str)
        or value in ("", ".", "..")
        or any(c in value for c in ("/", "\\", "\0"))
    ):
        raise ValueError(f"patch ID must be one safe directory name: {value!r}")
    return value


def capture_json(path, limit):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON field: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    source = Snapshot.read(path, limit)
    try:
        data = json.loads(
            source.text(), object_pairs_hook=unique, parse_constant=reject
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting is too deep") from exc
    return source, data


def reference_patches(path):
    source, data = capture_json(path, MAX_REFERENCE_BYTES)
    rows = data.get("patches") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_PATCHES:
        raise ValueError(f"reference must contain 1..{MAX_PATCHES} patches")
    result = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or not {"id", "fraction", "total_area"} <= row.keys()
        ):
            raise ValueError("reference patches need id, fraction and total_area")
        pid = patch_id(row["id"])
        if pid in result:
            raise ValueError(f"duplicate patch ID: {pid}")
        result[pid] = (
            number(row["fraction"], "fraction", upper=1),
            number(row["total_area"], "total_area"),
        )
    if number(sum(area for _, area in result.values()), "total reference area") <= 0:
        raise ValueError("total reference area must be positive")
    return source, result


def entries(directory):
    result = []
    with os.scandir(directory) as stream:
        for entry in stream:
            if len(result) >= MAX_PATCHES * 2:
                raise ValueError("dataset entry limit exceeded")
            result.append(Path(entry.path))
    return sorted(result)


def distinct_patch_targets(targets):
    """Different IDs must not count the same physical patch directory twice."""
    seen = {}
    for pid, target in targets.items():
        info = Path(target).stat()
        identity = (info.st_dev, info.st_ino)
        if identity in seen:
            raise ValueError(
                f"patch IDs {seen[identity]} and {pid} resolve to the same directory"
            )
        seen[identity] = pid


def dataset_links(source, ids):
    root = Path(source).resolve(strict=True)
    if not root.is_dir() or not (root / "verified_patches").is_dir():
        raise ValueError(f"dataset needs a verified_patches directory: {root}")
    auxiliary = {}
    for path in entries(root):
        if path.name == "verified_patches":
            continue
        if path.name == MANIFEST:
            raise ValueError(
                "source already has a selection manifest; use the original full dataset"
            )
        auxiliary[path.name] = path.resolve(strict=True)
    patches = {}
    for pid in ids:
        path = (root / "verified_patches" / patch_id(pid)).resolve(strict=True)
        if not path.is_dir():
            raise ValueError(f"scored patch must be a directory: {pid}")
        patches[pid] = path
    distinct_patch_targets(patches)
    return root, auxiliary, patches


def geometry(root, ids):
    boxes, records = {}, []
    for pid in sorted(ids):
        requested = root / "verified_patches" / pid / "meta.json"
        source, data = capture_json(requested, MAX_META_BYTES)
        box = data.get("bbox") if isinstance(data, dict) else None
        if (
            not isinstance(box, list)
            or len(box) != 2
            or any(not isinstance(v, list) or len(v) != 3 for v in box)
        ):
            raise ValueError(f"patch {pid} needs a 2x3 XYZ bbox")
        for point in box:
            for value in point:
                number(value, f"patch {pid} bbox", lower=None)
        if any(lo > hi for lo, hi in zip(*box, strict=True)):
            raise ValueError(f"patch {pid} bbox is reversed")
        boxes[pid] = box
        records.append({"id": pid, "input_path": str(requested), **source.provenance()})
    return boxes, records


def verify_geometry(records):
    for record in records:
        if str(Path(record["input_path"]).resolve()) != record["path"]:
            raise ValueError("patch metadata mapping changed before publication")
        current = Snapshot.read(record["path"], MAX_META_BYTES).provenance()
        if any(current[key] != record[key] for key in ("path", "sha256", "bytes")):
            raise ValueError("patch metadata changed before publication")


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def publish_dataset(links, output, selected, manifest, *, inputs=(), verify):
    root, auxiliary, patches = links
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing existing output: {output}")
    output = output.resolve()
    for source in (
        root,
        root / "verified_patches",
        *auxiliary.values(),
        *patches.values(),
        *map(Path, inputs),
    ):
        source = source.resolve()
        if source == output or source in output.parents or output in source.parents:
            raise ValueError("output must not overlap dataset inputs")
    selected = sorted(selected)
    if (
        not selected
        or len(set(selected)) != len(selected)
        or set(selected) - patches.keys()
    ):
        raise ValueError(
            "selection must contain distinct source patches and be nonempty"
        )
    facts = {
        "schema": "patch-dataset-selection-v1",
        "status": "PREPARED",
        "source": str(root),
        "selected_ids": selected,
        "selected_ids_sha256": fingerprint(selected),
        "payloads_copied": False,
    }
    if facts.keys() & manifest.keys():
        raise ValueError("selection metadata must not overwrite dataset facts")
    manifest = {**manifest, **facts}
    encoded = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    staging = workspace / "dataset"
    try:
        (staging / "verified_patches").mkdir(parents=True)
        for name, target in auxiliary.items():
            os.symlink(target, staging / name, target_is_directory=target.is_dir())
        for pid in selected:
            os.symlink(
                patches[pid],
                staging / "verified_patches" / pid,
                target_is_directory=True,
            )
        (staging / MANIFEST).write_text(encoded, encoding="utf-8")
        current = dataset_links(root, patches)
        if current != links:
            raise ValueError("dataset link mappings changed before publication")
        verify()
        if output.exists() or output.is_symlink():
            raise ValueError("output appeared during preparation")
        staging.rename(output)
    finally:
        shutil.rmtree(workspace)
    return manifest
