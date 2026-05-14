#!/usr/bin/env python3
"""Launcher for villa's LeJEPA-native fine-tuner (TrainFineTuneLEJEPA).

Loads encoder weights from one of our pretrained LeJEPA foundation checkpoints
(checkpoints/lejepa_foundation_v1*/...) and trains a supervised ink-detection
head on labeled fragment data. The default recipe uses a 64-px ML window so
the resulting model is submittable under the Vesuvius Challenge
hallucination-mitigation rule (0.5x0.5 mm @ 8 um).

Villa's official CLI does NOT dispatch ``finetune_lejepa`` (only ``lejepa`` for
pretrain and ``finetune_mae_unet`` for the MAE variant), so this launcher
bypasses the CLI: it generates a tiny runner under scripts/ that imports
TrainFineTuneLEJEPA directly. Mirrors the launch_gp_winner.py pattern; keeps
the villa submodule clean.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VILLA_PYTHON_ROOT = PROJECT_ROOT / "villa" / "vesuvius" / "src"


def discover_lejepa_checkpoint(explicit: str | None) -> Path | None:
    """Pick the newest LeJEPA checkpoint we have locally."""
    if explicit:
        path = Path(explicit)
        return path if path.exists() else None

    base = PROJECT_ROOT / "checkpoints"
    if not base.is_dir():
        return None

    candidates: list[Path] = []
    for run_dir in base.glob("lejepa_foundation_v1*"):
        if not run_dir.is_dir():
            continue
        finals = sorted(run_dir.glob("*_final.pth"), key=lambda p: p.stat().st_mtime, reverse=True)
        if finals:
            candidates.append(finals[0])
            continue
        epochs = sorted(
            run_dir.glob("*_epoch*.pth"),
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        )
        if epochs:
            candidates.append(epochs[0])

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_labeled_volumes() -> list[dict]:
    """Resolve ink-labeled volumes for fine-tuning."""
    paris2 = PROJECT_ROOT / "local_data" / "PHercParis2Fr47"
    surface = paris2 / "surface_volume"
    labels = paris2 / "inklabels.png"
    if surface.is_dir() and labels.exists():
        return [
            {
                "image": str(surface),
                "label": str(labels),
            }
        ]
    return []


def build_config(
    model_name: str,
    patch: tuple[int, int, int],
    embed: tuple[int, int, int],
    pretrained_ckpt: Path | None,
    labeled_volumes: list[dict],
    output_dir: Path,
    max_epoch: int,
    initial_lr: float,
    encoder_lr_mult: float,
    freeze_epochs: int,
    warmup_epochs: int,
) -> dict:
    return {
        "tr_setup": {
            "model_name": model_name,
            "ckpt_out_base": str(output_dir),
            "tr_val_split": 0.9,
        },
        "model_config": {
            "patch_embed_size": list(embed),
        },
        "tr_config": {
            "trainer": "finetune_lejepa",
            "initial_lr": initial_lr,
            "weight_decay": 0.01,
            "batch_size": 4,
            "patch_size": list(patch),
            "max_epoch": max_epoch,
            "num_dataloader_workers": 0,
            "optimizer": "AdamW",
        },
        "dataset_config": {
            "data_format": "image",
            "num_workers": 0,
            "volumes": labeled_volumes,
            "targets": {
                "ink": {
                    "in_channels": 1,
                    "out_channels": 1,
                    "activation": "none",
                    "loss_fn": "BCEWithLogitsLoss",
                    "weight": 1.0,
                },
            },
        },
        # Recorded only — the runner sets these explicitly on the mgr.
        "finetune_lejepa": {
            "pretrained_lejepa_checkpoint": str(pretrained_ckpt) if pretrained_ckpt else None,
            "freeze_encoder_epochs": freeze_epochs,
            "encoder_lr_mult": encoder_lr_mult,
            "finetune_warmup_epochs": warmup_epochs,
            "load_decoder_from_pretrain": False,
        },
    }


def write_runner(runner_path: Path, villa_python_root: Path) -> None:
    """Emit the runner script.

    Lives under autoresearch/scripts/ (gitignored) — NOT inside the villa
    submodule. The runner injects villa onto sys.path, loads the config,
    sets the four fine-tune-specific attrs on the mgr (since ConfigManager
    has no dedicated section for them), and starts training.
    """
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text(
        '"""Auto-generated LeJEPA fine-tune runner. Invoked by scripts/launch_finetune_lejepa.py."""\n'
        "import argparse\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        f"VILLA_PY = Path({str(villa_python_root)!r})\n"
        "if str(VILLA_PY) not in sys.path:\n"
        "    sys.path.insert(0, str(VILLA_PY))\n"
        "\n"
        "import yaml\n"
        "from vesuvius.models.configuration.config_manager import ConfigManager\n"
        "from vesuvius.models.training.trainers.self_supervised.train_finetune_lejepa import (\n"
        "    TrainFineTuneLEJEPA,\n"
        ")\n"
        "\n"
        "\n"
        "def main():\n"
        '    parser = argparse.ArgumentParser(description="Run villa TrainFineTuneLEJEPA.")\n'
        '    parser.add_argument("--config", required=True)\n'
        "    args = parser.parse_args()\n"
        "\n"
        "    with open(args.config) as f:\n"
        "        raw = yaml.safe_load(f) or {}\n"
        '    ft = raw.get("finetune_lejepa", {}) or {}\n'
        "\n"
        "    mgr = ConfigManager(verbose=True)\n"
        "    mgr.load_config(args.config)\n"
        '    mgr.pretrained_lejepa_checkpoint = ft.get("pretrained_lejepa_checkpoint")\n'
        '    mgr.freeze_encoder_epochs = int(ft.get("freeze_encoder_epochs", 0))\n'
        '    mgr.encoder_lr_mult = float(ft.get("encoder_lr_mult", 1.0))\n'
        '    mgr.finetune_warmup_epochs = int(ft.get("finetune_warmup_epochs", 0))\n'
        '    mgr.load_decoder_from_pretrain = bool(ft.get("load_decoder_from_pretrain", False))\n'
        "\n"
        "    trainer = TrainFineTuneLEJEPA(mgr=mgr)\n"
        "    trainer.train()\n"
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def _is_submittable(patch: tuple[int, int, int]) -> bool:
    return max(patch[-2], patch[-1]) <= 64


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch villa's LeJEPA→UNet fine-tuner.")
    parser.add_argument("--model-name", default="lejepa_finetune_ink_v1")
    parser.add_argument("--checkpoint", default=None, help="Explicit LeJEPA .pth. Default: auto-discover newest.")
    parser.add_argument(
        "--patch", type=int, nargs=3, default=[32, 64, 64],
        help="Train patch size (D H W). Default keeps 64x64 ML window (submittable).",
    )
    parser.add_argument(
        "--embed", type=int, nargs=3, default=[8, 8, 8],
        help="patch_embed_size. Should match the pretrain (default [8,8,8]).",
    )
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--encoder-lr-mult", type=float, default=0.1)
    parser.add_argument("--freeze-encoder-epochs", type=int, default=3)
    parser.add_argument("--warmup-epochs", type=int, default=2)
    parser.add_argument("--max-epoch", type=int, default=30)
    parser.add_argument(
        "--config-out",
        default=str(PROJECT_ROOT / "configs" / "finetune_lejepa" / "finetune_lejepa_config.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "checkpoints" / "finetune_lejepa"),
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    pretrained = discover_lejepa_checkpoint(args.checkpoint)
    volumes = resolve_labeled_volumes()
    patch = tuple(args.patch)
    embed = tuple(args.embed)
    submittable = _is_submittable(patch)

    config_path = Path(args.config_out)
    output_dir = Path(args.output_dir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = build_config(
        model_name=args.model_name,
        patch=patch,
        embed=embed,
        pretrained_ckpt=pretrained,
        labeled_volumes=volumes,
        output_dir=output_dir,
        max_epoch=args.max_epoch,
        initial_lr=args.lr,
        encoder_lr_mult=args.encoder_lr_mult,
        freeze_epochs=args.freeze_encoder_epochs,
        warmup_epochs=args.warmup_epochs,
    )
    with open(config_path, "w") as f:
        yaml.safe_dump(cfg, f)

    runner_path = PROJECT_ROOT / "scripts" / "_finetune_lejepa_runner.py"
    write_runner(runner_path, VILLA_PYTHON_ROOT)

    cmd = [sys.executable, str(runner_path), "--config", str(config_path)]

    blockers: list[str] = []
    if pretrained is None:
        blockers.append("no LeJEPA checkpoint found under checkpoints/lejepa_foundation_v1*")
    if not volumes:
        blockers.append("no labeled volume found at local_data/PHercParis2Fr47")

    marker_path = PROJECT_ROOT / "reports" / "finetune_lejepa_run.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "model_name": args.model_name,
        "config_path": str(config_path),
        "runner": str(runner_path),
        "pretrained_lejepa_checkpoint": str(pretrained) if pretrained else None,
        "patch_size": list(patch),
        "patch_embed_size": list(embed),
        "submittable": submittable,
        "labeled_volumes": volumes,
        "freeze_encoder_epochs": args.freeze_encoder_epochs,
        "encoder_lr_mult": args.encoder_lr_mult,
        "warmup_epochs": args.warmup_epochs,
        "max_epoch": args.max_epoch,
        "ready": not blockers,
        "blockers": blockers,
        "command": cmd,
        "executed": bool(args.execute),
    }
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)

    print(f"Fine-tune config: {config_path}")
    print(f"Pretrained LeJEPA: {pretrained}")
    print(f"Labeled volumes ({len(volumes)}): {[v['image'] for v in volumes]}")
    print(f"Patch {patch} (embed {embed}) — {'SUBMITTABLE' if submittable else 'NOT submittable'}")
    print(f"Marker: {marker_path}")
    if blockers:
        print("Not ready to launch:")
        for b in blockers:
            print(f"  - {b}")

    if args.execute:
        if blockers:
            print("Refusing --execute due to blockers above.", file=sys.stderr)
            return 2
        env = os.environ.copy()
        return subprocess.call(cmd, cwd=str(PROJECT_ROOT), env=env)

    print("Dry run. Use --execute to start fine-tuning:")
    print(" ", " ".join(cmd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
