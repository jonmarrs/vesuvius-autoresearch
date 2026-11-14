"""The finding-112 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_band_fit.md").read_text()
RECORD = json.loads((ROOT / "reports/first_letters_0211_band_fit.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/eligible_band/band_fit_verdict.py"
    spec = importlib.util.spec_from_file_location("band_fit_verdict_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bv = _load()


def _pct(share):
    return f"{100 * share:.1f}%"


def test_the_verdict_follows_from_the_registered_table():
    assert len(RECORD["steps"]) == 3
    assert RECORD["p1"] == bv.holds(RECORD["full"], bv.P1)
    assert RECORD["p2"] == bv.holds(RECORD["full"], bv.P2)
    verdict = bv.verdict(RECORD["steps"], RECORD["smoke"], RECORD["full"])
    assert verdict == RECORD["verdict"]
    assert f"**Verdict `{verdict}`**" in REPORT


def test_the_score_rows_are_the_records():
    full, smoke = RECORD["full"], RECORD["smoke"]
    assert f"| {full['windings_scored']} | **{full['excess_median']:.3f}** |" in REPORT
    positive = _pct(full["share_of_windings_with_positive_excess"])
    assert f"| **{positive}** | {full['on_sheet_median']:.3f} |" in REPORT
    assert f"| {smoke['windings_scored']} | {smoke['excess_median']:.3f} |" in REPORT
    assert _pct(smoke["share_of_windings_with_positive_excess"]) in REPORT
    reference = RECORD["reference_pherc343"]["full"]
    assert f"| {reference['excess_median']:.3f} |" in REPORT
    ratio = full["excess_median"] / reference["excess_median"]
    assert f"The median is\n{100 * ratio:.0f}% of PHerc. 343's." in REPORT


def test_the_thirds_are_the_records():
    assert len(RECORD["full_by_index"]) == 3
    for part in RECORD["full_by_index"]:
        row = (
            f"| {part['excess_median']:.3f} | {_pct(part['positive'])} | "
            f"{part['at_least_p1_median']} of {part['windings']} | "
            f"{part['on_sheet_median']:.3f} | {part['nodes_scored_median']:,} |"
        )
        assert row in REPORT, row
    total = sum(part["at_least_p1_median"] for part in RECORD["full_by_index"])
    assert f"{total} of the 120 windings score 0.07 or above" in REPORT


def test_the_profile_in_the_report_is_the_records_and_peaks_at_zero():
    extra = RECORD["not_registered"]
    offsets = extra["offsets_voxels"]
    shown = [-24, -14, -6, -2, 0, 2, 6, 14, 24]
    for arm, bold in (("full", 0), ("smoke", None)):
        cells = []
        for offset in shown:
            value = f"{extra[arm][offsets.index(offset)]:.3f}"
            cells.append(f"**{value}**" if offset == bold else value)
        assert "| " + " | ".join(cells) + " |" in REPORT, cells
    assert max(extra["full"]) == extra["full"][offsets.index(0)]
    spread = max(extra["smoke"]) - min(extra["smoke"])
    assert f"flat to within {spread:.3f}" in REPORT


def test_the_record_holds_no_winding_and_no_geometry():
    text = json.dumps(RECORD)
    assert '"w0' not in text and '"w1' not in text
    assert "spiral_out/" not in text and ".tif" not in text


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_band_fit.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
