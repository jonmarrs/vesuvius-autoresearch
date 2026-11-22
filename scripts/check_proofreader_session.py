#!/usr/bin/env python3
"""Read-only check of 3D proofreader inputs, progress and saved labels."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument(
        "--verify-approved-patches",
        action="store_true",
        help="check saved TIFF pairs and compare each image with its recorded CT crop",
    )
    parser.add_argument(
        "--verify-edited-labels",
        action="store_true",
        help="check approved TIFF pairs and compare each label with its edited Zarr crop",
    )
    parser.add_argument("--max-source-bytes", type=int, default=8 * 1024**3)
    parser.add_argument("--max-file-bytes", type=int, default=64 * 1024**2)
    parser.add_argument("--max-entries", type=int, default=100_000)
    args = parser.parse_args(argv)
    from vesuvius_autoresearch.core.proofreader_session import verify_record

    try:
        result = verify_record(
            args.session,
            ROOT / "villa/segmentation/vc_proofreader/main.py",
            {
                "max_source_bytes": args.max_source_bytes,
                "max_file_bytes": args.max_file_bytes,
                "max_entries": args.max_entries,
            },
            verify_approved_patches=args.verify_approved_patches,
            verify_edited_labels=args.verify_edited_labels,
        )
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        OverflowError,
    ) as exc:
        print(f"Proofreader session check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
