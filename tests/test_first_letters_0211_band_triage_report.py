"""Finding 138's report states its record's numbers, the checks after the result are the audit script's, and the
audit script reproduces a ranking it can be checked against."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_band_triage.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0211_band_triage.json").read_text())
REG = " ".join((ROOT / RECORD["registration"]).read_text().split())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
_spec = importlib.util.spec_from_file_location(
    "band_triage_audit",
    ROOT / "repro/first_letters/pherc0211_control/band_triage_audit.py",
)
assert _spec and _spec.loader
audit_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit_mod)


def _hms(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h} h {m} min {s} s" if h else f"{m} min {s} s"


def test_the_verdict_follows_the_registered_rule():
    reg = RECORD["registered"]
    assert RECORD["finding"] == 138 and RECORD["registration_commit"] == "26d5c8a5"
    assert RECORD["verdict"] == "TRIAGE_FINDS_THE_TEXT"
    assert reg["best_place_rank"] <= reg["lines"]["first"] == 10
    assert reg["lines"]["high"] == max(10, -(-5 * reg["windows"] // 100))
    assert reg["place_windows"] == reg["place_windows_scored"] == 11
    assert (
        "| `TRIAGE_FINDS_THE_TEXT` | ranks among the band's first 10 windows |" in REG
    )
    assert "**Verdict: `TRIAGE_FINDS_THE_TEXT`.**" in REPORT
    assert f"ranks 2nd of the band's {reg['windows']} scored windows" in FLAT
    assert f"| **its rank** | **{reg['best_place_rank']}** |" in REPORT
    assert all(g["exit"] == 0 for g in RECORD["steps"].values())
    for step in ("flatten", "render", "studio"):
        assert (
            RECORD["read"][step]["attempted"]
            == RECORD["read"][step]["exited_zero"]
            == 80
        )


def test_the_place_windows_and_the_first_ten_are_the_records():
    d = RECORD["described"]
    for p in d["place_windows"]:
        assert (
            f"| {p['winding']}, x0 {p['x0']} | {p['glyph']} | {p['rank']} | {p['rows']} |"
            in REPORT
        ), p
    top = d["top"][:10]
    assert top[1]["winding"] == "w033" and top[1]["x0"] == 2000
    assert f"{top[0]['winding']} at x0 {top[0]['x0']} ({top[0]['glyph']})" in FLAT
    assert f"{top[-1]['winding']} at {top[-1]['x0']} ({top[-1]['glyph']})" in FLAT
    q = d["glyph_quantiles"]
    assert (
        f"median {q['p50']}, 90th percentile {q['p90']}, 99th {q['p99']}, the largest {q['max']}"
        in FLAT
    )
    assert (
        f"{d['share_of_windows_above_their_p99']} of the windows score above the team's admission line"
        in FLAT
    )
    place = RECORD["place"]
    assert (
        f"reach {place['place_cells']:,} of the winner's {place['mask_cells']:,} mask cells ({place['place_share_of_mask']})"
        in FLAT
    )
    best = RECORD["audit_after_the_result"]["best_place_window"]
    assert (
        best["place_cells"]
        == place["by_winding"]["w033"]["by_window"][-1]["place_cells"]
    )
    assert f"holding {best['place_cells']:,} cells" in FLAT


def test_the_predictions_are_scored_as_registered():
    p = RECORD["predictions"]
    assert not p["1_verdict"]["held"] and not p["2_best_place_window_on_w035"]["held"]
    assert p["3_rows_rank_the_place_lower"]["held"]
    assert (
        p["3_rows_rank_the_place_lower"]["rows_rank"]
        == RECORD["described"]["best_place_rank_by_rows"]
        == 4
    )
    assert (
        f"w035's best window ranks {p['2_best_place_window_on_w035']['w035_best_rank']}th"
        in FLAT
    )
    assert (
        "1. `TRIAGE_RANKS_THE_TEXT_HIGH`, low confidence. `TRIAGE_FINDS_THE_TEXT` is nearly as likely."
        in REG
    )
    assert "2. The best place window is on w035, moderate confidence" in REG


def test_the_checks_after_the_result_are_the_audits():
    a = RECORD["audit_after_the_result"]
    assert a["registered"] is False
    e = a["end_windows"]
    assert f"They are {e['all']} of the 467 windows ({e['share']})" in FLAT
    assert (
        f"but {e['in_first']['10']} of the first 10, {e['in_first']['20']} of the first 20 and {e['in_first']['50']} of the first 50"
        in FLAT
    )
    assert f"({e['glyph_median']} against {e['others_glyph_median']})" in FLAT
    g = a["grid_only"]
    assert (
        f"ranking only the grid's {g['windows']} windows" in FLAT
        and f"the best place window ranks {g['best_place_rank']}th" in FLAT
    )
    b = a["best_place_window"]
    assert b["end_window"] and a["first_rank"]["end_window"]
    assert (
        f"scores {b['below_first_rank']} below the first rank, {b['above_next_rank']} above the next and "
        f"{b['above_rank_10']} above the 10th" in FLAT
    )
    assert (
        "Ours: ... a last window ends at each winding's end" not in REG
    )  # the addition is registered in prose
    assert "a last window ends at each winding's end" in REG


def test_the_look_is_described_and_the_freeze_disclosed():
    look = RECORD["look_after_the_result"]
    assert look["rank_1"]["winding"] == RECORD["described"]["top"][0]["winding"]
    assert (
        "I can read no letters in it" in FLAT
        and "I will also look at the windows ranked above the place" in REG
    )
    fr = RECORD["freeze"]
    assert (
        fr["seconds"] == 41417
        and RECORD["read"]["stages"]["orient"]["seconds"] >= fr["seconds"]
    )
    assert (
        RECORD["read_seconds_without_the_freeze"]
        == RECORD["steps"]["read"]["seconds"] - fr["seconds"]
    )
    total = sum(g["seconds"] for g in RECORD["steps"].values())
    assert (
        f"**{_hms(total)}; without the freeze, {_hms(total - fr['seconds'])}**"
        in REPORT
    )
    assert f"of which {_hms(fr['seconds'])} frozen" in FLAT
    assert "/home/" not in json.dumps(RECORD)


def test_the_strategy_carries_the_finding():
    assert (
        "reports/first_letters_0211_band_triage.md" in STRATEGY
        and "finding 138" in STRATEGY
    )
    at = STRATEGY.index("first_letters_0211_band_triage.md")
    assert (
        STRATEGY.index("first_letters_0800_studio_band.md")
        < at
        < STRATEGY.index("**Kill criterion.**")
    )


# The audit script on a record whose answer is known.


def _glyph(windows: dict) -> dict:
    return {
        "windings": {
            w: [{"x0": x, "glyph": g} for x, g in xs] for w, xs in windows.items()
        }
    }


def test_the_audit_finds_end_windows_and_reranks_without_them():
    glyph = _glyph({
        "w010": [(0, 9.0), (1300, 9.5), (1700, 14.0)],  # 1700 is off the grid: an end window
        "w011": [(0, 12.0), (1300, 13.0), (2100, 13.5)],  # the place: 2100 (end) and 1300 (grid)
        "w012": [(0, 13.2), (1300, 8.0)],
    })  # fmt: skip
    triage = {
        "registered": {"best_place_rank": 2},
        "described": {
            "place_windows": [
                {"winding": "w011", "x0": 2100},
                {"winding": "w011", "x0": 1300},
            ]
        },
    }
    place = {
        "windows": {
            "w011": {
                "by_window": [
                    {"x0": 1300, "place_cells": 5000},
                    {"x0": 2100, "place_cells": 9000},
                ]
            }
        }
    }
    out = audit_mod.audit(glyph, triage, place)
    assert out["windows"] == 8 and out["end_windows"]["all"] == 2
    assert out["end_windows"]["in_first"]["10"] == 2
    # grid only: 13.2 (w012), 13.0 (w011 place), ... -> the place ranks 2nd of 6
    assert out["grid_only"] == {"windows": 6, "best_place_rank": 2}
    b = out["best_place_window"]
    assert (b["winding"], b["x0"], b["end_window"], b["place_cells"]) == (
        "w011",
        2100,
        True,
        9000,
    )
    assert b["below_first_rank"] == 0.5 and b["above_next_rank"] == pytest.approx(0.3)
    assert b["above_rank_10"] is None  # fewer than 10 windows


def test_the_audit_refuses_a_ranking_that_does_not_reproduce_the_verdict():
    glyph = _glyph({"w010": [(0, 10.0)], "w011": [(0, 11.0)]})
    triage = {
        "registered": {"best_place_rank": 1},
        "described": {"place_windows": [{"winding": "w010", "x0": 0}]},
    }
    with pytest.raises(AssertionError, match="does not reproduce"):
        audit_mod.audit(glyph, triage, {"windows": {}})
