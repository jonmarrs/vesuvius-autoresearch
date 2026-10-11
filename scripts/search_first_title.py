#!/usr/bin/env python3
"""Retired simulated First Title search; no title detection is implemented."""

import argparse
import sys

UNIMPLEMENTED_MESSAGE = (
    "First Title search is not implemented. The previous launcher only simulated "
    "scans and reported zero candidates without inference or evidence. "
    "No scan, detection, prediction export or absence measurement has run. "
    "For explicit regional model predictions, use scripts/inference/ensemble_predict.py "
    "with real checkpoints and a specified CT region; inspect and validate results "
    "before making any title or legibility claim."
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scrolls", nargs="+", help="legacy option; search remains unimplemented"
    )
    parser.add_argument(
        "--batch_size",
        "--batch-size",
        type=int,
        help="legacy option; search remains unimplemented",
    )
    parser.parse_args(argv)
    print(UNIMPLEMENTED_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
