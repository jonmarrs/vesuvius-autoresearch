"""The finding-115 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0826_winding_count.md").read_text()
RECORD = json.loads(
    (ROOT / "reports/first_letters_0826_winding_count.json").read_text()
)
PREVIOUS = json.loads((ROOT / "reports/first_letters_0826_band_fit.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/eligible_band/band_fit_verdict.py"
    spec = importlib.util.spec_from_file_location(
        "band_fit_verdict_for_0826_count", path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bv = _load()


def _pct(share):
    return f"{100 * share:.1f}%"


def _signed(value):
    return f"{value:.3f}".replace("-", "−")


def test_the_verdict_follows_from_the_registered_table():
    assert len(RECORD["steps"]) == 3
    assert RECORD["p1"] == bv.holds(RECORD["full"], bv.P1) is False
    assert RECORD["p2"] == bv.holds(RECORD["full"], bv.P2) is True
    verdict = bv.verdict(RECORD["steps"], RECORD["smoke"], RECORD["full"])
    assert verdict == RECORD["verdict"] == "PARTLY_ON_SHEETS"
    assert f"**Verdict `{verdict}`**" in REPORT


def test_p3_follows_from_the_registered_line():
    p3 = RECORD["p3"]
    assert p3["line"] == round(p3["baseline_median"] + 0.01, 4) == 0.0925
    assert p3["median"] == RECORD["full"]["excess_median"]
    assert p3["holds"] is (p3["median"] >= p3["line"]) is True
    assert p3["label"] == "HELPS" and "**P3 `HELPS`**" in REPORT
    assert f"P3 holds by {p3['median'] - p3['line']:.3f} over its line" in REPORT


def test_the_score_rows_are_the_records():
    full, smoke = RECORD["full"], RECORD["smoke"]
    positive = _pct(full["share_of_windings_with_positive_excess"])
    row = (
        f"| {full['windings_scored']} | **{full['excess_median']:.3f}** | "
        f"{_signed(full['excess_p10'])} to {full['excess_p90']:.3f} | **{positive}** | "
        f"{full['on_sheet_median']:.3f} |"
    )
    assert row in REPORT, row
    row = (
        f"| {smoke['windings_scored']} | {smoke['excess_median']:.3f} | "
        f"{_signed(smoke['excess_p10'])} to {smoke['excess_p90']:.3f} | "
        f"{_pct(smoke['share_of_windings_with_positive_excess'])} | {smoke['on_sheet_median']:.3f} |"
    )
    assert row in REPORT, row
    base = RECORD["baseline_same_windings_finding_114"]
    row = (
        f"| {base['windings']} | {base['excess_median']:.3f} | {_signed(base['excess_p10'])} to "
        f"{base['excess_p90']:.3f} | {_pct(base['positive'] / base['windings'])} |"
    )
    assert row in REPORT, row
    before = PREVIOUS["full"]
    assert f"| 120 | {before['excess_median']:.3f} |" in REPORT


def test_the_counts_are_the_records():
    full, counts = RECORD["full"], RECORD["this_fit_counts"]
    share = counts["positive"] / full["windings_scored"]
    assert abs(share - full["share_of_windings_with_positive_excess"]) < 1e-4
    assert f"{counts['positive']} of 70 are positive and 56 would be 80%" in REPORT
    assert (
        f"among its {counts['at_least_p1_median']} windings at 0.07 or above" in REPORT
    )
    assert (
        f"{counts['at_least_p1_median']} of the 70 windings score 0.07 or above"
        in REPORT
    )


def test_the_thirds_are_the_records():
    for part in RECORD["full_by_index"]:
        row = f"| w{part['first']:03d} to w{part['last']:03d}"
        assert row in REPORT, row
        row = (
            f"| {_signed(part['excess_median'])} | {_pct(part['positive'])} | "
            f"{part['at_least_p1_median']} of {part['windings']} | "
            f"{part['on_sheet_median']:.3f} | {part['nodes_scored_median']:,} |"
        )
        assert row in REPORT, row
    total = sum(part["at_least_p1_median"] for part in RECORD["full_by_index"])
    assert total == RECORD["this_fit_counts"]["at_least_p1_median"]


def test_the_groups_of_ten_are_the_records():
    here = RECORD["not_registered"]["by_tens"]
    there = RECORD["not_registered"]["finding_114_by_tens"]
    assert len(here) == len(there) == 7
    for a, b, old in zip(
        here, there, PREVIOUS["not_registered"]["by_tens"], strict=False
    ):
        assert (
            (a["first"], a["last"])
            == (b["first"], b["last"])
            == (old["first"], old["last"])
        )
        assert b["excess_median"] == old["excess_median"]
        row = (
            f"| w{a['first']:03d} to w{a['last']:03d} | {_signed(a['excess_median'])} | "
            f"{a['on_sheet_median']:.3f} | {a['below_minus_003']} | {_signed(b['excess_median'])} | "
            f"{b['on_sheet_median']:.3f} | {b['below_minus_003']} |"
        )
        assert row in REPORT, row
    rose = sum(
        a["excess_median"] - b["excess_median"] > 0.005
        for a, b in zip(here, there, strict=True)
    )
    fell = sum(
        b["excess_median"] - a["excess_median"] > 0.005
        for a, b in zip(here, there, strict=True)
    )
    assert (rose, fell) == (4, 2)
    assert sum(part["below_minus_003"] for part in here) == 9
    assert sum(part["below_minus_003"] for part in there) == 10


def test_the_paired_comparison_is_the_records():
    paired = RECORD["not_registered"]["paired"]
    assert (
        f"{paired['higher_in_this_fit']} of the {paired['windings']} score higher"
        in REPORT
    )
    assert f"a median {paired['median_difference']:.3f} higher" in REPORT
    assert f"p = {paired['sign_test_two_sided_p']:.2f}" in REPORT


def test_the_spacing_is_the_records():
    spacing = RECORD["spacing"]
    assert spacing["peak_offset"] == 0 and spacing["sheet_spacing"] == 14.0
    assert f"a median {spacing['winding_spacing_median']:.1f} voxels apart" in REPORT
    assert f"over {spacing['pairs']} pairs" in REPORT
    assert f"The ratio is {spacing['ratio']:.3f}." in REPORT
    assert f"it was {PREVIOUS['spacing']['ratio']:.3f} over all" in REPORT
    share = dict(zip(spacing["offsets_voxels"], spacing["share_inside"], strict=True))
    assert f"peaks at zero displacement ({share[0]:.3f})" in REPORT
    assert f"rises again to {share[-14]:.3f} and {share[14]:.3f} at 14 voxels" in REPORT


def test_the_fit_log_rows_are_the_records():
    now, before = RECORD["fit_log"], PREVIOUS["fit_log"]
    assert (
        f"| total loss at step 29,800 | {now['loss']['29800']} | {before['loss']['29800']} |"
        in REPORT
    )
    for term in ("track_radius", "track_dt", "sym_dirichlet"):
        assert f"| {now['at_29800'][term]} | {before['at_29800'][term]} |" in REPORT
    assert RECORD["costs"]["fit_full"]["seconds"] == 3 * 3600 + 28 * 60 + 6
    assert "| fit, 30,000 steps | 3 h 28 min 6 s | 6.6 GB | 11.9 GB |" in REPORT


def test_the_record_holds_no_winding_and_no_geometry():
    text = json.dumps(RECORD)
    assert '"w0' not in text and '"w1' not in text
    assert "spiral_out/" not in text and ".tif" not in text


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0826_winding_count.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
