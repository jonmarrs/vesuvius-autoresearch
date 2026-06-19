# tests/test_ink_repro_model.py
import torch

from repro.ink_segformer.model import InkSegformer, Stem3D


def test_stem_collapses_depth_to_channels():
    stem = Stem3D(out_channels=16)
    out = stem(torch.rand(2, 1, 8, 64, 64))  # [B,1,D,H,W]
    assert out.shape == (2, 16, 64, 64)  # depth gone, C=16, H/W preserved


def test_inksegformer_forward_shape():
    # encoder_weights=None to avoid a pretrained-weight download in tests
    model = InkSegformer(stem_channels=16, encoder="mit_b3", encoder_weights=None)
    out = model(torch.rand(2, 1, 8, 224, 224))
    assert out.shape == (2, 1, 224, 224)
