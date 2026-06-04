#!/usr/bin/env python3
"""
Prototype for Volumetric Ink Detection using Villa's Cube/Instance logic.
Instead of 2D surface projection, we treat ink as a 3D distribution.
"""

import numpy as np
import torch
import torch.nn as nn


class VolumetricInkHead(nn.Module):
    def __init__(self, in_channels, num_layers):
        super().__init__()
        # We output a (num_layers, H, W) distribution
        self.conv3d = nn.Conv3d(in_channels, 1, kernel_size=3, padding=1)
        self.num_layers = num_layers

    def forward(self, x):
        # x: [B, C, Z, H, W]
        out_3d = self.conv3d(x)  # [B, 1, Z, H, W]
        return out_3d.squeeze(1)


def main():
    print("--- Volumetric Ink Detection Prototype ---")
    # Simulate a deep feature map from a 3D UNet
    batch_size = 2
    channels = 64
    z, h, w = 16, 64, 64

    features = torch.randn(batch_size, channels, z, h, w)
    head = VolumetricInkHead(channels, z)

    output = head(features)
    print(f"Input shape:  {features.shape}")
    print(f"Output shape: {output.shape} (3D Probability Distribution)")

    # Sigmoid to get probabilities
    probs = torch.sigmoid(output)
    print(f"Max Prob: {probs.max().item():.4f}")
    print(
        "This 3D output allows capturing ink 'thickness' and 'ghosting' across Z layers."
    )


if __name__ == "__main__":
    main()
