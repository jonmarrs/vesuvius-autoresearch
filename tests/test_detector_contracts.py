"""Behavioral regressions for detector configuration and report boundaries."""

import importlib
import json
import subprocess
import sys
from dataclasses import asdict, replace

import numpy as np
import pytest
import pytorch_lightning as pl
import torch
from torch import nn

from vesuvius_autoresearch.detector import cli
from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.eval import evaluate
from vesuvius_autoresearch.detector.model import DetectorModel
from vesuvius_autoresearch.detector.model_resenc import ResEncDetectorModel
from vesuvius_autoresearch.detector.train import build_scheduler

inference = importlib.import_module("vesuvius_autoresearch.detector.infer")
measurement = importlib.import_module("vesuvius_autoresearch.detector.measure")


def test_reproduction_gate_is_enforced_with_python_optimization():
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            "from vesuvius_autoresearch.detector.cli import assert_auc; "
            "assert_auc({'pixel_auc': 0.56})",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "below target" in result.stderr


@pytest.mark.parametrize(
    "settings",
    [
        {"start_idx": 17.0, "end_idx": 43.0},
        {"start_idx": True, "end_idx": 27},
        {"architecture": []},
        {"architecture": "resenc", "resenc_n_stages": 3.5},
        {"architecture": "resenc", "resenc_base_feat": 0},
        {"um_per_px": float("nan")},
        {"um_per_px": 0},
        {"max_lateral_px": float("inf")},
        {"use_tta": "false"},
        {"epochs": 0},
        {"num_workers": -1},
        {"lr": float("nan")},
        {"weight_decay": -1},
        {"max_grad_norm": 0},
        {"warmup_factor": 0.5},
        {"bce_smooth": 2},
        {"dice_w": 0, "bce_w": 0},
        {"train_fragment_ids": "one-fragment"},
    ],
)
def test_invalid_config_is_rejected_before_work(settings):
    with pytest.raises(ValueError):
        DetectorConfig(**settings).validate()


def test_cli_reports_wrong_config_types_as_usage_errors(tmp_path, capsys):
    config = tmp_path / "config.json"
    config.write_text('{"architecture": "resenc", "resenc_n_stages": 3.5}')
    with pytest.raises(SystemExit) as exc:
        cli.main(["train", "--config", str(config)])
    assert exc.value.code == 2
    assert "invalid detector configuration" in capsys.readouterr().err


@pytest.mark.parametrize("model_cls", [DetectorModel, ResEncDetectorModel])
def test_optimizer_obeys_weight_decay(model_cls):
    model = nn.Linear(1, 1)
    model.cfg = DetectorConfig(weight_decay=0.123)
    optimizers, _ = model_cls.configure_optimizers(model)
    assert optimizers[0].param_groups[0]["weight_decay"] == pytest.approx(0.123)


def test_default_config_describes_the_existing_training_recipe():
    cfg = DetectorConfig()
    assert cfg.weight_decay == 0.01  # AdamW's previously implicit default
    assert cfg.max_grad_norm == 1.0  # previously hardcoded by train()
    assert cfg.warmup_factor == 1.0  # previously hardcoded by build_scheduler()


def test_scheduler_obeys_warmup_factor():
    cfg = DetectorConfig(lr=0.001, warmup_factor=3.0)
    optimizer = torch.optim.AdamW(nn.Linear(1, 1).parameters(), lr=cfg.lr)
    scheduler = build_scheduler(cfg, optimizer)
    optimizer.step()
    scheduler.step()
    assert optimizer.param_groups[0]["lr"] == pytest.approx(0.003)


def test_training_obeys_gradient_clip(tmp_path, monkeypatch):
    training = importlib.import_module("vesuvius_autoresearch.detector.train")
    monkeypatch.setattr(
        training, "build_datasets", lambda cfg: ([0, 1], [0], [], (1, 1))
    )
    monkeypatch.setattr(training, "build_model", lambda *args, **kwargs: None)
    seen = {}

    class Trainer:
        def __init__(self, **kwargs):
            seen.update(kwargs)
            self.callback = kwargs["callbacks"][0]

        def fit(self, *args, **kwargs):
            path = tmp_path / "saved.ckpt"
            path.touch()
            self.callback.best_model_path = str(path)

    monkeypatch.setattr(training.pl, "Trainer", Trainer)
    training.train(
        DetectorConfig(
            model_dir=str(tmp_path),
            train_batch_size=2,
            num_workers=0,
            max_grad_norm=2.5,
        )
    )
    assert seen["gradient_clip_val"] == 2.5


