#!/usr/bin/env python3
"""Launcher for the villa Grand-Prize-2023 recipe (TrainerTimesFormer).

Pins the recipe verbatim:
  - model: TimeSFormerInk (pred_shape = 256)
  - patch: (16, 256, 256)
  - loss : 0.5 * DiceLoss + 0.5 * SoftBCEWithLogitsLoss(smooth_factor=0.25)
  - optim: AdamW, lr = 3e-5

Because patch_size > 64 px, the resulting model is NOT submittable under the
Vesuvius Challenge hallucination-mitigation rule. Use this run as a fixed
baseline comparator — every Autoresearch sweep result should be compared to the
number this launcher records in reports/gp_winner_baseline.json.

Default mode is dry-run; use --execute to actually start training. Default mode
in turn emits the exact subprocess command so it can be inspected first.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VILLA_ROOT = PROJECT_ROOT / "villa"
GP_WINNER_ROOT = VILLA_ROOT / "segmentation" / "models" / "multi-task-3d-unet"


def _resolve_labeled_volumes() -> list[dict]:
    """Pick labeled ink volumes available locally; user can override with --config."""
    candidates = [
        PROJECT_ROOT / "local_data" / "PHercParis2Fr47",
        PROJECT_ROOT / "local_data" / "curated_fragments",
    ]
    volumes = []
    for c in candidates:
        if not c.is_dir():
            continue
        data_vol = c / "surface_volume"
        label_vol = c / "inklabels.png"
        if data_vol.exists() and label_vol.exists():
            volumes.append(
                {
                    "data_volume": str(data_vol),
                    "label_volume": str(label_vol),
                    "format": "image",
                }
            )
    return volumes


def build_config(model_name: str, output_dir: Path) -> dict:
    volumes = _resolve_labeled_volumes()
    return {
        "tr_setup": {
            "model_name": model_name,
            "ckpt_out_base": str(output_dir / "checkpoints"),
            "tensorboard_log_dir": str(output_dir / "logs"),
            "tr_val_split": 0.9,
            "vram_max": 22000,
            "autoconfigure": False,
        },
        "tr_config": {
            "optimizer": "AdamW",
            "initial_lr": 3.0e-5,
            "patch_size": [16, 256, 256],
            "batch_size": 2,
            "max_steps_per_epoch": 500,
            "max_val_steps_per_epoch": 25,
            "max_epoch": 50,
            "num_dataloader_workers": 4,
        },
        "model_config": {},
        "dataset_config": {
            "min_bbox_percent": 0.2,
            "min_labeled_ratio": 0.2,
            "use_cache": True,
            "cache_file": str(output_dir / "patch_cache"),
            "targets": {
                "ink": {
                    "in_channels": 1,
                    "out_channels": 1,
                    "activation": "none",
                    "weight": 1,
                    "loss_fn": "BCEWithLogitsLoss",
                    "volumes": volumes,
                }
            },
        },
    }


def write_runner(runner_path: Path, gp_winner_root: Path) -> None:
    """Emit a tiny entry script that the launcher invokes via subprocess.

    The multi-task-3d-unet tree uses flat imports (e.g. `from configuration...`),
    so the runner prepends that tree to sys.path before importing the trainer.
    The runner lives under autoresearch's own tree (NOT inside the villa
    submodule) to keep the submodule clean.
    """
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text(
        '"""Auto-generated GP-winner runner. Invoked by scripts/launch_gp_winner.py."""\n'
        "import argparse\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        f"GP_WINNER_ROOT = Path({str(gp_winner_root)!r})\n"
        "if str(GP_WINNER_ROOT) not in sys.path:\n"
        "    sys.path.insert(0, str(GP_WINNER_ROOT))\n"
        "\n"
        "from training.trainers.train_gp_winner import TrainerTimesFormer\n"
        "\n"
        "\n"
        "def main():\n"
        '    parser = argparse.ArgumentParser(description="Run villa GP-2023 TimeSformerInk recipe.")\n'
        '    parser.add_argument("--config", required=True)\n'
        "    args = parser.parse_args()\n"
        "    trainer = TrainerTimesFormer(config_file=args.config)\n"
        "    trainer.train()\n"
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch the villa GP-2023 TimeSFormerInk baseline."
    )
    parser.add_argument(
        "--model-name",
        default="gp_winner_baseline_v1",
        help="Model name used for checkpoint / wandb run identification.",
    )
    parser.add_argument(
        "--config-out",
        default=str(
            PROJECT_ROOT / "configs" / "gp_winner_recipe" / "gp_winner_config.yaml"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "checkpoints" / "gp_winner_recipe"),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run training. Default is dry-run that only writes config + prints command.",
    )
    args = parser.parse_args()

    config_path = Path(args.config_out)
    output_dir = Path(args.output_dir)
    runner_path = PROJECT_ROOT / "scripts" / "_gp_winner_runner.py"

    if not GP_WINNER_ROOT.is_dir():
        print(
            f"ERROR: villa multi-task-3d-unet not found at {GP_WINNER_ROOT}",
            file=sys.stderr,
        )
        return 1

    config_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = build_config(args.model_name, output_dir)
    volumes = cfg["dataset_config"]["targets"]["ink"]["volumes"]
    with open(config_path, "w") as f:
        yaml.safe_dump(cfg, f)

    write_runner(runner_path, GP_WINNER_ROOT)

    cmd = [sys.executable, str(runner_path), "--config", str(config_path)]
    print(f"GP-winner config written: {config_path}")
    print(f"Resolved labeled volumes ({len(volumes)}):")
    for v in volumes:
        print(f"  - {v['data_volume']}  (labels: {v['label_volume']})")
    print()
    print(
        "Recipe: TimeSFormerInk + 0.5*DiceLoss + 0.5*SoftBCE(smooth=0.25), AdamW lr=3e-5, patch (16,256,256)"
    )
    print(
        "NOTE: patch_size > 64 px. Result is a RESEARCH-ONLY baseline; NOT submittable."
    )
    print()

    baseline_marker = PROJECT_ROOT / "reports" / "gp_winner_baseline.json"
    baseline_marker.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "model_name": args.model_name,
        "config_path": str(config_path),
        "runner": str(runner_path),
        "patch_size": [16, 256, 256],
        "submittable": False,
        "reason_not_submittable": "patch_size > 64 px",
        "labeled_volumes": volumes,
        "command": cmd,
        "executed": bool(args.execute),
    }
    with open(baseline_marker, "w") as f:
        json.dump(marker, f, indent=2)
    print(f"Baseline marker: {baseline_marker}")

    if not volumes:
        print(
            "WARNING: no labeled ink volumes found; --execute will fail until data is staged."
        )

    if args.execute:
        if not volumes:
            print("Refusing --execute: no labeled volumes available.", file=sys.stderr)
            return 2
        env = os.environ.copy()
        print("Executing GP-winner training...")
        return subprocess.call(cmd, cwd=str(PROJECT_ROOT), env=env)

    print("Dry run. Use --execute to start training, e.g.:")
    print(" ", " ".join(cmd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
