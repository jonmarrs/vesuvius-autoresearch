"""Inspect or fetch one explicit public teacher prediction into a verified cache."""

import argparse
import json
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix", required=True, help="public ink-detection bucket prefix"
    )
    parser.add_argument("--out", required=True, help="local teacher bundle directory")
    parser.add_argument(
        "--source", help="exact TIFF basename; required for ambiguous listings"
    )
    parser.add_argument("--max-bytes", type=int, default=2 * 1024**3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        from .teacher_artifacts import fetch_teacher

        result = fetch_teacher(
            args.prefix,
            args.out,
            source=args.source,
            max_bytes=args.max_bytes,
            dry_run=args.dry_run,
        )
        print(json.dumps(result if args.dry_run else {"teacher": result}, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"teacher cache failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
