"""The finding-114 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0826_band_fit.md").read_text()
RECORD = json.loads((ROOT / "reports/first_letters_0826_band_fit.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/eligible_band/band_fit_verdict.py"
    spec = importlib.util.spec_from_file_location("band_fit_verdict_for_0826", path)
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
    assert RECORD["p2"] == bv.holds(RECORD["full"], bv.P2) is False
    verdict = bv.verdict(RECORD["steps"], RECORD["smoke"], RECORD["full"])
    assert verdict == RECORD["verdict"] == "NOT_ON_SHEETS"
    assert f"**Verdict `{verdict}`**" in REPORT


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
    other = RECORD["reference_pherc0211"]["full"]
    assert f"| 120 | {other['excess_median']:.3f} |" in REPORT


def test_the_thirds_are_the_records():
    for part in RECORD["full_by_index"]:
        row = (
            f"| {_signed(part['excess_median'])} | {_pct(part['positive'])} | "
            f"{part['at_least_p1_median']} of {part['windings']} | "
            f"{part['on_sheet_median']:.3f} | {part['nodes_scored_median']:,} |"
        )
        assert row in REPORT, row
    total = sum(part["at_least_p1_median"] for part in RECORD["full_by_index"])
    assert f"{total} of the 120 windings score 0.07 or above" in REPORT


def test_the_groups_of_ten_are_the_records():
    here = RECORD["not_registered"]["by_tens"]
    there = RECORD["not_registered"]["pherc0211_by_tens"]
    assert len(here) == len(there) == 12
    for a, b in zip(here, there, strict=True):
        assert (a["first"], a["last"]) == (b["first"], b["last"]) and a[
            "windings"
        ] == 10
        row = (
            f"| w{a['first']:03d} to w{a['last']:03d} | {_signed(a['excess_median'])} | "
            f"{a['on_sheet_median']:.3f} | {_signed(b['excess_median'])} | {b['on_sheet_median']:.3f} |"
        )
        assert row in REPORT, row
    assert all(part["on_sheet_median"] < 0.04 for part in here[7:])
    assert all(part["on_sheet_median"] > 0.2 for part in here[:7])


def test_the_spacing_is_the_records():
    spacing = RECORD["spacing"]
    assert spacing["peak_offset"] == 0 and spacing["sheet_spacing"] == 14.0
    assert f"a median {spacing['winding_spacing_median']:.1f} voxels apart" in REPORT
    assert f"over {spacing['pairs']} pairs" in REPORT
    assert f"The ratio is {spacing['ratio']:.3f}." in REPORT
    share = dict(zip(spacing["offsets_voxels"], spacing["share_inside"], strict=True))
    assert f"peaks at zero displacement ({share[0]:.3f})" in REPORT
    assert f"rises again to {share[-14]:.3f} and {share[14]:.3f} at 14 voxels" in REPORT


def test_the_record_holds_no_winding_and_no_geometry():
    text = json.dumps(RECORD)
    assert '"w0' not in text and '"w1' not in text
    assert "spiral_out/" not in text and ".tif" not in text


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0826_band_fit.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
