"""Evaluation consumes one volume generation and preserves its filesystem inputs."""

import importlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
from torch import nn

from vesuvius_autoresearch.core.report_artifacts import check_report
from vesuvius_autoresearch.detector import cli, data
from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.eval import evaluate
from vesuvius_autoresearch.detector.scoring import score_prediction

inference = importlib.import_module("vesuvius_autoresearch.detector.infer")
measurement = importlib.import_module("vesuvius_autoresearch.detector.measure")


@pytest.fixture
def fragment(tmp_path, monkeypatch):
    root = tmp_path / "data/frag"
    (root / "layers").mkdir(parents=True)
    for index in range(2):
        assert cv2.imwrite(
            str(root / "layers" / f"{index:02d}.tif"),
            np.full((32, 36), 100, np.uint8),
        )
    label = np.zeros((32, 36), np.uint8)
    label[:, ::2] = 255
    assert cv2.imwrite(str(root / "frag_inklabels.png"), label)
    assert cv2.imwrite(str(root / "frag_mask.png"), np.full_like(label, 255))
    cfg = DetectorConfig(
        data_root=str(root.parent),
        reports_dir=str(tmp_path / "reports"),
        valid_fragment_id="frag",
        start_idx=0,
        end_idx=2,
        in_chans=2,
        size=16,
        tile_size=16,
        stride=16,
    )

    class Grid(nn.Module):
        def forward(self, x):
            return torch.zeros((len(x), 1, 1, 1), device=x.device)

    loads = []

    def load(*args, **kwargs):
        loads.append(True)
        return Grid()

    monkeypatch.setattr(inference.DetectorModel, "load_from_checkpoint", load)
    return cfg, root, loads


def _score(cfg, mode, **kwargs):
    if mode == "eval":
        return cli._eval_fragment(cfg, "test.ckpt", "frag", **kwargs)
    return measurement.measure(cfg, "test.ckpt", [("frag", "same")], **kwargs)["frag"]


@pytest.mark.parametrize("mode", ["eval", "measure"])
def test_scoring_decodes_each_ct_layer_and_fragment_mask_only_once(
    fragment, monkeypatch, mode
):
    cfg, root, _ = fragment
    reads = Counter()
    original = data.cv2.imread

    def read(path, *args, **kwargs):
        reads[Path(path)] += 1
        return original(path, *args, **kwargs)

    monkeypatch.setattr(data.cv2, "imread", read)
    with pytest.warns(RuntimeWarning, match="uncovered"):
        row = _score(cfg, mode)
    assert "error" not in row
    assert reads[root / "layers/00.tif"] == 1
    assert reads[root / "layers/01.tif"] == 1
    assert reads[root / "frag_mask.png"] == 1
    assert reads[root / "frag_inklabels.png"] == 1


@pytest.mark.parametrize("command", ["eval", "measure", "reproduce"])
def test_cli_cannot_replace_its_own_configuration_with_report_files(
    fragment, monkeypatch, command
):
    cfg, _, loads = fragment
    reports = Path(cfg.reports_dir)
    reports.mkdir()
    name = (
        "cross_scroll_measurement.json"
        if command == "measure"
        else "frag_scorecard.json"
    )
    config = reports / name
    before = json.dumps(asdict(cfg)).encode()
    config.write_bytes(before)
    if command == "reproduce":
        monkeypatch.setattr(
            cli,
            "_ensure_converted",
            lambda *args: pytest.fail("conversion started before report preflight"),
        )
    args = [command, "--config", str(config)]
    if command == "eval":
        args += ["--fragment", "frag", "--checkpoint", "test.ckpt"]
    elif command == "measure":
        args += ["--same", "frag", "--cross", "missing", "--checkpoint", "test.ckpt"]
    with pytest.raises(ValueError, match="artifact collision"):
        cli.main(args)
    assert config.read_bytes() == before
    assert loads == []


