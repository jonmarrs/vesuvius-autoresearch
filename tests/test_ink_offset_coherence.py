"""Tests for the coherence statistic.

The script under test was first called `scripts/test_ink_offset_coherence.py`,
which collides with this file's module name: pytest imports the test first, so
`import test_ink_offset_coherence` inside it resolved to the test module itself
and every attribute lookup failed. A non-test script must not be named `test_*`.

A null result from this test is only worth reporting if the test can see the
thing it looked for. The load-bearing test here is therefore the positive
control: an injected coherent shift must be detected. The real data returned
p = 0.60-0.72, and that means nothing unless a planted signal comes back
significant.
"""

import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import measure_ink_offset_coherence as mod  # noqa: E402


def _map(nz=96, nt=256, seed=0):
    rng = np.random.default_rng(seed)
    zz, tt = np.meshgrid(np.arange(nz), np.arange(nt), indexing="ij")
    H = 2.0 + np.sin(2 * np.pi * tt / nt * 5) + np.cos(2 * np.pi * zz / nz * 3)
    return H * (rng.random(H.shape) < 0.6)


def test_the_registered_parameters_are_constants():
    assert mod.N_SLICES == 24
    assert mod.MAX_SHIFT_DEG == 15.0
    assert mod.N_SHUFFLE == 1000


def test_positive_control_a_planted_coherent_shift_is_detected():
    """THE load-bearing test. Without this the reported null is just silence."""
    H = _map()
    nz = H.shape[0]
    shifted = np.stack(
        [np.roll(H[i], int(round(4 * np.sin(2 * np.pi * i / nz)))) for i in range(nz)]
    )
    r = mod.coherence(H, shifted, np.random.default_rng(1))
    assert r["p"] < 0.05, f"a planted coherent shift was missed (p={r['p']})"
    assert r["lag1"] > 0.5


def test_independent_noise_is_not_called_coherent():
    rng = np.random.default_rng(3)
    H = _map(seed=1)
    jittered = np.stack(
        [np.roll(H[i], int(rng.integers(-6, 7))) for i in range(H.shape[0])]
    )
    r = mod.coherence(H, jittered, np.random.default_rng(2))
    assert not (r["p"] == r["p"] and r["p"] < 0.01), (
        "independent jitter read as coherent"
    )


def test_lag1_is_nan_when_there_is_no_variation():
    assert np.isnan(mod.lag1(np.zeros(10)))
    assert np.isnan(mod.lag1(np.array([1.0, 2.0])))


def test_slice_shift_recovers_a_known_roll():
    rng = np.random.default_rng(0)
    a = rng.random(256)
    assert mod.slice_shift(a, np.roll(a, 7), 20) == -7.0


def test_slice_shift_returns_None_on_empty_input():
    assert mod.slice_shift(np.zeros(64), np.ones(64), 10) is None
    assert mod.slice_shift(np.ones(64), np.ones(64), 10) is None


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(_REPO, "reports/ink_offset_coherence.json")),
    reason="coherence test not run",
)
def test_the_published_null_covers_every_pair():
    import json

    d = json.load(open(os.path.join(_REPO, "reports/ink_offset_coherence.json")))
    assert len(d["pairs"]) == 3, (
        "all three baseline pairs must be reported, none dropped"
    )
    assert d["n_slices"] == 24 and d["n_shuffle"] == 1000
