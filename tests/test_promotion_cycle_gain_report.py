"""reports/promotion_cycle_gain_2026-10-17.md quotes its JSON and the pooled probe correctly."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import promotion_cycle_gain as pcg  # noqa: E402

REPORT = " ".join(
    (ROOT / "reports/promotion_cycle_gain_2026-10-17.md").read_text().split()
)
RESULT = json.loads((ROOT / "reports/promotion_cycle_gain_2026-10-17.json").read_text())
PROBE = json.loads((ROOT / "reports/noise_probe_v3_pooled_2026-10-17.json").read_text())
BEFORE, AFTER = RESULT["segments"]
ROWS = RESULT["rows"]


def _rows(segment, minutes=None):
    return [
        r
        for r in ROWS
        if r["incumbent"] == segment["incumbent"]
        and r["gain"] is not None
        and minutes in (None, r["minutes"])
    ]


def test_the_segments_follow_from_the_rows():
    assert (
        RESULT["source"] == "autoresearch.out" and RESULT["first_incumbent"] == 0.249348
    )
    assert pcg.segments(ROWS) == RESULT["segments"]
    assert len(RESULT["segments"]) == 2
    assert [r["outcome"] for r in ROWS].count("promoted") == 1


def test_the_table():
    for label, seg in (("0.2493", BEFORE), ("0.2658", AFTER)):
        row = (
            f"| {label} | {seg['scored']} | {seg['mean_gain']:+.4f} | {seg['sd_gain']:.4f} | "
            f"{seg['min_gain']:+.4f} to {seg['max_gain']:+.4f} | {seg['clear']['0.01']} |"
        )
        assert row in REPORT, row


def test_before_the_promotion():
    assert BEFORE["crashed"] == 1 and BEFORE["promoted"] == 1
    (under,) = [r for r in _rows(BEFORE) if r["gain"] <= 0.01]
    assert f"`{under['cycle']}` ({under['gain']:+.4f})" in REPORT
    for minutes, label in ((15, "15-minute"), (60, "60-minute")):
        g = [r["gain"] for r in _rows(BEFORE, minutes)]
        assert (
            f"{label} cycles gained {statistics.mean(g):+.4f} (n = {len(g)})" in REPORT
        )


def test_after_the_promotion():
    assert AFTER["promoted"] == AFTER["clear"]["0.01"] == AFTER["crashed"] == 0
    assert {r["minutes"] for r in _rows(AFTER)} == {15}
    best = max(_rows(AFTER), key=lambda r: r["gain"])
    assert f"the best is `{best['cycle']}` at {best['gain']:+.4f}" in REPORT
    assert f"through `{ROWS[-1]['cycle']}`" in REPORT
    promoted = next(r for r in ROWS if r["outcome"] == "promoted")
    assert f"`{promoted['cycle']}` ({promoted['val_f1']:.4f})" in REPORT


def test_the_spread_against_the_probe():
    lead = PROBE["lead"]
    lo, hi = lead["interval"]
    assert lo < AFTER["sd_gain"] < hi
    assert (
        f"SD {AFTER['sd_gain']:.4f} lies inside the interval for identical cycles, "
        f"{lead['sd']:.4f} ({lo:.4f}–{hi:.4f})"
    ) in REPORT
    after_mean = statistics.mean(r["val_f1"] for r in _rows(AFTER))
    assert f"their mean val_f1, {after_mean:.4f}" in REPORT
    assert f"the probe's mean, {PROBE['pooled']['mean']:.4f}" in REPORT
    assert after_mean == pytest.approx(PROBE["pooled"]["mean"], abs=PROBE["lead"]["sd"])
