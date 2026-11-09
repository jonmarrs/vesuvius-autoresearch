"""reports/neural_tracer_link_splice.md (finding 105), its registration's result line and the strategy's entry: every
figure from reports/neural_tracer_link_splice.json."""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import neural_tracer_link_splice as ls  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "reports/neural_tracer_link_splice.json"
REPORT = ROOT / "reports/neural_tracer_link_splice.md"
REGISTRATION = ROOT / "docs/preregistration/2026-11-05_neural_tracer_link_splice.md"
STRATEGY = ROOT / "docs/RESEARCH_STRATEGY.md"


def flat(path: Path) -> str:
    return " ".join(path.read_text().split())


def record() -> dict:
    return json.loads(RECORD.read_text())


def held(d: dict) -> list[dict]:
    return [d["per_cube"][c] for c in ls.HELD_OUT]


def test_the_record_is_the_registered_runs_and_its_verdict_recomputes():
    d = record()
    assert d["registration"] == REGISTRATION.relative_to(ROOT).as_posix()
    assert d["settings"] == {"tols": [2.0, 4.0], "splice_arc": 32.0, "ktan": 4, "gain_bar": 0.1, "merge_slack": 0.05,
                             "wrong_share": 0.05}  # fmt: skip
    assert set(d["per_cube"]) == set(ls.HELD_OUT + ls.IN_SAMPLE)
    assert all(v == [] for v in d["gate"].values())
    assert ls.verdict(d["per_cube"], d["gate"]) == d["verdict"]
    v = d["verdict"]
    assert v["status"] == "OK" and v["decision"] == "SUPPORTED_AT_TOL4_ONLY"
    assert v["predictions"] == {"P1": False, "P2": True, "P3": True, "P4": True}


def test_the_table_rows():
    d = record()
    text = REPORT.read_text()
    for c in ls.HELD_OUT:
        r = d["per_cube"][c]
        a, b = r["tol2"], r["tol4"]
        row = (
            f"| {c} | {r['splices']:,} | {a['base']['erl_merge_penalized']:.2f} → "
            f"{a['splice']['erl_merge_penalized']:.2f} | {b['base']['erl_merge_penalized']:.2f} → "
            f"{b['splice']['erl_merge_penalized']:.2f} | {a['base']['merges']:,.0f} → {a['splice']['merges']:,.0f} |"
        )
        assert row in text, row


def test_the_summary_figures():
    d = record()
    v, rows, t = d["verdict"], held(d), flat(REPORT)
    g2 = [r["tol2"]["splice"]["gain"] for r in rows]
    g4 = [r["tol4"]["splice"]["gain"] for r in rows]
    assert all(g > 0 for g in g2 + g4)
    assert (
        f"by a median {v['median_gain']['tol4']:.3f} ({min(g4):.3f} to {max(g4):.3f}). P3 held."
        in t
    )
    assert (
        f"by a median {v['median_gain']['tol2']:.3f} ({min(g2):.3f} to {max(g2):.3f}), under the 0.10 bar"
        in t
    )
    m2, m4 = (
        v["merges_tol2"],
        {k: sum(r["tol4"][k]["merges"] for r in rows) for k in ("base", "splice")},
    )
    rise = m2["splice"] / m2["base"] - 1
    assert (
        f"from {m2['base']:,.0f} to {m2['splice']:,.0f} at tolerance 2 (+{100 * rise:.1f}%;"
        in t
    )
    assert f"from {m4['base']:,.0f} to {m4['splice']:,.0f} at tolerance 4" in t
    k = v["splice_kinds_tol2"]
    known = k["same"] + k["different"]
    assert (
        f"Of the {known:,} splices whose two pieces both touch the reference, {k['different']} "
        in t
    )
    assert (
        f"({100 * v['wrong_share_tol2']:.1f}%) join two different reference fibers (P4 held)"
        in t
    )
    assert f"Another {k['unknown']} splices join a piece" in t
    a2 = [r["tol2"]["all"]["gain"] for r in rows]
    all_m2 = sum(r["tol2"]["all"]["merges"] for r in rows)
    assert (
        f"(−{-statistics.median(a2):.3f}; it rose on {sum(g > 0 for g in a2)} of 10 cubes)"
        in t
    )
    assert f"from {m2['base']:,.0f} to {all_m2:,.0f}" in t
    s = d["summary_median_gain"]
    assert (
        f"gained a median {s['held_out']['tol4']['all']:.3f}, against the splice's {v['median_gain']['tol4']:.3f}"
        in t
    )
    assert (
        f"median gains {s['in_sample']['tol2']['splice']:.3f} at tolerance 2 and {s['in_sample']['tol4']['splice']:.3f}"
        in t
    )
    assert f"rises by {round(100 * v['median_gain']['tol4'])}% at tolerance 4" in t
    assert (
        d["inputs"]["scrollgt_commit"].startswith("c7b2f6f2")
        and "ScrollGT c7b2f6f2" in t
    )


def test_the_title_registration_line_and_strategy_entry():
    v = record()["verdict"]
    pct4, pct2 = (
        round(100 * v["median_gain"]["tol4"]),
        f"{100 * v['median_gain']['tol2']:.1f}",
    )
    title = REPORT.read_text().splitlines()[0]
    assert (
        title.startswith("Finding 105:")
        and f"a median {pct4}% at tolerance 4 and {pct2}% at tolerance 2" in title
    )
    reg = flat(REGISTRATION)
    assert (f"(median held-out gain {v['median_gain']['tol2']:.3f} at τ = 2, {v['median_gain']['tol4']:.3f} at τ = 4): "
            "`SUPPORTED_AT_TOL4_ONLY`") in reg  # fmt: skip
    m2 = v["merges_tol2"]
    strat = flat(STRATEGY)
    assert (
        f"by a median {pct4}% at tolerance 4 and {pct2}% at tolerance 2 (under the 0.10 bar there)"
        in strat
    )
    assert f"with summed merges +{100 * (m2['splice'] / m2['base'] - 1):.1f}%" in strat


