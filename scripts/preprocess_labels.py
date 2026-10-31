#!/usr/bin/env python3
"""Create a review bundle of bounded 2D hole-fill proposals; never adopt labels."""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "src")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="bounded binary PNG")
    parser.add_argument(
        "--out",
        "--output",
        type=Path,
        required=True,
        help="new review directory outside source folders",
    )
    parser.add_argument(
        "--region-mask",
        type=Path,
        help="binary PNG declaring pixels eligible for proposed edits",
    )
    parser.add_argument("--max-hole-pixels", type=int, default=16)
    parser.add_argument("--max-added-pixels", type=int, default=4096)
    parser.add_argument(
        "--connectivity",
        type=int,
        choices=(4, 8),
        default=8,
        help="background connectivity",
    )
    parser.add_argument("--max-pixels", type=int, default=2048**2)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute the bounded proposal and print JSON; create no output",
    )
    parser.add_argument("--alpha", help=argparse.SUPPRESS)
    parser.add_argument("--fill-value", help=argparse.SUPPRESS)
    parser.add_argument("--skip-inner", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--skip-outer", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if (
        args.alpha is not None
        or args.fill_value is not None
        or args.skip_inner
        or args.skip_outer
    ):
        parser.error(
            "spiral inner/outer filling flags are retired for ink PNGs; see docs/LABEL_EDIT_PROPOSALS.md"
        )
    # --help and retired options need neither scientific packages nor Villa.
    from scripts.label_edit_proposals import create_proposal

    try:
        report = create_proposal(
            args.input,
            args.out,
            region_mask=args.region_mask,
            max_hole_pixels=args.max_hole_pixels,
            max_added_pixels=args.max_added_pixels,
            connectivity=args.connectivity,
            max_pixels=args.max_pixels,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError) as exc:
        print(f"Label proposal failed: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print(f"PROPOSAL_ONLY: {args.out.resolve() / 'review.md'}")
        print(
            f"Added {report['counts']['added_pixels']} pixels; training targets have not been adopted."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
