#!/usr/bin/env python3
"""Retired automatic flattening selector; no validated selection metric exists."""

import argparse
import sys

UNSUPPORTED_MESSAGE = (
    "Automatic flattening selection is unsupported. The old sweep used an "
    "incompatible vc_flatten command, fell back to file size as a quality score, "
    "and recorded temporary mesh paths that were deleted. No flattening or "
    "quality measurement has run. The pinned native vc_flatten accepts a Tifxyz "
    "directory and supports --iterations and --lscm-only; inspect its --help "
    "and validate geometry and rendered output independently. See "
    "docs/MESH_PREPARATION.md for supported mesh sampling and migration."
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True, help="legacy input; selector is unsupported"
    )
    parser.add_argument(
        "--output", required=True, help="legacy output; no artifact is written"
    )
    parser.parse_args(argv)
    print(UNSUPPORTED_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
