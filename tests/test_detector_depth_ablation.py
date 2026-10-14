"""scripts/detector_depth_ablation.py: its windows are the loop's, its fills come
from the window it keeps."""

import json
from pathlib import Path

import numpy as np
import pytest
from conftest import restore_cuda_env

from scripts import detector_depth_ablation as mod
from scripts.detector_on_loop_sample import ZARR_SLICE_0_LAYER
from vesuvius_autoresearch.core.inference_constants import DEPTH_MARGIN
from vesuvius_autoresearch.detector.config import DetectorConfig

restore_cuda_env()  # do not leave the mask for other test modules

REPO = Path(__file__).resolve().parents[1]


def _loop_offsets():
    """The detector channels where the loop's 16-slice window can start.

    As VesuviusLabeledDataset draws validation reads: a band widened by the
    margin and clamped to the volume, a read of num_layers + 2 margins starting
    anywhere in it, and the model keeps the read's middle num_layers.
    """
    config = json.loads((REPO / "config.json").read_text())
    profile = json.loads((REPO / "reports" / "ink_depth_profile.json").read_text())
    depth = profile["fragments"]["PHercParis2Fr143"]["shape"][0]
    band_start, band_end = config["depth_band"]
    read = config["num_layers"] + 2 * DEPTH_MARGIN
    start = max(0, band_start - DEPTH_MARGIN)
    end = min(depth, band_end + DEPTH_MARGIN)
    channel_0 = DetectorConfig().start_idx - ZARR_SLICE_0_LAYER
    return [z0 + DEPTH_MARGIN - channel_0 for z0 in range(start, end - read + 1)]


def test_the_offsets_are_the_loops_lowest_middle_and_highest_window():
    offsets = _loop_offsets()
    low, high = min(offsets), max(offsets)
    assert (mod.OFFSETS[0], mod.OFFSETS[-1]) == (low, high) == (3, 10)
    assert mod.OFFSETS[1] in {(low + high) // 2, (low + high + 1) // 2}
    config = json.loads((REPO / "config.json").read_text())
    assert config["num_layers"] == mod.KEPT


@pytest.mark.parametrize("fill", mod.FILLS)
@pytest.mark.parametrize("offset", mod.OFFSETS)
def test_the_window_is_kept_and_the_fill_comes_from_it(offset, fill):
    channels = DetectorConfig().in_chans
    x = np.arange(2 * channels * 4, dtype=np.float32).reshape(2, channels, 2, 2)
    out = mod.windowed(x, offset, fill)
    assert out.shape == x.shape
    kept = slice(offset, offset + mod.KEPT)
    np.testing.assert_array_equal(out[:, kept], x[:, kept])
    for c in [*range(offset), *range(offset + mod.KEPT, channels)]:
        assert any(
            np.array_equal(out[:, c], x[:, k]) for k in range(*kept.indices(channels))
        ), f"channel {c} is not a copy of a kept channel"
    if fill == "edge" and offset > 0:
        np.testing.assert_array_equal(out[:, 0], x[:, offset])


def test_every_variant_is_scored_and_the_first_is_the_full_depth():
    names = [name for name, _, _ in mod.variants(DetectorConfig().in_chans)]
    assert names[0] == "full"
    assert len(names) == 1 + len(mod.FILLS) * len(mod.OFFSETS)


def test_the_draw_is_inside_the_mask_and_repeatable():
    mask = np.zeros((300, 300), bool)
    mask[40:260, 10:290] = True
    a, n = mod.random_windows(mask, 64, 32, 0, 10)
    b, _ = mod.random_windows(mask, 64, 32, 0, 10)
    assert a == b and len(a) == 10 and n >= 10
    for y, x in a:
        assert y % 32 == 0 and x % 32 == 0
        assert mask[y : y + 64, x : x + 64].all()
