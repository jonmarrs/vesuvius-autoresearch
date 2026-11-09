"""reports/afv_generator_block_seams.md (finding 106): every figure from reports/afv_generator_block_seams.json, the
record the chain's verdict step wrote once."""

from __future__ import annotations

import inspect
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "reports/afv_generator_block_seams.json"
REPORT = ROOT / "reports/afv_generator_block_seams.md"
EVIDENCE = ROOT / "reports/evidence/afv_generator_seam_diag_2026-11-07.json"
REGISTRATION = ROOT / "docs/preregistration/2026-11-06_afv_generator_block_seams.md"
STRATEGY = ROOT / "docs/RESEARCH_STRATEGY.md"


def flat(path: Path) -> str:
    return " ".join(path.read_text().split())


def signed(x: float, places: int = 4) -> str:
    return f"{x:+.{places}f}".replace("-", "−")


def record() -> dict:
    return json.loads(RECORD.read_text())


def rows(d: dict) -> list[dict]:
    return [d["cubes"][c]["rows"] for c in bs.HELD_OUT]


def gains(d: dict, arm: str, tol: str) -> list[float]:
    return [bs.gain(r, arm, tol) for r in rows(d)]


def ratios(d: dict, arm: str, variant: str, tol: str) -> list[float]:
    return [
        r[f"{arm}/{variant}"][tol]["erl_merge_penalized"]
        / r["one/main"][tol]["erl_merge_penalized"]
        for r in rows(d)
    ]


def test_the_record_is_the_registered_run_and_its_verdict_recomputes():
    d = record()
    assert sorted(d["cubes"]) == sorted(bs.HELD_OUT)
    # gates 1-3 (identity, model revision, one block unchanged by the patch) all report into identity_problems
    assert all(r["identity_problems"] == [] for r in d["cubes"].values())
    assert len({r["patched_stitch_sha256"] for r in d["cubes"].values()}) == 1
    for r in d["cubes"].values():
        s = r["settings"]
        assert (s["threshold"], s["margin"], s["max_join_angle"], s["min_length"], s["black_distance"]) == (
            60.0, 32, 45.0, 100.0, 16.0)  # fmt: skip
        assert s["revision"] == bs.REVISION and s["villa_main"].startswith("7e6b82164")
        assert (r["size"], r["block"], r["cut_end"]) == (512, 256, 16.0)
    assert bs.verdict(d["cubes"]) == d["verdict"]
    assert d["verdict"]["decision"] == "SUPPORTED"
    assert "**Status OK; decision `SUPPORTED`.**" in flat(REPORT)


def test_the_table_rows():
    d, text = record(), REPORT.read_text()
    for c in bs.HELD_OUT:
        a, b = d["cubes"][c]["rows"]["real/main"], d["cubes"][c]["rows"]["real/patched"]
        x, y = a["crossings"], b["crossings"]
        row = (
            f"| {c} | {a['tol2']['erl_merge_penalized']:.2f} → {b['tol2']['erl_merge_penalized']:.2f} | "
            f"{a['tol4']['erl_merge_penalized']:.2f} → {b['tol4']['erl_merge_penalized']:.2f} | "
            f"{a['tol2']['merges']} → {b['tol2']['merges']} | "
            f"{a['duplicated_share']:.3f} → {b['duplicated_share']:.3f} | "
            f"{x['whole']}/{x['broken']}/{x['lost']} → {y['whole']}/{y['broken']}/{y['lost']} |"
        )
        assert row in text, row


def test_the_summary_figures():
    d, t = record(), flat(REPORT)
    g4, g2 = gains(d, "real", "tol4"), gains(d, "real", "tol2")
    assert (
        f"rises on {sum(g > 0 for g in g4)} of 8 cubes, by a median {statistics.median(g4):.3f} ({min(g4):.3f} to {max(g4):.3f})"
        in t
    )
    assert f"a median {statistics.median(g2):.3f} ({min(g2):.3f} to {max(g2):.3f})" in t
    assert all(g > 0 for g in g2) and "rises on all eight cubes as well" in t
    m_main, m_fix, _ = d["verdict"]["P3_merges_tol2"]
    assert (
        f"from {m_main:,} to {m_fix:,} at tolerance 2 ({signed(100 * (m_fix / m_main - 1), 1)}%"
        in t
    )
    m4 = [
        sum(r[f"real/{v}"]["tol4"]["merges"] for r in rows(d))
        for v in ("main", "patched")
    ]
    assert f"At tolerance 4 they went from {m4[0]:,} to {m4[1]:,}" in t


