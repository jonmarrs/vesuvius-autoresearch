"""Run one isolated repeatability trial through the existing training function."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def run(config_path):
    from scripts.training.config import ExperimentConfig
    from vesuvius_autoresearch.core.checkpoint_tools import load_tool_checkpoint

    config_path = Path(config_path).resolve()
    workspace = config_path.parent
    config = ExperimentConfig.load(config_path)
    if (
        Path(config.checkpoint_out or "").resolve() != workspace / "candidate.pt"
        or Path(config.cache_dir or "").resolve() != workspace / "cache"
        or config.use_wandb
    ):
        raise ValueError(
            "trial requires private candidate.pt/cache paths and disabled tracking"
        )
    checkpoint = workspace / "best_model.pt"
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise ValueError("trial requires a private starting checkpoint copy")
    model, settings, saved = load_tool_checkpoint(checkpoint, "cpu")
    for key in (
        "architecture",
        "patch_size",
        "num_layers",
        "base_feat",
        "num_blocks",
        "num_heads",
        "dropout",
        "use_ridges",
        "multi_task_heads",
        "ridge_sigma",
    ):
        if settings[key] != getattr(config, key):
            raise ValueError(f"probe config differs from starting checkpoint's {key}")
    if saved["config"].get("use_lasagna") != config.use_lasagna:
        raise ValueError("probe config differs from starting checkpoint's use_lasagna")
    from scripts.training import train

    mismatch = train.warm_start_mismatch(saved["config"], config)
    if mismatch is not None:
        raise ValueError(f"starting checkpoint must record matching {mismatch}")
    del model, saved

    # The legacy trainer writes run_result.json relative to cwd, but its
    # histogram directory is file-anchored. Isolate both without copying its
    # evaluation or promotion logic into the probe.
    previous_cwd, previous_hist = Path.cwd(), train.SKELETON_HIST_DIR
    try:
        os.chdir(workspace)
        train.SKELETON_HIST_DIR = str(workspace / "skeleton_hists")
        train.train(config, strict_warm_start=True)
    finally:
        train.SKELETON_HIST_DIR = previous_hist
        os.chdir(previous_cwd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    run(parser.parse_args().config)


if __name__ == "__main__":
    main()
