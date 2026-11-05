"""Coverage visibility and non-destructive detector prediction exports."""

import errno
import importlib
import os
import stat

import numpy as np
import pytest
import torch
from torch import nn

from vesuvius_autoresearch.core.file_modes import current_umask
from vesuvius_autoresearch.detector import cli
from vesuvius_autoresearch.detector.config import DetectorConfig

inference = importlib.import_module("vesuvius_autoresearch.detector.infer")


class ConstantModel(nn.Module):
    def forward(self, batch):
        return torch.zeros((len(batch), 1, 2, 2), device=batch.device)


def local_volume(monkeypatch, shape=(64, 100), hole=False):
    image = np.zeros((*shape, 26), np.uint8)
    mask = np.ones(shape, np.uint8)
    if hole:
        mask[0, 0] = 0
    # Include the loader's zero padding, which must never count as missing data.
    padded_image = np.pad(image, ((0, 16), (0, 12), (0, 0)))
    padded_mask = np.pad(mask, ((0, 16), (0, 12)))
    monkeypatch.setattr(
        inference,
        "read_volume_mask",
        lambda *args: (padded_image, padded_mask, shape),
    )
    return mask


@pytest.mark.parametrize("hole", [False, True])
def test_partial_coverage_is_visible_and_preserves_existing_probabilities(
    monkeypatch, hole
):
    mask = local_volume(monkeypatch, hole=hole)
    with pytest.warns(RuntimeWarning, match="uncovered.*zero"):
        result = inference.infer(
            DetectorConfig(), None, "frag", model=ConstantModel(), return_details=True
        )
    expected = np.zeros((64, 100), bool)
    expected[:, 32 if hole else 0 : 96] = True
    np.testing.assert_array_equal(result.coverage, expected)
    np.testing.assert_array_equal(result.fragment_mask, mask != 0)
    np.testing.assert_array_equal(result.probability, expected.astype(np.float32) / 2)
    assert result.probability.dtype == np.float32
    assert result.coverage.dtype == result.fragment_mask.dtype == np.bool_
    assert result.summary == {
        "valid_pixels": int(mask.sum()),
        "predicted_pixels": int(expected.sum()),
        "uncovered_pixels": int(mask.sum() - expected.sum()),
        "coverage_fraction": float(expected.sum() / mask.sum()),
    }
    with pytest.warns(RuntimeWarning, match="uncovered"):
        legacy = inference.infer(DetectorConfig(), None, "frag", model=ConstantModel())
    np.testing.assert_array_equal(legacy, result.probability)


def test_full_coverage_ignores_padding_and_nonfragment_pixels(monkeypatch):
    local_volume(monkeypatch, shape=(64, 96))
    result = inference.infer(
        DetectorConfig(),
        None,
        "frag",
        model=ConstantModel(),
        return_details=True,
        require_full_coverage=True,
    )
    assert result.summary["coverage_fraction"] == 1.0
    assert result.summary["uncovered_pixels"] == 0
    np.testing.assert_array_equal(result.probability, np.full((64, 96), 0.5))


def test_strict_coverage_refuses_a_partial_prediction(monkeypatch):
    local_volume(monkeypatch)
    with pytest.raises(ValueError, match="256.*uncovered"):
        inference.infer(
            DetectorConfig(),
            None,
            "frag",
            model=ConstantModel(),
            require_full_coverage=True,
        )


def test_coverage_distinguishes_a_predicted_zero_from_an_unvisited_pixel(monkeypatch):
    local_volume(monkeypatch)

    class BackgroundModel(nn.Module):
        def forward(self, batch):
            return torch.full((len(batch), 1, 2, 2), -1000.0, device=batch.device)

    with pytest.warns(RuntimeWarning, match="uncovered"):
        result = inference.infer(
            DetectorConfig(), None, "frag", model=BackgroundModel(), return_details=True
        )
    assert not result.probability.any()
    assert result.coverage[:, :96].all()
    assert not result.coverage[:, 96:].any()


