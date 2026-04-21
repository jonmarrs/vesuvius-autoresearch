import torch
import torch.nn as nn
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
import sys
import os

# Add villa segmentation path
VILLA_TRAIN_PATH = os.path.abspath("villa/segmentation/models/multi-task-3d-unet")
sys.path.append(VILLA_TRAIN_PATH)

from training.base_trainer import BaseTrainer

class VesuviusTrainer(BaseTrainer):
    """
    Subclass of villa's BaseTrainer.
    Integrates our custom InkDetectorOptimized model into the official Challenge Standard framework.
    """
    
    def _get_loss(self):
        """Integration for our multi-task (Ink + Fiber + Auxiliary Tasks) losses."""
        return {
            "ink": nn.BCEWithLogitsLoss(),
            "fiber": nn.BCEWithLogitsLoss(),
            "surface_normals": nn.MSELoss(),
            "distance_transform": nn.L1Loss(),
            "structure_tensor": nn.MSELoss()
        }

    def _build_model(self):
        """Constructs the InkDetectorOptimized model from the v3 task config."""
        print("--- Building v3.1.0 Omni-Sensing Model ---")
        config = self.config
        
        # Mapping villa config to our VesuviusConfig
        v_config = VesuviusConfig(
            patch_size=config.dataset_config.patch_size if hasattr(config.dataset_config, 'patch_size') else 64,
            num_layers=config.dataset_config.num_layers if hasattr(config.dataset_config, 'num_layers') else 24,
            base_feat=config.model_config.base_feat,
            in_channels=config.model_config.in_channels
        )
        
        self.model = InkDetectorOptimized(v_config)
        
        # Add auxiliary heads dynamically
        self.model.surface_normal_head = nn.Conv3d(v_config.base_feat // 4, 3, kernel_size=1)
        self.model.dist_transform_head = nn.Conv3d(v_config.base_feat // 4, 1, kernel_size=1)
        self.model.st_head = nn.Conv3d(v_config.base_feat // 4, 6, kernel_size=1) # 6 symmetric tensor components
        
        self.model.to(self.device)
        return self.model

if __name__ == "__main__":
    # Smoke test the trainer initialization
    from training.config_manager import ConfigManager
    config = ConfigManager("v3_training/task.yaml")
    trainer = VesuviusTrainer(config)
    print("Trainer initialized successfully.")
