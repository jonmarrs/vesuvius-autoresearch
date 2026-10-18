"""reports/loader_epoch_boundary_measured_2026-10-18.md quotes its JSONs correctly."""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import epoch_boundary_overhead as ebo  # noqa: E402

REPORT = " ".join(
    (ROOT / "reports/loader_epoch_boundary_measured_2026-10-18.md").read_text().split()
)
BEFORE = json.loads((ROOT / "reports/epoch_boundary_overhead_workers.json").read_text())
AFTER = json.loads(
    (ROOT / "reports/epoch_boundary_overhead_persistent.json").read_text()
)


def slope_se(result):
    xs = [r["boundaries"] for r in result["rows"]]
    mx = statistics.mean(xs)
    return result["fit"]["residual_sd_s"] / math.sqrt(sum((x - mx) ** 2 for x in xs))


def night5(result):
    (g,) = [g for g in result["groups"] if (g["budget"], g["boundaries"]) == (3600, 5)]
    return g


def test_the_after_rows_are_the_fixed_shift():
    assert AFTER["since"] == "2026-10-17T21:17:25"
    assert AFTER["sources"]["run_log"] == ["run.log.old", "run.log"]
    assert all(r["start"] >= AFTER["since"] for r in AFTER["rows"])
    assert {r["shift"] for r in AFTER["rows"]} == {"2026-10-17_19-10-03_night_shift"}
    assert len(AFTER["rows"]) == 10 and {r["budget"] for r in AFTER["rows"]} == {3600}
    assert [r["cycle"] for r in AFTER["rows"] if r["batch_size"] != 8] == [
        "batch_size_16"
    ]
    assert "10 cycles, all 60 minutes, at batch 8 except `batch_size_16`" in REPORT
    assert ebo.fit(AFTER["rows"]) == pytest.approx(AFTER["fit"])
    groups = defaultdict(list)
    for r in AFTER["rows"]:
        groups[(r["budget"], r["boundaries"])].append(r["overhead_s"])
    assert [
        (g["budget"], g["boundaries"], g["n"], g["median_s"], g["min_s"], g["max_s"])
        for g in AFTER["groups"]
    ] == [
        (b, n, len(v), statistics.median(v), min(v), max(v))
        for (b, n), v in sorted(groups.items())
    ]
    for r in AFTER["rows"] + AFTER["control_rows"]:
        assert r["boundaries"] == r["steps"] * r["batch_size"] // ebo.CATALOGUE


def test_the_control():
    c = AFTER["control_rows"]
    assert all(r["start"] < AFTER["since"] for r in c)
    assert [(r["batch_size"], r["boundaries"]) for r in c] == [(8, 5), (8, 5)]
    assert (
        f"{c[0]['overhead_s']} s and {c[1]['overhead_s']} s, both at 5 boundaries"
        in REPORT
    )


def test_the_answer_and_the_table():
    b, a = BEFORE["fit"], AFTER["fit"]
    assert (
        f"{a['per_boundary_s']:.1f} s per boundary (SE {slope_se(AFTER):.1f}), "
        f"against {b['per_boundary_s']:.1f} s (SE {slope_se(BEFORE):.1f}) before"
    ) in REPORT
    for fit, result in ((b, BEFORE), (a, AFTER)):
        assert (
            f"{fit['intercept_s']:.0f} s + {fit['per_boundary_s']:.1f} s per boundary "
            f"(SE {slope_se(result):.1f})"
        ) in REPORT
    assert (
        f"| {b['n']}, {b['residual_sd_s']:.0f} s | {a['n']}, {a['residual_sd_s']:.0f} s |"
        in REPORT
    )
    gb, ga = night5(BEFORE), night5(AFTER)
    for g in (gb, ga):
        assert (
            f"median {g['median_s']:g} s ({g['n']} cycles, {g['min_s']}–{g['max_s']})"
            in REPORT
        )
    assert f"from a median of {gb['median_s']:g} s to {ga['median_s']:g} s" in REPORT


def test_the_killed_config_completed():
    (r,) = [r for r in AFTER["rows"] if r["cycle"] == "use_uamt_False"]
    assert r["result"] == "REVERTED" and r["val_f1"] is not None
    b = BEFORE["fit"]
    predicted = b["intercept_s"] + b["per_boundary_s"] * r["boundaries"]
    assert predicted > BEFORE["timeout_margin_s"]
    assert (
        f"made {r['steps']:,} steps at batch {r['batch_size']}, {r['boundaries']} passes"
        in REPORT
    )
    assert f"The old fit predicts {predicted:.0f} s" in REPORT
    assert f"It took {r['overhead_s']} s and scored val_f1 {r['val_f1']:.4f}" in REPORT
    assert r["val_f1"] == min(x["val_f1"] for x in AFTER["rows"])  # "the lowest"


def test_what_it_does_not_say():
    b = BEFORE["fit"]
    gb, ga = night5(BEFORE), night5(AFTER)
    saved, predicted = gb["median_s"] - ga["median_s"], 5 * b["per_boundary_s"]
    assert (
        f"The saving is {saved:g} s per 60-minute cycle, not the {predicted:.0f} s predicted"
        in REPORT
    )
    before, after = 3600 + gb["median_s"], 3600 + ga["median_s"]
    assert f"takes {after:,} s instead of {before:,} s" in REPORT
    assert f"which is {100 * (before / after - 1):.1f}% more cycles" in REPORT
    passes = (
        int((BEFORE["timeout_margin_s"] - b["intercept_s"]) // b["per_boundary_s"]) + 1
    )
    assert f"any 60-minute cycle of {passes} or more passes past the margin" in REPORT
    assert f"about {b['per_boundary_s']:.0f} s saved per cycle" in REPORT
    assert f"The {ga['median_s']:g} s a cycle is startup" in REPORT


def test_the_first_report_points_here():
    first = " ".join(
        (ROOT / "reports/loader_epoch_boundary_2026-10-17.md").read_text().split()
    )
    assert (
        "Measured on 2026-10-18 (`loader_epoch_boundary_measured_2026-10-18.md`): "
        f"{AFTER['fit']['per_boundary_s']:.1f} s per boundary over the first fixed shift"
    ) in first


def test_the_slope_rests_on_one_cycle():
    """Nine cycles at 5 boundaries and one at 18: the slope is that one against the rest."""
    counts = sorted(r["boundaries"] for r in AFTER["rows"])
    assert counts == [5] * 9 + [18]
    (far,) = [r for r in AFTER["rows"] if r["boundaries"] == 18]
    assert far["cycle"] == "use_uamt_False"
    assert "The slope rests on one cycle." in REPORT
    assert (
        "Nine of the ten cycles crossed 5 boundaries; only `use_uamt_False` crossed more (18)."
        in REPORT
    )
