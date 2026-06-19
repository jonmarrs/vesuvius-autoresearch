# repro/ink_segformer/model.py
import segmentation_models_pytorch as smp
import torch.nn.functional as F
from torch import nn


class Stem3D(nn.Module):
    """4-layer 3D-conv stem over the depth stack, then max over the depth axis —
    collapses depth into feature channels (the 1st-place '3D conv then max-z',
    depth-invariant)."""

    def __init__(self, out_channels=32):
        super().__init__()
        chans = [1, 16, 32, 32, out_channels]
        layers = []
        for i in range(4):
            layers += [
                nn.Conv3d(chans[i], chans[i + 1], kernel_size=3, padding=1),
                nn.BatchNorm3d(chans[i + 1]),
                nn.ReLU(inplace=True),
            ]
        self.net = nn.Sequential(*layers)

    def forward(self, x):  # x: [B,1,D,H,W]
        x = self.net(x)  # [B,C,D,H,W]
        return x.max(dim=2).values  # [B,C,H,W]


class InkSegformer(nn.Module):
    def __init__(self, stem_channels=32, encoder="mit_b3", encoder_weights="imagenet"):
        super().__init__()
        self.stem = Stem3D(out_channels=stem_channels)
        self.seg = smp.Segformer(
            encoder_name=encoder,
            in_channels=stem_channels,
            classes=1,
            encoder_weights=encoder_weights,
        )

    def forward(self, x):  # [B,1,D,H,W] -> [B,1,H,W]
        h, w = x.shape[-2], x.shape[-1]
        feat = self.stem(x)
        out = self.seg(feat)
        if out.shape[-2:] != (h, w):
            out = F.interpolate(out, size=(h, w), mode="bilinear", align_corners=False)
        return out
