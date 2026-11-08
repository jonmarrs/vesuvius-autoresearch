"""Bind the November filing draft to the round's rollover record, villa's criteria at the rollover, and the measured
records of each contribution it names."""

import datetime as dt
import json
import re
import statistics
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRAFT = (ROOT / "docs/PRIZE_FILING_2026-11_DRAFT.md").read_text()
TEXT = " ".join(DRAFT.split())
ROLLOVER = json.loads(
    (ROOT / "reports/evidence/november_form_rollover_2026-11-05.json").read_text()
)
OPENED = "9c343a16494cf61d72727cbc85dc5e12e8773677"  # villa #2301's merge
# villa #2450, merged just before it
CRITERIA = "aa8784bff0b43149374f7d9928b899bc5f7ae30d"
OCTOBER_DEADLINE = dt.datetime(2026, 10, 31, 23, 59, tzinfo=ZoneInfo("America/Los_Angeles"))  # fmt: skip


def _utc(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _section(heading: str) -> str:
    return DRAFT.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def _url_field() -> list:
    block = _section("URL field").split("```", 2)[1]
    return [line.strip() for line in block.splitlines()[1:] if line.strip()]


def test_the_round_s_deadline_and_form_are_the_rollover_s():
    row = {r["number"]: r for r in ROLLOVER["rollover_prs"]}[2301]
    assert row["state"] == "MERGED"
    opened = _utc(row["merged_at"])
    assert f"opened {opened:%Y-%m-%d %H:%M} UTC (2026-11-04 Pacific)" in TEXT
    assert opened.astimezone(ZoneInfo("America/Los_Angeles")).date() == dt.date(2026, 11, 4)  # fmt: skip
    assert f"**deadline {row['deadline_after']}**" in TEXT
    form = ROLLOVER["filing_form"]
    assert form["url"] == row["form_after"]
    assert DRAFT.count(form["url"]) == 2  # the round's form and the filing-day check
    assert ROLLOVER["expected_form_title"] == form["title"] == "November 2026 Progress Prizes"  # fmt: skip
    assert form["accepting_responses"] and ROLLOVER["filing_form_title_matches"]
    checked = _utc(ROLLOVER["checked_at_utc"])
    assert f"passed on {checked:%Y-%m-%d} at {checked:%H:%M} UTC" in TEXT
    assert "--expected-title 'November 2026 Progress Prizes'" in DRAFT


def test_the_url_field_is_exactly_the_november_merges():
    """Each merge in "Merged in November" is cited once in the URL field, with its Pacific date and UTC stamp."""
    merged = re.findall(
        r"\[villa #(\d+)\]\((\S+?)\) \(merged (\d{4}-\d\d-\d\d) Pacific; `(\S+)`",
        " ".join(_section("Merged in November").split()),
    )
    assert merged
    assert _url_field() == [url for _, url, _, _ in merged]
    for number, url, day, stamp in merged:
        assert url == f"https://github.com/ScrollPrize/villa/pull/{number}"
        when = _utc(stamp).astimezone(ZoneInfo("America/Los_Angeles"))
        assert when.date().isoformat() == day
        assert when > OCTOBER_DEADLINE and when.month == 11


def test_2258_s_numbers_are_its_record():
    rows = json.loads(
        (ROOT / "reports/villa_fractional_plane_spacing_2026-10-20.json").read_text()
    )["rows"]
    fractional = [r for r in rows if abs(r["spacing"] - 52.733333) < 1e-5]
    changes = [f"{r['before']['dots']} → {r['after']['dots']}" for r in fractional]
    assert f"seed counts change {', '.join(changes[:-1])} and {changes[-1]}" in TEXT
    worst = max(abs(r["after"]["dots"] - r["before"]["dots"]) / r["before"]["dots"] for r in fractional)  # fmt: skip
    assert f"at most {100 * worst:.2f}%" in TEXT
    assert all(r["identical"] for r in rows if r["spacing"] == 64.0)
    assert "the default 64-voxel seed spacing is unchanged" in TEXT


def _villa(rev: str, path: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT / "villa"), "show", f"{rev}:{path}"],
            capture_output=True, text=True, check=True,
        ).stdout  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(f"villa {rev} not in this checkout's submodule objects")


