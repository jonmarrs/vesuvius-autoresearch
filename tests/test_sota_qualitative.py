import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.qualitative import region_to_layers, write_fragment


def test_region_to_layers_centered_window():
    vol = np.arange(40 * 8 * 8).reshape(40, 8, 8).astype(np.uint8)
    out = region_to_layers(vol, n_layers=26)
    assert out.shape == (26, 8, 8)
    # centered: lo = 20 - 13 = 7
    assert np.array_equal(out[0], vol[7])


def test_region_to_layers_too_few_raises():
    with pytest.raises(ValueError, match="depth"):
        region_to_layers(np.zeros((10, 8, 8), np.uint8), n_layers=26)


def test_write_fragment_layout(tmp_path):
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    out = write_fragment(layers, str(tmp_path), "segX")
    names = sorted(os.listdir(os.path.join(out, "layers")))
    assert names == [f"{i:02d}.tif" for i in range(17, 43)]
    assert os.path.exists(os.path.join(out, "segX_inklabels.png"))
    assert os.path.exists(os.path.join(out, "segX_mask.png"))
