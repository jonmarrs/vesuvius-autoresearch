import numpy as np
from PIL import Image

from scripts.spatial_split_mask import split_mask


def test_split_produces_disjoint_regions_with_buffer():
    mask = np.ones((20, 100), dtype=bool)
    u, v = split_mask(mask, axis=1, fraction=0.5, buffer=10)
    assert u[:, :45].all() and not u[:, 45:].any()
    assert v[:, 55:].all() and not v[:, :55].any()
    assert not (u & v).any()
    assert not u[:, 45:55].any() and not v[:, 45:55].any()


def test_split_respects_original_mask():
    mask = np.zeros((10, 100), dtype=bool)
    mask[:, 10:90] = True
    u, v = split_mask(mask, axis=1, fraction=0.5, buffer=10)
    assert (u <= mask).all() and (v <= mask).all()
