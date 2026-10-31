"""Bounded local catalogue inputs, source fingerprints and report publication."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import os
import stat
import warnings
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.candidate_artifacts import integer, write_json
from scripts.pseudo_label_artifacts import read_png

MAX_ENTRIES = 100_000
MAX_DEPTH = 32
MAX_CANDIDATE_ENTRIES = 4096
MAX_IMAGE_BYTES = 16 * 1024**2
MAX_IMAGE_PIXELS = 4096**2
MAX_FRAGMENTS = 24


def bounded_integer(value, name, maximum):
    if isinstance(value, np.bool_):
        raise ValueError(f"{name} must be an integer")
    result = integer(value, name, 1)
    if result > maximum:
        raise ValueError(f"{name} must not exceed {maximum}")
    return result


def local_root(path):
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"root must be a regular directory, not a symlink: {path}")
    return path.resolve()


def signature(path):
    try:
        result = Path(path).lstat()
    except FileNotFoundError:
        return None
    return {
        "mode": result.st_mode,
        "bytes": result.st_size,
        "mtime_ns": result.st_mtime_ns,
        "inode": result.st_ino,
        "device": result.st_dev,
    }


def children(path, remaining):
    """Bound enumeration itself before sorting; never follow entry symlinks."""
    entries = []
    with os.scandir(path) as stream:
        for entry in stream:
            if len(entries) >= remaining:
                raise ValueError(f"entry budget exceeded while listing {path}")
            entries.append(Path(entry.path))
    return sorted(entries, key=lambda entry: entry.name)


def fingerprint(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def inventory_snapshot(root, max_entries=MAX_ENTRIES, max_depth=MAX_DEPTH):
    root = local_root(root)
    limit = bounded_integer(max_entries, "max_entries", MAX_ENTRIES)
    depth_limit = bounded_integer(max_depth, "max_depth", MAX_DEPTH)
    root_signature = signature(root)
    entries = []
    stack = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        current = signature(directory)
        if current is None or not stat.S_ISDIR(current["mode"]):
            raise ValueError(f"directory changed while scanning: {directory}")
        subdirectories = []
        for path in children(directory, limit - len(entries)):
            info = signature(path)
            if info is None:
                raise ValueError(f"entry disappeared while scanning: {path}")
            mode = info["mode"]
            if stat.S_ISLNK(mode):
                kind = "symlink_not_followed"
            elif stat.S_ISREG(mode):
                kind = "regular_file"
            elif stat.S_ISDIR(mode):
                kind = "directory"
                if depth + 1 > depth_limit:
                    raise ValueError(f"max_depth={depth_limit} exceeded: {path}")
                subdirectories.append((path, depth + 1))
            else:
                kind = "special_file_not_read"
            entries.append(
                {"path": path.relative_to(root).as_posix(), "kind": kind, **info}
            )
        stack.extend(reversed(subdirectories))
    return {"root": str(root), "root_signature": root_signature, "entries": entries}


def fragment_snapshot(root, max_entries=MAX_CANDIDATE_ENTRIES):
    root = local_root(root)
    limit = bounded_integer(max_entries, "max_entries", MAX_CANDIDATE_ENTRIES)
    root_signature = signature(root)
    entries = []
    for path in children(root, limit):
        info = signature(path)
        if info is None:
            raise ValueError(f"entry disappeared while discovering: {path}")
        record = {"name": path.name, **info}
        if stat.S_ISDIR(info["mode"]):
            record["labels"] = signature(path / "inklabels.png")
            record["mask"] = signature(path / "mask.png")
        entries.append(record)
    return {"root": str(root), "root_signature": root_signature, "entries": entries}


def captured_binary_png(path, *, max_pixels, shape=None):
    max_pixels = bounded_integer(max_pixels, "max_pixels", MAX_IMAGE_PIXELS)
    path = Path(path)
    before = signature(path)
    if before is None or not stat.S_ISREG(before["mode"]):
        raise ValueError(f"PNG source must be a regular file, not a symlink: {path}")
    if before["bytes"] > MAX_IMAGE_BYTES:
        raise ValueError(f"PNG source exceeds {MAX_IMAGE_BYTES} bytes: {path}")
    with path.open("rb") as stream:
        data = stream.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"PNG source exceeds {MAX_IMAGE_BYTES} bytes: {path}")
    if signature(path) != before:
        raise ValueError(f"PNG source changed while reading: {path}")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            values = read_png(
                io.BytesIO(data), kind="binary", shape=shape, max_pixels=max_pixels
            )
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError(f"PNG exceeds Pillow image safety limits: {path}") from exc
    # Pillow reports some damaged chunks as SyntaxError.
    except (OSError, SyntaxError, ValueError) as exc:
        raise ValueError(f"invalid binary PNG {path}: {exc}") from exc
    return values, {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "signature": before,
    }


def verify_png_source(record):
    path = Path(record["path"])
    if signature(path) != record["signature"]:
        raise ValueError(f"PNG source changed before publication: {path}")
    with path.open("rb") as stream:
        data = stream.read(MAX_IMAGE_BYTES + 1)
    if (
        signature(path) != record["signature"]
        or len(data) != record["bytes"]
        or hashlib.sha256(data).hexdigest() != record["sha256"]
    ):
        raise ValueError(f"PNG source changed before publication: {path}")


def display_name(value):
    """Keep filenames on one caption/table line; show control characters literally."""
    return "".join(
        character if character.isprintable() else repr(character)[1:-1]
        for character in str(value)
    )


def markdown_name(value):
    escaped = html.escape(display_name(value))
    for character in "|`*_[]\\":
        escaped = escaped.replace(character, f"&#{ord(character)};")
    return "<code>" + escaped + "</code>"


def default_output(kind):
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return Path("reports") / f"{kind}_{stamp}"


def artifact_record(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def write_verified_json(path, report):
    write_json(path, report)
    if json.loads(path.read_text(encoding="utf-8")) != report:
        raise ValueError("catalogue JSON verification failed")
