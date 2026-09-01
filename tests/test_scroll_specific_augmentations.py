import torch
from train import ExperimentConfig

from scroll_augmentations import apply_scroll_specific_3d_augmentations


def test_scroll_specific_augmentations_preserve_shapes_and_label_bounds():
    torch.manual_seed(7)
    config = ExperimentConfig(
        aug_scroll_decohesion_p=1.0,
        aug_scroll_squeeze_p=1.0,
        aug_scroll_z_dropout_p=1.0,
        aug_scroll_intensity_drift_p=1.0,
    )
    x = torch.linspace(0, 1, 2 * 1 * 8 * 16 * 16).reshape(2, 1, 8, 16, 16)
    ink = torch.zeros((2, 1, 16, 16))
    ink[:, :, 4:12, 4:12] = 1.0
    fiber = torch.zeros((2, 1, 1, 16, 16))
    fiber[:, :, :, :, 7:9] = 1.0

    x_aug, ink_aug, fiber_aug = apply_scroll_specific_3d_augmentations(
        x, ink, fiber, config
    )

    assert x_aug.shape == x.shape
    assert ink_aug.shape == ink.shape
    assert fiber_aug.shape == fiber.shape
    assert torch.isfinite(x_aug).all()
    assert float(ink_aug.min()) >= 0.0
    assert float(ink_aug.max()) <= 1.0
    assert float(fiber_aug.min()) >= 0.0
    assert float(fiber_aug.max()) <= 1.0
    assert not torch.allclose(x_aug, x)


def test_scroll_specific_augmentations_noop_when_disabled():
    config = ExperimentConfig(
        aug_scroll_decohesion_p=0.0,
        aug_scroll_squeeze_p=0.0,
        aug_scroll_z_dropout_p=0.0,
        aug_scroll_intensity_drift_p=0.0,
    )
    x = torch.rand((1, 1, 6, 8, 8))
    ink = torch.rand((1, 1, 8, 8))
    fiber = torch.rand((1, 1, 1, 8, 8))

    x_aug, ink_aug, fiber_aug = apply_scroll_specific_3d_augmentations(
        x, ink, fiber, config
    )

    torch.testing.assert_close(x_aug, x)
    torch.testing.assert_close(ink_aug, ink)
    torch.testing.assert_close(fiber_aug, fiber)


def test_adapter_exercises_all_nine_families(monkeypatch):
    import scroll_augmentations as sa

    called = set()

    def spy(name, fn):
        def wrapped(*a, **k):
            called.add(name)
            return fn(*a, **k)

        return wrapped

    for name in [
        "scroll_decohesion",
        "scroll_warping",
        "scroll_squeeze",
        "scroll_z_dropout",
        "scroll_intensity_drift",
        "scroll_sheet_compression",
        "scroll_thick_slice",
        "scroll_rician_noise",
        "scroll_blank_rectangles",
    ]:
        monkeypatch.setattr(sa, name, spy(name, getattr(sa, name)))

    cfg = ExperimentConfig(
        aug_scroll_decohesion_p=1.0,
        aug_scroll_warping_p=1.0,
        aug_scroll_squeeze_p=1.0,
        aug_scroll_z_dropout_p=1.0,
        aug_scroll_intensity_drift_p=1.0,
        aug_scroll_sheet_compression_p=1.0,
        aug_scroll_thick_slice_p=1.0,
        aug_scroll_rician_noise_p=1.0,
        aug_scroll_blank_rectangles_p=1.0,
    )
    x = torch.rand(2, 1, 8, 16, 16)
    ink = torch.zeros((2, 1, 16, 16))
    ink[:, :, 4:12, 4:12] = 1.0
    fiber = torch.zeros((2, 1, 1, 16, 16))
    fiber[:, :, :, :, 7:9] = 1.0

    sa.apply_scroll_specific_3d_augmentations(x, ink, fiber, cfg)

    assert called == {
        "scroll_decohesion",
        "scroll_warping",
        "scroll_squeeze",
        "scroll_z_dropout",
        "scroll_intensity_drift",
        "scroll_sheet_compression",
        "scroll_thick_slice",
        "scroll_rician_noise",
        "scroll_blank_rectangles",
    }
