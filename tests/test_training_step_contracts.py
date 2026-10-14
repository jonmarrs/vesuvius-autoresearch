"""What one training step optimises and what validation reports.

Before 2026-10-12: UA-MT's student and teacher saw independently augmented
views, so its pixel-wise consistency compared misaligned images; the
connected-component and critical-component metrics raised on every 2D patch and
the wrappers reported 0 (a perfect score); mAP was read under a key villa does
not return; and aug_mode="batchgeneratorsv2" fell back to Albumentations without
a word when unavailable and, when available, skipped the configured scroll
augmentations. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-12_TRAINING_STEP.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train  # noqa: E402

from scripts.training.config import ExperimentConfig  # noqa: E402

H = W = 32


def _bar_batch(batch=6, channels=2, depth=8):
    yy, xx = torch.meshgrid(torch.arange(H), torch.arange(W), indexing="ij")
    bar = ((xx < 8) & (yy < 20)).float()  # asymmetric under flips and rotations
    return bar.expand(batch, channels, depth, H, W).clone()


# --- UA-MT --------------------------------------------------------------------


def test_uamt_student_and_teacher_see_the_same_view():
    config = ExperimentConfig(aug_mode="albumentations", aug_scroll_squeeze_p=1.0)
    x = _bar_batch()
    np.random.seed(0)
    torch.manual_seed(0)
    student, teacher = train.uamt_views(x, 1, config)
    assert torch.equal(student, teacher)
    assert not torch.equal(student, x)  # still an augmented view


# --- per-patch metrics --------------------------------------------------------


def _strokes():
    gt = np.zeros((H, W), bool)
    gt[4:8, 4:28] = True
    gt[20:24, 4:28] = True
    blob = np.zeros((H, W), bool)
    blob[2:30, 2:30] = True
    return gt, blob


def test_connected_component_difference_is_measured_on_2d_patches():
    gt, blob = _strokes()
    assert train.compute_cc_diff(gt, gt) == 0
    assert train.compute_cc_diff(gt, blob) == 1  # was 0: the error was swallowed


def test_a_failing_component_metric_raises_instead_of_scoring_perfect(monkeypatch):
    if not hasattr(train, "compute_cc_official"):
        pytest.skip("villa connected_components metric not importable")

    def broken(*args, **kwargs):
        raise ValueError("Label array must have shape [H, W, D] or [N, H, W, D].")

    monkeypatch.setattr(train, "compute_cc_official", broken)
    gt, blob = _strokes()
    with pytest.raises(ValueError):
        train.compute_cc_diff(gt, blob)


def test_critical_components_report_villa_positive_plus_negative():
    if not hasattr(train, "compute_crit_official"):
        with pytest.raises(RuntimeError, match="unavailable"):
            train.compute_crit_comps(*_strokes())
        return
    gt, blob = _strokes()
    assert train.compute_crit_comps(gt, gt) == 0
    assert train.compute_crit_comps(gt, blob) > 0  # was always 0 ("_total" key)


def test_mean_ap_key_matches_villa():
    gt, _ = _strokes()
    prob = gt.astype(np.float32) * 0.9 + 0.05
    try:
        result = train.compute_mean_ap(gt.astype(np.uint8), prob, ignore_index=0)
    except RuntimeError as exc:
        assert "unavailable" in str(exc)
        return
    assert result["mean_ap"] == pytest.approx(1.0)


# --- augmentation modes -------------------------------------------------------


def test_an_unavailable_batchgeneratorsv2_mode_fails_preflight(monkeypatch):
    monkeypatch.setattr(train, "create_training_transforms", None)
    monkeypatch.setattr(train, "TRAINING_TRANSFORMS_IMPORT_ERROR", "No module 'x'")
    config = ExperimentConfig(
        aug_mode="batchgeneratorsv2",
        architecture="gated_unet",
        base_feat=8,
        num_layers=8,
        patch_size=16,
    )
    with pytest.raises(RuntimeError, match="batchgeneratorsv2.*No module 'x'"):
        train.preflight_smoke(config)
    config.aug_mode = "albumentations"
    train.preflight_smoke(config)


class _Identity:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, 0

    def __call__(self, **sample):
        self.calls += 1
        if self.fail:
            raise RuntimeError("Padding size should be less than the input dimension")
        return sample


def _bg2(monkeypatch, transform, **probs):
    x = _bar_batch(batch=2, channels=1, depth=8)
    monkeypatch.setattr(train, "create_training_transforms", lambda shape: transform)
    monkeypatch.setitem(train._bg2_aug_cache, tuple(x.shape[2:]), transform)
    seen = []

    def record(x, ink, fiber, config):
        seen.append(config)
        return x, ink, fiber

    monkeypatch.setattr(train, "apply_scroll_specific_3d_augmentations", record)
    config = ExperimentConfig(aug_mode="batchgeneratorsv2", **probs)
    out = train.apply_augmentations(
        x, torch.zeros(2, 1, H, W), torch.zeros(2, 1, 1, H, W), 1, None, config
    )
    return out, seen


def test_batchgeneratorsv2_still_applies_the_configured_scroll_augmentations(
    monkeypatch,
):
    probs = {
        "aug_scroll_squeeze_p": 0.25,
        "aug_scroll_intensity_drift_p": 0.25,
        "aug_scroll_thick_slice_p": 0.25,  # villa's pipeline applies this one
    }
    (x, ink, fiber), seen = _bg2(monkeypatch, _Identity(), **probs)
    assert len(seen) == 1
    assert seen[0].aug_scroll_squeeze_p == 0.25
    assert seen[0].aug_scroll_intensity_drift_p == 0.25
    assert seen[0].aug_scroll_thick_slice_p == 0.0  # not applied twice
    assert ink.shape == (2, 1, H, W) and fiber.shape == (2, 1, 1, H, W)


def test_batchgeneratorsv2_fallbacks_are_counted(monkeypatch):
    monkeypatch.setitem(train.AUGMENTATION_FALLBACKS, "batchgeneratorsv2", 0)
    transform = _Identity(fail=True)
    _bg2(monkeypatch, transform)
    assert transform.calls == 1
    assert train.AUGMENTATION_FALLBACKS["batchgeneratorsv2"] == 1


# --- TSV logs -----------------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]


def test_a_log_whose_header_differs_is_moved_aside_not_appended_to(tmp_path):
    log = tmp_path / "history.tsv"
    log.write_text("timestamp\tval_bpb\n2026-01-01\t0.5\n")
    train.append_tsv_row(str(log), ("timestamp", "val_bpb", "avg_mean_ap"), [1, 2, 3])
    assert log.read_text() == "timestamp\tval_bpb\tavg_mean_ap\n1\t2\t3\n"
    (aside,) = tmp_path.glob("history.until-*.tsv")
    assert aside.read_text() == "timestamp\tval_bpb\n2026-01-01\t0.5\n"
    train.append_tsv_row(str(log), ("timestamp", "val_bpb", "avg_mean_ap"), [4, 5, 6])
    assert log.read_text().splitlines()[-1] == "4\t5\t6"
    with pytest.raises(ValueError, match="2 values for 3 columns"):
        train.append_tsv_row(str(log), ("timestamp", "val_bpb", "avg_mean_ap"), [7, 8])


@pytest.mark.parametrize(
    "name,columns",
    [
        ("history.tsv", train.HISTORY_COLUMNS),
        ("prize_readiness.tsv", train.PRIZE_READINESS_COLUMNS),
    ],
)
def test_tracked_logs_match_the_columns_train_writes(name, columns):
    path = REPO / name
    if not path.exists():
        pytest.skip(f"{name} not present")
    rows = [line.split("\t") for line in path.read_text().splitlines()]
    assert tuple(rows[0]) == columns
    assert {len(row) for row in rows} == {len(columns)}


class _Catalogue:
    def __init__(self, size, failing=()):
        self.size, self.failing, self.reads = size, set(failing), []

    def __len__(self):
        return self.size

    def __getitem__(self, index):
        self.reads.append(index)
        if index in self.failing:
            raise OSError("chunk unreadable")
        return index


def test_the_probe_reads_only_the_first_protocol_patch():
    from scripts.training.promotion import validation_indices

    catalogue = _Catalogue(1000)
    train.probe_validation_read(catalogue)
    assert catalogue.reads == [int(validation_indices(1000)[0])]


def test_an_unreadable_first_protocol_patch_fails_the_probe():
    from scripts.training.promotion import validation_indices

    first = int(validation_indices(1000)[0])
    with pytest.raises(RuntimeError, match=f"validation patch {first} cannot be read"):
        train.probe_validation_read(_Catalogue(1000, failing=[first]))


def test_train_stops_at_an_unreadable_validation_patch_before_loading_anything(
    monkeypatch,
):
    monkeypatch.setattr(
        train, "build_validation_dataset", lambda config: _Catalogue(10, range(10))
    )

    def too_early(*args, **kwargs):
        pytest.fail("training data or the model was built before the probe")

    for name in ("VesuviusLabeledDataset", "VesuviusS3Dataset", "build_model"):
        monkeypatch.setattr(train, name, too_early)
    # Label files are checked first (file checks only); none exist here.
    monkeypatch.setattr(train, "training_label_path", lambda *args: "labels.png")
    with pytest.raises(RuntimeError, match="cannot be read"):
        train.train(ExperimentConfig())


def _tiny_step_setup(amp=False):
    model = torch.nn.Linear(3, 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0)
    scaler = torch.amp.GradScaler(device="cpu", enabled=amp)
    _backward(model, scaler)
    return model, optimizer, scaler


def _backward(model, scaler):
    scaler.scale(model(torch.ones(2, 3)).sum()).backward()


@pytest.mark.parametrize("amp", [False, True])
def test_a_finite_gradient_is_applied_at_the_scheduled_lr(amp):
    model, optimizer, scaler = _tiny_step_setup(amp)
    before = model.weight.detach().clone()
    assert train.guarded_update(model, optimizer, scaler, lr=0.1)
    assert optimizer.param_groups[0]["lr"] == 0.1
    assert not torch.equal(model.weight, before)


@pytest.mark.parametrize("amp", [False, True])
@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_a_non_finite_gradient_is_skipped_not_applied(value, amp, capsys):
    """With AMP off, GradScaler does not skip such a step, and AdamW made every
    weight and moment NaN for the rest of the cycle."""
    model, optimizer, scaler = _tiny_step_setup(amp)
    model.weight.grad[0, 1] = value
    before = {k: v.clone() for k, v in model.state_dict().items()}
    assert not train.guarded_update(model, optimizer, scaler, lr=0.1, step=7)
    for key, tensor in model.state_dict().items():
        torch.testing.assert_close(tensor, before[key])
    assert all(not state for state in optimizer.state.values())
    assert all(p.grad is None for p in model.parameters())
    # Named before clipping, which would have spread a NaN to the clean bias.
    assert "at step 7 in 1 tensors (weight)" in capsys.readouterr().out
    # The next finite step still works.
    _backward(model, scaler)
    assert train.guarded_update(model, optimizer, scaler, lr=0.1)
    assert all(torch.isfinite(p).all() for p in model.parameters())


def test_an_overflowing_norm_of_finite_gradients_is_named_as_such(capsys):
    model, optimizer, scaler = _tiny_step_setup()
    model.weight.grad.fill_(1e30)
    model.bias.grad.fill_(1e30)
    assert not train.guarded_update(model, optimizer, scaler, lr=0.1)
    assert "overflowed although every tensor is finite" in capsys.readouterr().out


def test_no_gradient_leaves_an_enabled_scaler_usable():
    model, optimizer, scaler = _tiny_step_setup(amp=True)
    optimizer.zero_grad(set_to_none=True)
    assert not train.guarded_update(model, optimizer, scaler, lr=0.1)
    _backward(model, scaler)
    assert train.guarded_update(model, optimizer, scaler, lr=0.1)


def test_both_labeled_datasets_read_inside_the_depth_band(tmp_path, monkeypatch):
    """Training and validation read from the band widened by the context."""
    for fragment in ("train", "val"):
        (tmp_path / fragment).mkdir()
        (tmp_path / fragment / "inklabels.png").write_bytes(b"")
    config = ExperimentConfig(
        num_layers=16,
        depth_band=[17, 43],
        uris=[str(tmp_path / "train" / "surface_volume.zarr")],
        val_uri=str(tmp_path / "val" / "surface_volume.zarr"),
    )
    seen = {}

    class Stop(Exception):
        pass

    def dataset(uri, *args, **kwargs):
        seen[os.path.basename(os.path.dirname(uri))] = (
            kwargs.get("depth_band"),
            kwargs.get("depth_margin"),
        )
        if "train" in uri:
            raise Stop
        return _Catalogue(10)

    monkeypatch.setattr(train, "VesuviusLabeledDataset", dataset)
    # train() builds its model (on CUDA) before the training loaders.
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    with pytest.raises(Stop):
        train.train(config)
    assert seen == {"val": ([17, 43], 4), "train": ([17, 43], 4)}
