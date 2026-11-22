import os
import sys

import pytest
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "training"))

from train import compute_dice_loss, confidence_weight  # noqa: E402

from scripts.training.ink_losses import confidence_weighted_ink_losses  # noqa: E402


def test_confidence_weight_zero_on_uncertain_band():
    target = torch.tensor([[0.0, 0.5, 1.0]])
    w = confidence_weight(target)
    assert torch.allclose(w, torch.tensor([[1.0, 0.0, 1.0]]))


def test_uncertain_pixels_contribute_zero_ink_gradient():
    torch.manual_seed(0)
    logits = torch.randn(1, 1, 4, 4, requires_grad=True)
    target = torch.full((1, 1, 4, 4), 0.5)
    w = confidence_weight(target)
    bce_map = torch.nn.functional.binary_cross_entropy_with_logits(
        logits, target.clamp(0, 1), reduction="none"
    )
    loss = (bce_map * w).sum() / w.sum().clamp_min(1.0)
    loss.backward()
    assert torch.allclose(logits.grad, torch.zeros_like(logits.grad))


def test_dice_loss_weight_is_noop_on_binary_target():
    pred = torch.randn(2, 1, 8, 8)
    target = (torch.rand(2, 1, 8, 8) > 0.5).float()
    w = confidence_weight(target)
    assert torch.allclose(
        compute_dice_loss(pred, target, weight=w), compute_dice_loss(pred, target)
    )


@pytest.mark.parametrize("term", ["bce", "dice"])
@pytest.mark.parametrize(
    "dtype", [torch.float16, torch.bfloat16, torch.float32, torch.float64]
)
def test_png_ignore_pixels_have_zero_loss_and_gradient(term, dtype):
    logits = torch.full((1, 1, 32, 32), 2.0, dtype=dtype, requires_grad=True)
    target = torch.full_like(logits, 128 / 255)
    bce, dice = confidence_weighted_ink_losses(logits, target)
    loss = bce if term == "bce" else dice
    loss.backward()
    assert loss.item() == 0
    assert torch.count_nonzero(logits.grad) == 0


def test_fractional_dice_weight_is_applied_once():
    logits = torch.logit(torch.tensor([[[[0.8, 0.2, 0.4, 0.6]]]]))
    target = torch.tensor([[[[1.0, 0.0, 1.0, 0.0]]]])
    weight = torch.tensor([[[[0.25, 1.0, 0.5, 0.0]]]])
    # Intersection = .8*.25 + .4*.5; mass = 1.8*.25 + .2 + 1.4*.5.
    expected = 1 - (2 * 0.4 + 1e-5) / (1.35 + 1e-5)
    assert compute_dice_loss(logits, target, weight=weight).item() == pytest.approx(
        expected
    )


def test_unscored_samples_do_not_dilute_weighted_dice():
    logits = torch.zeros(1, 1, 3, 3)
    target = torch.ones_like(logits)
    expected = compute_dice_loss(logits, target, weight=torch.ones_like(logits))
    padded_logits = torch.cat([logits, torch.full_like(logits, 10)])
    padded_target = torch.cat([target, torch.full_like(target, 128 / 255)])
    weight = torch.cat([torch.ones_like(logits), torch.zeros_like(logits)])
    assert compute_dice_loss(
        padded_logits, padded_target, weight=weight
    ).item() == pytest.approx(expected.item())


@pytest.mark.parametrize(
    "dtype", [torch.float16, torch.bfloat16, torch.float32, torch.float64]
)
def test_ignore_encoding_across_training_precisions(dtype):
    # Include a float32-decoded PNG value promoted to double, as well as values
    # constructed directly at the requested dtype.
    values = torch.tensor([0, 0.5, 128 / 255, 1], dtype=dtype)
    torch.testing.assert_close(
        confidence_weight(values), torch.tensor([1, 0, 0, 1], dtype=dtype)
    )
    decoded = torch.tensor(128 / 255, dtype=torch.float32).to(dtype)
    assert confidence_weight(decoded).item() == 0


