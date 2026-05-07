import os

import pytest
import torch


PrimusNetwork = pytest.importorskip(
    "villa.vesuvius.src.vesuvius.models.build.primus_wrapper"
).PrimusNetwork


def test_lejepa_foundation_checkpoint_loads_compatible_encoder_tensors():
    checkpoint_path = "checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth"
    if not os.path.exists(checkpoint_path):
        pytest.skip(f"Foundation checkpoint not found: {checkpoint_path}")

    model = PrimusNetwork(
        input_channels=1,
        config_name="S",
        patch_embed_size=(8, 8, 8),
        input_shape=(16, 64, 64),
        targets={"ink": {"out_channels": 1}},
        decoder_depth=2,
        decoder_num_heads=12,
    )

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state = checkpoint.get("model", checkpoint.get("model_state_dict", checkpoint))
    encoder_state = {
        key.replace("encoder.", ""): value
        for key, value in state.items()
        if key.startswith("encoder.")
    }
    current_state = model.shared_encoder.state_dict()
    compatible = {
        key: value
        for key, value in encoder_state.items()
        if key in current_state
        and hasattr(value, "shape")
        and current_state[key].shape == value.shape
    }

    assert encoder_state, "Checkpoint did not contain encoder weights"
    assert compatible, "Checkpoint did not contain compatible encoder weights"
    result = model.shared_encoder.load_state_dict(
        compatible,
        strict=False,
    )
    assert len(result.unexpected_keys) == 0
