print("Testing imports")
import os
import sys
import torch
from torch.cuda.amp import GradScaler, autocast
print("Torch imported")
sys.path.append(os.path.abspath('villa/segmentation/evaluation'))
from metrics.dice import compute as compute_official_dice
print("Dice imported")
from metrics.skeleton_distance_length import compute as compute_skeleton_dist
print("Skel imported")
