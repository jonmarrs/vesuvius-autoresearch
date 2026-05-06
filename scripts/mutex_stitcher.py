import os
import sys
import torch
import numpy as np

# Add villa paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VILLA_VESUVIUS_PATH = os.path.join(PROJECT_ROOT, "villa/vesuvius/src")
VILLA_THAUMATO_PATH = os.path.join(PROJECT_ROOT, "villa/thaumato-anakalyptor/ThaumatoAnakalyptor")

for p in [VILLA_VESUVIUS_PATH, VILLA_THAUMATO_PATH]:
    if p not in sys.path:
        sys.path.append(p)

from vesuvius.models.training.trainers.mutex_affinity_trainer import MutexAffinityTrainer

class MutexStitcher:
    """
    A post-processing plugin for ThaumatoAnakalyptor that uses 
    Mutex-Affinity to resolve ambiguous sheet boundaries.
    """
    def __init__(self, checkpoint_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Mock Manager for trainer initialization
        class MockMgr:
            def __init__(self):
                self.tr_configs = {"affinity_label_smoothing": 0.05}
                self.enable_deep_supervision = False
                self.train_patch_size = (64, 64, 64)
                self.image_size = (64, 64, 64)
        
        self.trainer = MutexAffinityTrainer(mgr=MockMgr())
        if checkpoint_path and os.path.exists(checkpoint_path):
            checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
            self.trainer.load_state_dict(checkpoint)
        self.trainer.model.to(self.device)
        self.trainer.model.eval()

    def refine_segments(self, volume_chunk):
        """
        Takes a 3D volume chunk and produces affinity maps for stitching.
        """
        tensor = torch.from_numpy(volume_chunk).float().to(self.device).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            affinities = self.trainer.model(tensor)
            # affinities contains [attractive, repulsive] maps
        return affinities.cpu().numpy()

def main():
    print("Mutex Stitcher Plugin Initialized.")
    # Example usage:
    # stitcher = MutexStitcher("best_mutex_model.pt")
    # refined = stitcher.refine_segments(my_volume_chunk)

if __name__ == "__main__":
    main()