@pytest.mark.parametrize("option", ["return_details", "require_full_coverage"])
def test_coverage_options_require_booleans_before_loading(monkeypatch, option):
    monkeypatch.setattr(
        inference.DetectorModel,
        "load_from_checkpoint",
        lambda *args, **kwargs: pytest.fail("loaded a checkpoint"),
    )
    with pytest.raises(ValueError, match=option):
        inference.infer(DetectorConfig(), "checkpoint", "frag", **{option: 1})


def stub_prediction(monkeypatch):
    probability = np.full((2, 3), 0.5, np.float32)
    coverage = np.ones((2, 3), bool)

    def predict(*args, **kwargs):
        if kwargs.get("return_details"):
            from vesuvius_autoresearch.detector.prediction import InferenceResult

            return InferenceResult(probability, coverage, coverage)
        return probability

    monkeypatch.setattr(inference, "infer", predict)
    return probability


def command(tmp_path, output, *extra):
    config = tmp_path / "config.json"
    if not config.exists():
        config.write_text('{"data_root": "' + str(tmp_path / "data") + '"}')
    return [
        "infer",
        "--config",
        str(config),
        "--checkpoint",
        str(tmp_path / "model.ckpt"),
        "--fragment",
        "frag",
        "--output",
        str(output),
        *extra,
    ]