def test_ignored_logits_do_not_change_loss_or_scored_gradients():
    target = torch.tensor([[[[0.0, 1.0, 128 / 255, 0.5]]]])
    losses, gradients = [], []
    for ignored_logit in [-30.0, 30.0]:
        logits = torch.tensor(
            [[[[-0.2, 0.4, ignored_logit, ignored_logit]]]], requires_grad=True
        )
        bce, dice = confidence_weighted_ink_losses(logits, target)
        loss = bce + dice
        loss.backward()
        losses.append(loss.detach())
        gradients.append(logits.grad)
    torch.testing.assert_close(losses[0], losses[1], rtol=0, atol=0)
    torch.testing.assert_close(gradients[0], gradients[1], rtol=0, atol=0)
    assert torch.count_nonzero(gradients[0][..., :2]) == 2
    assert torch.count_nonzero(gradients[0][..., 2:]) == 0


def test_unit_confidence_matches_binary_bce_and_dice():
    logits = torch.linspace(-2, 2, 24).reshape(2, 1, 3, 4)
    target = (torch.arange(24).reshape_as(logits) % 3 == 0).float()
    bce, dice = confidence_weighted_ink_losses(logits, target)
    torch.testing.assert_close(
        bce, torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
    )
    torch.testing.assert_close(dice, compute_dice_loss(logits, target))


@pytest.mark.parametrize("dtype", [torch.float16, torch.bfloat16])
def test_large_low_precision_weighted_losses_have_finite_reductions(dtype):
    logits = torch.full((1, 1, 256, 256), 8.0, dtype=dtype, requires_grad=True)
    target = torch.ones_like(logits)
    bce, dice = confidence_weighted_ink_losses(logits, target)
    (bce + dice).backward()
    assert torch.isfinite(bce) and torch.isfinite(dice)
    assert bce < 0.001 and dice < 0.001
    assert torch.isfinite(logits.grad).all()


@pytest.mark.parametrize("missing_channel", [False, True])
def test_supported_target_shapes_agree(missing_channel):
    logits = torch.zeros(2, 1, 4, 4)
    target = torch.ones_like(logits)
    expected = confidence_weighted_ink_losses(logits, target)
    if missing_channel:
        target = target[:, 0]
    for value, reference in zip(
        confidence_weighted_ink_losses(logits, target), expected, strict=True
    ):
        torch.testing.assert_close(value, reference)


def test_accidental_broadcasting_is_rejected():
    logits = torch.zeros(2, 1, 4, 4)
    with pytest.raises(ValueError, match="target must match"):
        confidence_weighted_ink_losses(logits, torch.ones(1, 1, 4, 4))
    with pytest.raises(ValueError, match="weight must match"):
        compute_dice_loss(logits, torch.ones_like(logits), weight=torch.ones(4, 4))


@pytest.mark.parametrize("confidence", [False, True])
@pytest.mark.parametrize("strict", [False, True])
def test_periodic_checkpoint_records_the_confidence_loss_recipe(
    tmp_path, confidence, strict
):
    import train

    from scripts.training.config import ExperimentConfig
    from scripts.training.ink_losses import CONFIDENCE_INK_RECIPE

    class TinyModel(torch.nn.Module):
        def forward(self, x):
            return x[:, :, 0]

    model = TinyModel()
    target = torch.tensor([[0.0, 1.0], [1.0, 0.0]])
    dataset = [(torch.zeros(1, 12, 2, 2), target, torch.zeros(1, 1, 2, 2))]
    config = ExperimentConfig(
        num_layers=4,
        checkpoint_out=str(tmp_path / "model.pt"),
        use_confidence_weight=confidence,
        strict_training_reads=strict,
    )
    train.periodic_pixel_auc_eval(model, dataset, config, "cpu", 3, 1.5)
    saved = torch.load(tmp_path / "model.pt.step3.pt", weights_only=False)
    assert saved["data_read_policy"] == {
        "training": "strict" if strict else "legacy_permissive",
        "validation": "strict",
    }
    assert saved["confidence_ink_recipe"] == (
        CONFIDENCE_INK_RECIPE if confidence else None
    )
    assert saved["config"]["use_confidence_weight"] is confidence
