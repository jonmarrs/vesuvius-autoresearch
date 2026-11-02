"""reports/neural_tracer_continuity_ceiling.md (finding 102): every figure from its JSON, finding 101's, and the
recorded rows it was gated on; the verdict recomputed by the registered rule."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_continuity_ceiling as cc  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_continuity_ceiling.json").read_text())
F101 = json.loads((ROOT / "reports/neural_tracer_confidence_stops.json").read_text())
REPORT = " ".join(
    (ROOT / "reports/neural_tracer_continuity_ceiling.md").read_text().split()
)
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
HELD = cc.HELD_OUT


def cube(c, tol="tol2"):
    return D["per_cube"][c][tol]


def gains(policy, cubes=HELD, tol="tol2"):
    return [cube(c, tol)[policy]["gain"] for c in cubes]


def median(policy, cubes=HELD, tol="tol2"):
    return statistics.median(gains(policy, cubes, tol))


def above(policy, tol="tol2"):
    return sum(g >= cc.GAIN_BAR for g in gains(policy, tol=tol))


def test_the_run_is_the_registered_one_on_every_cube():
    assert (
        D["registration"]
        == "docs/preregistration/2026-11-01_neural_tracer_continuity_ceiling.md"
    )
    assert D["settings"] == {"tol": cc.TOL, "tols": list(cc.TOLS), "L": cc.L, "edge": cc.EDGE, "ks": list(cc.KS),
                             "gain_bar": cc.GAIN_BAR, "p3_fraction": cc.P3_FRACTION,
                             "covered_slack": list(cc.COVERED_SLACK)}  # fmt: skip
    assert sorted(D["per_cube"]) == sorted(cc.ALL) and len(cc.ALL) == 21
    assert D["gate"] == {c: [] for c in cc.ALL}
    assert "Gate, passed on all 21 cubes at both tolerances" in REPORT
    assert D["provenance"]["scoring_version"] == 3
    assert D["provenance"]["scrollgt_commit"][:8] in REPORT
    assert D["provenance"]["checkpoints"] == [
        "scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
    ]
    assert D["provenance"]["skeleton_sha256"] == F101["provenance"]["skeleton_sha256"]


def test_the_verdict_is_the_registered_rule():
    v = cc.verdict(D["registered"], D["gate"])
    assert v == D["verdict"]
    assert (v["status"], v["decision"], v["P1"], v["P2"], v["P3"]) == (
        "OK",
        "open",
        True,
        False,
        True,
    )
    for c in cc.ALL:
        assert D["registered"][c] == {
            k: cube(c)[k]["gain"] for k in ("U", "U_20", "fill_join")
        }


def test_the_headline_figures():
    v = D["verdict"]
    assert (
        f"by a median {round(100 * v['median_U'])}%" in REPORT.split(" (2026-11-01)")[0]
    )
    assert (
        f"a median **{v['median_U']:.3f}** on the ten held-out cubes ({v['U_range'][0]:.3f}–{v['U_range'][1]:.3f})"
        in REPORT
    )
    assert above("U") == 10 and "All ten cubes clear it" in REPORT
    assert f"at tolerance 4 the median is {median('U', tol='tol4'):.3f}" in REPORT
    assert above("U", "tol4") == 10


def test_the_bounded_ceilings():
    assert (
        f"Bounded to 20 voxels past each stop, the ceiling is a median {median('U_20'):.3f} (P2 missed)"
        in REPORT
    )
    assert above("U_20") == 1 and "only 1 of the 10 cubes reaches 0.10" in REPORT
    assert (
        f"Bounded to 50 voxels it is {median('U_50'):.3f} ({above('U_50')} cubes)"
        in REPORT
    )
    assert (
        f"Within 20 voxels the ceiling is a median {100 * median('U_20'):.1f}%"
        in REPORT
    )


def test_the_fill_and_the_joins():
    assert (
        f"the fill alone raises held-out ERLpen by a median {median('U_fill'):.3f}"
        in REPORT
    )
    ratio = [cube(c)["U_fill"]["gain"] / F101["registered"][c]["G"] for c in HELD]
    assert (
        f"a median {statistics.median(ratio):.1f} times the coverage it adds ({min(ratio):.1f}–{max(ratio):.1f} by cube"
        in REPORT
    )
    joins = statistics.median(
        cube(c)["U"]["gain"] - cube(c)["U_fill"]["gain"] for c in HELD
    )
    assert f"Joining the split traces adds a further median {joins:.3f}" in REPORT
    n = {k: sum(cube(c)["counts"][k] for c in HELD) for k in cube(HELD[0])["counts"]}
    # finding 101's own held-out counts of continuing stops and splits
    reg = [
        F101["per_cube"][c]["tol2"]["settings"]["L20_edge6"]["confidence"] for c in HELD
    ]
    assert n["stops"] == sum(r["continues"] for r in reg) and n["splits"] == sum(
        r["splits"] for r in reg
    )
    assert (f"Of the {n['stops']:,} continuing confidence stops, {n['splits']:,} are splits, and {n['joins_unmerged']:,} "
            f"of those joins involve no trace that merges at baseline") in REPORT  # fmt: skip
    assert (
        f"{n['own_merging']:,} stops end traces that already merge, and {n['other_merging']:,} splits run into one"
        in REPORT
    )


def test_the_two_rules():
    assert f"**Fill only:** a median {median('fill'):.3f}" in REPORT
    assert (
        f"a median {median('fill_join'):.3f}, at least half of the ceiling (P3 held)"
        in REPORT
    )
    assert above("fill_join") == 10 and "above 0.10 on all ten cubes" in REPORT
    assert f"At tolerance 4 it falls to {median('fill_join', tol='tol4'):.3f}" in REPORT
    assert f"only {above('fill_join', 'tol4')} of the 10 cubes reach 0.10" in REPORT


def test_the_merge_counts():
    delta = {
        c: cube(c)["fill_join"]["merges"] - cube(c)["base"]["merges"] for c in HELD
    }
    fell, level = (
        sum(v < 0 for v in delta.values()),
        sum(v == 0 for v in delta.values()),
    )
    rose = [c for c, v in delta.items() if v > 0]
    assert rose == ["s5_13497_01497_02497_256"] and delta[rose[0]] == 1
    assert (
        f"the merge count fell on {fell} held-out cubes, stayed level on {level}, and rose by 1 on one ({rose[0]})"
        in REPORT
    )
    fill = [cube(c)["fill"]["merges"] - cube(c)["base"]["merges"] for c in HELD]
    up = [v for v in fill if v > 0]
    assert (
        min(fill) >= 0
        and f"rose on {len(up)} of the 10 held-out cubes, by {min(up)}–{max(up)}"
        in REPORT
    )


def test_the_table_rows():
    rows = D["per_cube"]
    for c in HELD:
        t = rows[c]["tol2"]
        assert abs(t["base"]["value"] - t["row"]["erl_merge_penalized"]) < 0.005
        row = (f"| {c} | {t['base']['value']:.2f} | {t['U']['value']:.2f} | {t['U']['gain']:.3f} | "
               f"{t['U_fill']['gain']:.3f} | {t['U_20']['gain']:.3f} | {t['U_50']['gain']:.3f} | "
               f"{t['fill_join']['gain']:.3f} |")  # fmt: skip
        assert row in REPORT, c


def test_the_other_sets():
    g = gains("U", cc.IN_SAMPLE)
    assert (
        f"the median gain of U is {statistics.median(g):.3f} ({min(g):.3f}–{max(g):.3f})"
        in REPORT
    )
    assert (
        f"the scrolls the tracer never saw, it is {median('U', cc.UNSEEN_SCROLLS):.3f}"
        in REPORT
    )
    assert (
        len(cc.UNSEEN_SCROLLS) == 16 and "sixteen Scroll-3 and Scroll-5 cubes" in REPORT
    )


def test_the_gate_figures():
    worst = 0.0
    for c in cc.ALL:
        for tol, filled in (("tol2", "fill"), ("tol4", "fill_join")):
            t = cube(c, tol)
            assert t["misaligned"] == 0 and t["U_none"]["value"] == t["base"]["value"]
            rise = t[filled]["covered"] - t["base"]["covered"]
            worst = max(worst, abs(rise / t["union_length"] - 1))
    assert round(100 * worst, 1) == 0.6 and "within 0.6%" in REPORT


def test_the_off_reference_ratio_is_finding_101s():
    conf = [
        F101["per_cube"][c]["tol2"]["settings"]["L20_edge6"]["confidence"] for c in HELD
    ]
    stops, on = sum(r["stops"] for r in conf), sum(r["on_fiber"] for r in conf)
    assert round((stops - on) / on) == 2
    assert (
        "would extend about two off-reference traces for each on-reference one"
        in REPORT
    )


def test_the_strategy_cites_the_same_figures():
    assert f"by up to a median {round(100 * D['verdict']['median_U'])}%" in STRATEGY
    assert f"only {100 * median('U_20'):.1f}% within 20 voxels of each stop" in STRATEGY
    assert "about two off-reference traces for each on-reference one" in STRATEGY
