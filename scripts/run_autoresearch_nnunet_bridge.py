#!/usr/bin/env python3
"""Retired nnUNet bridge prototype; no configuration or training is produced."""

import argparse
import sys

NOTICE = (
    "This nnUNet bridge is retired. It only wrote a fixed temporary YAML, "
    "discarded other template parameters and could overwrite its own input; "
    "it never generated trainers or ran training. No configuration was read "
    "or changed. Inspect the pinned Villa segmentation/model_optimization_framework "
    "README and use an explicitly reviewed configuration for that separate "
    "workflow. See docs/UNSUPPORTED_LAUNCHERS.md for retained source and limits."
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default="configs/config_nnunet.yml", help="legacy input; not read"
    )
    parser.add_argument("--evolve-attr", help="legacy flag; no mutation performed")
    parser.add_argument("--evolve-val", help="legacy flag; no mutation performed")
    parser.add_argument("--variant-name", help="legacy flag; no variant generated")
    parser.parse_args(argv)
    print(NOTICE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
