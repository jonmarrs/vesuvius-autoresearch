#!/usr/bin/env python3
"""Pin and import aligned local TIFF layers and binary PNG labels into a new CT training fragment."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser(
        "plan", help="verify local inputs and write a new hashed manifest"
    )
    plan.add_argument("--layers", type=Path, required=True)
    plan.add_argument("--labels", type=Path, required=True)
    plan.add_argument("--mask", type=Path)
    plan.add_argument("--z-start", type=int, required=True)
    plan.add_argument(
        "--z-stop", type=int, required=True, help="exclusive source slice index"
    )
    plan.add_argument(
        "--aligned-labels",
        action="store_true",
        help="declare independently verified matching XY labels",
    )
    plan.add_argument(
        "--output", type=Path, required=True, help="new manifest JSON path"
    )
    build = commands.add_parser(
        "build", help="create a new fragment from a pinned manifest"
    )
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument(
        "--output", type=Path, required=True, help="new fragment directory"
    )
    for command in (plan, build):
        command.add_argument("--max-file-bytes", type=int, default=512 * 1024**2)
        command.add_argument("--max-pixels", type=int, default=160 * 1024**2)
        command.add_argument("--max-volume-bytes", type=int, default=1024**3)
    args = parser.parse_args(argv)
    from scripts.candidate_artifacts import ARTIFACT_ERRORS
    from vesuvius_autoresearch.core.surface_volume_import import (
        build_import,
        plan_import,
        write_plan,
    )

    limits = {
        "max_file_bytes": args.max_file_bytes,
        "max_pixels": args.max_pixels,
        "max_volume_bytes": args.max_volume_bytes,
    }
    try:
        if args.command == "plan":
            value = plan_import(
                args.layers,
                args.labels,
                args.z_start,
                args.z_stop,
                mask=args.mask,
                aligned_labels=args.aligned_labels,
                **limits,
            )
            result = write_plan(value, args.output)
        else:
            result = build_import(args.manifest, args.output, **limits)
        print(json.dumps({"status": "complete", "path": str(result)}, allow_nan=False))
        return 0
    except ARTIFACT_ERRORS as exc:
        print(f"surface volume import: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
