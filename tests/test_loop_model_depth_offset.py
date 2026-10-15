"""Finding 90 forces each validation read to start at one slice; the plane
position and target must not move with it, or the comparison is not paired."""

import json

import numpy as np
import pytest
import torch
from conftest import restore_cuda_env
from PIL import Image

from scripts.loop_model_depth_offset import force_start, reading
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

restore_cuda_env()  # do not leave the mask for other test modules

SIZE, DEPTH, READ = 8, 32, 12


@pytest.fixture
def dataset(tmp_path):
    import zarr

    volume = tmp_path / "surface_volume.zarr"
    array = zarr.open(str(volume), mode="w", shape=(DEPTH, 40, 40), dtype="u1")
    array[:] = np.broadcast_to(  # slice z holds z
        np.arange(DEPTH, dtype="u1")[:, None, None], (DEPTH, 40, 40)
    )
    rng = np.random.default_rng(0)
    labels = tmp_path / "inklabels.png"
    Image.fromarray((rng.random((40, 40)) > 0.5).astype("u1") * 255).save(labels)
    catalog = tmp_path / "patches.json"
    origins = [(8, 8), (16, 24), (24, 8), (0, 32), (32, 0)]
    catalog.write_text(json.dumps({"patches": [{"y": y, "x": x} for y, x in origins]}))
    return VesuviusLabeledDataset(
        str(volume),
        str(labels),
        patch_size=SIZE,
        num_layers=READ,
        patches_json=str(catalog),
        cache_dir=str(tmp_path / "cache"),
        seed=42,
        depth_band=[4, 20],
        depth_margin=4,
    )


def _first_slice(item):
    return round(float(item[0][0, 0, 0, 0]) * 255)


def test_a_forced_start_reads_there_and_moves_nothing_else(dataset):
    assert dataset.depth_range == (0, 24)  # starts 0-12
    natural = [dataset[i] for i in range(len(dataset))]
    assert len({_first_slice(item) for item in natural}) > 1
    for z0 in (0, 5, 12):
        force_start(dataset, z0)
        forced = [dataset[i] for i in range(len(dataset))]
        assert {_first_slice(item) for item in forced} == {z0}
        for a, b in zip(natural, forced, strict=True):
            assert torch.equal(a[1], b[1])
    force_start(dataset, None)
    again = [dataset[i] for i in range(len(dataset))]
    assert [_first_slice(i) for i in again] == [_first_slice(i) for i in natural]


def test_a_start_outside_the_reads_is_refused(dataset):
    with pytest.raises(ValueError, match="outside"):
        force_start(dataset, 13)


@pytest.mark.parametrize(
    "incumbent,candidates,expected",
    [
        (0.02, [0.01] * 8 + [-0.01] * 2, "deep windows read better"),
        (0.019, [0.01] * 10, "mixed"),
        (0.03, [0.01] * 7 + [-0.01] * 3, "mixed"),
        (-0.02, [-0.01] * 8 + [0.01] * 2, "shallow windows read better"),
        (0.009, [0.009] * 10, "no dependence"),
        (0.009, [0.011] * 10, "mixed"),
    ],
)
def test_the_pre_registered_reading(incumbent, candidates, expected):
    assert reading(incumbent, candidates).startswith(expected)
