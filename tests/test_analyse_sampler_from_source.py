"""Sampler-from-source rule: tested before any arm was rendered."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_sampler_from_source import SAMPLER_SHA, decide  # noqa: E402

REF = 3_279_498.0
MD5 = "flat0"


def _arms(pub, a, b, **over):
    arms = {
        "smp_pub": {
            "ink": pub,
            "sampler": "published",
            "flat_md5": MD5,
            "reuse_engaged": True,
        },
        "smp_src_a": {
            "ink": a,
            "sampler": SAMPLER_SHA,
            "flat_md5": MD5,
            "reuse_engaged": True,
        },
        "smp_src_b": {
            "ink": b,
            "sampler": SAMPLER_SHA,
            "flat_md5": MD5,
            "reuse_engaged": True,
        },
    }
    for k, kw in over.items():
        arms[k] = {**arms[k], **kw}
    return arms


def test_partial_sample_is_refused():
    arms = _arms(REF, REF, REF)
    del arms["smp_src_b"]
    with pytest.raises(ValueError, match="partial"):
        decide(arms, REF, MD5)


@pytest.mark.parametrize(
    "over",
    [
        {"smp_src_a": {"reuse_engaged": False}},  # re-flattened: variance back in
        {"smp_pub": {"flat_md5": "other"}},  # a different surface
        {"smp_src_b": {"sampler": "published"}},  # the wrong binary
        {"smp_pub": {"sampler": SAMPLER_SHA}},
    ],
)
def test_gates_withhold_the_verdict(over):
    res = decide(_arms(REF, REF * 1.1, REF * 1.1, **over), REF, MD5)
    assert res["verdict"] == "INVALID" and "effect" not in res


def test_a_non_reproducing_reuse_path_is_invalid():
    res = decide(_arms(REF * 1.001, REF * 1.1, REF * 1.1), REF, MD5)
    assert res["verdict"] == "INVALID" and "effect" not in res


def test_identical_is_inert():
    res = decide(_arms(REF, REF, REF), REF, MD5)
    assert res["verdict"] == "SAMPLER INERT (within 0.5%)"


def test_a_change_is_called():
    res = decide(_arms(REF, REF * 0.97, REF * 0.97), REF, MD5)
    assert res["verdict"] == "SAMPLER CHANGES INK"
    assert res["effect"] == pytest.approx(-0.03)


def test_a_stochastic_source_sampler_needs_three_times_its_spread():
    res = decide(_arms(REF, REF * 1.02, REF * 1.04), REF, MD5)
    assert res["verdict"] == "NOT RESOLVED (source sampler nondeterministic)"
