"""The finding-116 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0826_wrong_hand_control.md").read_text()
RECORD = json.loads(
    (ROOT / "reports/first_letters_0826_wrong_hand_control.json").read_text()
)
RIGHT = json.loads((ROOT / "reports/first_letters_0826_winding_count.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()
FLAT = " ".join(REPORT.split())  # prose, with line breaks folded


def _load():
    path = ROOT / "repro/first_letters/eligible_band/band_fit_verdict.py"
    spec = importlib.util.spec_from_file_location(
        "band_fit_verdict_for_0826_hand", path
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


def registered_verdict(record):
    if any(step["exit"] != 0 for step in record["steps"].values()):
        return "DOES_NOT_RUN"
    if record["full"]["windings_scored"] < 60:
        return "DOES_NOT_RUN"
    median = record["full"]["excess_median"]
    if median <= record["lines"]["separates_at_most"]:
        return "SCORE_SEPARATES"
    if median < record["lines"]["blind_at_least"]:
        return "SCORE_PARTLY_SEPARATES"
    return "SCORE_BLIND_TO_DIRECTION"


def test_the_verdict_follows_from_the_registered_table():
    assert len(RECORD["steps"]) == 3
    assert RECORD["lines"] == {"separates_at_most": 0.03, "blind_at_least": 0.07}
    verdict = registered_verdict(RECORD)
    assert verdict == RECORD["verdict"] == "SCORE_BLIND_TO_DIRECTION"
    assert f"**Verdict `{verdict}`**" in REPORT
    assert (RECORD["published_sense"], RECORD["declared_sense"]) == ("ACW", "CW")


def test_the_table_of_finding_112_would_have_passed_the_wrong_direction():
    earned = bv.verdict(RECORD["steps"], RECORD["smoke"], RECORD["full"])
    assert earned == RECORD["what_the_fit_would_have_earned"] == "ON_SHEETS"
    assert RIGHT["verdict"] == "PARTLY_ON_SHEETS"
    assert "would have earned `ON_SHEETS`" in FLAT


def test_the_score_rows_are_the_records():
    for fit, bold in (
        (RECORD["full"], True),
        (RIGHT["full"], False),
        (RECORD["smoke"], False),
    ):
        median = _signed(fit["excess_median"])
        positive = _pct(fit["share_of_windings_with_positive_excess"])
        if bold:
            median, positive = f"**{median}**", f"**{positive}**"
        row = (
            f"| {fit['windings_scored']} | {median} | {_signed(fit['excess_p10'])} to "
            f"{fit['excess_p90']:.3f} | {positive} | {fit['on_sheet_median']:.3f} |"
        )
        assert row in REPORT, row


def test_the_counts_are_the_records():
    counts, right = RECORD["counts"], RIGHT["this_fit_counts"]
    assert (
        counts["positive"] / 70
        == RECORD["full"]["share_of_windings_with_positive_excess"]
    )
    assert (
        f"{counts['positive']} of its 70 windings are positive against {right['positive']}"
        in FLAT
    )
    assert (
        f"{counts['at_least_p1_median']} of its windings score 0.07 or above, "
        f"against {right['at_least_p1_median']}" in FLAT
    )


def test_the_thirds_are_the_records():
    for part in RECORD["full_by_index"]:
        row = (
            f"| {_signed(part['excess_median'])} | {_pct(part['positive'])} | "
            f"{part['at_least_p1_median']} of {part['windings']} | "
            f"{part['on_sheet_median']:.3f} | {part['nodes_scored_median']:,} |"
        )
        assert row in REPORT, row


def test_the_groups_of_ten_are_the_records_and_finding_115s():
    here = RECORD["not_registered"]["by_tens"]
    there = RECORD["not_registered"]["finding_115_by_tens"]
    assert [(a["first"], a["excess_median"]) for a in there] == [
        (b["first"], b["excess_median"]) for b in RIGHT["not_registered"]["by_tens"]
    ]
    for a, b in zip(here, there, strict=True):
        row = (
            f"| w{a['first']:03d} to w{a['last']:03d} | {_signed(a['excess_median'])} | "
            f"{a['on_sheet_median']:.3f} | {_signed(b['excess_median'])} | {b['on_sheet_median']:.3f} |"
        )
        assert row in REPORT, row
    higher = RECORD["not_registered"]["paired"]["right_direction_higher"]
    assert (
        f"The published direction scores higher on {higher} of the 70 windings" in FLAT
    )


def test_the_turn_check_shows_opposite_senses():
    swept = RECORD["not_registered"]["turn_check"]["angle_swept_rad"]
    assert all(a < -6 for a in swept["published_direction"])
    assert all(a > 6 for a in swept["reversed"])
    low, high = max(swept["published_direction"]), min(swept["published_direction"])
    assert f"is −{-low:.2f} to −{-high:.2f} radians" in FLAT
    assert (
        f"+{min(swept['reversed']):.2f} to +{max(swept['reversed']):.2f} in this one"
        in FLAT
    )


def test_the_fit_log_rows_are_the_records_and_the_loss_prediction_held():
    now, right = RECORD["fit_log"], RIGHT["fit_log"]
    assert (
        f"| total loss at step 29,800 | {now['loss']['29800']} | {right['loss']['29800']} |"
        in REPORT
    )
    for term in ("track_radius", "track_dt", "sym_dirichlet"):
        assert f"| {now['at_29800'][term]} | {right['at_29800'][term]} |" in REPORT
    rise = now["at_29800"]["track_radius"] / right["at_29800"]["track_radius"] - 1
    assert 0 < rise < 0.25
    assert f"It is {100 * rise:.1f}% higher" in FLAT


def test_the_spacing_and_costs_are_the_records():
    spacing = RECORD["spacing"]
    assert (
        f"a median {spacing['winding_spacing_median']:.1f} voxels apart over {spacing['pairs']} pairs"
        in FLAT
    )
    assert (
        f"ratio {spacing['ratio']:.3f} (finding 115: {RIGHT['spacing']['ratio']:.3f})"
        in FLAT
    )
    assert RECORD["costs"]["fit_full"]["seconds"] == 3 * 3600 + 21 * 60 + 44
    assert "| fit, 30,000 steps | 3 h 21 min 44 s | 6.6 GB | 13.8 GB |" in REPORT


def test_the_record_holds_no_winding_and_no_geometry():
    text = json.dumps(RECORD)
    assert '"w0' not in text and '"w1' not in text
    assert "spiral_out/" not in text and ".tif" not in text


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0826_wrong_hand_control.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
