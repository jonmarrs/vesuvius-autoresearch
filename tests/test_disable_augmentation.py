import os
import sys
from types import SimpleNamespace

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "training"))

from train import apply_augmentations  # noqa: E402


def test_disable_augmentation_is_identity():
    x = torch.rand(2, 1, 16, 64, 64)
    ti = torch.rand(2, 1, 64, 64)
    tf = torch.rand(2, 1, 1, 64, 64)
    cfg = SimpleNamespace(disable_augmentation=True)
    ox, oti, otf = apply_augmentations(x, ti, tf, 0, 1000, config=cfg)
    assert ox is x and oti is ti and otf is tf
