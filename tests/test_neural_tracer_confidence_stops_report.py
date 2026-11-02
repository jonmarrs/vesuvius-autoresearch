"""reports/neural_tracer_confidence_stops.md (finding 101): every figure from its JSON and the recorded rows it was
gated on, and the verdict recomputed by the registered rule."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_confidence_stops as cs  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_confidence_stops.json").read_text())
REPORT = " ".join(
    (ROOT / "reports/neural_tracer_confidence_stops.md").read_text().split()
)
ROWS = {}
for _p in cs.RECORDED.values():
    ROWS.update(json.loads((ROOT / _p).read_text())["rows_tol2"])
HELD = cs.HELD_OUT
REG = "L20_edge6"


def cube(c, tol="tol2"):
    return D["per_cube"][c][tol]


def conf(c, tol="tol2"):
    return cube(c, tol)["settings"][REG]["confidence"]


def total(key, reason="confidence", tol="tol2"):
    return sum(cube(c, tol)["settings"][REG][reason][key] for c in HELD)


def pct(a, b):
    return f"{round(100 * a / b)}%"


def test_the_run_is_the_registered_one_on_every_cube():
    assert (
        D["registration"]
        == "docs/preregistration/2026-11-01_neural_tracer_confidence_stops.md"
    )
    assert D["settings"] == {"tol": cs.TOL, "L": cs.L, "edge": cs.EDGE, "cap": cs.CAP, "step": cs.STEP,
                             "base_n": cs.BASE_N, "rng_seed": cs.RNG_SEED, "back_direction": cs.BACK_DIRECTION,
                             "back_late": cs.BACK_LATE}  # fmt: skip
    assert sorted(D["per_cube"]) == sorted(cs.ALL) and len(cs.ALL) == 21
    assert D["gate"] == {c: [] for c in cs.ALL}
    assert "Gate, passed on all 21 cubes" in REPORT
    assert D["provenance"]["scoring_version"] == 3
    assert D["provenance"]["scrollgt_commit"][:8] in REPORT
    assert D["provenance"]["checkpoints"] == [
        "scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
    ]
    assert all(cube(c)["base_n"] == cs.BASE_N for c in cs.ALL)


def test_the_verdict_is_the_registered_rule():
    v = cs.verdict(D["registered"], D["gate"])
    assert v == D["verdict"]
    assert (v["status"], v["decision"], v["P1"], v["P2"], v["P3"]) == (
        "OK",
        "close",
        True,
        True,
        False,
    )
    for c in cs.ALL:
        s = cube(c)["settings"][REG]
        assert D["registered"][c] == {"G": s["G"], "premature_share": s["premature_share"],
                                      "base_rate": cube(c)["base_rate"]["L20"]}  # fmt: skip


def test_the_headline_figures():
    v = D["verdict"]
    assert f"a median **{v['median_G']:.3f}**" in REPORT
    assert f"({v['G_range'][0]:.3f}–{v['G_range'][1]:.3f})" in REPORT
    G = sorted(D["registered"][c]["G"] for c in HELD)
    above = sum(g >= cs.G_BAR for g in G)
    assert above == 5 and "Five of the ten cubes are at or above 0.10" in REPORT
    assert f"between the fifth and sixth cubes ({G[4]:.3f} and {G[5]:.3f})" in REPORT


def test_every_variant_keeps_the_median_below_the_bar():
    s = D["summary"]["held_out"]
    medians = [s[t][k]["G"]["median"] for t in ("tol2", "tol4") for k in s[t]]
    assert len(medians) == 12 and max(medians) < cs.G_BAR
    named = [
        s[t][k]["G"]["median"]
        for t in ("tol2", "tol4")
        for k in ("L20_edge6", "L10_edge6", "L40_edge6", "L20_edge12")
    ]
    assert f"stays between {min(named):.3f} and {max(named):.3f}" in REPORT


def test_the_split_and_continuity_figures():
    splits, cont = total("splits"), total("continues")
    assert f"**{pct(splits, cont)} are splits** ({splits:,} of {cont:,})" in REPORT
    scrollgt = sum(ROWS[c]["splits"] for c in HELD)
    assert (
        f"those {splits:,} splits are {100 * splits / scrollgt:.1f}% of the {scrollgt:,}"
        in REPORT
    )


def test_where_the_stops_lie():
    stops, on = total("stops"), total("on_fiber")
    assert (
        f"Of the {stops:,} interior, unlinked confidence stops, {on:,} ({pct(on, stops)})"
        in REPORT
    )
    o_stops, o_on = total("stops", "owned_or_live"), total("on_fiber", "owned_or_live")
    assert f"it is {o_on:,} of {o_stops:,} ({pct(o_on, o_stops)})" in REPORT
    left, off = total("left_fiber"), total("off_fiber")
    assert (
        f"{left:,} ({pct(left, stops)}) of the confidence stops left the fiber"
        in REPORT
    )
    assert (
        f"{off - left:,} ({pct(off - left, stops)}) were already more than 2 voxels off"
        in REPORT
    )
    on4 = total("on_fiber", tol="tol4")
    assert total("stops", tol="tol4") == stops
    assert f"At tolerance 4, {on4:,} ({pct(on4, stops)}) are on the reference" in REPORT


def test_the_premature_share_and_its_base_rate():
    v = D["verdict"]
    assert (
        f"is {v['median_premature_share']:.2f} ({v['premature_share_range'][0]:.2f}–{v['premature_share_range'][1]:.2f})"
        in REPORT
    )
    base = statistics.median(D["registered"][c]["base_rate"] for c in HELD)
    assert f"it is {base:.2f} (P1 and P2 held)" in REPORT
    ratio, lows = [], []
    for c in HELD:
        k = conf(c)
        fe = k["fiber_ends"] / (k["continues"] + k["fiber_ends"])
        low = 1 - D["registered"][c]["base_rate"]
        ratio.append(fe / low)
        lows.append(low)
    assert f"is {min(ratio):.1f}–{max(ratio):.1f} times as common" in REPORT
    assert f"(median {statistics.median(ratio):.0f})" in REPORT
    assert (
        f"only {100 * min(lows):.1f}–{100 * max(lows):.1f}% of those decided" in REPORT
    )


def test_the_gap_per_continuing_stop():
    per = [cube(c)["settings"][REG]["gap_length"] / conf(c)["continues"] for c in HELD]
    assert f"a median {statistics.median(per):.0f} voxels of uncovered fiber" in REPORT


def test_the_table_rows():
    for c in HELD:
        k, s = conf(c), cube(c)["settings"][REG]
        row = (f"| {c} | {ROWS[c]['coverage']:.3f} | {k['stops']:,} | {k['on_fiber']:,} | {k['continues']:,} | "
               f"{k['fiber_ends']:,} | {k['censored']:,} | {k['splits']:,} | {s['G']:.3f} |")  # fmt: skip
        assert row in REPORT, c
        assert (
            abs(cube(c)["covered"] - ROWS[c]["coverage"] * ROWS[c]["gt_length"]) < 1e-6
        )


def test_the_in_sample_median():
    G = statistics.median(D["registered"][c]["G"] for c in cs.IN_SAMPLE)
    assert f"the median G is {G:.3f}" in REPORT


def test_the_strategy_cites_the_same_figures():
    strategy = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
    v = D["verdict"]
    assert (
        f"at most a median {100 * v['median_G']:.1f}% of held-out coverage" in strategy
    )
    assert (
        f"{pct(total('splits'), total('continues'))} of those stops are splits"
        in strategy
    )
    stops, on = total("stops"), total("on_fiber")
    assert (
        round(3 * (stops - on) / stops) == 2
        and "Two-thirds of the tracer's interior confidence stops" in strategy
    )
    left, off = total("left_fiber"), total("off_fiber")
    assert (
        (off - left) / off > 0.5
        and "most of them already off it 20 voxels before they stop" in strategy
    )