@pytest.mark.parametrize("output_format", ["npy", "npz"])
@pytest.mark.parametrize("character", ["p", "界"])
@pytest.mark.parametrize("existing", [False, True])
def test_valid_long_output_name_does_not_overflow_staging_name(
    tmp_path, monkeypatch, output_format, character, existing
):
    probability = stub_prediction(monkeypatch)
    suffix = f".{output_format}"
    limit = os.pathconf(tmp_path, "PC_NAME_MAX")
    output = tmp_path / (
        character * ((limit - len(suffix)) // len(character.encode())) + suffix
    )
    if existing:
        output.write_bytes(b"previous prediction")
        output.chmod(0o440)
    assert cli.main(command(tmp_path, output, "--output-format", output_format)) == 0
    if output_format == "npy":
        actual = np.load(output, allow_pickle=False)
    else:
        with np.load(output, allow_pickle=False) as bundle:
            actual = bundle["probability"]
    np.testing.assert_array_equal(actual, probability)
    if existing:
        assert stat.S_IMODE(output.stat().st_mode) == 0o440
    assert not list(tmp_path.glob(".prediction-*"))


@pytest.mark.parametrize("existing", [False, True])
def test_unwritable_output_directory_fails_before_inference(
    tmp_path, monkeypatch, existing
):
    if os.geteuid() == 0:
        pytest.skip("directory permissions do not constrain root")
    parent = tmp_path / "locked"
    parent.mkdir()
    output = parent / "prediction.npy"
    if existing:
        output.write_bytes(b"previous prediction")
    calls = []

    def infer(*args, **kwargs):
        calls.append(True)
        raise AssertionError("inference must not run before output staging succeeds")

    monkeypatch.setattr(inference, "infer", infer)
    parent.chmod(0o555)
    try:
        with pytest.raises(PermissionError):
            cli.main(command(tmp_path, output))
        assert calls == []
        if existing:
            assert output.read_bytes() == b"previous prediction"
    finally:
        parent.chmod(0o755)


def test_staging_error_does_not_invoke_prediction_producer(tmp_path, monkeypatch):
    prediction = importlib.import_module("vesuvius_autoresearch.detector.prediction")
    output = tmp_path / "prediction.npy"
    output.write_bytes(b"previous prediction")
    calls = []
    stub_prediction(monkeypatch)
    predict = inference.infer

    def counted(*args, **kwargs):
        calls.append(True)
        return predict(*args, **kwargs)

    def fail(*args, **kwargs):
        raise OSError(errno.ENOSPC, "no room for staging")

    monkeypatch.setattr(inference, "infer", counted)
    monkeypatch.setattr(prediction.tempfile, "mkstemp", fail)
    with pytest.raises(OSError, match="no room for staging"):
        cli.main(command(tmp_path, output))
    assert calls == []
    assert output.read_bytes() == b"previous prediction"


@pytest.mark.parametrize("existing", [False, True])
def test_prediction_failure_cleans_reserved_staging_file(
    tmp_path, monkeypatch, existing
):
    output = tmp_path / "prediction.npy"
    if existing:
        output.write_bytes(b"previous prediction")
    seen = []

    def fail(*args, **kwargs):
        staged = list(tmp_path.glob(".prediction-*"))
        assert len(staged) == 1
        assert staged[0].stat().st_size == 0
        assert stat.S_IMODE(staged[0].stat().st_mode) == 0o600 & ~current_umask()
        seen.append(staged[0])
        raise ValueError("prediction failed")

    monkeypatch.setattr(inference, "infer", fail)
    with pytest.raises(ValueError, match="prediction failed"):
        cli.main(command(tmp_path, output))
    assert len(seen) == 1 and not seen[0].exists()
    if existing:
        assert output.read_bytes() == b"previous prediction"
    else:
        assert not output.exists()


@pytest.mark.parametrize("output_format", ["npy", "npz"])
@pytest.mark.parametrize("lazy", [False, True])
def test_prediction_writer_accepts_direct_and_single_call_results(
    tmp_path, output_format, lazy
):
    from vesuvius_autoresearch.detector.prediction import (
        InferenceResult,
        write_prediction,
    )

    probability = np.array([[0.1, 0.9]], dtype=np.float32)
    mask = np.ones(probability.shape, bool)
    result = InferenceResult(probability, mask, mask)
    calls = []

    def produce():
        calls.append(True)
        return result

    output = tmp_path / "prediction.exact"
    actual = write_prediction(output, produce if lazy else result, output_format, [])
    assert actual is result
    assert len(calls) == int(lazy)
    if output_format == "npy":
        np.testing.assert_array_equal(np.load(output, allow_pickle=False), probability)
    else:
        with np.load(output, allow_pickle=False) as bundle:
            np.testing.assert_array_equal(bundle["probability"], probability)
            np.testing.assert_array_equal(bundle["coverage"], mask)
            np.testing.assert_array_equal(bundle["fragment_mask"], mask)


@pytest.mark.parametrize("output_format", ["npy", "npz"])
def test_output_alias_created_during_serialization_is_not_published(
    tmp_path, monkeypatch, output_format
):
    output = tmp_path / "prediction.exact"
    checkpoint = tmp_path / "model.ckpt"
    checkpoint.write_bytes(b"checkpoint to preserve")
    stub_prediction(monkeypatch)
    name = "save" if output_format == "npy" else "savez_compressed"
    save = getattr(np, name)

    def serialize_then_alias(*args, **kwargs):
        save(*args, **kwargs)
        output.symlink_to(checkpoint)

    monkeypatch.setattr(np, name, serialize_then_alias)
    with pytest.raises(ValueError, match="symlink"):
        cli.main(command(tmp_path, output, "--output-format", output_format))
    assert checkpoint.read_bytes() == b"checkpoint to preserve"
    assert output.is_symlink() and output.resolve() == checkpoint
    assert not list(tmp_path.glob(".prediction-*"))


@pytest.mark.parametrize("source", ["checkpoint", "config", "layer", "mask"])
@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
def test_cli_rejects_output_input_aliases_before_inference(
    tmp_path, monkeypatch, source, alias
):
    paths = {
        "checkpoint": tmp_path / "model.ckpt",
        "config": tmp_path / "config.json",
        "layer": tmp_path / "data/frag/layers/17.tif",
        "mask": tmp_path / "data/frag/frag_mask.png",
    }
    target = paths[source]
    target.parent.mkdir(parents=True, exist_ok=True)
    args = command(tmp_path, tmp_path / "prediction.npy")
    if source != "config":
        target.write_bytes(b"input to preserve")
    original = target.read_bytes()
    output = target
    if alias != "direct":
        output = tmp_path / "alias.npy"
        if alias == "symlink":
            output.symlink_to(target)
        else:
            os.link(target, output)
    args[args.index("--output") + 1] = str(output)
    calls = []

    def predict(*args, **kwargs):
        calls.append(True)
        return np.zeros((2, 3), np.float32)

    monkeypatch.setattr(inference, "infer", predict)
    with pytest.raises(ValueError, match="collision|symlink"):
        cli.main(args)
    assert not calls
    assert target.read_bytes() == original


def test_cli_rejects_symlinked_fragment_directory_alias(tmp_path, monkeypatch):
    fragment = tmp_path / "data/frag"
    fragment.mkdir(parents=True)
    alias = tmp_path / "fragment_alias"
    alias.symlink_to(fragment, target_is_directory=True)
    monkeypatch.setattr(
        inference, "infer", lambda *args, **kwargs: pytest.fail("inferred")
    )
    with pytest.raises(ValueError, match="collision"):
        cli.main(command(tmp_path, alias / "new.npy"))
    assert not (fragment / "new.npy").exists()


def test_cli_does_not_truncate_existing_output_when_serialization_fails(
    tmp_path, monkeypatch
):
    stub_prediction(monkeypatch)
    output = tmp_path / "prediction.npy"
    output.write_bytes(b"previous complete prediction")

    def fail(stream, *args, **kwargs):
        stream.write(b"partial replacement")
        raise OSError("disk full")

    monkeypatch.setattr(np, "save", fail)
    with pytest.raises(OSError, match="disk full"):
        cli.main(command(tmp_path, output))
    assert output.read_bytes() == b"previous complete prediction"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "config.json",
        "prediction.npy",
    ]