@pytest.mark.parametrize(
    "quote, path, now",
    [
        ("We discourage standalone analytic, auditing or evaluation tools, and instead encourage work that directly "
         "**advances unwrapping or ink detection**.", "34_prizes.md", True),
        ("Fixes for issues that are theoretically wrong but rarely or never cause problems in practice are unlikely "
         "to be awarded.", "34_prizes.md", True),
        ("Reveal **insightful, actionable** information", "34_prizes.md", False),
        ("facilitated improvements to unwrapping or ink detection", "34_prizes.md", False),
        ("improvements to tooling", "34_prizes.md", True),
        ("several bugfix PRs on our [villa](https://github.com/ScrollPrize/villa) monorepo", "34_prizes.md", False),
        ("This is why better diagnostics matter just as much as better models", "37_2026_open_problems.md", False),
    ],
)  # fmt: skip
def test_each_quoted_criterion_is_villa_s_wording(quote, path, now):
    """Quoted in the draft; present in villa at the rollover when added, and only before #2450 when removed."""
    assert f"“{quote}" in TEXT
    after = _villa(OPENED, f"scrollprize.org/docs/{path}")
    before = _villa(f"{CRITERIA}^", f"scrollprize.org/docs/{path}")
    assert (quote in after, quote in before) == (
        (True, False) if now else (False, True)
    )


def test_the_seed_heading_entry_quotes_the_fix_not_the_sheet_heading():
    """The queued fix is finding 100's `keep` arm; ×1.20/×1.43 are its `sheet` arm, which the draft does not propose."""
    d = json.loads((ROOT / "reports/neural_tracer_steep_heading.json").read_text())
    b, rows = d["baseline_rows_tol2"], d["rows_tol2"]
    s5 = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
    keep = [rows["keep"][c]["coverage"] / b[c]["coverage"] for c in s5]
    sheet = [rows["sheet"][c]["coverage"] / b[c]["coverage"] for c in s5]
    section = " ".join(_section("Queued, not posted").split())
    assert f"raised their coverage ×{keep[0]:.2f} and ×{keep[1]:.2f}" in section
    assert (
        f"The ×{sheet[0]:.2f} and ×1.43 in finding 100 belong to a heading along the sheet"
        in section
    )
    assert round(sheet[1], 3) == 1.425  # finding 100's report rounds it to 1.43


def test_the_splice_entry_is_the_polyline_record():
    s = json.loads(
        (
            ROOT / "reports/evidence/neural_tracer_splice_polylines_2026-11-06.json"
        ).read_text()
    )
    h = s["summary"]["held_out"]
    m = h["tol2"]["merges"]
    section = " ".join(_section("Queued, not posted").split())
    assert (f"a median +{round(100 * h['tol4']['median_gain_poly'])}% at tolerance 4 and "
            f"+{100 * h['tol2']['median_gain_poly']:.1f}% at tolerance 2, with merges {m['base']:,} → {m['poly']:,}") in section  # fmt: skip
    assert (
        h["tol2"]["cubes_gaining"] == h["tol4"]["cubes_gaining"] == 10
        and "raised ERLpen on every cube" in section
    )


def test_the_seam_trim_entry_is_finding_106s_record():
    d = json.loads((ROOT / "reports/afv_generator_block_seams.json").read_text())
    v = d["verdict"]
    rows = [r["rows"] for r in d["cubes"].values()]
    lost = [
        sum(r[f"real/{k}"]["crossings"]["lost"] for r in rows)
        for k in ("main", "patched")
    ]
    n = sum(sum(r["real/main"]["crossings"].values()) for r in rows)
    m = v["P3_merges_tol2"]
    section = " ".join(_section("Queued, not posted").split())
    assert v["decision"] == "SUPPORTED" and len(rows) == 8
    g = {t: statistics.median(r["real/patched"][t]["erl_merge_penalized"] / r["real/main"][t]["erl_merge_penalized"] - 1 for r in rows)
         for t in ("tol2", "tol4")}  # fmt: skip
    assert (round(g["tol4"], 4), round(g["tol2"], 4)) == (
        v["P2_median_gain_tol4"][0],
        v["P4_median_gain_tol2"][0],
    )
    assert (f"a median +{100 * g['tol4']:.1f}% at tolerance 4 and "
            f"+{100 * g['tol2']:.1f}% at tolerance 2, with merges {m[0]} → {m[1]} at tolerance 2") in section  # fmt: skip
    assert f"Lost face crossings rise, {lost[0]} → {lost[1]} of {n:,}." in section
    erl = [
        [r[f"real/{k}"][t]["erl_merge_penalized"] for k in ("main", "patched")]
        for r in rows
        for t in ("tol2", "tol4")
    ]
    assert (
        all(b > a for a, b in erl)
        and "trimming the cut ends raised ERLpen on every cube" in section
    )
