print("Testing imports")
import os
import sys

print("Torch imported")
sys.path.append(os.path.abspath("villa/segmentation/evaluation"))
print("Dice imported")
try:
    from metrics.skeleton_distance_length import compute as compute_skeleton_dist

    print("Skel imported")
except ImportError as exc:
    print(f"Skel optional import skipped: {exc}")
