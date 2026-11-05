"""reports/seed_heading_confirmation.md (finding 103): every figure from its JSON, the verdict recomputed by the
registered rule, and what the villa draft, the registration and the strategy say about it."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import seed_heading_confirmation as m  # noqa: E402

D = json.loads((ROOT / "reports/seed_heading_confirmation.json").read_text())
REPORT = " ".join((ROOT / "reports/seed_heading_confirmation.md").read_text().split())
DRAFT = " ".join((ROOT / "docs/VILLA_DRAFT_volume_seed_heading.md").read_text().split())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
REG = " ".join(
    (ROOT / "docs/preregistration/2026-11-02_seed_heading_confirmation.md")
    .read_text()
    .split()
)
V = D["verdict"]
S = V["skip_share"]


def row(c, side, tol=2):
    return D[f"rows_tol{tol}"][side][c]


def factor(c, key, tol=2):
    return row(c, "after", tol)[key] / row(c, "before", tol)[key]


def change(c, key, tol=2):
    return row(c, "after", tol)[key] - row(c, "before", tol)[key]


def pct_lost(f):
    return f"{100 * (1 - f):.1f}%"


def test_the_run_is_the_registered_one():
    assert (
        D["registration"]
        == "docs/preregistration/2026-11-02_seed_heading_confirmation.md"
    )
    assert (D["status"], D["failed"], D["smoke_identical"]) == ("OK", [], True)
    assert D["smoke_cube"] == m.SMOKE
    assert m.VILLA_SHA.startswith(D["villa"])
    assert D["scoring_version"] == 3
    assert D["scrollgt_commit"][:8] in REPORT
    assert D["presence_held_out"] == list(m.PRESENCE_HELD_OUT)
    assert D["data_sha256"] == {
        c: {"nml": n, "image": i} for c, (n, i) in m.DATA_SHA256.items()
    }
    for side in m.SIDES:
        assert (
            sorted(D["rows_tol2"][side])
            == sorted(D["rows_tol4"][side])
            == sorted(m.CUBES)
        )
        assert all(r["tolerance"] == 2.0 for r in D["rows_tol2"][side].values())
        assert all(r["tolerance"] == 4.0 for r in D["rows_tol4"][side].values())
    assert "registered at f7145c5d (PR #330) before any cube was traced" in REPORT


def test_the_verdict_is_the_registered_rule():
    v = m.verdict(D["rows_tol2"], D["records"])
    assert v == V
    assert m.status(D["smoke_identical"], D["failed"], v) == D["status"]
    assert (
        v["decision"],
        v["prediction_P1"],
        v["prediction_P2"],
        v["prediction_P3"],
    ) == (
        "NO_HIGH_SKIP_CUBE",
        True,
        True,
        None,
    )
    assert (v["prediction_P4"], v["prediction_P5"], v["manipulation_ok"]) == (
        False,
        True,
        True,
    )
    assert v["zero_baseline"] == [] and v["high_skip_cubes"] == []
    assert all(D["records"]["after"][c]["no_heading"] == 0 for c in m.CUBES)
    assert "**Status OK; decision `NO_HIGH_SKIP_CUBE`.**" in REPORT
    assert "decision `NO_HIGH_SKIP_CUBE`" in DRAFT


def test_the_headline_figures():
    top = max(S, key=S.get)
    assert top == "s5_15494_04494_02494_512" and f"(the most, {S[top]:.3f})" in REPORT
    worst_prec = min(V["precision_change"].values())
    worst_pen = min(V["erl_merge_penalized_factor"].values())
    assert f"Precision fell by at most {-worst_prec:.3f} (bound {m.P2_DROP})" in REPORT
    assert f"by at most {pct_lost(worst_pen)} (bound {1 - m.P5_PEN:.0%})" in REPORT


def test_the_predictions_table():
    low = V["low_skip_cubes"]
    cov = V["coverage_factor"]
    lo, hi = min(cov[c] for c in low), max(cov[c] for c in low)
    assert f"**held**: {lo:.4f}–{hi:.4f} on the {len(low)} such cubes" in REPORT
    prec = V["precision_change"].values()
    assert f"**held**: −{-min(prec):.3f} to +{max(prec):.3f}" in REPORT
    assert f"**missed**: ρ = {V['spearman_rho']:.2f}" in REPORT
    pen = V["erl_merge_penalized_factor"].values()
    assert f"**held**: {min(pen):.3f}–{max(pen):.3f}" in REPORT
    assert (
        f"coverage factor over the ten is {statistics.median(cov.values()):.4f}"
        in REPORT
    )
    assert V["median_coverage_factor"] == statistics.median(cov.values())


def test_every_cube_row():
    for c in m.CUBES:
        b, a, r = row(c, "before"), row(c, "after"), D["records"]["before"][c]
        held = "yes" if c in m.PRESENCE_HELD_OUT else "no"
        line = (
            f"| {c} | {held} | {r['no_heading']:,} of {r['dots']:,} ({S[c]:.3f}) "
            f"| {b['coverage']:.3f} → {a['coverage']:.3f} | {b['precision']:.3f} → {a['precision']:.3f} "
            f"| {b['erl_merge_penalized']:.2f} → {a['erl_merge_penalized']:.2f} | {b['merges']} → {a['merges']} |"
        )
        assert line in REPORT, line
    same = [c for c, x in D["before_identical_to_after"].items() if x]
    assert same == ["s5_05497_02497_02497_256"] and S[same[0]] == 0
    assert (
        "On `s5_05497_02497_02497_256`, which skipped no dot, `before` and `after` traced the same fibers"
        in REPORT
    )


def test_the_unregistered_observations():
    c = "s5_15494_04494_02494_512"
    assert (
        f"skipped {S[c]:.3f} of its dots and gained {factor(c, 'coverage'):.3f}× coverage"
        in REPORT
    )
    assert f"({factor(c, 'coverage', 4):.3f}× at tolerance 4)" in REPORT
    assert max(V["coverage_factor"].values()) == V["coverage_factor"][c]
    assert max(V["merges_change"].values()) == V["merges_change"][c]
    assert (
        f"{V['merges_change'][c]} more merges and {-change(c, 'precision'):.3f} less precision"
        in REPORT
    )
    assert (
        f"its ERLpen fell {pct_lost(factor(c, 'erl_merge_penalized'))} at tolerance 2"
        in REPORT
    )
    assert (
        f"(it rose {100 * (factor(c, 'erl_merge_penalized', 4) - 1):.1f}% at tolerance 4)"
        in REPORT
    )
    n = "s5_16997_03497_03997_256"
    assert sorted(S.values())[-2] == S[n]
    assert (
        f"skipped {S[n]:.3f} and lost: coverage {factor(n, 'coverage'):.3f}×" in REPORT
    )
    assert (
        f"ERLpen {factor(n, 'erl_merge_penalized'):.3f}×, the lowest of the ten"
        in REPORT
    )
    assert (
        min(V["erl_merge_penalized_factor"].values())
        == V["erl_merge_penalized_factor"][n]
    )


def test_tolerance_4():
    pen4 = {c: factor(c, "erl_merge_penalized", 4) for c in m.CUBES}
    assert (
        f"ERLpen factors run {min(pen4.values()):.3f}–{max(pen4.values()):.3f}"
        in REPORT
    )
    worst = min(pen4, key=pen4.get)
    assert worst == "s5_16997_03497_03997_256"
    assert (
        f"`{worst}` loses {pct_lost(pen4[worst])} ({pen4[worst]:.3f}×), past the 5% bound"
        in REPORT
    )
    assert [c for c in m.CUBES if pen4[c] < m.P5_PEN] == [worst]
    second = sorted(pen4, key=pen4.get)[1]
    assert f"`{second}` loses {pct_lost(pen4[second])}" in REPORT
    prec4 = min(change(c, "precision", 4) for c in m.CUBES)
    assert f"Precision at tolerance 4 falls by at most {-prec4:.4f}" in REPORT
    assert f"one cube lost {pct_lost(pen4[worst])} of ERLpen" in REPORT
    assert f"one cube lost {pct_lost(pen4[worst])} of merge-penalized ERL" in DRAFT
    assert f"At tolerance 4 one cube lost {pct_lost(pen4[worst])}" in STRATEGY


def test_the_draft_and_strategy_say_what_the_rule_allows():
    worst_prec = -min(V["precision_change"].values())
    worst_pen = pct_lost(min(V["erl_merge_penalized_factor"].values()))
    top = max(S.values())
    assert (
        f"precision fell by at most {worst_prec:.3f} and merge-penalized ERL by at most {worst_pen}"
        in DRAFT
    )
    assert (
        f"cost at most {worst_prec:.3f} precision and {worst_pen} of ERLpen on each cube at tolerance 2"
        in STRATEGY
    )
    assert (
        f"the fix cost at most {worst_prec:.3f} precision and {worst_pen} of ERLpen at tolerance 2"
        in REPORT
    )
    assert f"(the most was {top:.2f})" in DRAFT and f"(the most, {top:.3f})" in STRATEGY
    low = V["low_skip_cubes"]
    lo = min(V["coverage_factor"][c] for c in low)
    hi = max(V["coverage_factor"][c] for c in low)
    assert len(low) == 7
    assert (
        f"On the seven cubes that skipped under 2% of their dots, coverage moved by {lo:.4f}–{hi:.4f}×"
        in DRAFT
    )
    assert "Nothing here licenses saying the gain replicated." in REPORT
    assert (
        "so they do not test the coverage gain, which rests on the two Scroll-5 cubes above"
        in DRAFT
    )


def test_the_registration_records_the_run():
    assert "**Status: REGISTERED 2026-11-03.**" in REG
    assert (
        "finding 103, `reports/seed_heading_confirmation.md`. Status OK, decision `NO_HIGH_SKIP_CUBE`"
        in REG
    )
    assert f"(the most, {max(S.values()):.3f})" in REG
    assert f"P4 missed (ρ {V['spearman_rho']:.2f})" in REG


def overlap(a: str, b: str, margin: int) -> list[int]:
    """Voxels two cubes' regions share on each axis, each padded by margin."""
    (a0, a1), (b0, b1) = m.cc.padded_bounds(a, margin), m.cc.padded_bounds(b, margin)
    return [max(0, min(a1[i], b1[i]) - max(a0[i], b0[i])) for i in range(3)]


def test_the_neighbouring_cube_and_the_limits():
    near, f100 = "s5_16997_03497_03997_256", "s5_16997_03997_04497_256"
    assert sorted(overlap(near, f100, m.MARGIN)) == [12, 12, 512]
    assert 0 in overlap(near, f100, 0)
    keep = json.loads((ROOT / "reports/neural_tracer_steep_heading.json").read_text())
    gain = keep["verdict"]["coverage_factor"]["keep"][f100]
    assert (
        f"shares a 12 × 12-voxel column with finding 100's `{f100}`, which gained {gain:.2f}× there; their cubes and "
        "labels do not overlap" in REPORT
    )
    held = [c for c in m.CUBES if c in m.PRESENCE_HELD_OUT]
    assert (len(m.CUBES), len(held), {c[:2] for c in m.CUBES}) == (10, 3, {"s1", "s5"})
    assert "Seven of the ten cubes have in-sample presence" in REPORT
    assert (
        "**Ten cubes, three of them held out from the presence model.** Scroll 1 and Scroll 5 only."
        in REPORT
    )
