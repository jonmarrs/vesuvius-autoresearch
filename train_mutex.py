import os
import sys
import torch
import torch.nn as nn
from dataclasses import dataclass
from torch.utils.data import DataLoader

# Add villa paths to sys.path
VILLA_PATHS = [
    os.path.abspath("villa/vesuvius/src"),
    os.path.abspath("villa/vesuvius/src/vesuvius/models/training")
]
for p in VILLA_PATHS:
    if p not in sys.path:
        sys.path.append(p)

from vesuvius.models.training.trainers.mutex_affinity_trainer import MutexAffinityTrainer
from vesuvius.models.datasets.mutex_affinity_dataset import MutexAffinityDataset, TargetSpec

@dataclass
class MutexConfig:
    data_path: str = "local_data/curated_fragments"
    batch_size: int = 4
    lr: float = 1e-4
    max_epochs: int = 10
    time_budget: int = 900
    
    # Dataset specific
    affinity_dirname: str = "affinity_graph"
    image_dirname: str = "images"
    
def train_mutex(config: MutexConfig):
    # This is a simplified integration leveraging the official villa Trainer
    # In a full Autoresearch cycle, we would wrap this in a manager
    print(f"Starting Mutex-Affinity training on {config.data_path}")
    
    # Configure the Trainer (Villa uses a Manager object pattern)
    # This requires mocking or configuring the 'mgr' expected by MutexAffinityTrainer
    # For simplicity, we create a minimal configuration manager
    class MockManager:
        def __init__(self, cfg):
            self.tr_configs = {"affinity_label_smoothing": 0.05}
            self.enable_deep_supervision = False
            self.data_path = cfg.data_path
            self.affinity_dirname = cfg.affinity_dirname
            self.image_dirname = cfg.image_dirname
            self.train_patch_size = (64, 64, 64)
            self.image_size = (64, 64, 64)
            self.affinity_targets = {
                "attractive": TargetSpec(affinity_key="affinities/attractive", mask_key="mask/attractive", invert_for_loss=True),
                "repulsive": TargetSpec(affinity_key="affinities/repulsive", mask_key="mask/repulsive", invert_for_loss=False)
            }
            
    mgr = MockManager(config)
    trainer = MutexAffinityTrainer(mgr=mgr)
    
    # Initialize Dataset and Dataloader
    dataset = MutexAffinityDataset(mgr, is_training=True)
    dataloader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True)
    
    # ...
    # Run training
    # Instead of lightning Trainer, we manually trigger a training step
    # Based on villa's BaseTrainer and train.py flow
    print("Mutex-Affinity trainer initialized. Pipeline ready.")
    
    # Example of how to iterate and train
    # for batch in dataloader:
    #     trainer.train_step(batch)

if __name__ == "__main__":
    cfg = MutexConfig()
    train_mutex(cfg)
