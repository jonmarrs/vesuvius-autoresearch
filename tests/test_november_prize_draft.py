"""Bind the November filing draft to the round's rollover record, villa's criteria at the rollover, and the measured
records of each contribution it names."""

import datetime as dt
import importlib.util
import json
import os
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
# Each finding the draft cites, by its report's stem under reports/: the .md opens "Finding N:", the .json is its record.
FINDINGS = {
    100: "neural_tracer_steep_heading",
    103: "seed_heading_confirmation",
    105: "neural_tracer_link_splice",
    106: "afv_generator_block_seams",
    107: "afv_generator_default_zone",
    108: "afv_generator_cross_block_duplicates",
    109: "afv_generator_seam_confirmation",
}


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
    assert (f"the form is titled “{form['title']}”, answers HTTP {form['http_status']} and accepts "
            "responses") in TEXT  # fmt: skip
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
    deadline = OCTOBER_DEADLINE.astimezone(dt.timezone.utc)
    assert f"after October's deadline ({deadline:%Y-%m-%d %H:%M} UTC)" in TEXT


def test_the_upstream_check_reads_only_the_november_merges():
    """Checklist step 3 runs scripts/check_filing_upstream_claims.py on this file. It reads every "#N (merged DATE)" as
    a villa merge and looks up any it was not given, so one of our own PRs written that way comes back stale."""
    spec = importlib.util.spec_from_file_location(
        "check_filing_upstream_claims",
        ROOT / "scripts/check_filing_upstream_claims.py",
    )
    cf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cf)
    merged = re.findall(
        r"\[villa #(\d+)\]\(\S+?\) \(merged (\d{4}-\d\d-\d\d) Pacific; `(\S+)`",
        " ".join(_section("Merged in November").split()),
    )
    prs = [{"number": int(n), "state": "MERGED", "mergedAt": t} for n, _, t in merged]

    def not_a_november_merge(number: int) -> dict:
        raise AssertionError(f"#{number} reads as a villa merge claim")

    checks, missing = cf.month_checks(DRAFT, prs, "2026-11", not_a_november_merge)
    assert merged and missing == []
    assert [c[:2] for c in checks] == [(f"#{n} merged {day}", True) for n, day, _ in merged]  # fmt: skip


def test_the_draft_names_the_villa_commits_its_quotes_are_checked_at():
    assert f"(merge `{OPENED[:9]}`)" in TEXT
    assert f"(`{CRITERIA[:9]}`, merged by" in TEXT


def test_2258_s_numbers_are_its_record():
    rows = json.loads(
        (ROOT / "reports/villa_fractional_plane_spacing_2026-10-20.json").read_text()
    )["rows"]
    fractional = [r for r in rows if abs(r["spacing"] - 52.733333) < 1e-5]
    changes = [f"{r['before']['dots']} → {r['after']['dots']}" for r in fractional]
    scrolls = [r["cube"].split("_")[0].removeprefix("s") for r in fractional]
    assert (f"At a fractional spacing of {fractional[0]['spacing']:.2f} voxels the seed counts change "
            f"{', '.join(changes[:-1])} and {changes[-1]} on masks from Scrolls {', '.join(scrolls[:-1])} and "
            f"{scrolls[-1]}") in TEXT  # fmt: skip
    worst = max(abs(r["after"]["dots"] - r["before"]["dots"]) / r["before"]["dots"] for r in fractional)  # fmt: skip
    assert f"at most {100 * worst:.2f}%" in TEXT
    assert all(r["identical"] for r in rows if r["spacing"] == 64.0)
    assert "the default 64-voxel seed spacing is unchanged" in TEXT


def _villa(rev: str, path: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT / "villa"), "show", f"{rev}:{path}"],
            capture_output=True, text=True, check=True,
            # villa is a blob:none partial clone: a missing object must skip, not fetch
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
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
    d = json.loads((ROOT / f"reports/{FINDINGS[100]}.json").read_text())
    b, rows = d["baseline_rows_tol2"], d["rows_tol2"]
    s5 = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
    keep = [rows["keep"][c]["coverage"] / b[c]["coverage"] for c in s5]
    sheet = [rows["sheet"][c]["coverage"] / b[c]["coverage"] for c in s5]
    section = " ".join(_section("Queued, not posted").split())
    assert (f"is finding 100's two held-out Scroll-5 cubes. The fix itself (finding 100's `keep` arm) raised their "
            f"coverage ×{keep[0]:.2f} and ×{keep[1]:.2f}.") in section  # fmt: skip
    assert (
        f"The ×{sheet[0]:.2f} and ×1.43 in finding 100 belong to a heading along the sheet"
        in section
    )
    assert round(sheet[1], 3) == 1.425  # finding 100's report rounds it to 1.43


