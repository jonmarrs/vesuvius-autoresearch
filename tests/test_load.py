import os

import pytest
import torch.nn as nn

# train.py first: importing it puts villa/vesuvius/src on sys.path, which
# primus_wrapper's own imports ("vesuvius.models...") need.
from scripts.training.train import load_foundation_model

PrimusNetwork = pytest.importorskip(
    "villa.vesuvius.src.vesuvius.models.build.primus_wrapper"
).PrimusNetwork


def test_the_project_lejepa_checkpoint_does_not_fit_lejepa_unet():
    """The project's LeJEPA checkpoint is a larger encoder than the "S" that
    LeJEPAUNet builds: it fills 70 of shared_encoder's 280 tensors, the patch
    embedding only (measured on the GPU host, 2026-10-15). train() stops such a
    run rather than train a mostly random encoder under the checkpoint's name.
    Once LeJEPAUNet is built to the checkpoint's size, this should load."""
    checkpoint_path = "checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth"
    if not os.path.exists(checkpoint_path):
        pytest.skip(f"Foundation checkpoint not found: {checkpoint_path}")

    model = nn.Module()  # LeJEPAUNet's shape: backbone.shared_encoder
    model.backbone = PrimusNetwork(
        input_channels=1,
        config_name="S",
        patch_embed_size=(8, 8, 8),
        input_shape=(16, 64, 64),
        targets={"ink": {"out_channels": 1}},
        decoder_depth=2,
        decoder_num_heads=12,
    )
    with pytest.raises(ValueError, match=r"only \d+ of 280 tensors"):
        load_foundation_model(model, checkpoint_path)
