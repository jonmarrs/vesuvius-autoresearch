"""Auto-generated LeJEPA fine-tune runner. Invoked by scripts/launch_finetune_lejepa.py."""

import argparse
import sys
from pathlib import Path

VILLA_PY = Path(
    "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/scripts/villa/vesuvius/src"
)
if str(VILLA_PY) not in sys.path:
    sys.path.insert(0, str(VILLA_PY))

import yaml
from vesuvius.models.configuration.config_manager import ConfigManager
from vesuvius.models.training.trainers.self_supervised.train_finetune_lejepa import (
    TrainFineTuneLEJEPA,
)


def main():
    parser = argparse.ArgumentParser(description="Run villa TrainFineTuneLEJEPA.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config) as f:
        raw = yaml.safe_load(f) or {}
    ft = raw.get("finetune_lejepa", {}) or {}

    mgr = ConfigManager(verbose=True)
    mgr.load_config(args.config)
    mgr.pretrained_lejepa_checkpoint = ft.get("pretrained_lejepa_checkpoint")
    mgr.freeze_encoder_epochs = int(ft.get("freeze_encoder_epochs", 0))
    mgr.encoder_lr_mult = float(ft.get("encoder_lr_mult", 1.0))
    mgr.finetune_warmup_epochs = int(ft.get("finetune_warmup_epochs", 0))
    mgr.load_decoder_from_pretrain = bool(ft.get("load_decoder_from_pretrain", False))

    trainer = TrainFineTuneLEJEPA(mgr=mgr)
    trainer.train()


if __name__ == "__main__":
    main()
