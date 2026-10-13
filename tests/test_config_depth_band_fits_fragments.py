"""config.json's depth_band must name slices of the volumes it is applied to.

The labeled dataset indexes the zarr's own slices. These fragments' zarrs hold
surface-volume layers 16-48 (33 slices), so the detector's layers 17-42 are zarr
slices 1-26; a band copied in layer numbers lies past the volume and every dataset
build refuses it (finding 87).
"""

import os
from pathlib import Path

import pytest
import zarr

from scripts.training.config import ExperimentConfig

REPO = Path(__file__).resolve().parents[1]
CONFIG = ExperimentConfig.load(REPO / "config.json")


def _depth(uri):
    z = zarr.open(str(REPO / uri), "r")
    return (z["0"] if isinstance(z, zarr.Group) else z).shape[0]


@pytest.mark.parametrize("uri", [*CONFIG.uris, CONFIG.val_uri])
def test_config_depth_band_lies_inside_each_labeled_volume(uri):
    if CONFIG.depth_band is None:
        pytest.skip("no depth band configured")
    if not os.path.exists(REPO / uri):
        pytest.skip(f"{uri} is not in this checkout")
    start, end = CONFIG.depth_band
    depth = _depth(uri)
    assert start >= 0 and end <= depth, (
        f"depth_band {CONFIG.depth_band} lies outside {uri} ({depth} slices)"
    )
