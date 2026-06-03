"""Auto-generated GP-winner runner. Invoked by scripts/launch_gp_winner.py."""
import argparse
import sys
from pathlib import Path

GP_WINNER_ROOT = Path('/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/segmentation/models/multi-task-3d-unet')
if str(GP_WINNER_ROOT) not in sys.path:
    sys.path.insert(0, str(GP_WINNER_ROOT))

from training.trainers.train_gp_winner import TrainerTimesFormer


def main():
    parser = argparse.ArgumentParser(description="Run villa GP-2023 TimeSformerInk recipe.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    trainer = TrainerTimesFormer(config_file=args.config)
    trainer.train()


if __name__ == "__main__":
    main()
