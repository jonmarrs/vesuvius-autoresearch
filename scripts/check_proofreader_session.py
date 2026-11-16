#!/usr/bin/env python3
"""Rehash a recorded 3D proofreader session's inputs and check logged context.

Read-only: does not resume the GUI, verify approved TIFFs or feed ink training.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
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
