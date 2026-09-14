"""Tests for the confidence-vs-reproducibility analysis, written before its data.

The gate that carries the weight is **bin-size dependence**. Agreement fractions
in this corpus move from 89.7% to 43.2% purely with binning, so a result at one
binning proves nothing and the registration requires all three to agree. A
significant result at two of three must report BIN-DEPENDENT, not a finding --
that is the difference between this and the consensus fraction I nearly published.
"""

import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import measure_confidence_vs_reproducibility as mod  # noqa: E402


def test_the_registered_parameters_are_constants():
    assert mod.BINNINGS == ((48, 128), (96, 256), (192, 512))
    assert mod.N_SHUFFLE == 1000
    assert mod.DIFF_THRESHOLD == 0.05
    assert mod.INK_TOLERANCE == 0.001


def test_three_binnings_are_required_not_one():
    assert len(mod.BINNINGS) == 3, "one binning proves nothing in this corpus"


def _fake(nz, nt, diff, rng, n_arms=3):
    """Three arms where unanimous bins carry probability `0.5 + diff` and
    lone-arm bins carry 0.5."""
    ink = np.zeros((n_arms, nz, nt))
    prob = np.zeros((n_arms, nz, nt))
    idx = rng.random((nz, nt))
    unan, lone = idx < 0.25, (idx >= 0.25) & (idx < 0.45)
    for a in range(n_arms):
        ink[a][unan] = 100.0
        prob[a][unan] = 100.0 * (0.5 + diff)
    ink[0][lone] = 100.0
    prob[0][lone] = 100.0 * 0.5
    return {f"a{i}": (ink[i], prob[i]) for i in range(n_arms)}


def test_a_planted_confidence_gap_is_detected():
    rng = np.random.default_rng(0)
    r = mod.one_binning(_fake(96, 256, 0.15, rng), 96, 256, np.random.default_rng(1))
    assert r["diff"] == pytest.approx(0.15, abs=0.01)
    assert r["p"] < 0.05


def test_no_gap_is_not_called_significant():
    rng = np.random.default_rng(2)
    r = mod.one_binning(_fake(96, 256, 0.0, rng), 96, 256, np.random.default_rng(3))
    assert abs(r["diff"]) < 0.01
    assert not (r["p"] < 0.05 and r["diff"] > mod.DIFF_THRESHOLD)


def test_too_few_bins_yields_nan_rather_than_a_number():
    rng = np.random.default_rng(4)
    r = mod.one_binning(_fake(4, 4, 0.2, rng), 4, 4, np.random.default_rng(5))
    assert np.isnan(r["diff"])


def test_missing_probability_maps_are_refused_not_skipped(tmp_path):
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    msg = str(e.value)
    assert "INK_METRIC_KEEP_PROB" in msg
    assert "refused" in msg


def test_load_prob_returns_None_when_the_patch_was_not_applied(tmp_path):
    """The default scorer writes no *_prob.npy at all; that must read as absent
    rather than raise, so the refusal message above is what the user sees."""
    (tmp_path / "ink_metric_prob" / "predictions").mkdir(parents=True)
    assert mod.load_prob(str(tmp_path), (449, 8982)) is None


def test_load_prob_reads_one_whole_strip_not_tiles(tmp_path):
    """The artifact is a SINGLE (h*10, w*10) array, not one file per mask tile.
    The first version of this function sorted by tile index and crashed on
    `w120-129_flat_flat_prob.npy`; only running it against a real re-score found
    that."""
    d = tmp_path / "ink_metric_prob" / "predictions"
    d.mkdir(parents=True)
    h, w = 8, 12
    full = np.zeros((h * 10, w * 10), dtype=np.float16)
    full[:, : 10 * (w // 2)] = 0.8  # left half high, right half zero
    np.save(d / "w120-129_flat_flat_prob.npy", full)
    got = mod.load_prob(str(tmp_path), (h, w))
    assert got is not None and got.shape == (h, w)
    assert got[:, : w // 2] == pytest.approx(0.8, abs=1e-3)
    assert got[:, w // 2 :] == pytest.approx(0.0, abs=1e-6)


def test_load_prob_rejects_a_shape_that_does_not_match_the_grid(tmp_path):
    d = tmp_path / "ink_metric_prob" / "predictions"
    d.mkdir(parents=True)
    np.save(d / "x_prob.npy", np.zeros((37, 41), dtype=np.float16))
    assert mod.load_prob(str(tmp_path), (449, 8982)) is None