def test_the_fibers_written_twice():
    d, t = record(), flat(REPORT)
    dup = {
        k: statistics.median(r[k]["duplicated_share"] for r in rows(d))
        for k in ("real/main", "real/patched", "same/main", "same/patched")
    }
    written = {
        k: sum(r[k]["written"] for r in rows(d))
        for k in ("real/main", "real/patched", "one/main")
    }
    assert f"falls from {dup['real/main']:.3f} to {dup['real/patched']:.3f}" in t
    assert (
        f"Arm same falls from {dup['same/main']:.3f} to {dup['same/patched']:.3f}" in t
    )
    assert (f"writes {written['real/main']:,} fibers without the trim and {written['real/patched']:,} with it, against "
            f"{written['one/main']:,} from one block") in t  # fmt: skip


def test_against_one_block():
    d, t = record(), flat(REPORT)
    for arm, variant in (("real", "main"), ("real", "patched"), ("same", "patched")):
        x = ratios(d, arm, variant, "tol4")
        assert f"{min(x):.3f} to {max(x):.3f}" in t, (arm, variant)
    v = d["verdict"]["defect_real_vs_one_tol4"]
    assert all(
        round(a, 4) == v[c]
        for c, a in zip(bs.HELD_OUT, ratios(d, "real", "main", "tol4"), strict=True)
    )
    gap = [
        s - r
        for s, r in zip(
            ratios(d, "same", "patched", "tol4"),
            ratios(d, "real", "patched", "tol4"),
            strict=True,
        )
    ]
    assert (
        f"a median {statistics.median(gap):.3f} of one block's ERLpen ({min(gap):.3f} to {max(gap):.3f})"
        in t
    )
    top = sorted(zip(gap, bs.HELD_OUT, strict=True), reverse=True)[:2]
    assert (
        f"It is largest on {top[0][1]} ({top[0][0]:.3f}) and {top[1][1]} ({top[1][0]:.3f})"
        in t
    )
    assert (
        f"a median {statistics.median(gap):.3f} of it lower, and up to {max(gap):.3f} lower"
        in t
    )


def test_the_costs():
    d, t = record(), flat(REPORT)
    for arm in ("real", "same"):
        lost = [
            sum(r[f"{arm}/{k}"]["crossings"]["lost"] for r in rows(d))
            for k in ("main", "patched")
        ]
        n = sum(sum(r[f"{arm}/main"]["crossings"].values()) for r in rows(d))
        assert f"{lost[0]} to {lost[1]} of {n:,} in arm {arm}" in t, arm
    kinds = {
        v: {
            k: sum(r[f"real/{v}"]["crossings"][k] for r in rows(d))
            for k in ("whole", "broken")
        }
        for v in ("main", "patched")
    }
    assert (f"whole crossings went from {kinds['main']['whole']} to {kinds['patched']['whole']} and broken ones from "
            f"{kinds['main']['broken']} to {kinds['patched']['broken']}") in t  # fmt: skip

    def cov(arm: str, a: str, b: str) -> list[float]:
        return [
            r[f"{arm}/{a}"]["tol4"]["coverage"] - r[b]["tol4"]["coverage"]
            for r in rows(d)
        ]

    assert (
        f"by a median {signed(statistics.median(cov('real', 'patched', 'real/main')))}"
        in t
    )
    over = cov("real", "main", "one/main")
    assert (
        f"a median {signed(statistics.median(over))} more of the hand tracing than one block ({signed(min(over))} to {signed(max(over))})"
        in t
    )
    land = cov("real", "patched", "one/main")
    assert (
        f"a median {signed(statistics.median(land))} from it ({signed(min(land))} to {signed(max(land))})"
        in t
    )
    assert (
        f"already matched one block ({signed(statistics.median(cov('same', 'main', 'one/main')))})"
        in t
    )
    assert (
        f"changes it by a median {signed(statistics.median(cov('same', 'patched', 'same/main')))}"
        in t
    )
    prec = [
        statistics.median(r[k]["tol4"]["precision"] for r in rows(d))
        for k in ("real/main", "real/patched", "one/main")
    ]
    assert (
        f"rises from a median {prec[0]:.4f} to {prec[1]:.4f} (one block: {prec[2]:.4f})"
        in t
    )


