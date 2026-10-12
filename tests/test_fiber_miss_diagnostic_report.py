"""Finding 84's report states what the registered analysis wrote: hold its numbers to reports/fiber_miss_diagnostic.json."""

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_JSON = _REPO / "reports/fiber_miss_diagnostic.json"
_MD = _REPO / "reports/fiber_miss_diagnostic.md"
pytestmark = pytest.mark.skipif(
    not (_JSON.exists() and _MD.exists()), reason="finding 84 artifacts absent"
)
NEW = ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")


def _text() -> str:
    return " ".join(_MD.read_text().split())


def test_verdict_and_predictions():
    d = json.loads(_JSON.read_text())
    v = d["verdict"]
    assert v["status"] == "OK" and v["conclusion"] == "SOFTER_BUT_NOT_RESCUED"
    assert v["predictions"] == {
        "P2_threshold_0.1_does_not_rescue": True,
        "P3_misses_no_softer_than_in_sample": False,
    }
    assert not any(v["frame_offset_flag"].values())
    t = _text()
    assert (
        "Verdict: `SOFTER_BUT_NOT_RESCUED`" in t and "P2 HELD" in t and "P3 FAILED" in t
    )
    assert f"in-sample Scroll-5 maximum of {v['in_sample_s5_max_soft_miss']:.3f}" in t


def test_every_cube_passed_both_gates_and_the_control():
    c = json.loads(_JSON.read_text())["cubes"]
    assert len(c) == 21
    for k, r in c.items():
        assert r["g1_prob_threshold_equals_shipped_mask"], k
        assert abs(r["g2_zero_shift_coverage"] - r["published_cc_coverage"]) <= 1e-4, k
    gains = [r["shift"]["gain"] for r in c.values() if r["split"] != "held_out"]
    assert max(gains) < 0.05 and f"{max(gains):.4f}" in _text()


def test_the_new_cubes_numbers():
    c, t = json.loads(_JSON.read_text())["cubes"], _text()
    a, b = (c[k] for k in NEW)
    assert f"gains {a['shift']['gain']:.4f} and {b['shift']['gain']:.4f}" in t
    assert (
        f"coverage is {a['sweep']['coverage']['0.1']:.3f} and {b['sweep']['coverage']['0.1']:.3f}"
        in t
    )
    hard = [100 * (1 - r["sweep"]["coverage"]["0.05"]) for r in (a, b)]
    assert f"{hard[0]:.1f}% and {hard[1]:.1f}% of their annotated fiber" in t


def test_group_ranges():
    c, t = json.loads(_JSON.read_text())["cubes"], _text()

    def rng(keys, f, fmt):
        vals = [f(c[k]) for k in keys]
        return f"{fmt(min(vals))}–{fmt(max(vals))}"

    s3 = [k for k in c if k.startswith("s3_")]
    ins = [k for k, r in c.items() if r["split"] != "held_out"]
    soft = lambda r: r["sweep"]["soft_miss_fraction"]  # noqa: E731
    hard = lambda r: 100 * (1 - r["sweep"]["coverage"]["0.05"])  # noqa: E731
    assert f"soft-miss fraction {rng(s3, soft, lambda x: f'{x:.3f}')}" in t
    assert f"{rng(ins, soft, lambda x: f'{x:.3f}')} in sample" in t
    assert f"{rng(s3, hard, lambda x: f'{x:.1f}')}% on Scroll 3" in t
    assert f"{rng(ins, hard, lambda x: f'{x:.1f}')}% in sample" in t
