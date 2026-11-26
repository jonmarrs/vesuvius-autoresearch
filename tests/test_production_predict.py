"""Exercise the production CLI against a real local volume and checkpoint."""

import json
import sys
from pathlib import Path
from weakref import ref

import numpy as np
import pytest
import torch
import zarr

from scripts import production_predict as production
from vesuvius_autoresearch.core import model_wrappers, vesuvius_loader


class ConstantModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.bias = torch.nn.Parameter(torch.tensor(0.0))
        self.batches = []

    def forward(self, x):
        assert x.ndim == 5 and x.shape[1:3] == (1, 2)
        assert torch.allclose(x, torch.full_like(x, 128 / 255))
        self.batches.append(len(x))
        return self.bias.expand(x.shape[0], 1, x.shape[-2], x.shape[-1])


def production_fixture(tmp_path, monkeypatch):
    volume = tmp_path / "ct.zarr"
    array = zarr.open(
        str(volume), mode="w", shape=(5, 20, 24), chunks=(2, 8, 8), dtype="u1"
    )
    array[:] = 128
    model = ConstantModel()
    checkpoint = tmp_path / "trained.pt"
    torch.save(
        {
            "config": {
                "architecture": "gated_unet",
                "patch_size": 8,
                "num_layers": 2,
                "base_feat": 4,
                "voxel_size_um": 2.0,
            },
            "model_state_dict": model.state_dict(),
        },
        checkpoint,
    )
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(model_wrappers, "build_inference_model", lambda **kwargs: model)
    # The prediction wrapper imports the same canonical factory at module load.
    monkeypatch.setattr(
        "scripts.inference.predict.build_inference_model", lambda **kwargs: model
    )
    out = tmp_path / "output"
    argv = [
        "production_predict.py",
        "--uri",
        str(volume),
        "--checkpoint",
        str(checkpoint),
        "--x",
        "3",
        "--y",
        "2",
        "--z",
        "1",
        "--width",
        "13",
        "--height",
        "11",
        "--stride",
        "4",
        "--batch-size",
        "4",
        "--out-dir",
        str(out),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    return out, argv, model


def test_production_checkpoint_volume_edges_and_metadata(tmp_path, monkeypatch):
    out, _, model = production_fixture(tmp_path, monkeypatch)
    production.production_predict()
    dest = next(out.glob("*.zarr"))
    result = zarr.open(str(dest / "0"), mode="r")[:]
    assert result.shape == (1, 11, 13)
    np.testing.assert_array_equal(result, np.full((1, 11, 13), 127, np.uint8))
    assert model.batches == [4, 2]  # six tiles, including the remainder batch
    attrs = json.loads((dest / ".zattrs").read_text())
    transforms = attrs["multiscales"][0]["datasets"][0]["coordinateTransformations"]
    assert transforms[0]["scale"] == [2.0, 2.0, 2.0]
    assert transforms[1]["translation"] == [2.0, 4.0, 6.0]  # z, y, x in micrometers
    metadata = json.loads(next(out.glob("*_meta.json")).read_text())
    assert metadata["patch_size"] == 8
    assert metadata["position_xyz"] == [3, 2, 1]
    assert metadata["output_image_path"] is None
    assert metadata["scale_bar_cm"] is False


@pytest.mark.parametrize("state_key", ["model_state_dict", "model"])
def test_production_releases_saved_checkpoint_storage(tmp_path, monkeypatch, state_key):
    out, _, model = production_fixture(tmp_path, monkeypatch)
    checkpoint_path = tmp_path / "trained.pt"
    checkpoint = torch.load(checkpoint_path, weights_only=True)
    checkpoint.pop("model_state_dict")
    checkpoint[state_key] = {"bias": torch.tensor(1.0)}
    checkpoint["optimizer"] = {"unused": torch.zeros(64)}
    torch.save(checkpoint, checkpoint_path)

    load = production.load_checkpoint
    open_volume = production.FastVesuviusVolume
    transfer = model.to
    storage = {}
    observed = []

    def track_checkpoint(*args, **kwargs):
        loaded = load(*args, **kwargs)
        storage["weights"] = ref(loaded[state_key]["bias"].untyped_storage())
        storage["optimizer"] = ref(loaded["optimizer"]["unused"].untyped_storage())
        return loaded

    def track_volume(*args, **kwargs):
        observed.append(("open CT", storage["optimizer"]() is None))
        return open_volume(*args, **kwargs)

    def track_transfer(*args, **kwargs):
        observed.append(("transfer model", storage["weights"]() is None))
        return transfer(*args, **kwargs)

    monkeypatch.setattr(production, "load_checkpoint", track_checkpoint)
    monkeypatch.setattr(production, "FastVesuviusVolume", track_volume)
    monkeypatch.setattr(model, "to", track_transfer)
    production.production_predict()

    assert observed == [("open CT", True), ("transfer model", True)]
    assert model.batches == [4, 2]
    store = next(out.glob("*.zarr"))
    pixels = zarr.open_group(str(store), mode="r")["0"][:]
    expected = int(torch.sigmoid(torch.tensor(1.0)).item() * 255)
    np.testing.assert_array_equal(pixels, np.full((1, 11, 13), expected, np.uint8))


def test_production_releases_blend_planes_before_export(tmp_path, monkeypatch):
    out, _, _ = production_fixture(tmp_path, monkeypatch)
    normalize = production.normalize_blend
    quantize = production.quantize_probabilities
    blend_planes = []
    resident_at_quantization = []

    def remember_blend_planes(values, weights):
        blend_planes.extend((ref(values), ref(weights)))
        return normalize(values, weights)

    def check_planes_at_quantization(values):
        resident_at_quantization.extend(plane() is not None for plane in blend_planes)
        return quantize(values)

    monkeypatch.setattr(production, "normalize_blend", remember_blend_planes)
    monkeypatch.setattr(
        production, "quantize_probabilities", check_planes_at_quantization
    )
    production.production_predict()

    assert resident_at_quantization == [False, False]
    store = next(out.glob("*.zarr"))
    pixels = zarr.open_group(str(store), mode="r")["0"][:]
    np.testing.assert_array_equal(pixels, np.full((1, 11, 13), 127, np.uint8))


def test_production_memory_profile_is_opt_in_and_preserves_pixels(
    tmp_path, monkeypatch
):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    profile_type = production.RegionalMemoryProfile
    monkeypatch.setattr(
        production,
        "RegionalMemoryProfile",
        lambda *args: pytest.fail("profiling enabled by default"),
    )
    production.production_predict()
    sidecar = next(out.glob("*_meta.json"))
    store = next(out.glob("*.zarr"))
    assert "memory_profile" not in json.loads(sidecar.read_text())
    before = zarr.open_group(str(store), mode="r")["0"][:]

    monkeypatch.setattr(production, "RegionalMemoryProfile", profile_type)
    argv.append("--profile-memory")
    production.production_predict()

    profile = json.loads(sidecar.read_text())["memory_profile"]
    assert profile["device"] == "cpu" and profile["units"] == "bytes"
    assert [entry["phase"] for entry in profile["observations"]] == [
        "before_models",
        "models_loaded",
        "inference_complete",
        "metadata_ready",
    ]
    assert all(entry["process_rss_bytes"] > 0 for entry in profile["observations"])
    assert all(entry["cuda"] is None for entry in profile["observations"])
    np.testing.assert_array_equal(zarr.open_group(str(store), mode="r")["0"][:], before)


@pytest.mark.parametrize(
    "option,value",
    [("--width", "4"), ("--stride", "9"), ("--batch-size", "0"), ("--x", "-1")],
)
def test_invalid_prediction_geometry_fails_early(tmp_path, monkeypatch, option, value):
    out, argv, model = production_fixture(tmp_path, monkeypatch)
    argv[argv.index(option) + 1] = value
    with pytest.raises((ValueError, SystemExit)):
        production.production_predict()
    assert model.batches == []
    assert not list(out.glob("*.zarr"))


def test_real_resenc_checkpoint_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    config = {
        "architecture": "resenc_unet",
        "patch_size": 8,
        "num_layers": 8,
        "base_feat": 4,
    }
    model = model_wrappers.build_inference_model(**config).eval()
    checkpoint = tmp_path / "model.pt"
    torch.save({"config": config, "model_state_dict": model.state_dict()}, checkpoint)
    data = np.random.default_rng(3).integers(0, 256, (8, 8, 8), dtype=np.uint8)
    volume = tmp_path / "ct.zarr"
    array = zarr.open(str(volume), mode="w", shape=data.shape, dtype="u1")
    array[:] = data
    with torch.no_grad():
        expected = torch.sigmoid(
            model(torch.from_numpy(data.astype(np.float32) / 255)[None, None])
        )
    out = tmp_path / "predictions"
    production.production_predict(
        [
            "--uri",
            str(volume),
            "--checkpoint",
            str(checkpoint),
            "--x",
            "0",
            "--y",
            "0",
            "--z",
            "0",
            "--width",
            "8",
            "--height",
            "8",
            "--out-dir",
            str(out),
        ]
    )
    actual = zarr.open(str(next(out.glob("*.zarr")) / "0"), mode="r")[:]
    np.testing.assert_allclose(
        actual[0], (expected.numpy()[0, 0] * 255).astype(np.uint8), atol=1
    )


@pytest.mark.parametrize("bad_logit", [float("inf"), float("-inf"), float("nan")])
def test_production_rejects_nonfinite_logits_before_sigmoid(
    tmp_path, monkeypatch, bad_logit
):
    out, _, model = production_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        model, "forward", lambda x: torch.full((len(x), 1, 8, 8), bad_logit)
    )
    with pytest.raises(ValueError, match="finite floating-point ink logits"):
        production.production_predict()
    assert not out.exists()


