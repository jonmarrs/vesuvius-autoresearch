#!/usr/bin/env python3
"""Retired unvalidated Thaumato solver sweep; retained as an explicit failure."""

import argparse
import sys

RETIRED_MESSAGE = (
    "The legacy Thaumato solver sweep is retired. Its Python PKL adapter does not "
    "match the vendored graph format/units, mesh selection can reuse old output, "
    "and texture variance does not establish winding correctness or ink legibility. "
    "Use scripts/sheet_stitcher.py for bounded JSON relative-angle diagnostics. "
    "Those reports are not solved Thaumato graphs or a mesh/render pipeline."
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(RETIRED_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
