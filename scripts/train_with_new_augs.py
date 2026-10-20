#!/usr/bin/env python3
"""Wrapper around train.train() for scripts/ablate_scroll_augmentations.py.

It used to swap scroll_augmentations.py's augmentations into train.py for the
Phase 3 ablation. train.py imports them from there itself now, so the swap
replaced the function with itself and is gone; what remains is the seed.

Usage:
    uv run python scripts/train_with_new_augs.py --config <path>.json [--seed N]

CLI mirrors train.py's --config flag plus an optional --seed that pins
torch / numpy / random seeds before train.train() is invoked, so the
ablation can run multiple seeds for statistical confidence.
"""

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True, help="Path to configuration JSON")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional global seed for torch / numpy / random.",
    )
    args = parser.parse_args()

    # Match train.py's own __main__ behavior.
    import torch.multiprocessing as mp

    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass

    # Seed BEFORE importing train (whose import has light RNG side-effects).
    if args.seed is not None:
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        np.random.seed(args.seed)
        random.seed(args.seed)

    from scripts.training import train

    config = train.ExperimentConfig.load(args.config)
    train.train(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