def test_the_registrations_already_seen_figures_are_the_in_sample_records():
    """The registration's in-sample splice figures came from the exploratory screen, which divided unrounded ERLpen;
    the registered script divides ScrollGT's rows (ERLpen to two decimals). They agree within that rounding, and the
    counts exactly."""
    d = record()
    rows = [d["per_cube"][c] for c in ls.IN_SAMPLE]
    g2 = [r["tol2"]["splice"]["gain"] + 1 for r in rows]
    g4 = [r["tol4"]["splice"]["gain"] + 1 for r in rows]
    reg = flat(REGISTRATION)
    m = re.search(r"median ERLpen ×([0-9.]+) at τ = 2 \(×([0-9.]+)–×([0-9.]+), above 1 on (\d+) of 11\) and "
                  r"×([0-9.]+) at τ = 4 \(×([0-9.]+)–×([0-9.]+), (\d+) of 11\)", reg)  # fmt: skip
    assert m, "the registration's in-sample splice sentence"
    stated = [float(x) for x in m.group(1, 2, 3, 5, 6, 7)]
    now = [
        statistics.median(g2),
        min(g2),
        max(g2),
        statistics.median(g4),
        min(g4),
        max(g4),
    ]
    assert all(abs(a - b) <= 0.0015 for a, b in zip(stated, now, strict=True)), (
        stated,
        now,
    )
    assert (int(m.group(4)), int(m.group(8))) == (
        sum(g > 1 for g in g2),
        sum(g > 1 for g in g4),
    )
    mt = {k: sum(r["tol2"][k]["merges"] for r in rows) for k in ("base", "splice")}
    m4 = {k: sum(r["tol4"][k]["merges"] for r in rows) for k in ("base", "splice")}
    assert (
        f"from {mt['base']:.0f} to {mt['splice']:.0f} at τ = 2 (+{100 * (mt['splice'] / mt['base'] - 1):.1f}%)"
        in reg
    )
    assert f"from {m4['base']:,.0f} to {m4['splice']:,.0f} at τ = 4" in reg
    k = {
        x: sum(r["tol2"]["kinds"]["splice"][x] for r in rows)
        for x in ("same", "different")
    }
    known = k["same"] + k["different"]
    assert (
        f"{k['different']} of {known:,} ({100 * k['different'] / known:.1f}%) join two different reference fibers"
        in reg
    )


def test_the_merge_claims_follow_from_the_merges():
    """Summed held-out merges rose at tolerance 2 and fell at tolerance 4: the title says by how much at 2, nothing
    says "no more merges", and "no rise in merges" is said of tolerance 4."""
    d = record()
    m2, rows = d["verdict"]["merges_tol2"], held(d)
    m4 = {k: sum(r["tol4"][k]["merges"] for r in rows) for k in ("base", "splice")}
    assert m2["splice"] > m2["base"] and m4["splice"] <= m4["base"]
    title = REPORT.read_text().splitlines()[0]
    assert (
        f"with {100 * (m2['splice'] / m2['base'] - 1):.1f}% more merges at tolerance 2"
        in title
    )
    t = flat(REPORT)
    assert "no more merges" not in t.lower()
    assert "no more wrong connections" not in t.lower()
    pct4 = round(100 * d["verdict"]["median_gain"]["tol4"])
    assert f"rises by {pct4}% at tolerance 4, with no rise in merges" in t


def test_the_rule_and_the_borrowed_share():
    d, t = record(), flat(REPORT)
    assert f"within {d['settings']['splice_arc']:.0f} voxels of arclength" in t
    off = json.loads(
        (
            ROOT / "reports/evidence/neural_tracer_offref_location_2026-11-05.json"
        ).read_text()
    )
    share = off["summary"]["tol2"]["shares"]["gap_same"]
    assert (
        f"put {round(100 * share)}% of the tracer's tolerance-2 off-reference length there"
        in t
    )


def test_the_registrations_link_counts_and_join_all_screen():
    """The counts the registration says were taken on all 21 cubes, and its join-every-link screen (unrounded ERLpen,
    as the splice figures above)."""
    d, reg = record(), flat(REGISTRATION)
    pc = d["per_cube"]
    ends, linked = (
        2 * sum(r["pieces"] for r in pc.values()),
        sum(r["links"] for r in pc.values()),
    )
    assert f"{ends:,} piece ends in the 21 runs, {linked:,} of them linked" in reg
    s3 = [pc[c]["pieces"] for c in ls.HELD_OUT if c.startswith("s3_")]
    assert len(s3) == 8 and f"({min(s3):,} to {max(s3):,} pieces each)" in reg
    rows = [pc[c] for c in ls.IN_SAMPLE]
    g2 = [r["tol2"]["all"]["gain"] + 1 for r in rows]
    g4 = [r["tol4"]["all"]["gain"] + 1 for r in rows]
    m = re.search(r"median ERLpen ×([0-9.]+) at τ = 2 \(×([0-9.]+)–×([0-9.]+)\) and ×([0-9.]+) at\s+τ = 4 "
                  r"\(×([0-9.]+)–×([0-9.]+)\)", reg)  # fmt: skip
    assert m, "the registration's join-every-link sentence"
    now = [
        statistics.median(g2),
        min(g2),
        max(g2),
        statistics.median(g4),
        min(g4),
        max(g4),
    ]
    assert all(
        abs(float(a) - b) <= 0.0015 for a, b in zip(m.groups(), now, strict=True)
    )