class FixedGrid(nn.Module):
    """A deliberately non-equivariant model to expose missing TTA/unflipping."""

    def __init__(self, bad=None):
        super().__init__()
        self.seen = []
        self.bad = bad

    def forward(self, x):
        self.seen.append(x.detach().cpu().clone())
        out = torch.tensor([[-2.0, 2.0], [-1.0, 1.0]], device=x.device)
        out = out.expand(x.shape[0], 1, 2, 2).clone()
        if self.bad == "nan":
            out[0, 0, 0, 0] = float("nan")
        elif self.bad == "batch":
            out = out[:1]
        elif self.bad == "channels":
            out = out.expand(-1, 2, -1, -1)
        elif self.bad == "integer":
            out = out.long()
        return out


def _local_volume(monkeypatch, width=64):
    image = np.arange(64 * width * 26, dtype=np.uint8).reshape(64, width, 26)
    mask = np.ones((64, width), np.uint8)
    monkeypatch.setattr(
        inference, "read_volume_mask", lambda *args: (image, mask, (64, width))
    )


@pytest.mark.parametrize("batch_size", [1, 3])
def test_tta_mirrors_inputs_and_unflips_probability_maps(monkeypatch, batch_size):
    _local_volume(monkeypatch, width=96)
    model = FixedGrid()
    prob = inference.infer(
        DetectorConfig(use_tta=True), None, "frag", model=model, batch_size=batch_size
    )
    # Opposing logits have complementary probabilities, so properly unflipped
    # four-view averages are uniformly 0.5 across both windows and their overlap.
    np.testing.assert_allclose(prob, 0.5, atol=1e-6)
    assert len(model.seen) == (8 if batch_size == 1 else 4)
    for start in range(0, len(model.seen), 4):
        original = model.seen[start]
        for offset, dims in enumerate(((-1,), (-2,), (-2, -1)), 1):
            torch.testing.assert_close(model.seen[start + offset], original.flip(dims))


def test_disabled_tta_keeps_one_forward(monkeypatch):
    _local_volume(monkeypatch)
    model = FixedGrid()
    prob = inference.infer(DetectorConfig(), None, "frag", model=model)
    assert len(model.seen) == 1
    assert prob[0, 0] < prob[0, -1]


@pytest.mark.parametrize("bad", ["nan", "batch", "channels", "integer"])
def test_bad_model_output_fails_instead_of_exporting_it(monkeypatch, bad):
    _local_volume(monkeypatch, width=96)
    with pytest.raises(ValueError, match="model output"):
        inference.infer(
            DetectorConfig(), None, "frag", model=FixedGrid(bad), batch_size=3
        )


def _checkpoint(tmp_path, *, record=True):
    cfg = DetectorConfig(
        architecture="resenc",
        resenc_n_stages=3,
        resenc_base_feat=4,
        in_chans=8,
        start_idx=0,
        end_idx=8,
    )
    model = ResEncDetectorModel(cfg, (1, 1))
    payload = {
        "state_dict": model.state_dict(),
        "pytorch-lightning_version": pl.__version__,
    }
    if record:
        model.on_save_checkpoint(payload)
    path = tmp_path / "model.ckpt"
    torch.save(payload, path)
    return cfg, model, payload, path


def test_checkpoint_records_config_and_reloads_real_weights(tmp_path):
    cfg, original, payload, path = _checkpoint(tmp_path)
    assert payload["detector_config"] == asdict(cfg)
    loaded = ResEncDetectorModel.load_from_checkpoint(
        path, cfg=cfg, pred_shape=(1, 1), weights_only=False
    ).eval()
    original.eval()
    x = torch.randn(1, 1, 8, 64, 64)
    with torch.no_grad():
        torch.testing.assert_close(loaded(x), original(x))


def test_checkpoint_rejects_same_shape_but_wrong_depth_origin_before_volume_read(
    tmp_path, monkeypatch
):
    cfg, _, _, path = _checkpoint(tmp_path)
    reads = []
    monkeypatch.setattr(inference, "read_volume_mask", lambda *args: reads.append(args))
    with pytest.raises(ValueError, match="checkpoint.*start_idx"):
        inference.infer(replace(cfg, start_idx=1, end_idx=9), path, "absent")
    assert not reads


