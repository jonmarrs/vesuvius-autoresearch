"""Regression test: the Frangi fiber target must actually compute, not silently
fall back to zeros. The upstream villa tools.py uses a global cupy backend that
rejects numpy input, so detect_vesselness(numpy_array) raises and the loader
was returning zeros for the fiber head."""

import numpy as np

from vesuvius_autoresearch.core.vesuvius_loader import frangi_vesselness_zcollapsed


def _tubular_volume(z=12, h=32, w=32):
    """A bright horizontal line through a dark volume -> strong vesselness."""
    vol = np.zeros((z, h, w), dtype=np.float32)
    vol[:, h // 2, :] = 1.0
    return vol


def test_frangi_target_is_nonzero_for_structured_input():
    out = frangi_vesselness_zcollapsed(_tubular_volume(), sigma=2.0)
    assert out.shape == (32, 32)
    assert np.isfinite(out).all()
    assert out.sum() > 0.0  # the bug made this exactly zero


def test_frangi_target_accepts_numpy_without_raising():
    # The exact failure mode: numpy input under a cupy-global tools.py.
    out = frangi_vesselness_zcollapsed(
        np.random.rand(8, 16, 16).astype(np.float32), sigma=2.0
    )
    assert out.shape == (16, 16)
    assert np.isfinite(out).all()