def test_the_seed_heading_entry_s_rebase_is_the_stubbed_record():
    record = (
        ROOT / "reports/evidence/villa_volume_seed_heading_tests_eab6108b9_stubbed.txt"
    ).read_text()
    villa = re.search(r"^villa ([0-9a-f]{40}) \(", record, re.M)[1]
    section = " ".join(_section("Queued, not posted").split())
    assert f"the rebase onto villa main `{villa[:9]}`" in section
    assert "STUBBED" in record.splitlines()[0]
    assert "Those tests were run with the native readers stubbed only." in section


def test_finding_103_s_skip_figures_are_its_record():
    """How often the skip occurs: no unseen cube reached the registered 0.20 share, and the one that came nearest."""
    v = json.loads((ROOT / f"reports/{FINDINGS[103]}.json").read_text())["verdict"]
    share, gain = v["skip_share"], v["coverage_factor"]
    most = max(share, key=share.get)
    assert v["decision"] == "NO_HIGH_SKIP_CUBE" and v["high_skip_cubes"] == []
    assert max(share.values()) < 0.20
    section = " ".join(_section("Queued, not posted").split())
    assert (f"Finding 103 found no unseen cube that skipped 20% of its seed dots: the most was {share[most]:.3f}, "
            f"which gained {gain[most]:.3f}×.") in section  # fmt: skip


def test_each_finding_cited_is_the_report_it_names():
    assert {int(n) for n in re.findall(r"\b[Ff]inding (\d+)", TEXT)} == set(FINDINGS)
    for n, stem in FINDINGS.items():
        title = (ROOT / f"reports/{stem}.md").read_text().splitlines()[0]
        assert re.match(rf"(# )?Finding {n}: ", title), title
    links = re.findall(r"\[finding (\d+)\]\(\.\./reports/(\S+?)\.md\)", TEXT)
    assert links and all(FINDINGS[int(n)] == stem for n, stem in links)


def test_the_splice_entry_is_the_polyline_record():
    s = json.loads(
        (
            ROOT / "reports/evidence/neural_tracer_splice_polylines_2026-11-06.json"
        ).read_text()
    )
    assert s["finding"] == f"reports/{FINDINGS[105]}.json"
    h = s["summary"]["held_out"]
    m = h["tol2"]["merges"]
    section = " ".join(_section("Queued, not posted").split())
    assert (f"a median +{round(100 * h['tol4']['median_gain_poly'])}% at tolerance 4 and "
            f"+{100 * h['tol2']['median_gain_poly']:.1f}% at tolerance 2, with merges {m['base']:,} → {m['poly']:,}") in section  # fmt: skip
    assert (
        h["tol2"]["cubes_gaining"] == h["tol4"]["cubes_gaining"] == 10
        and "raised ERLpen on every cube" in section
    )
    assert h["tol2"]["n"] == h["tol4"]["n"] == 10
    assert "on the ten held-out cubes, splicing them as polylines" in section


def test_villa_objects_are_read_without_a_lazy_fetch(monkeypatch):
    seen = {}

    def run(cmd, **kwargs):
        seen.update(kwargs.get("env") or {})
        raise subprocess.CalledProcessError(128, cmd)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(pytest.skip.Exception):
        _villa("HEAD", "README.md")
    assert seen.get("GIT_NO_LAZY_FETCH") == "1"


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


def test_the_seam_trim_case_in_practice_is_finding_107s_record():
    d = json.loads((ROOT / f"reports/{FINDINGS[107]}.json").read_text())
    r, section = d["result"], " ".join(_section("Queued, not posted").split())
    m, p = r["rows"]["main"], r["rows"]["patched"]
    assert (
        d["verdict"]["decision"] == "BITES_AT_DEFAULTS"
        and "(`BITES_AT_DEFAULTS`)" in section
    )
    assert (
        (r["zone"], r["block"]) == (1024, 512)
        and "1024³ zone of the Scroll-3 scan at villa's default block size of 512"
        in section
    )
    assert (
        f"**On main:** {m['zone']['duplicated_share']:.3f} of the zone's written length"
        in section
    )
    assert f"**With the trim:** {p['zone']['duplicated_share']:.3f}." in section
    g = [
        100
        * (
            p["cube"][t]["erl_merge_penalized"] / m["cube"][t]["erl_merge_penalized"]
            - 1
        )
        for t in ("tol4", "tol2")
    ]
    c = 100 * (p["cube"]["tol4"]["coverage"] / m["cube"]["tol4"]["coverage"] - 1)
    assert (f"ERLpen rises {g[0]:+.1f}% at tolerance 4 and {g[1]:+.1f}% at tolerance 2, with merges "
            f"{m['cube']['tol2']['merges']} → {p['cube']['tol2']['merges']} at tolerance 2 and coverage "
            f"{c:.1f}% at tolerance 4").replace("coverage -", "coverage −") in section  # fmt: skip