def test_checkpoint_allows_different_targets_paths_and_tta(tmp_path):
    cfg, _, _, path = _checkpoint(tmp_path)
    cfg = replace(
        cfg,
        data_root="elsewhere",
        valid_fragment_id="new",
        use_tta=True,
        stride=16,
        lr=1e-4,
    )
    ResEncDetectorModel.load_from_checkpoint(
        path, cfg=cfg, pred_shape=(1, 1), weights_only=False
    )


def test_checkpoint_rejects_wrong_window_with_compatible_convolution_weights(tmp_path):
    cfg, _, _, path = _checkpoint(tmp_path)
    with pytest.raises(ValueError, match="checkpoint.*size"):
        ResEncDetectorModel.load_from_checkpoint(
            path, cfg=replace(cfg, size=32), pred_shape=(1, 1), weights_only=False
        )


def test_legacy_checkpoint_warns_that_config_is_unverified(tmp_path):
    cfg, _, _, path = _checkpoint(tmp_path, record=False)
    with pytest.warns(UserWarning, match="legacy.*configuration"):
        ResEncDetectorModel.load_from_checkpoint(
            path, cfg=cfg, pred_shape=(1, 1), weights_only=False
        )


@pytest.mark.parametrize("record", [None, {}, {"size": 64}, "invalid"])
def test_malformed_recorded_checkpoint_config_is_rejected(tmp_path, record):
    cfg, _, payload, path = _checkpoint(tmp_path)
    payload["detector_config"] = record
    torch.save(payload, path)
    with pytest.raises(ValueError, match="checkpoint.*configuration"):
        ResEncDetectorModel.load_from_checkpoint(
            path, cfg=cfg, pred_shape=(1, 1), weights_only=False
        )


@pytest.mark.parametrize("version", [None, True, 2])
def test_checkpoint_rejects_unknown_config_version(tmp_path, version):
    cfg, _, payload, path = _checkpoint(tmp_path)
    payload["detector_config_version"] = version
    torch.save(payload, path)
    with pytest.raises(ValueError, match="checkpoint.*configuration version"):
        ResEncDetectorModel.load_from_checkpoint(
            path, cfg=cfg, pred_shape=(1, 1), weights_only=False
        )


@pytest.mark.parametrize(
    "kind",
    [
        "no_positive",
        "no_negative",
        "empty_mask",
        "nan_label",
        "nan_mask",
        "negative_prob",
        "shape",
    ],
)
def test_invalid_evaluation_does_not_replace_reports(tmp_path, kind):
    cfg = DetectorConfig(reports_dir=str(tmp_path))
    label = np.array([[0.0, 1.0], [1.0, 0.0]])
    prob = label.copy()
    mask = np.ones((2, 2), bool)
    if kind == "no_positive":
        label[:] = 0
    elif kind == "no_negative":
        label[:] = 1
    elif kind == "empty_mask":
        mask[:] = False
    elif kind == "nan_label":
        label[0, 0] = float("nan")
    elif kind == "nan_mask":
        mask = mask.astype(float)
        mask[0, 0] = float("nan")
    elif kind == "negative_prob":
        prob[0, 0] = -1
    elif kind == "shape":
        mask = np.ones((1, 2), bool)
    saved = tmp_path / "frag_scorecard.json"
    saved.write_text('{"previous": true}')
    with pytest.raises(ValueError):
        evaluate(prob, label, mask, cfg)
    assert saved.read_text() == '{"previous": true}'
    assert sorted(p.name for p in tmp_path.iterdir()) == ["frag_scorecard.json"]


def test_measure_records_degenerate_target_failure_and_cli_exits_nonzero(
    tmp_path, monkeypatch, capsys
):
    cfg = DetectorConfig(reports_dir=str(tmp_path))
    monkeypatch.setattr(
        measurement, "infer", lambda *args, **kwargs: np.ones((2, 2), np.float32)
    )

    def inputs(cfg, fid):
        label = np.zeros((2, 2))
        if fid == "good":
            label[0, 0] = 1
        return None, label, np.ones((2, 2), np.uint8)

    monkeypatch.setattr(measurement, "read_image_mask", inputs)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"reports_dir": str(tmp_path)}))
    assert (
        cli.main(["measure", "--config", str(path), "--same", "good", "--cross", "bad"])
        == 1
    )
    rows = json.loads(
        (tmp_path / "cross_scroll_measurement.json").read_text(),
        parse_constant=lambda value: pytest.fail(f"nonfinite JSON: {value}"),
    )
    assert rows["good"]["val_f1"] > 0
    assert "error" in rows["bad"]
    assert "bad" in capsys.readouterr().err
