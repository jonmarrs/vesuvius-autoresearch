import torch

from vesuvius_model import VesuviusConfig, VesuviusResNet3DDecoder


def test_resnet3d_decoder_forward():
    config = VesuviusConfig(patch_size=64, num_layers=62, in_channels=1)
    model = VesuviusResNet3DDecoder(config).eval()
    x = torch.randn(2, 1, 62, 64, 64)
    out = model(x)
    assert out.shape == (2, 1, 16, 16), f"Unexpected output shape: {out.shape}"