@pytest.mark.parametrize("output_format", ["npy", "npz"])
def test_cli_exports_exact_path_with_expected_permissions(
    tmp_path, monkeypatch, capsys, output_format
):
    probability = stub_prediction(monkeypatch)
    output = tmp_path / "nested/map.exact"
    args = command(tmp_path, output, "--output-format", output_format)
    assert cli.main(args) == 0
    assert "coverage: 6/6" in capsys.readouterr().out
    assert sorted(path.name for path in output.parent.iterdir()) == ["map.exact"]
    assert stat.S_IMODE(output.stat().st_mode) == 0o666 & ~current_umask()
    if output_format == "npy":
        np.testing.assert_array_equal(np.load(output, allow_pickle=False), probability)
    else:
        with np.load(output, allow_pickle=False) as bundle:
            assert set(bundle.files) == {
                "schema_version",
                "probability",
                "coverage",
                "fragment_mask",
            }
            assert bundle["schema_version"].item() == 1
            np.testing.assert_array_equal(bundle["probability"], probability)
            np.testing.assert_array_equal(bundle["coverage"], np.ones((2, 3), bool))
            assert bundle["coverage"].dtype == bundle["fragment_mask"].dtype == np.bool_
    output.chmod(0o640)
    assert cli.main(args) == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o640


def test_cli_strict_failure_preserves_previous_output(tmp_path, monkeypatch):
    output = tmp_path / "prediction.npy"
    output.write_bytes(b"previous prediction")
    local_volume(monkeypatch)
    monkeypatch.setattr(
        inference.DetectorModel,
        "load_from_checkpoint",
        lambda *args, **kwargs: ConstantModel(),
    )
    with pytest.raises(ValueError, match="uncovered"):
        cli.main(command(tmp_path, output, "--require-full-coverage"))
    assert output.read_bytes() == b"previous prediction"


def test_cli_rechecks_output_alias_after_inference(tmp_path, monkeypatch):
    output = tmp_path / "prediction.npy"
    checkpoint = tmp_path / "model.ckpt"
    checkpoint.write_bytes(b"checkpoint to preserve")
    stub_prediction(monkeypatch)
    predictor = inference.infer

    def retarget(*args, **kwargs):
        output.symlink_to(checkpoint)
        return predictor(*args, **kwargs)

    monkeypatch.setattr(inference, "infer", retarget)
    with pytest.raises(ValueError, match="symlink|collision"):
        cli.main(command(tmp_path, output))
    assert checkpoint.read_bytes() == b"checkpoint to preserve"


