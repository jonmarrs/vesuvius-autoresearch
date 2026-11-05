"""reports/neural_tracer_refit_retry.md (finding 104): every figure from its JSON, the verdict recomputed by the
registered rule, and what the registration, finding 102's report and the strategy say about it."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_refit_retry as m  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_refit_retry.json").read_text())
RAW = (ROOT / "reports/neural_tracer_refit_retry.md").read_text()
REPORT = " ".join(RAW.split())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
F102 = " ".join(
    (ROOT / "reports/neural_tracer_continuity_ceiling.md").read_text().split()
)
REG = " ".join(
    (ROOT / "docs/preregistration/2026-11-02_neural_tracer_refit_retry.md")
    .read_text()
    .split()
)
V = D["verdict"]
G = V["pen_gain"]
HELD, IN = m.HELD, m.IN_SAMPLE


def base(c, tol=2):
    return D[f"baseline_rows_tol{tol}"][c]


def arm(c, a="refit", tol=2):
    return D[f"rows_tol{tol}"][a][c]


def rec(c, a="refit"):
    return D["baseline_records"][c] if a == "base" else D["records"][a][c]


def total(key, cubes, a):
    return sum(rec(c, a)[key] for c in cubes)


def merges(cubes, a="refit", tol=2):
    return sum(arm(c, a, tol)["merges"] - base(c, tol)["merges"] for c in cubes)


def test_the_run_is_the_registered_one():
    assert (
        D["registration"]
        == "docs/preregistration/2026-11-02_neural_tracer_refit_retry.md"
    )
    assert (D["status"], D["failed"], D["smoke_identical"], D["smoke_cube"]) == (
        "OK",
        [],
        True,
        m.SMOKE,
    )
    assert D["baseline_reproduced"] == {c: True for c in m.ALL_CUBES}
    assert D["scrollgt_commit"][:8] in REPORT
    assert sorted(D["rows_tol2"]["refit"]) == sorted(m.ALL_CUBES)
    assert sorted(D["rows_tol2"]["floor"]) == sorted(HELD)
    assert D["ceiling_gain"] == m.ceiling_gains(ROOT / m.CEILING)
    assert "registered at f7145c5d (PR #330) before any arm was traced" in REPORT


def test_the_verdict_is_the_registered_rule():
    v = m.verdict(
        D["rows_tol2"], D["baseline_rows_tol2"], D["records"], D["ceiling_gain"]
    )
    assert v == V
    assert (
        m.status(
            D["smoke_identical"], v, D["failed"], all(D["baseline_reproduced"].values())
        )
        == "OK"
    )
    assert (v["prediction_P1"], v["prediction_P2"], v["prediction_P3"]) == (
        False,
        False,
        True,
    )
    assert v["manipulation_ok"] and v["floor_ok"]
    assert f'The registered reading:** "{v["reading"]}."' in REPORT


def test_the_predictions_table():
    g = [G["refit"][c] for c in HELD]
    assert (
        f"**missed**: {V['median_gain_held']:.3f} (−{-min(g):.3f} to +{max(g):.3f})"
        in REPORT
    )
    mh = V["merges_held"]
    assert (
        f"**missed**: {mh['base']:,} → {mh['refit']:,} (+{mh['refit'] - mh['base']}), against the floor's +{mh['floor'] - mh['base']}"
        in REPORT
    )
    kept = sum(V["precision_change"][c] >= -m.P3_DROP - m.EPS for c in HELD)
    assert kept == 9 and "**held**: on 9 |" in REPORT
    assert (
        f"Its median |ERLpen change| over the held-out cubes is {V['floor_median_abs']:.3f}, below the 0.03 limit"
        in REPORT
    )


def test_the_retry_works():
    cs = {a: total("stop_confidence", HELD, a) for a in ("base", "refit", "floor")}
    assert (
        f"confidence stops fall from {cs['base']:,} to {cs['refit']:,} (−{100 * (1 - cs['refit'] / cs['base']):.0f}%;"
        in REPORT
    )
    by = [
        rec(c)["stop_confidence"] / rec(c, "base")["stop_confidence"] - 1 for c in HELD
    ]
    assert (
        f"−{-max(by) * 100:.0f}% to −{-min(by) * 100:.0f}% by cube), while the floor arm leaves them at {cs['floor']:,}"
        in REPORT
    )
    kv = total("kept_vox", HELD, "refit") / total("kept_vox", HELD, "base") - 1
    assert f"The traces keep {100 * kv:.1f}% more voxels" in REPORT
    cov = [V["coverage_factor"][c] for c in HELD]
    assert min(cov) > 1
    assert (
        f"(a median {statistics.median(cov):.3f}×, {min(cov):.3f}–{max(cov):.3f}×)"
        in REPORT
    )
    assert all(not x for a in ("refit", "floor") for x in D["unchanged"][a].values())


def test_what_it_adds_lies_off_the_reference():
    prec = [V["precision_change"][c] for c in HELD]
    assert max(prec) < 0
    assert (
        f"Precision falls on all ten held-out cubes, by {-max(prec):.3f} to {-min(prec):.3f}"
        in REPORT
    )
    add = sum(arm(c)["pred_length"] - base(c)["pred_length"] for c in HELD)
    on = sum(arm(c)["precision"] * arm(c)["pred_length"] - base(c)["precision"] * base(c)["pred_length"] for c in HELD)  # fmt: skip
    assert f"the refit traces are {round(add):,} longer than the baseline's" in REPORT
    assert (
        f"only {on / add:.3f} of that added length lies within 2 voxels of the reference"
        in REPORT
    )
    bp = [base(c)["precision"] for c in HELD]
    assert (
        f"The baseline's own precision is {min(bp):.3f}–{max(bp):.3f} on these cubes"
        in REPORT
    )
    mg = [arm(c)["merges"] - base(c)["merges"] for c in HELD]
    assert (
        min(mg) > 0 and f"Merges rise on all ten, by {min(mg)} to {max(mg)}" in REPORT
    )
    g = [G["refit"][c] for c in HELD]
    assert f"positive on {sum(x > 0 for x in g)} of the 10 cubes" in REPORT
    share = statistics.median(V["share_of_ceiling"].values())
    assert f"ceiling U on each cube, it is a median {share:.3f}" in REPORT
    assert (
        f"only {on / add:.3f} of the length it added lies on the reference" in STRATEGY
    )


def test_the_one_large_gain_is_half_floor():
    top = max(HELD, key=lambda c: G["refit"][c])
    assert top == "s5_13497_01497_02497_256"
    assert [c for c in HELD if G["refit"][c] >= m.GAIN_BAR] == [top]
    assert (
        f"`{top}` gains {G['refit'][top]:.3f}, the only held-out cube above the bar"
        in REPORT
    )
    fl = G["floor"]
    assert max(HELD, key=lambda c: abs(fl[c])) == top
    assert f"moves the same cube by +{fl[top]:.3f}" in REPORT
    assert sum(abs(G["refit"][c]) < abs(fl[top]) for c in HELD) == 9
    assert (
        "Nine of the ten refit gains are smaller in size than that floor change, the largest of the ten"
        in REPORT
    )


def test_every_cube_row():
    for c in HELD + IN:
        b, r = base(c), arm(c)
        fl = f"{G['floor'][c]:+.3f} | " if c in HELD else ""
        line = (
            f"| {c} | {b['erl_merge_penalized']:.2f} → {r['erl_merge_penalized']:.2f} | {G['refit'][c]:+.3f} | {fl}"
            f"{V['coverage_factor'][c]:.3f}× | {V['precision_change'][c]:+.3f} | {b['merges']} → {r['merges']} "
            f"| {rec(c, 'base')['stop_confidence']:,} → {rec(c)['stop_confidence']:,} |"
        )
        assert line in RAW, line


def test_in_sample_tolerance_4_and_cost():
    assert f"the median gain is {V['median_gain_in_sample']:.3f}" in REPORT
    cs = (
        total("stop_confidence", IN, "refit") / total("stop_confidence", IN, "base") - 1
    )
    assert (
        f"Confidence stops fall by {-100 * cs:.0f}% in total, coverage rises on all 11 cubes"
        in REPORT
    )
    assert min(V["coverage_factor"][c] for c in IN) > 1
    mg = [arm(c)["merges"] - base(c)["merges"] for c in IN]
    assert (
        min(mg) >= 0
        and f"merges rise on {sum(x > 0 for x in mg)} of them and fall on none"
        in REPORT
    )
    g4 = [
        arm(c, tol=4)["erl_merge_penalized"] / base(c, 4)["erl_merge_penalized"] - 1
        for c in HELD
    ]
    assert (
        f"the held-out median ERLpen gain is {statistics.median(g4):.3f} (−{-min(g4):.3f} to +{max(g4):.3f})"
        in REPORT
    )
    assert f"held-out merges rise by {merges(HELD, tol=4)}" in REPORT
    t = {a: total("seconds", HELD, a) for a in ("base", "refit")}
    assert (
        f"took {round(t['refit']):,} s in total against the baseline's {round(t['base']):,} s (+{100 * (t['refit'] / t['base'] - 1):.0f}%)"
        in REPORT
    )


def test_the_registration_finding_102_and_the_strategy_record_it():
    assert "**Status: REGISTERED 2026-11-03.**" in REG
    assert (
        "finding 104, `reports/neural_tracer_refit_retry.md`. Status OK; all 21 baseline rows reproduced"
        in REG
    )
    assert f"floor {V['floor_median_abs']:.3f}" in REG
    assert f"(median held-out gain {V['median_gain_held']:.3f})" in REG
    mh = V["merges_held"]
    assert (
        f"P2 missed (merges +{mh['refit'] - mh['base']} against the floor's +{mh['floor'] - mh['base']})"
        in REG
    )
    assert (
        f"It gains a median {V['median_gain_held']:.3f} and adds merges, so it closes as a continuation rule"
        in F102
    )
    cs = (
        total("stop_confidence", HELD, "refit") / total("stop_confidence", HELD, "base")
        - 1
    )
    assert f"It cut confidence stops by {-100 * cs:.0f}%" in STRATEGY
    assert (
        f"merges rose by {mh['refit'] - mh['base']} against the floor's {mh['floor'] - mh['base']}"
        in STRATEGY
    )
    assert (
        f"the median held-out ERLpen gain is {V['median_gain_held']:.3f} against the 0.10 bar"
        in STRATEGY
    )


def test_the_checks_and_limits_name_what_was_run():
    assert (
        f"All {len(D['baseline_reproduced'])} baseline runs, re-scored with the scorer the arms used"
        in REPORT
    )
    add = round(sum(arm(c)["pred_length"] - base(c)["pred_length"] for c in HELD))
    screen = json.loads(
        (
            ROOT
            / "reports/evidence/neural_tracer_refit_presence_screen_2026-11-03.json"
        ).read_text()
    )
    assert screen["pooled"]["added"] > add
    assert f"so it is larger than the net change of {add:,} above" in REPORT
    # Finding 103 traced ten cubes outside these 21 (its smoke only reproduced one of them), so it developed nothing
    # on them.
    import seed_heading_confirmation as f103

    assert len(m.ALL_CUBES) == 21 and not set(f103.CUBES) & set(m.ALL_CUBES)
    assert "Findings 91–102 developed on these 21 cubes" in REPORT
