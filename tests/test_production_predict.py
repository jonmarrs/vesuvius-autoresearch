"""Exercise the production CLI against a real local volume and checkpoint."""

import json
import sys

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