@pytest.mark.parametrize("failure", ["npz_save", "rename"])
def test_failed_bundle_publication_keeps_previous_file_and_cleans_temporary(
    tmp_path, monkeypatch, failure
):
    prediction = importlib.import_module("vesuvius_autoresearch.detector.prediction")
    stub_prediction(monkeypatch)
    output = tmp_path / "prediction.npz"
    output.write_bytes(b"previous complete bundle")

    def fail(*args, **kwargs):
        if failure == "npz_save":
            args[0].write(b"partial zip")
        raise OSError("publication failed")

    if failure == "npz_save":
        monkeypatch.setattr(np, "savez_compressed", fail)
    else:
        monkeypatch.setattr(prediction.os, "replace", fail)
    with pytest.raises(OSError, match="publication failed"):
        cli.main(command(tmp_path, output, "--output-format", "npz"))
    assert output.read_bytes() == b"previous complete bundle"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "config.json",
        "prediction.npz",
    ]


@pytest.mark.parametrize("kind", ["directory", "fifo", "dangling_symlink"])
def test_nonregular_outputs_are_refused_before_inference(tmp_path, monkeypatch, kind):
    output = tmp_path / "output"
    if kind == "directory":
        output.mkdir()
    elif kind == "fifo":
        os.mkfifo(output)
    else:
        output.symlink_to(tmp_path / "missing")
    monkeypatch.setattr(
        inference, "infer", lambda *args, **kwargs: pytest.fail("inferred")
    )
    with pytest.raises(ValueError, match="regular file|symlink"):
        cli.main(command(tmp_path, output))


def test_cli_bundle_round_trip_with_real_checkpoint_and_unlabeled_fragment(tmp_path):
    import json
    from dataclasses import asdict

    import cv2
    import pytorch_lightning as pl

    from vesuvius_autoresearch.detector.model_resenc import ResEncDetectorModel

    cfg = DetectorConfig(
        architecture="resenc",
        resenc_n_stages=3,
        resenc_base_feat=4,
        in_chans=8,
        start_idx=0,
        end_idx=8,
        data_root=str(tmp_path / "data"),
    )
    layers = tmp_path / "data/frag/layers"
    layers.mkdir(parents=True)
    for index in range(8):
        assert cv2.imwrite(
            str(layers / f"{index:02d}.tif"), np.zeros((64, 100), np.uint8)
        )
    assert cv2.imwrite(
        str(layers.parent / "frag_mask.png"), np.full((64, 100), 255, np.uint8)
    )
    model = ResEncDetectorModel(cfg, (1, 1))
    checkpoint = {
        "state_dict": model.state_dict(),
        "pytorch-lightning_version": pl.__version__,
    }
    model.on_save_checkpoint(checkpoint)
    torch.save(checkpoint, tmp_path / "model.ckpt")
    (tmp_path / "config.json").write_text(json.dumps(asdict(cfg)))
    output = tmp_path / "prediction.npz"
    args = command(tmp_path, output, "--output-format", "npz", "--batch-size", "2")
    with pytest.warns(RuntimeWarning, match="256.*uncovered"):
        assert cli.main(args) == 0
    with np.load(output, allow_pickle=False) as bundle:
        assert bundle["probability"].shape == (64, 100)
        assert bundle["probability"].dtype == np.float32
        assert np.isfinite(bundle["probability"]).all()
        assert bundle["coverage"].sum() == 6144
        assert bundle["fragment_mask"].sum() == 6400
        assert not bundle["probability"][:, 96:].any()
    previous = output.read_bytes()
    with pytest.raises(ValueError, match="256.*uncovered"):
        cli.main([*args, "--require-full-coverage"])
    assert output.read_bytes() == previous
