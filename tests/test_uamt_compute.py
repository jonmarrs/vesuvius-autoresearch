"""UA-MT's teacher passes and the projection view cost only what they buy.

Before 2026-10-14 every step built a second augmented view and ran a full forward
pass on it for the DINO-lite projection consistency, which only UA-MT trains on,
and UA-MT ran four teacher passes whose variance comes from dropout on a model
without dropout. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-14_UAMT_COMPUTE.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train  # noqa: E402

from vesuvius_autoresearch.core.model_wrappers import build_resenc_unet  # noqa: E402


def test_dropout_is_detected_where_it_acts():
    assert not train.has_dropout(build_resenc_unet(2, 4, True))
    assert train.has_dropout(torch.nn.Sequential(torch.nn.Dropout3d(0.1)))
    assert not train.has_dropout(torch.nn.Sequential(torch.nn.Dropout(0.0)))
    assert train.has_dropout(torch.nn.MultiheadAttention(8, 2, dropout=0.1))
    assert not train.has_dropout(torch.nn.MultiheadAttention(8, 2, dropout=0.0))


def test_one_teacher_pass_gives_a_zero_variance_not_nan():
    teacher = torch.nn.Conv3d(1, 1, 1)
    x = torch.rand(2, 1, 4, 8, 8)
    prob, var = train.uamt_teacher(teacher, x, 1)
    assert prob.shape == var.shape == (2, 1, 4, 8, 8)
    assert torch.equal(var, torch.zeros_like(prob))
    assert not teacher.training  # restored to eval mode


def test_dropout_makes_the_passes_differ():
    torch.manual_seed(0)
    teacher = torch.nn.Sequential(torch.nn.Conv3d(1, 4, 1), torch.nn.Dropout3d(0.5))
    _, var = train.uamt_teacher(teacher, torch.rand(2, 1, 4, 8, 8), 4)
    assert var.max() > 1e-3
    assert not teacher.training


def test_without_dropout_one_pass_matches_four():
    """The four passes differ only by the 0.01 input noise: the uncertainty
    weights exp(-var) are 1 to 4 decimals, and one pass moves the teacher's
    target by no more than the noise it injects anyway (two single passes)."""
    torch.manual_seed(0)
    teacher = build_resenc_unet(2, 8, True)
    x = torch.rand(2, 2, 8, 32, 32)
    with torch.no_grad():
        four, var = train.uamt_teacher(teacher, x, 4)
        one, _ = train.uamt_teacher(teacher, x, 1)
        another, _ = train.uamt_teacher(teacher, x, 1)
    assert torch.exp(-var).min() > 0.9999
    assert (four - one).abs().max() <= 2 * (one - another).abs().max()