def test_production_uses_checkpoint_ridge_sigma(tmp_path, monkeypatch):
    out, argv, model = production_fixture(tmp_path, monkeypatch)
    checkpoint_path = argv[argv.index("--checkpoint") + 1]
    checkpoint = torch.load(checkpoint_path, weights_only=False)
    checkpoint["config"].update(use_ridges=True, ridge_sigma=3.0, num_layers=3)
    torch.save(checkpoint, checkpoint_path)
    seen = []

    def ridges(ct, *, sigma):
        seen.append(sigma)
        return np.ones_like(ct)

    def forward(x):
        assert x.shape[1:3] == (2, 3)
        torch.testing.assert_close(x[:, 0], torch.full_like(x[:, 0], 128 / 255))
        assert torch.all(x[:, 1] == 1)
        return torch.zeros((len(x), 1, 8, 8))

    monkeypatch.setattr(vesuvius_loader, "detect_ridges", ridges)
    monkeypatch.setattr(model, "forward", forward)
    production.production_predict()
    assert seen and set(seen) == {3.0}
    assert next(out.glob("*.zarr")).exists()


def test_failed_production_metadata_install_leaves_no_previous_record(
    tmp_path, monkeypatch
):
    out, _, _ = production_fixture(tmp_path, monkeypatch)
    production.production_predict()
    metadata = next(out.glob("*_meta.json"))
    replace = Path.replace

    def stopped(path, target):
        if Path(target) == metadata:
            assert not metadata.exists()
            raise OSError("stopped during metadata installation")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", stopped)
    with pytest.raises(OSError, match="stopped during metadata installation"):
        production.production_predict()
    assert list(out.glob("*.zarr"))
    assert not metadata.exists()
    assert not list(out.glob(".*-*"))


