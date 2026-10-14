"""Finding 88's detector windows must sit where the loader read each patch.

Validation jitters every patch by up to half a patch (VesuviusLabeledDataset,
jitter=True). Finding 88 first read the detector at valid_coords, before the
jitter, so it was scored against targets a median 16 px away (corrected
2026-10-14).
"""

import json

import numpy as np
import pytest
from conftest import restore_cuda_env
from PIL import Image

from scripts.detector_on_loop_sample import check_origins, patch_origin
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

restore_cuda_env()  # do not leave the mask for other test modules

SIZE = 8
ORIGINS = [(8, 8), (16, 24), (24, 8), (0, 32), (32, 0)]


@pytest.fixture
def fragment(tmp_path):
    import zarr

    volume = tmp_path / "surface_volume.zarr"
    zarr.open(str(volume), mode="w", shape=(12, 40, 40), dtype="u1")[:] = 128
    labels = tmp_path / "inklabels.png"
    rng = np.random.default_rng(0)
    Image.fromarray((rng.random((40, 40)) > 0.5).astype("u1") * 255).save(labels)
    catalog = tmp_path / "patches.json"
    catalog.write_text(json.dumps({"patches": [{"y": y, "x": x} for y, x in ORIGINS]}))

    def dataset(jitter):
        return VesuviusLabeledDataset(
            str(volume),
            str(labels),
            patch_size=SIZE,
            num_layers=12,
            patches_json=str(catalog),
            cache_dir=str(tmp_path / "cache"),
            seed=42,
            jitter=jitter,
        )

    return volume, dataset


def _windows(labels, origins):
    return [labels[y : y + SIZE, x : x + SIZE] for y, x in origins]


@pytest.mark.parametrize("jitter", [True, False])
def test_the_origin_is_where_the_loader_read_the_target(fragment, jitter):
    volume, make = fragment
    data = make(jitter)
    labels = np.asarray(Image.open(volume.parent / "inklabels.png")) > 127
    origins = [patch_origin(data, i) for i in range(len(data))]
    targets = [
        np.asarray(data[i][1]).reshape(SIZE, SIZE) > 0.5 for i in range(len(data))
    ]
    for window, target in zip(_windows(labels, origins), targets, strict=True):
        np.testing.assert_array_equal(window, target)
    check_origins(str(volume), origins, [data[i][1] for i in range(len(data))])


def test_the_pre_jitter_coordinates_are_not_where_it_read(fragment):
    volume, make = fragment
    data = make(True)
    labels = np.asarray(Image.open(volume.parent / "inklabels.png")) > 127
    before = [tuple(int(v) for v in data.valid_coords[i]) for i in range(len(data))]
    assert before != [patch_origin(data, i) for i in range(len(data))]
    with pytest.raises(RuntimeError, match="not that patch's target"):
        check_origins(str(volume), before, [data[i][1] for i in range(len(data))])
    assert labels.any()
