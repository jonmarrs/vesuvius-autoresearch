"""Pinned-tier spiralcheck replication: tested before spiralcheck ran on any pinned fit."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_spiralcheck_pinned_replication import ARMS, DF, decide  # noqa: E402
from analyse_spiralcheck_validation import METRICS, r_critical  # noqa: E402

TAGS = sorted(ARMS)


def _data(scored_fn, ink_fn, det=True, match=True):
    return {
        "fits": {
            t: {
                "deterministic": det,
                "meshes_match": match,
                "scored": {m: scored_fn(i, t, m) for m in METRICS},
                "total_fg_pixels": ink_fn(i),
            }
            for i, t in enumerate(TAGS)
        }
    }


def test_registered_design():
    assert len(ARMS) == 24 and len(set(ARMS.values())) == 6
    assert DF == 17
    assert r_critical(DF) == pytest.approx(0.561, abs=0.001)


def test_partial_sample_is_refused():
    d = _data(lambda i, t, m: i, lambda i: 1.6e6 + i)
    del d["fits"][TAGS[0]]
    with pytest.raises(ValueError, match="partial"):
        decide(d)


@pytest.mark.parametrize("det,match", [(False, True), (True, False)])
def test_a_failed_gate_withholds_the_verdict(det, match):
    res = decide(_data(lambda i, t, m: i, lambda i: 1.6e6 + i, det=det, match=match))
    assert res["verdict"] == "INVALID" and "q3_scored" not in res


def test_constant_metrics_are_uninformative():
    res = decide(_data(lambda i, t, m: 0.5, lambda i: 1.6e6 + 1e4 * (i % 5)))
    assert res["verdict"] == "UNINFORMATIVE"


def test_tracking_within_config_is_detected():
    ink = [1.6e6 + 3e4 * ((i * 7) % 11) for i in range(24)]
    res = decide(_data(lambda i, t, m: ink[i] / 1e6, lambda i: ink[i]))
    assert res["verdict"] == "READING-RELEVANT ON PINNED"


def test_unrelated_metrics_are_not_called():
    ink = [1.6e6 + 3e4 * ((i * 7) % 11) for i in range(24)]
    noise = [((i * 5) % 7) / 7 for i in range(24)]
    res = decide(_data(lambda i, t, m: noise[i], lambda i: ink[i]))
    assert res["verdict"] == "NO DETECTED RELATION"
