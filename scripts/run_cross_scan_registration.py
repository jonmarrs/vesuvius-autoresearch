#!/usr/bin/env python3
"""Retired registration prototype; no alignment or transform is produced."""

import argparse
import sys

NOTICE = (
    "This registration launcher is retired. It never called align_zarrs or "
    "saved a transform, despite reporting success. No volume was opened and "
    "no output was created. For manual alignment, use the pinned Villa "
    "foundation/volume-registration/find_transform.py and its README; review "
    "voxel sizes, axis conventions and landmark residuals. See "
    "docs/UNSUPPORTED_LAUNCHERS.md for the source and migration limits."
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed", required=True, help="legacy input; not opened")
    parser.add_argument("--moving", required=True, help="legacy input; not opened")
    parser.add_argument(
        "--out",
        default="registration/transform.json",
        help="legacy output; not written",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="legacy flag; automatic alignment was not implemented",
    )
    parser.parse_args(argv)
    print(NOTICE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
