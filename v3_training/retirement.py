"""Read-only compatibility message for the archived v3 training launchers."""

import argparse

MESSAGE = (
    "The v3 training CLI is retired. Use uv run python scripts/training/train.py "
    "--config <ExperimentConfig.json> for maintained training. The old v3 YAML "
    "files are not interchangeable with ExperimentConfig; see v3_training/README.md."
)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="v3-training", description=MESSAGE)
    parser.add_argument("config", nargs="?", help="archived YAML path (never opened)")
    parser.parse_args(argv)
    parser.error(MESSAGE)
