"""spiralcheck validation rule: tested before spiralcheck ran on any study fit."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_spiralcheck_validation import (  # noqa: E402
    ALPHA,
    ARMS,
    METRICS,
    decide,
    metric_row,
    oneway,
    r_critical,
    within_config_r,
)

TAGS = sorted(ARMS)
GROUPS = [ARMS[t][0] for t in TAGS]


def _data(all_fn, scored_fn, ink_fn=lambda i: 2.9e6 + 1e4 * (i % 3), det=True):
    fits = {}
    for i, t in enumerate(TAGS):
        fits[t] = {
            "deterministic": {"all": det, "scored": True},
            "all": {m: all_fn(i, t, m) for m in METRICS},
            "scored": {m: scored_fn(i, t, m) for m in METRICS},
            "total_fg_pixels": ink_fn(i),
            "satisfied_area_fraction": 0.85,
        }
    return {"fits": fits}


def test_registered_constants():
    assert ALPHA == 0.0125
    assert len(ARMS) == 12
    assert r_critical(8) == pytest.approx(0.750, abs=0.001)


def test_inflated_fraction_is_derived_from_counts():
    row = metric_row(
        {
            "violated_bin_fraction": 0.1,
            "collapsed_bin_fraction": 0.2,
            "n_inflated": 5,
            "n_bins_checked": 50,
            "median_pitch": 18.0,
        }
    )
    assert row["inflated_bin_fraction"] == 0.1


def test_oneway_matches_scipy():
    from scipy import stats

    x = [1.0, 2.0, 3.0, 2.0, 3.0, 4.0, 5.0, 6.0, 5.5, 6.5, 7.0, 5.0]
    g = ["a"] * 3 + ["b"] * 3 + ["c"] * 6
    a = oneway(x, g)
    f, p = stats.f_oneway(x[:3], x[3:6], x[6:])
    assert a["F"] == pytest.approx(f) and a["p"] == pytest.approx(p)
    assert (a["df_between"], a["df_within"]) == (2, 9)


def test_within_config_r_ignores_config_offsets():
    # y = x within configs, but configs are offset in opposite directions
    x = [0, 1, 2, 10, 11, 12, 20, 21, 22, 23, 24, 25]
    g = ["a"] * 3 + ["b"] * 3 + ["c"] * 6
    y = [v - 100 * (i >= 3) + 300 * (i >= 6) for i, v in enumerate(x)]
    c = within_config_r(x, y, g)
    assert c["r"] == pytest.approx(1.0) and c["df"] == 8


def test_partial_sample_is_refused():
    d = _data(lambda i, t, m: i, lambda i, t, m: i)
    del d["fits"][TAGS[0]]
    with pytest.raises(ValueError, match="incomplete"):
        decide(d)


def test_nondeterminism_refuses_every_verdict():
    d = _data(lambda i, t, m: i, lambda i, t, m: i, det=False)
    res = decide(d)
    assert res["verdict"] == "INSTRUMENT NONDETERMINISTIC"
    assert "q2_all" not in res and "q3_scored" not in res


def test_constant_metric_is_uninformative_not_null():
    d = _data(lambda i, t, m: 0.0, lambda i, t, m: 0.0)
    res = decide(d)
    assert all(v["verdict"] == "UNINFORMATIVE" for v in res["q2_all"].values())
    assert all(v["verdict"] == "UNINFORMATIVE" for v in res["q3_scored"].values())
    assert res["verdict"] == "NOT DISCRIMINATING HERE"


def test_config_separation_without_ink_tracking_is_geometry_only():
    offs = {"anchor10cov": 0.0, "nosamecur": 1.0, "curbase": 2.0}
    noise = [0.01, -0.02, 0.01, 0.02, -0.01, -0.01, 0.0, 0.01, -0.01, 0.02, -0.02, 0.0]

    def all_fn(i, t, m):
        return offs[ARMS[t][0]] + noise[i]

    # scored metric: within-config pattern orthogonal to the ink pattern
    def scored_fn(i, t, m):
        return [1, -1, 0][i % 3] * 0.01 + offs[ARMS[t][0]]

    res = decide(
        _data(all_fn, scored_fn, ink_fn=lambda i: 2.9e6 + 1e4 * [1, 1, -2][i % 3])
    )
    assert all(v["verdict"] == "SEPARATES CONFIGS" for v in res["q2_all"].values())
    assert res["verdict"] == "GEOMETRY-ONLY"


def test_within_config_tracking_is_reading_relevant():
    ink = [2.9e6 + 1e4 * ((i * 7) % 5) for i in range(12)]
    res = decide(
        _data(
            lambda i, t, m: 1.0,
            lambda i, t, m: ink[i] / 1e6,
            ink_fn=lambda i: ink[i],
        )
    )
    assert res["q3_scored"]["median_pitch"]["verdict"] == "TRACKS INK (+)"
    assert res["verdict"] == "READING-RELEVANT"
    assert not math.isnan(res["r_critical_df8"])
