import torch
import torch.nn as nn
import numpy as np
from argparse import Namespace

from predict import load_compatible_state_dict, save_vc3d_zarr, write_prediction_metadata


def test_load_compatible_state_dict_skips_mismatched_tensors():
    model = nn.Linear(2, 1)
    state = {
        "weight": torch.ones((1, 2)),
        "bias": torch.ones(3),
        "extra.weight": torch.ones(1),
    }

    skipped = load_compatible_state_dict(model, state)

    assert skipped == ["bias", "extra.weight"]
    torch.testing.assert_close(model.weight, torch.ones((1, 2)))


def test_save_vc3d_zarr_writes_ome_scale_metadata(tmp_path):
    out = tmp_path / "fiber.zarr"
    arr = np.full((8, 8), 127, dtype=np.uint8)

    save_vc3d_zarr(out, arr, name="Fiber Prediction", voxel_size_um=7.91, source_uri="local.zarr", origin_xyz=[1, 2, 3])

    zattrs = __import__("json").loads((out / ".zattrs").read_text())
    transform = zattrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][0]
    translation = zattrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][1]
    assert transform == {"type": "scale", "scale": [7.91, 7.91, 7.91]}
    assert translation == {"type": "translation", "translation": [1.0, 2.0, 3.0]}
    assert (out / "meta.json").exists()
    assert (out / "0" / ".zarray").exists()


def test_write_prediction_metadata_records_fiber_vc3d_artifacts(tmp_path):
    args = Namespace(
        uri="local_data/scroll/0",
        x=10,
        y=20,
        z=30,
        width=64,
        height=64,
        patch_size=64,
        voxel_size_um=7.91,
    )
    path = tmp_path / "meta.json"

    write_prediction_metadata(
        path,
        args,
        {"patch_size": 64, "scroll_id": "Scroll 2"},
        "ink.zarr",
        "prediction.png",
        {"mean": 0.1, "std": 0.2, "max": 0.3},
        fiber_zarr_path="fiber.zarr",
        fiber_stats={"mean": 0.4, "std": 0.5, "max": 0.6},
    )

    metadata = __import__("json").loads(path.read_text())
    assert metadata["vc3d_zarr_path"] == "ink.zarr"
    assert metadata["fiber_vc3d_zarr_path"] == "fiber.zarr"
    assert metadata["fiber_stats"]["max"] == 0.6
