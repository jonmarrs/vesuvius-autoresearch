import os
import sys

import torch

# Add the villa repository to the path so we can import modules from it
sys.path.append(os.path.abspath("villa/ink-detection"))
from models.resnetall import generate_model


def get_resnet3d_baseline(config, device):
    """Instantiates the official ResNet3D baseline."""
    # Assuming config defines input dimensions, e.g., 3 input channels (for RGB or specific scan channels)
    model = generate_model(model_depth=18, n_input_channels=1, n_classes=1)
    return model.to(device)


if __name__ == "__main__":
    from vesuvius_model import VesuviusConfig

    config = VesuviusConfig()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    baseline = get_resnet3d_baseline(config, device)
    print(
        f"ResNet3D Baseline instantiated: {sum(p.numel() for p in baseline.parameters()) / 1e6:.2f}M parameters"
    )

    # Test a forward pass
    x = torch.randn((1, 1, 16, 64, 64), device=device)
    out = baseline(x)
    print(f"Forward pass output shape: {out.shape}")
