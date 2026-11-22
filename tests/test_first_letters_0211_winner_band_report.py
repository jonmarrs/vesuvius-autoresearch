"""The finding-119 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_winner_band.md").read_text()
FLAT = REPORT.replace("\n", " ")
RECORD = json.loads((ROOT / "reports/first_letters_0211_winner_band.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/winner_sheet.py"
    spec = importlib.util.spec_from_file_location("winner_sheet_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ws = _load()


def _pct(share: float) -> str:
    """A recorded share as the report prints it: a percentage to one place, halves rounded up (0.5515 is 55.2%)."""
    from decimal import ROUND_HALF_UP, Decimal

    return f"{(Decimal(str(share)) * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def _n(value) -> str:
    """A number as the report prints it: a minus sign, not a hyphen."""
    return f"{value:+.2f}".replace("-", "−")


def _clock(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h} h {m} min {s} s" if h else f"{m} min {s} s"


def test_every_step_exited_zero():
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    assert RECORD["steps"]["fit_full"]["steps"] == 30000
    assert RECORD["band"] == [ws.Z_BEGIN, ws.Z_END] == [7650, 9150]


def test_the_verdict_follows_from_the_registered_table():
    snapped = RECORD["registered"]["snapped_chosen"]
    assert (
        ws.verdict(snapped)
        == RECORD["verdict"]
        == RECORD["predicted"]
        == "PARTLY_ON_IT"
    )
    lines = RECORD["registered"]["lines"]
    assert (
        lines["on_share_within_2"],
        lines["on_median"],
        lines["partly_share_within_2"],
    ) == (
        ws.ON_SHARE,
        ws.ON_MEDIAN,
        ws.PARTLY_SHARE,
    )
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT


def test_the_registered_numbers_in_the_report_are_the_records():
    s = RECORD["registered"]["snapped_chosen"]
    within = s["fraction_within"]
    assert f"| **{_pct(within['2'])}** |" in REPORT
    assert f"| {s['median']} voxels |" in REPORT
    assert (
        f"| {_pct(within['1'])}, {_pct(within['3'])}, {_pct(within['5'])} |" in REPORT
    )
    q = s["quantiles"]
    assert f"| {q['p5']} to {q['p95']} voxels |" in REPORT
    assert f"{RECORD['winner_nodes_in_band']:,} of {RECORD['winner_nodes']:,}" in REPORT
    assert f"| {RECORD['raw_windings']} |" in REPORT
    assert f"{RECORD['chosen']}, covering {_pct(s['covered_fraction'])}" in REPORT
    assert RECORD["snap_list"] == ["w034", "w035", "w036"]


def test_the_described_numbers_in_the_report_are_the_records():
    d = RECORD["described"]
    for row in d["three_closest_raw"]:
        assert (
            f"{_pct(row['fraction_within']['2'])} | {row['median']} | {_n(row['signed_median'])} |"
            in REPORT
        ), row["winding"]
    near = d["near_any_raw_winding"]
    assert f"{_pct(near['within_2_of_any_winding'])} of the winner's nodes" in FLAT
    assert f"and {_pct(near['within_4_of_any_winding'])} within 4" in FLAT
    for name, s in d["snapped_neighbours"].items():
        assert f"{_pct(s['fraction_within']['2'])} within 2 voxels" in FLAT or (
            f"{_pct(s['fraction_within']['2'])} (median {s['median']})" in FLAT
        ), name
    tiles = d["tiles_of_chosen_raw_winding"]
    assert tiles["auc_reported"] is False and tiles["wrong"] < 15
    assert f"{tiles['tiles']} tiles, of which {tiles['right']}" in FLAT
    assert f"and {tiles['wrong']} do not" in FLAT
    assert (
        f"median excess of {d['sheet_following_score_full_fit']['excess_median']}"
        in FLAT
    )


def test_the_unregistered_numbers_in_the_report_are_the_records():
    nr = RECORD["not_registered"]
    parts = nr["scores_by_part_of_the_winner_surface"]
    for key, label in (
        ("snapped w035 cols 0-181", "| columns 0 to 181 | snapped w035 |"),
        ("raw w035 cols 0-181", "| columns 0 to 181 | raw w035 |"),
        ("raw w033 cols 193-300", "| columns 193 to 300 | raw w033 |"),
        ("raw w035 cols 193-300", "| columns 193 to 300 | raw w035 |"),
    ):
        p = parts[key]
        assert f"{label} {_pct(p['within_2'])} | {p['median']} |" in REPORT, key
    # each part meets finding 110's P1 on its own winding
    for key in ("snapped w035 cols 0-181", "raw w033 cols 193-300"):
        assert (
            parts[key]["within_2"] >= ws.ON_SHARE
            and parts[key]["median"] <= ws.ON_MEDIAN
        )
    shares = nr["share_of_winner_nodes_within_2_by_nearest_winding"]
    for name in ("w035", "w033", "w036", "w034"):
        assert f"{_pct(shares[name])} on {name}" in FLAT
    lengths = nr["lengths_along_middle_row_voxels"]
    assert f"{lengths['winner']:,.0f} voxels long" in FLAT
    assert f"one turn of w035 in the band is {lengths['w035']:,.0f} voxels" in FLAT
    ink = nr["winner_ink_share_by_part"]
    assert f"{_pct(ink['columns_0_181'])} in columns 0 to 181" in FLAT
    assert f"{_pct(ink['columns_182_300'])} in columns 182 to 300" in FLAT


def test_the_column_runs_in_the_report_are_the_records():
    runs = [
        (r["winding"], r["from_column"], r["to_column"])
        for r in RECORD["not_registered"]["nearest_raw_winding_by_winner_column"]
    ]
    assert runs[0] == ("w035", 0, 93) and runs[-2] == ("w034", 299, 299)
    single = {r[1]: r[0] for r in runs if r[1] == r[2] and r[1] <= 158}
    assert single == {94: "w034", 123: "w036"}
    assert "except column 94 (w034) and column 123 (w036)" in REPORT
    assert all(w == "w033" for w, a, b in runs if a >= 193 and b != 299)
    assert {w for w, a, b in runs if 159 <= a <= 192} == {
        "w033",
        "w034",
        "w035",
        "w036",
    }


def test_the_neighbourhood_snap_table_is_the_records():
    snap = RECORD["not_registered"]["snap_of_w028_to_w042"]
    on = {n: v["share_already_within_2_of_a_sheet"] for n, v in snap.items()}
    move = {n: v["median_abs_offset"] for n, v in snap.items()}
    block = [f"w{i:03d}" for i in range(29, 34)]
    assert (
        f"| {100 * min(on[n] for n in block):.0f}% to {100 * max(on[n] for n in block):.0f}% |"
        in REPORT
    )
    assert (
        f"{min(move[n] for n in block):.2f} to {max(move[n] for n in block):.2f}"
        in REPORT
    )
    for n in ("w034", "w035", "w036", "w037"):
        assert f"| {_pct(on[n])} |" in REPORT, n
    # the registered snap's rows are the same windings' rows of this table
    assert RECORD["described"]["snap_report"] == {
        n: snap[n] for n in ("w034", "w035", "w036")
    }


def test_the_costs_in_the_report_are_the_records():
    steps = RECORD["steps"]
    assert (
        f"| full fit, 30,000 steps | {_clock(steps['fit_full']['seconds'])} |" in REPORT
    )
    assert (
        f"| distance field | {_clock(steps['distance_field']['seconds'])} |" in REPORT
    )
    assert (
        f"| smoke fit, 300 steps | {_clock(steps['fit_smoke']['seconds'])} |" in REPORT
    )
    assert (
        f"{steps['fit_full']['gpu_peak_mib_all_processes'] / 1000:.1f} GB of GPU memory"
        in REPORT
    )
    assert (
        f"{_clock(steps['quality']['seconds'])}, {_clock(steps['choose']['seconds'])}, {steps['snap']['seconds']} s"
        in REPORT
    )


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_winner_band.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