@pytest.mark.parametrize("mode", ["eval", "measure"])
def test_reports_record_coverage_without_changing_the_scoring_mask(fragment, mode):
    cfg, _, _ = fragment
    with pytest.warns(RuntimeWarning, match="uncovered"):
        row = _score(cfg, mode)
    assert row["n_pixels"] == 1152
    assert row["prediction_coverage"] == {
        "valid_pixels": 1152,
        "predicted_pixels": 1024,
        "uncovered_pixels": 128,
        "coverage_fraction": 1024 / 1152,
    }
    name = (
        "frag_scorecard.json"
        if mode == "eval"
        else "cross_scroll_measurement_manifest.json"
    )
    assert check_report(Path(cfg.reports_dir) / name)["report_status"] == "COMPLETE"
    if mode == "measure":
        saved = json.loads(
            (Path(cfg.reports_dir) / "cross_scroll_measurement.json").read_text()
        )
        assert saved["frag"]["prediction_coverage"] == row["prediction_coverage"]
        assert (
            "uncovered_pixels"
            in (Path(cfg.reports_dir) / "cross_scroll_measurement.md").read_text()
        )


@pytest.mark.parametrize("mode", ["eval", "measure"])
def test_scoring_uses_the_mask_captured_during_inference(fragment, monkeypatch, mode):
    cfg, root, _ = fragment
    read = inference.read_volume_mask

    def captured(*args):
        result = read(*args)
        assert cv2.imwrite(str(root / "frag_mask.png"), np.zeros((32, 36), np.uint8))
        return result

    monkeypatch.setattr(inference, "read_volume_mask", captured)
    with pytest.warns(RuntimeWarning, match="uncovered"):
        row = _score(cfg, mode)
    assert "error" not in row
    assert row["n_pixels"] == row["prediction_coverage"]["valid_pixels"] == 1152


def test_strict_eval_preserves_a_previous_complete_report(fragment, tmp_path):
    cfg, _, _ = fragment
    with pytest.warns(RuntimeWarning):
        _score(cfg, "eval")
    reports = Path(cfg.reports_dir)
    before = {p.name: p.read_bytes() for p in reports.iterdir()}
    config = tmp_path / "config.json"
    config.write_text(json.dumps(asdict(cfg)))
    with pytest.raises(ValueError, match="128 of 1152 fragment pixels are uncovered"):
        cli.main(
            [
                "eval",
                "--config",
                str(config),
                "--checkpoint",
                "test.ckpt",
                "--fragment",
                "frag",
                "--require-full-coverage",
            ]
        )
    assert {p.name: p.read_bytes() for p in reports.iterdir()} == before


def test_strict_measurement_records_partial_failure_and_exits_nonzero(
    fragment, tmp_path
):
    cfg, root, _ = fragment
    full = root.parent / "full"
    (full / "layers").mkdir(parents=True)
    for index in range(2):
        assert cv2.imwrite(
            str(full / "layers" / f"{index:02d}.tif"),
            cv2.imread(str(root / "layers" / f"{index:02d}.tif"), 0)[:, :32],
        )
    for suffix in ("mask", "inklabels"):
        assert cv2.imwrite(
            str(full / f"full_{suffix}.png"),
            cv2.imread(str(root / f"frag_{suffix}.png"), 0)[:, :32],
        )
    config = tmp_path / "config.json"
    config.write_text(json.dumps(asdict(cfg)))
    assert (
        cli.main(
            [
                "measure",
                "--config",
                str(config),
                "--checkpoint",
                "test.ckpt",
                "--same",
                "full",
                "--cross",
                "frag",
                "--require-full-coverage",
            ]
        )
        == 1
    )
    report = Path(cfg.reports_dir)
    rows = json.loads((report / "cross_scroll_measurement.json").read_text())
    assert rows["full"]["prediction_coverage"]["uncovered_pixels"] == 0
    assert "uncovered" in rows["frag"]["error"]
    manifest = check_report(report / "cross_scroll_measurement_manifest.json")
    assert manifest["report_status"] == "PARTIAL"
    assert manifest["success_count"] == manifest["failure_count"] == 1


