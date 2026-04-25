import sys
import os

# Add project root and villa paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VILLA_TRAIN_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "villa/segmentation/models/multi-task-3d-unet"))

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if VILLA_TRAIN_PATH not in sys.path:
    sys.path.append(VILLA_TRAIN_PATH)

from trainer import VesuviusTrainer
from configuration.config_manager import ConfigManager

def main():
    if len(sys.argv) < 2:
        print("Usage: uv run v3_training/train.py <config_path>")
        sys.exit(1)
        
    config_path = sys.argv[1]
    # In villa, ConfigManager is initialized with the file path
    trainer = VesuviusTrainer(config_path)
    
    # Run training
    trainer.train()

if __name__ == "__main__":
    main()