def test_the_rest_of_the_seam_defect_is_finding_108s_record():
    d = json.loads((ROOT / f"reports/{FINDINGS[108]}.json").read_text())
    one = json.loads((ROOT / f"reports/{FINDINGS[106]}.json").read_text())["cubes"]
    section = " ".join(_section("Queued, not posted").split())
    assert d["verdict"]["decision"] == "SUPPORTED" and "(`SUPPORTED`)" in section
    rows = [d["cubes"][c]["rows"] for c in d["cubes"]]
    gain = {t: [r["trim+dup"][t]["erl_merge_penalized"] / r["trim"][t]["erl_merge_penalized"] - 1 for r in rows]
            for t in ("tol4", "tol2")}  # fmt: skip
    assert (
        all(x > 0 for x in gain["tol4"] + gain["tol2"])
        and "over the trim alone on every cube" in section
    )
    m = d["verdict"]["P3_merges_tol2"][0]
    assert (f"a median +{100 * statistics.median(gain['tol4']):.1f}% at tolerance 4 and "
            f"+{100 * statistics.median(gain['tol2']):.1f}% at tolerance 2, with merges {m[0]} → {m[1]} at "
            "tolerance 2") in section  # fmt: skip
    f = [d["cubes"][c]["rows"]["trim+dup"]["tol4"]["erl_merge_penalized"]
         / one[c]["rows"]["one/main"]["tol4"]["erl_merge_penalized"] for c in d["cubes"]]  # fmt: skip
    assert (
        f"eight blocks reach {min(f):.3f} to {max(f):.3f} of one block's ERLpen at tolerance 4"
        in section
    )


def test_the_seam_changes_on_other_scrolls_are_finding_109s_record():
    d = json.loads((ROOT / f"reports/{FINDINGS[109]}.json").read_text())
    section = " ".join(_section("Queued, not posted").split())
    assert d["verdict"]["decision"] == "CONFIRMED" and "(`CONFIRMED`)" in section
    cubes = d["cubes"]
    assert len(cubes) == 10 and sorted(c[:2] for c in cubes).count("s1") == 3

    def figures(names):
        rows = [cubes[c]["rows"] for c in names]
        gain = {t: [r["real/trim+dup"][t]["erl_merge_penalized"] / r["real/main"][t]["erl_merge_penalized"] - 1
                    for r in rows] for t in ("tol4", "tol2")}  # fmt: skip
        assert all(x > 0 for x in gain["tol4"] + gain["tol2"])
        m = [sum(r[f"real/{k}"]["tol2"]["merges"] for r in rows) for k in ("main", "trim+dup")]  # fmt: skip
        return (f"a median +{100 * statistics.median(gain['tol4']):.1f}% at tolerance 4 and "
                f"+{100 * statistics.median(gain['tol2']):.1f}% at tolerance 2"), f"with merges {m[0]} → {m[1]} at tolerance 2"  # fmt: skip

    big = [c for c in cubes if cubes[c]["block"] == 256]
    assert len(big) == 4 and all(cubes[c]["size"] == 512 for c in big)
    assert sum(cubes[c]["block"] == 128 for c in cubes) == 6
    gains, merges = figures(big)
    assert f"both changes raised ERLpen over main on every cube, {gains}, {merges}" in section  # fmt: skip
    gains, merges = figures(list(cubes))
    assert f"**All ten:** {gains}, up on every cube, {merges}" in section
    cov = [100 * (r["rows"]["real/trim+dup"]["tol4"]["coverage"] / r["rows"]["real/main"]["tol4"]["coverage"] - 1)
           for r in cubes.values()]  # fmt: skip
    assert all(x < 0 for x in cov)
    assert (f"coverage at tolerance 4 fell on every cube, a median {statistics.median(cov):.1f}%"
            .replace("median -", "median −")) in section  # fmt: skip