@pytest.mark.parametrize("artifact", ["zarr", "metadata", "profile"])
def test_failed_production_preparation_preserves_the_previous_run(
    tmp_path, monkeypatch, artifact
):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    production.production_predict()

    def snapshot():
        return {
            path.relative_to(out): path.read_bytes()
            for path in out.rglob("*")
            if path.is_file()
        }

    before = snapshot()
    assert next(out.glob("*_meta.json")).is_file()
    checkpoint_path = argv[argv.index("--checkpoint") + 1]
    checkpoint = torch.load(checkpoint_path, weights_only=True)
    checkpoint["model_state_dict"]["bias"].fill_(2)
    torch.save(checkpoint, checkpoint_path)
    write_chunk = zarr.Array.__setitem__
    write_text = Path.write_text

    def fail_after_chunk(array, key, values):
        write_chunk(array, key, values)
        if array.chunks == (1, 256, 256):
            raise OSError("stopped during Zarr preparation")

    def fail_after_partial_record(path, data, *args, **kwargs):
        if '"prediction_complete"' in data:
            write_text(path, '{"prediction_complete":', *args, **kwargs)
            raise OSError("stopped during metadata preparation")
        return write_text(path, data, *args, **kwargs)

    sample = production.RegionalMemoryProfile.sample

    def fail_at_metadata_ready(self, phase):
        if phase == "metadata_ready":
            assert list(out.glob(".prediction-zarr-*/new.zarr/0/.zarray"))
            raise OSError("stopped during profile preparation")
        sample(self, phase)

    if artifact == "zarr":
        monkeypatch.setattr(zarr.Array, "__setitem__", fail_after_chunk)
    elif artifact == "metadata":
        monkeypatch.setattr(Path, "write_text", fail_after_partial_record)
    else:
        argv.append("--profile-memory")
        monkeypatch.setattr(
            production.RegionalMemoryProfile, "sample", fail_at_metadata_ready
        )
    with pytest.raises(OSError, match="stopped during .* preparation"):
        production.production_predict()

    assert snapshot() == before
    assert not list(out.glob(".*-*"))