@pytest.mark.parametrize(
    "coverage",
    [
        np.ones((1, 2), bool),
        np.ones((2, 2), np.uint8),
        np.ones((1, 2, 2), bool),
        np.empty((0, 2), bool),
    ],
)
def test_invalid_coverage_cannot_replace_a_previous_scorecard(tmp_path, coverage):
    marker = tmp_path / "frag_scorecard.json"
    marker.write_bytes(b"previous")
    label = np.array([[0.0, 1.0], [1.0, 0.0]])
    with pytest.raises(ValueError, match="matching nonempty 2D boolean"):
        evaluate(
            label,
            label,
            np.ones((2, 2), bool),
            DetectorConfig(reports_dir=str(tmp_path)),
            coverage=coverage,
        )
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == {
        marker.name: b"previous"
    }


def test_coverage_counts_exclude_pixels_outside_the_scoring_mask():
    label = np.array([[0.0, 1.0], [1.0, 0.0]])
    mask = np.array([[True, False], [True, True]])
    coverage = np.array([[True, True], [False, True]])
    plain = score_prediction(label, label, mask)
    detailed = score_prediction(label, label, mask, coverage=coverage)
    summary = detailed.pop("prediction_coverage")
    assert detailed == plain
    assert summary == {
        "valid_pixels": 3,
        "predicted_pixels": 2,
        "uncovered_pixels": 1,
        "coverage_fraction": 2 / 3,
    }


@pytest.mark.parametrize("mode", ["eval", "measure"])
@pytest.mark.parametrize(
    "source", ["layers/00.tif", "frag_mask.png", "frag_inklabels.png"]
)
def test_report_aliases_to_fragment_inputs_are_refused_before_inference(
    fragment, mode, source
):
    cfg, root, loads = fragment
    reports = Path(cfg.reports_dir)
    reports.mkdir()
    target = reports / (
        "frag_pred_thumb.png" if mode == "eval" else "cross_scroll_measurement.json"
    )
    target.hardlink_to(root / source)
    before = (root / source).read_bytes()
    with pytest.raises(ValueError, match="artifact collision"):
        _score(cfg, mode)
    assert loads == []
    assert (root / source).read_bytes() == target.read_bytes() == before


@pytest.mark.parametrize("mode", ["eval", "measure"])
def test_reports_cannot_be_published_inside_a_selected_fragment(fragment, mode):
    cfg, root, loads = fragment
    cfg.reports_dir = str(root)
    before = sorted(root.rglob("*"))
    with pytest.raises(ValueError, match="artifact collision"):
        _score(cfg, mode)
    assert loads == [] and sorted(root.rglob("*")) == before


@pytest.mark.parametrize("mode", ["eval", "measure"])
def test_input_alias_created_after_inference_is_refused_before_publication(
    fragment, monkeypatch, mode
):
    cfg, root, _ = fragment
    infer = inference.infer

    def alias(*args, **kwargs):
        result = infer(*args, **kwargs)
        reports = Path(cfg.reports_dir)
        reports.mkdir()
        target = reports / (
            "frag_pred_thumb.png" if mode == "eval" else "cross_scroll_measurement.json"
        )
        target.hardlink_to(root / "frag_inklabels.png")
        return result

    monkeypatch.setattr(inference if mode == "eval" else measurement, "infer", alias)
    before = (root / "frag_inklabels.png").read_bytes()
    with (
        pytest.warns(RuntimeWarning),
        pytest.raises(ValueError, match="artifact collision"),
    ):
        _score(cfg, mode)
    assert (root / "frag_inklabels.png").read_bytes() == before


@pytest.mark.parametrize("mode", ["eval", "measure"])
def test_changed_label_shape_fails_instead_of_cropping_the_prediction(fragment, mode):
    cfg, root, _ = fragment
    assert cv2.imwrite(str(root / "frag_inklabels.png"), np.zeros((16, 16), np.uint8))
    if mode == "eval":
        with (
            pytest.warns(RuntimeWarning),
            pytest.raises(ValueError, match="mask shape mismatch"),
        ):
            _score(cfg, mode)
    else:
        with pytest.warns(RuntimeWarning):
            row = _score(cfg, mode)
        assert "mask shape mismatch" in row["error"]


def test_measurement_rejects_nonboolean_coverage_policy_before_model_work(fragment):
    cfg, _, loads = fragment
    with pytest.raises(ValueError, match="require_full_coverage must be a boolean"):
        measurement.measure(
            cfg, "test.ckpt", [("frag", "same")], require_full_coverage="false"
        )
    assert loads == []
