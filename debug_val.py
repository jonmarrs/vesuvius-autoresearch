import torch
import numpy as np
from train import ExperimentConfig, train

config = ExperimentConfig(
    uris=["local_data/PHercParis2Fr47/surface_volume.zarr"],
    val_uri="local_data/PHercParis2Fr143/surface_volume.zarr",
    time_budget=30,
    batch_size=4,
    patch_size=64,
    num_layers=16
)

# Run a tiny training to trigger validation
train(config)
