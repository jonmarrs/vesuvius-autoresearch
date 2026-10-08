#!/usr/bin/env python3
"""Read one real pinned Mutex dataset patch on CPU before permitting training."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path


def probe(config_path):
    # This process is separate from training; no accelerator or weights are used.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / "villa/vesuvius/src"))
    from vesuvius.models.configuration.config_manager import ConfigManager
    from vesuvius.models.datasets.mutex_affinity_dataset import MutexAffinityDataset

    config = json.loads(Path(config_path).read_text())
    config["dataset_config"]["cache_valid_patches"] = False
    config["dataset_config"]["skip_intensity_sampling"] = True
    config["dataset_config"]["num_workers"] = 0
    with tempfile.TemporaryDirectory(prefix="mutex-runtime-") as directory:
        source = Path(directory) / "config.json"
        source.write_text(json.dumps(config, allow_nan=False))
        manager = ConfigManager(verbose=False)
        manager.load_config(source)
        dataset = MutexAffinityDataset(manager, is_training=False)
        if len(dataset) == 0:
            raise ValueError("pinned loader found no usable validation patches")
        sample = dataset[0]
        patch = tuple(manager.train_patch_size)
        if tuple(sample["image"].shape) != (1, *patch):
            raise ValueError("pinned loader returned an invalid image patch shape")
        import torch

        if not torch.isfinite(sample["image"]).all():
            raise ValueError("pinned loader returned nonfinite image values")
        for name, target in config["dataset_config"]["targets"].items():
            expected = (target["out_channels"], *patch)
            for key in (name, f"{name}_mask"):
                if key not in sample or tuple(sample[key].shape) != expected:
                    raise ValueError(f"pinned loader {key} must have shape {expected}")
                if not torch.isfinite(sample[key]).all():
                    raise ValueError(f"pinned loader {key} contains nonfinite values")
    return {"contract": 1, "status": "PASS", "patch_size": list(patch)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = probe(args.config)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "contract": 1,
                    "status": "FAIL",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        )
        return 1
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
