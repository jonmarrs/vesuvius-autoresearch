import sys
import os
from trainer import VesuviusTrainer
from training.config_manager import ConfigManager

def main():
    if len(sys.argv) < 2:
        print("Usage: uv run v3_training/train.py <config_path>")
        sys.exit(1)
        
    config_path = sys.argv[1]
    config = ConfigManager(config_path)
    trainer = VesuviusTrainer(config)
    
    # Run training
    trainer.train()

if __name__ == "__main__":
    main()
