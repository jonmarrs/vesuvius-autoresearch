from pathlib import Path

import pytest
import torch

from vesuvius_model import VesuviusConfig, VesuviusResNet3DDecoder

# The backbone is villa's (vesuvius_model.VesuviusResNet3DDecoder imports it from here).
VILLA_DECODER = (
    Path(__file__).resolve().parents[1]
    / "villa/ink-detection/optimized_inference/model_resnet3d_3d_decoder.py"
)


@pytest.mark.skipif(
    not VILLA_DECODER.is_file(), reason="villa's ink-detection is absent"
)
def test_resnet3d_decoder_forward():
    config = VesuviusConfig(patch_size=64, num_layers=62, in_channels=1)
    model = VesuviusResNet3DDecoder(config).eval()
    x = torch.randn(2, 1, 62, 64, 64)
    out = model(x)
    assert out.shape == (2, 1, 16, 16), f"Unexpected output shape: {out.shape}"
