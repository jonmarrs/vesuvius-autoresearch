from argparse import Namespace
from pathlib import Path
from stat import S_IMODE

import numpy as np
import pytest
import torch
import zarr

from scripts.inference.predict import (
    save_vc3d_zarr,
    write_prediction_metadata,
)


def test_save_vc3d_zarr_writes_ome_scale_metadata(tmp_path):
    out = tmp_path / "fiber.zarr"
    arr = np.full((8, 8), 127, dtype=np.uint8)

    save_vc3d_zarr(
        out,
        arr,
        name="Fiber Prediction",
        voxel_size_um=7.91,
        source_uri="local.zarr",
        origin_xyz=[1, 2, 3],
    )

    zattrs = __import__("json").loads((out / ".zattrs").read_text())
    transform = zattrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][0]
    translation = zattrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][
        1
    ]
    assert transform == {"type": "scale", "scale": [7.91, 7.91, 7.91]}
    assert translation["type"] == "translation"
    assert translation["translation"] == pytest.approx([3 * 7.91, 2 * 7.91, 1 * 7.91])
    assert (out / "meta.json").exists()
    assert (out / "0" / ".zarray").exists()
    assert zarr.open_group(str(out), mode="r")["0"].shape == (1, 8, 8)


def test_replacing_vc3d_level_zero_preserves_other_entries_and_modes(tmp_path):
    out = tmp_path / ("prediction-" + "x" * 233 + ".zarr")
    save_vc3d_zarr(out, np.full((3, 4), 17, dtype=np.uint8))
    group = zarr.open_group(str(out), mode="a")
    group.create_dataset("1", shape=(1, 2, 2), dtype="u1")[:] = 42
    notes = out / "notes.txt"
    notes.write_text("keep alongside the generated level")
    out.chmod(0o750)
    (out / ".zattrs").chmod(0o644)
    (out / "meta.json").chmod(0o640)

    save_vc3d_zarr(out, np.full((5, 6), 19, dtype=np.uint8))

    group = zarr.open_group(str(out), mode="r")
    assert group["0"].shape == (1, 5, 6)
    np.testing.assert_array_equal(group["0"][0], 19)
    np.testing.assert_array_equal(group["1"][0], 42)
    assert notes.read_text() == "keep alongside the generated level"
    assert S_IMODE(out.stat().st_mode) == 0o750
    assert S_IMODE((out / ".zattrs").stat().st_mode) == 0o644
    assert S_IMODE((out / "meta.json").stat().st_mode) == 0o640
    assert list(tmp_path.iterdir()) == [out]


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
    assert metadata["vc3d_zarr_path"] == str(Path("ink.zarr").resolve())
    assert metadata["fiber_vc3d_zarr_path"] == str(Path("fiber.zarr").resolve())
    assert metadata["scale_bar_cm"] is False
    assert metadata["fiber_stats"]["max"] == 0.6