def test_the_crossings_are_where_the_one_block_runs_fibers_cross():
    """run() takes the crossings from arm one's main fibers, not from the hand tracing; the report and the villa draft
    say so."""
    src = " ".join(inspect.getsource(bs.run).split())
    assert (
        'if arm == "one" and variant == "main": reference = (fibers, families)' in src
    )
    assert (
        src.count("crossings(") == 1
        and "crossings(reference[0], reference[1], n)" in src
    )
    draft = flat(ROOT / "docs/VILLA_DRAFT_afv_generator_seam_trim.md")
    assert (
        "A crossing is a place where a fiber of arm one (main) crosses a mid-plane"
        in flat(REPORT)
    )
    assert (
        "places where a fiber written from the cube as one block crosses a block face"
        in draft
    )
    assert "hand-traced fiber crosses" not in flat(REPORT) + draft
    # ERLpen is scored on the hand tracing; it does not count the crossings' outcomes (#373 caught "counts both")
    assert "counts both" not in flat(REPORT) + draft
    assert (
        "Merge-penalized ERL is scored against the hand tracing, not at these crossings, and it rises on every cube."
        in draft
    )


def test_the_lost_crossings_diagnosis():
    d, e, t = record(), json.loads(EVIDENCE.read_text()), flat(REPORT)
    assert (
        e["committed_copy_same_syntax_tree"]
        and e["record"] == RECORD.relative_to(ROOT).as_posix()
    )
    assert sorted(e["cubes"]) == sorted(bs.HELD_OUT)
    assert all(
        e["cubes"][c][arm]["reproduces_record"]
        for c in bs.HELD_OUT
        for arm in ("real", "same")
    )
    assert (
        "It reproduced every row's fibers written, written length and crossing counts."
        in t
    )
    n = {
        arm: sum(sum(r[f"{arm}/main"]["crossings"].values()) for r in rows(d))
        for arm in ("real", "same")
    }
    assert all(e["totals"][arm]["n_crossings"] == n[arm] for arm in n)
    real, same = e["totals"]["real"], e["totals"]["same"]
    better, worse = sum(real["better"].values()), sum(real["worse"].values())
    assert (f"In arm real, {better} crossings are better with the trim and {worse} worse (arm same: "
            f"{sum(same['better'].values())} and {sum(same['worse'].values())})") in t  # fmt: skip
    assert (
        f"{real['better_by_join']['chained only with the trim']} of the {better} gain a join: copies that main left apart"
        in t
    )
    join, neither = (
        real["worse_by_join"]["chained only in main"],
        real["worse_by_join"]["chained in neither"],
    )
    assert f"**A join lost:** in {join} of the {worse}, main chained the copies" in t
    reasons = sorted(
        real["reasons_chained_only_in_main"].items(), key=lambda kv: (-kv[1], kv[0])
    )
    assert "; ".join(f"{k} ({v})" for k, v in reasons) + "." in t
    best = real["chained_in_neither_best_share"]
    assert len(best) == neither
    m, p = (statistics.median(b[i] for b in best) for i in (0, 1))
    assert f"**Never chained:** in {neither}, the copies were chained in neither." in t
    assert (
        f"the best written fiber covers a median {p:.3f} of the window, against {m:.3f} without the trim"
        in t
    )
    assert (
        f"In {real['chained_in_neither_neighbour_short']} of them, every copy from the other blocks"
        in t
    )
    rest = worse - join - neither
    assert rest == real["worse_by_join"].get("chained in both", 0) + real[
        "worse_by_join"
    ].get("chained only with the trim", 0)
    assert f"The other {rest} were chained in both or only with the trim." in t
    # per cube: crossings that gain a join (better) and lose one (worse), where whole crossings fall and elsewhere
    gain = {
        c: e["cubes"][c]["real"]["better_by_join"].get("chained only with the trim", 0)
        for c in bs.HELD_OUT
    }
    loss = {
        c: e["cubes"][c]["real"]["worse_by_join"].get("chained only in main", 0)
        for c in bs.HELD_OUT
    }
    whole = {
        c: [
            d["cubes"][c]["rows"][f"real/{v}"]["crossings"]["whole"]
            for v in ("main", "patched")
        ]
        for c in bs.HELD_OUT
    }
    fall = [c for c in bs.HELD_OUT if whole[c][1] < whole[c][0]]
    a, b = sorted(fall, key=lambda c: -loss[c])
    assert (
        f"Whole crossings fall on two cubes, {b} ({whole[b][0]} to {whole[b][1]}) and {a} ({whole[a][0]} to {whole[a][1]})"
        in t
    )
    assert loss[a] == max(loss.values())
    assert (
        f"On {a}, {loss[a]} crossings lose a join, the most of any cube, and {gain[a]} gain one."
        in t
    )
    assert f"On {b}, {loss[b]} lose one and {gain[b]} gain one." in t
    others = [c for c in bs.HELD_OUT if c not in fall]
    g, lo = [gain[c] for c in others], [loss[c] for c in others]
    assert (
        f"On the other six cubes, {min(g)} to {max(g)} gain a join and {min(lo)} to {max(lo)} lose one."
        in t
    )
    assert (
        all(x > 0 for x in gains(d, "real", "tol4"))
        and "ERLpen, scored against the hand tracing and not at these crossings, rises on all eight."
        in t
    )


