import os
import sys

import torch

sys.path.append(os.getcwd())
# The correct import is VesuviusLabeledDataset and VesuviusS3Dataset
from torch.utils.data import DataLoader

from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


# Setup minimal config
class Config:
    def __init__(self):
        self.patch_size = 64
        self.num_layers = 16
        self.batch_size = 4
        self.in_channels = 1
        self.aug_mode = "albumentations"
        self.use_ridges = False
        self.ridge_sigma = 2.0
        self.use_lasagna = False
        self.is_unlabeled = False
        self.require_ink = False


config = Config()
# Using a dummy labels path for testing. In reality, it should be a real file.
# The dataset will handle it not existing by setting labels to None.
dataset = VesuviusLabeledDataset(
    "local_data/PHercParis2Fr47/surface_volume.zarr",
    labels_path="nonexistent.png",
    patch_size=config.patch_size,
    num_layers=config.num_layers,
    use_ridges=config.use_ridges,
    use_lasagna=config.use_lasagna,
    is_unlabeled=config.is_unlabeled,
    require_ink=config.require_ink,
)
dataloader = DataLoader(dataset, batch_size=4)

print("Checking first batch for NaNs...")
for batch in dataloader:
    x = batch[0]  # volume is the first element
    if torch.isnan(x).any() or torch.isinf(x).any():
        print("FOUND NaN/Inf in input data!")
        break
    else:
        print("Batch is clean.")
    break
