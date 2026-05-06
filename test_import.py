print("Testing imports")
import os
import sys
import torch
from torch.amp import GradScaler, autocast
print("Torch imported")
sys.path.append(os.path.abspath('villa/segmentation/evaluation'))
from metrics.dice import compute as compute_official_dice
print("Dice imported")
try:
    from metrics.skeleton_distance_length import compute as compute_skeleton_dist
    print("Skel imported")
except ImportError as exc:
    print(f"Skel optional import skipped: {exc}")