def test_the_title_registration_line_and_strategy_entry():
    d = record()
    v = d["verdict"]
    g4, g2 = (
        statistics.median(gains(d, "real", "tol4")),
        statistics.median(gains(d, "real", "tol2")),
    )
    assert (round(g4, 4), round(g2, 4)) == (
        v["P2_median_gain_tol4"][0],
        v["P4_median_gain_tol2"][0],
    )
    pct4, pct2 = round(100 * g4), f"{100 * g2:.1f}"
    title = REPORT.read_text().splitlines()[0]
    assert (
        title.startswith("Finding 106:")
        and f"a median {pct4}% at tolerance 4 and {pct2}% at tolerance 2" in title
    )
    assert (
        f"(median held-out gain {g2:.3f} at τ = 2, {g4:.3f} at τ = 4): `{v['decision']}`"
        in flat(REGISTRATION)
    )
    m_main, m_fix, _ = v["P3_merges_tol2"]
    strat = flat(STRATEGY)
    assert f"by a median {pct4}% at tolerance 4 and {pct2}% at tolerance 2" in strat
    assert (
        f"summed merges at tolerance 2 {signed(100 * (m_fix / m_main - 1), 1)}%"
        in strat
    )
    lost = [
        sum(r[f"real/{k}"]["crossings"]["lost"] for r in rows(d))
        for k in ("main", "patched")
    ]
    n = sum(sum(r["real/main"]["crossings"].values()) for r in rows(d))
    assert f"lost ({lost[0]} to {lost[1]} of {n:,})" in strat
    e = json.loads(EVIDENCE.read_text())["totals"]["real"]
    better, worse = sum(e["better"].values()), sum(e["worse"].values())
    assert (f"found that {e['better_by_join']['chained only with the trim']} of the {better} crossings the trim "
            f"improves gain a join, and {e['worse_by_join']['chained only in main']} of the {worse} it worsens lose "
            f"one. At {e['worse_by_join']['chained in neither']} more of those, never chained") in strat  # fmt: skip
