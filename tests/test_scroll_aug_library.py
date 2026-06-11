import torch

from scroll_augmentations import ScrollAugProbs, apply_scroll_augmentations


def _sample():
    x = torch.linspace(0, 1, 2 * 1 * 8 * 16 * 16).reshape(2, 1, 8, 16, 16)
    ink = torch.zeros((2, 1, 16, 16))
    ink[:, :, 4:12, 4:12] = 1.0
    fiber = torch.zeros((2, 1, 1, 16, 16))
    fiber[:, :, :, :, 7:9] = 1.0
    return x, ink, fiber


def test_all_probs_one_changes_input_and_preserves_shapes():
    torch.manual_seed(0)
    x, ink, fiber = _sample()
    probs = ScrollAugProbs(
        decohesion=1.0,
        warping=1.0,
        squeeze=1.0,
        z_dropout=1.0,
        intensity_drift=1.0,
        sheet_compression=1.0,
        thick_slice=1.0,
        rician_noise=1.0,
        blank_rectangles=1.0,
    )
    x2, ink2, fiber2 = apply_scroll_augmentations(
        x.clone(), ink.clone(), fiber.clone(), probs
    )
    assert (
        x2.shape == x.shape and ink2.shape == ink.shape and fiber2.shape == fiber.shape
    )
    assert torch.isfinite(x2).all()
    assert not torch.equal(x2, x)  # something actually happened
    assert float(ink2.min()) >= 0.0 and float(ink2.max()) <= 1.0


def test_all_probs_zero_is_identity():
    torch.manual_seed(0)
    x, ink, fiber = _sample()
    x2, ink2, fiber2 = apply_scroll_augmentations(
        x.clone(), ink.clone(), fiber.clone(), ScrollAugProbs()
    )
    assert torch.equal(x2, x) and torch.equal(ink2, ink) and torch.equal(fiber2, fiber)
