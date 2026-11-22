#!/usr/bin/env python3
"""Untrained volumetric-head shape demonstration; no ink detection measurement."""

import argparse
from numbers import Integral

import torch
import torch.nn as nn


class VolumetricInkHead(nn.Module):
    def __init__(self, in_channels, num_layers):
        super().__init__()
        for name, value in (("in_channels", in_channels), ("num_layers", num_layers)):
            if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        # One logit per input voxel; the declared depth is checked in forward.
        self.conv3d = nn.Conv3d(in_channels, 1, kernel_size=3, padding=1)
        self.num_layers = num_layers

    def forward(self, x):
        if not isinstance(x, torch.Tensor):
            raise TypeError("volumetric features must be a tensor")
        if x.ndim != 5 or min(x.shape) < 1:
            raise ValueError("volumetric features must be nonempty [B,C,Z,H,W]")
        if x.shape[1] != self.conv3d.in_channels or x.shape[2] != self.num_layers:
            raise ValueError(
                "volumetric feature channels/depth must match in_channels/num_layers"
            )
        out_3d = self.conv3d(x)  # [B, 1, Z, H, W]
        return out_3d.squeeze(1)


def main(argv=None):
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    print("--- Untrained volumetric-head shape demo ---")
    # Simulate a deep feature map from a 3D UNet
    batch_size = 1
    channels = 8
    z, h, w = 4, 8, 8

    features = torch.randn(batch_size, channels, z, h, w)
    head = VolumetricInkHead(channels, z)

    output = head(features)
    print(f"Input shape:  {features.shape}")
    print(f"Output logits shape: {output.shape}")
    print(
        "Features and weights are random; no checkpoint or trained ink detector is used."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
