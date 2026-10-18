"""reports/loader_epoch_boundary_2026-10-17.md quotes its three JSONs correctly."""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import epoch_boundary_overhead as ebo  # noqa: E402

REPORT = " ".join(
    (ROOT / "reports/loader_epoch_boundary_2026-10-17.md").read_text().split()
)
WORKERS = json.loads(
    (ROOT / "reports/epoch_boundary_overhead_workers.json").read_text()
)
INLINE = json.loads((ROOT / "reports/epoch_boundary_overhead_inline.json").read_text())
PASSES = json.loads((ROOT / "reports/loader_pass_cost_2026-10-17.json").read_text())


@pytest.mark.parametrize("result", [WORKERS, INLINE], ids=["workers", "inline"])
def test_each_fit_and_its_groups_follow_from_its_rows(result):
    assert ebo.fit(result["rows"]) == pytest.approx(result["fit"])
    groups = defaultdict(list)
    for r in result["rows"]:
        assert r["boundaries"] == r["steps"] * r["batch_size"] // ebo.CATALOGUE
        groups[(r["budget"], r["boundaries"])].append(r["overhead_s"])
    assert [
        (g["budget"], g["boundaries"], g["n"], g["median_s"]) for g in result["groups"]
    ] == [(b, n, len(v), statistics.median(v)) for (b, n), v in sorted(groups.items())]


def test_the_sources():
    assert (
        WORKERS["sources"]["sprint_logs"] == "sprint_logs/sprint_log_2026-10-1[67]_*.md"
    )
    assert (
        INLINE["sources"]["sprint_logs"] == "sprint_logs/sprint_log_2026-10-1[345]_*.md"
    )


def test_the_fits_are_quoted():
    w, i = WORKERS["fit"], INLINE["fit"]
    assert (
        f"overhead = {w['intercept_s']:.0f} s + {w['per_boundary_s']:.1f} s per boundary "
        f"over {w['n']} cycles (residual SD {w['residual_sd_s']:.0f} s)"
    ) in REPORT
    assert (
        f"{i['per_boundary_s']:.1f} s per boundary over {i['n']} cycles "
        f"(intercept {i['intercept_s']:.0f} s)"
    ) in REPORT


def test_the_group_table():
    for g in WORKERS["groups"]:
        row = f"| {g['budget']} | {g['boundaries']} | {g['n']} | {g['median_s']:g} | {g['min_s']}–{g['max_s']} |"
        assert row in REPORT, row


def test_five_pass_night_cycles_before_and_after_the_workers():
    def night5(result):
        (g,) = [
            g for g in result["groups"] if g["budget"] == 3600 and g["boundaries"] == 5
        ]
        return g["median_s"]

    assert (
        f"{night5(INLINE):g} s with the loader in-process, {night5(WORKERS):g} s with"
        in REPORT
    )
    assert (
        f"about {5 * WORKERS['fit']['per_boundary_s']:.0f} s of each 60-minute cycle"
        in REPORT
    )


def test_the_margin_allows_about_ten_passes():
    f = WORKERS["fit"]
    assert (
        int((WORKERS["timeout_margin_s"] - f["intercept_s"]) // f["per_boundary_s"])
        == 10
    )
    assert "the timeout's margin allows about 10" in REPORT
    assert (
        f"about {f['per_boundary_s']:.0f} s of most 15-minute ones (1 boundary)"
        in REPORT
    )
    day = [g for g in WORKERS["groups"] if g["budget"] == 900]
    assert max(day, key=lambda g: g["n"])["boundaries"] == 1  # "most"


def test_the_killed_cycle():
    (k,) = WORKERS["killed"]
    night = [
        r["steps"]
        for r in WORKERS["rows"]
        if r["budget"] == 3600 and r["batch_size"] == 4
    ]
    assert (
        f"against a median of {statistics.median(night):,} for the other 60-minute cycles at batch 4"
        in REPORT
    )
    assert (k["cycle"], k["budget"], k["remaining_s"]) == ("use_uamt_False", 3600, 89)
    assert f"{k['steps']:,} steps" in REPORT and f"{k['boundaries']} passes" in REPORT
    assert f"predicts {k['predicted_overhead_s']:.0f} s of overhead" in REPORT
    assert k["predicted_overhead_s"] > WORKERS["timeout_margin_s"] == 300
    assert f"with {k['remaining_s']} s of its budget left" in REPORT


def test_the_pass_costs():
    old, new = PASSES["loaders"]["respawned"], PASSES["loaders"]["persistent"]
    assert PASSES["workers"] == 3 and len(old) == len(new) == 3
    assert f"{PASSES['dataset_pickle_bytes']:,} B" in REPORT
    lo, hi = min(p["iter_s"] for p in old), max(p["iter_s"] for p in old)
    assert f"respawned: {lo:.1f}–{hi:.1f} s in iter() on every pass" in REPORT
    later = max(p["iter_s"] + p["first_batch_s"] for p in new[1:])
    assert later < 0.05
    assert (
        f"persistent: {new[0]['iter_s']:.1f} s on the first pass, {later:.2f} s on each after"
        in REPORT
    )
