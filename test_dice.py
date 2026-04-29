import torch
import sys
import os
VILLA_SRC = os.path.abspath("villa/segmentation/evaluation")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)
from metrics.dice import compute as compute_official_dice

label = torch.zeros((1, 64, 64))
pred = torch.zeros((1, 64, 64))
d = compute_official_dice(label, pred)
print(f"Dice for all zeros: {d}")

label = torch.ones((1, 64, 64))
pred = torch.ones((1, 64, 64))
d = compute_official_dice(label, pred)
print(f"Dice for all ones: {d}")
