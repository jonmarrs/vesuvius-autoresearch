"""Completion contracts shared by the spiral shell drivers (stdlib only).

A metrics filename or a count of arbitrary meshes is not proof that a stage
completed. Keep these checks beside the drivers so frozen snapshots include them.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def _reject_constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def _counts(row, foreground_key):
    if not isinstance(row, dict):
        raise ValueError("pixel counts must be in a JSON object")
    total, foreground = row.get("total_pixels"), row.get(foreground_key)
    if type(total) is not int or total <= 0:
        raise ValueError("total_pixels must be a positive integer")
    if type(foreground) is not int or not 0 <= foreground <= total:
        raise ValueError(f"{foreground_key} must be an integer between 0 and total_pixels")
    return total, foreground


def validate_metrics(path):
    """Reject incomplete/invalid scorer output; a genuine zero-ink result is valid."""
    with Path(path).open() as f:
        metrics = json.load(f, parse_constant=_reject_constant)
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a JSON object")
    total, foreground = _counts(metrics.get("summary"), "total_fg_pixels")
    strips = metrics.get("strips")
    if not isinstance(strips, list) or not strips:
        raise ValueError("metrics must contain at least one scored strip")
    counts = [_counts(strip, "fg_pixels") for strip in strips]
    if sum(n for n, _ in counts) != total or sum(fg for _, fg in counts) != foreground:
        raise ValueError("summary pixel counts do not match scored strips")


def validate_meshes(directory, first, last, *, exact=False):
    """Require one mesh directory per requested winding, optionally no extras."""
    if first < 0 or last < first:
        raise ValueError("windings must be ordered non-negative integers")
    root = Path(directory)
    if not directory or not root.is_dir():
        raise ValueError(f"no such mesh directory: {directory}")
    expected = {f"{w:03d}" for w in range(first, last + 1)}
    found = {}
    for path in root.iterdir():
        match = re.fullmatch(r"w([0-9]+)_spliced_.+", path.name)
        if match and path.is_dir():
            winding = match[1]
            found[winding] = found.get(winding, 0) + 1
    invalid = sorted(w for w in expected if found.get(w, 0) != 1)
    if invalid:
        raise ValueError(f"expected exactly one mesh for winding(s): {', '.join(invalid)}")
    if exact and set(found) != expected:
        raise ValueError(f"unexpected winding(s): {', '.join(sorted(set(found) - expected))}")


def validate_arm(directory, first, last):
    """A resumable arm must have scores for the requested mesh range."""
    root = Path(directory)
    validate_meshes(root / "meshes", first, last, exact=True)
    validate_metrics(root / "ink_metric/metrics.json")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    metrics = sub.add_parser("metrics")
    metrics.add_argument("path")
    meshes = sub.add_parser("meshes")
    meshes.add_argument("directory")
    meshes.add_argument("first", type=int)
    meshes.add_argument("last", type=int)
    meshes.add_argument("--exact", action="store_true")
    arm = sub.add_parser("arm")
    arm.add_argument("directory")
    arm.add_argument("first", type=int)
    arm.add_argument("last", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "metrics":
            validate_metrics(args.path)
        elif args.command == "arm":
            validate_arm(args.directory, args.first, args.last)
        else:
            validate_meshes(args.directory, args.first, args.last, exact=args.exact)
    except (OSError, ValueError) as exc:
        print(f"[artifact] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
