"""Render-path rule: tested before any arm was rendered."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_upstream_render_path import ARMS, PIN, REF, UP, decide  # noqa: E402

BASE = 3_279_498.0


def _arms(up_a, up_b, pin_a, ref=BASE, **over):
    ink = {"rpath_up_a": up_a, "rpath_up_b": up_b, "rpath_pin_a": pin_a, REF: ref}
    arms = {
        a: {
            "ink": ink[a],
            "villa_sha": sha,
            "image_id": "img",
            "flatten_deterministic": "1",
        }
        for a, sha in ARMS.items()
    }
    for a, kw in over.items():
        arms[a] = {**arms[a], **kw}
    return arms


def test_partial_sample_is_refused():
    arms = _arms(BASE, BASE, BASE)
    del arms["rpath_up_b"]
    with pytest.raises(ValueError, match="partial"):
        decide(arms)


@pytest.mark.parametrize(
    "over",
    [
        {"rpath_up_a": {"villa_sha": PIN}},  # upstream arm built from the pin
        {"rpath_pin_a": {"villa_sha": UP}},
        {"rpath_up_b": {"image_id": "other"}},
        {"rpath_up_a": {"flatten_deterministic": "0"}},
    ],
)
def test_provenance_gates(over):
    res = decide(_arms(BASE * 1.1, BASE * 1.1, BASE, **over))
    assert res["verdict"] == "INVALID" and "effect" not in res


def test_environment_drift_withholds_the_comparison():
    res = decide(_arms(BASE * 1.1, BASE * 1.1, BASE * 1.002))
    assert res["verdict"] == "INVALID" and "effect" not in res


def test_identical_output_is_inert():
    res = decide(_arms(BASE, BASE, BASE))
    assert res["verdict"] == "RENDER PATH INERT (within 0.5%)" and res["effect"] == 0


def test_a_deterministic_change_is_called():
    res = decide(_arms(BASE * 1.03, BASE * 1.03, BASE))
    assert res["verdict"] == "RENDER PATH CHANGES INK"
    assert res["effect"] == pytest.approx(0.03)


def test_a_stochastic_stage_needs_three_times_its_spread():
    # repeats differ by 2%: a 3% effect is inside 3x that and is not resolved
    res = decide(_arms(BASE * 1.02, BASE * 1.04, BASE))
    assert res["upstream_deterministic"] is False
    assert res["verdict"] == "NOT RESOLVED (upstream stage nondeterministic)"
    res = decide(_arms(BASE * 1.20, BASE * 1.21, BASE))
    assert res["verdict"].startswith("RENDER PATH CHANGES INK")
