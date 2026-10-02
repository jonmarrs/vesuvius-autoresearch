import importlib
import json

import numpy as np
import pytest

from vesuvius_autoresearch.detector import cli


def test_assert_auc_passes_at_target():
    cli.assert_auc({"pixel_auc": 0.711}, target=0.70)  # must not raise


def test_assert_auc_fails_below_target():
    with pytest.raises(AssertionError, match="0.70"):
        cli.assert_auc({"pixel_auc": 0.56}, target=0.70)


def test_main_parses_subcommands():
    assert cli.main(["--help-check"]) == 0  # no-op path returns 0


def test_measure_cli_reports_partial_failure(monkeypatch, capsys):
    module = importlib.import_module("vesuvius_autoresearch.detector.measure")
    monkeypatch.setattr(module, "measure", lambda *args: {
        "same": {"scroll_label": "same", "val_f1": 0.5},
        "cross": {"scroll_label": "cross", "error": "missing layer 17.tif"},
    })
    assert cli.main(["measure"]) == 1
    output = capsys.readouterr()
    assert "val_f1=0.5" in output.out
    assert "cross" in output.err and "missing layer 17.tif" in output.err


def test_infer_cli_uses_config_and_saves_probability_map(tmp_path, monkeypatch):
    module = importlib.import_module("vesuvius_autoresearch.detector.infer")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"data_root": str(tmp_path), "architecture": "resenc"}))
    expected = np.full((64, 96), 0.7, dtype=np.float32)

    def predict(cfg, checkpoint, fragment_id, *, batch_size):
        assert cfg.architecture == "resenc"
        assert cfg.data_root == str(tmp_path)
        assert checkpoint == "test.ckpt" and fragment_id == "unlabeled"
        assert batch_size == 3
        return expected

    monkeypatch.setattr(module, "infer", predict)
    output = tmp_path / "predictions/prob.npy"
    assert cli.main([
        "infer", "--config", str(config), "--checkpoint", "test.ckpt",
        "--fragment", "unlabeled", "--output", str(output), "--batch-size", "3",
    ]) == 0
    np.testing.assert_array_equal(np.load(output), expected)


def test_cli_rejects_unknown_config_fields(tmp_path, capsys):
    path = tmp_path / "config.json"
    path.write_text('{"architecure": "resenc"}')
    with pytest.raises(SystemExit) as error:
        cli.main(["train", "--config", str(path)])
    assert error.value.code == 2
    assert "architecure" in capsys.readouterr().err
