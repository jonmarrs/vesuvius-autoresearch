"""UA-MT's teacher passes and the projection view cost only what they buy.

Before 2026-10-14 every step built a second augmented view and ran a full forward
pass on it for the DINO-lite projection consistency, which only UA-MT trains on,
and UA-MT ran four teacher passes whose variance comes from dropout-like layers
on a model without any. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-14_UAMT_COMPUTE.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train  # noqa: E402

from vesuvius_autoresearch.core.model_wrappers import build_resenc_unet  # noqa: E402


class _DropPath(torch.nn.Module):
    """Stochastic depth as timm writes it: no dropout module, a random mask."""

    def forward(self, x):
        if not self.training:
            return x
        keep = (torch.rand(x.shape[0], 1, 1, 1, 1) > 0.5).float()
        return x * keep / 0.5


def test_a_teacher_is_stochastic_when_its_passes_differ():
    torch.manual_seed(0)
    x = torch.rand(16, 2, 4, 8, 8)  # per-sample masks: a repeat is ~0 at batch 16
    assert not train.teacher_is_stochastic(build_resenc_unet(2, 4, True), x)
    conv = torch.nn.Conv3d(2, 1, 1)
    assert train.teacher_is_stochastic(
        torch.nn.Sequential(conv, torch.nn.Dropout3d(0.5)), x
    )
    assert not train.teacher_is_stochastic(
        torch.nn.Sequential(conv, torch.nn.Dropout(0.0)), x
    )
    assert train.teacher_is_stochastic(torch.nn.Sequential(conv, _DropPath()), x)
    # Batch statistics are deterministic for one input.
    bn = torch.nn.Sequential(conv, torch.nn.BatchNorm3d(1))
    assert not train.teacher_is_stochastic(bn, x)
    teacher = torch.nn.Sequential(conv, torch.nn.Dropout3d(0.5)).eval()
    train.teacher_is_stochastic(teacher, x)
    assert not teacher.training  # mode restored


def test_one_teacher_pass_gives_a_zero_variance_not_nan():
    teacher = torch.nn.Conv3d(1, 1, 1)
    x = torch.rand(2, 1, 4, 8, 8)
    prob, var = train.uamt_teacher(teacher, x, 1)
    assert prob.shape == var.shape == (2, 1, 4, 8, 8)
    assert torch.equal(var, torch.zeros_like(prob))
    assert teacher.training  # the mode it was called with
    train.uamt_teacher(teacher.eval(), x, 1)
    assert not teacher.training


def test_dropout_makes_the_passes_differ():
    torch.manual_seed(0)
    teacher = torch.nn.Sequential(torch.nn.Conv3d(1, 4, 1), torch.nn.Dropout3d(0.5))
    _, var = train.uamt_teacher(teacher.eval(), torch.rand(2, 1, 4, 8, 8), 4)
    assert var.max() > 1e-3  # dropout acts in the passes
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
