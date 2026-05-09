import torch
from vesuvius_model import VesuviusConfig, VesuviusResNet3DDecoder
config = VesuviusConfig(patch_size=64, num_layers=62, in_channels=1)
model = VesuviusResNet3DDecoder(config).eval()
x = torch.randn(2, 1, 62, 64, 64)
out = model(x)
print(f"Output shape: {out.shape}")
