"""Explain the supported workflow without importing GPU libraries or writing."""

import argparse

MESSAGE = (
    "This legacy figure generator is retired. Use python -m "
    "vesuvius_autoresearch.fibers.cli for maintained fiber filtering; "
    "see docs/FIBER_DETECTION.md. Historical source is preserved under "
    "scripts/archive/legacy_figures and is not validated research evidence."
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=MESSAGE)
    parser.parse_args(argv)
    parser.error(MESSAGE)
