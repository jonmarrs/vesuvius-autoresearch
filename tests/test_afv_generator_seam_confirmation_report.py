"""reports/afv_generator_seam_confirmation.md (finding 109): every figure from
reports/afv_generator_seam_confirmation.json, the record the runner's verdict step wrote once, and the Scroll 3
comparison from findings 106's and 108's records."""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_seam_confirmation as sc  # noqa: E402

ROOT = sc.ROOT
RECORD = ROOT / "reports/afv_generator_seam_confirmation.json"
REPORT = ROOT / "reports/afv_generator_seam_confirmation.md"
REGISTRATION = (
    ROOT / "docs/preregistration/2026-11-09_afv_generator_seam_confirmation.md"
)
V = sc.VARIANTS
BIG = tuple(c for c in sc.CUBES if c.endswith("_512"))
SMALL = tuple(c for c in sc.CUBES if c.endswith("_256"))
SEEN = tuple(c for c in sc.CUBES if c not in sc.BASE_MODEL_UNSEEN)


def flat(path: Path = REPORT) -> str:
    return " ".join(path.read_text().split())


def record() -> dict:
    return json.loads(RECORD.read_text())


def rows(cubes=sc.CUBES) -> list[dict]:
    d = record()["cubes"]
    return [d[c]["rows"] for c in cubes]


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%".replace("-", "−")


def med(xs) -> float:
    return statistics.median(xs)


def span(xs) -> str:
    xs = list(xs)
    return f"{pct(med(xs))} ({pct(min(xs))} to {pct(max(xs))})"


def gains(R, a, b, tol):
    return [sc.gain(r, a, b, tol) for r in R]


def section(t: str, start: str, end: str | None = None) -> str:
    part = t.split(start, 1)[1]
    return part.split(end, 1)[0] if end else part


def test_the_verdict_is_the_registered_rule_applied_to_the_record():
    d, t = record(), flat()
    assert d["verdict"] == sc.verdict(d["cubes"])
    assert list(d["cubes"]) == list(sc.CUBES)
    assert f"**Decision `{d['verdict']['decision']}`.**" in t
    for c, r in d["cubes"].items():
        assert r["identity_problems"] == [] and r["cut_end"] == 16.0
        assert (r["size"], r["block"]) == (sc.size_of(c), sc.size_of(c) // 2)
        assert r["data_sha256"] == dict(
            zip(("nml", "image"), sc.DATA_SHA256[c], strict=True)
        )
        assert set(r["rows"]) == {"one/main", *(f"real/{v}" for v in V)}
    for key, shown in (
        ("villa_main", "villa main `{:.9}`"),
        ("revision", "at `{:.8}`"),
    ):
        (value,) = {r["settings"][key] for r in d["cubes"].values()}
        assert shown.format(value) in t, key
    assert {r["settings"]["device"] for r in d["cubes"].values()} == {"cpu"}
    assert "on the CPU at nice 19" in t
    stitch = {r["patched_stitch_sha256"] for r in d["cubes"].values()}
    catalog = {r["patched_catalog_sha256"] for r in d["cubes"].values()}
    assert len(stitch) == 1 and len(catalog) == 1
    d108 = json.loads(sc.RECORD_108.read_text())["cubes"]
    assert stitch == {r["patched_stitch_sha256"] for r in d108.values()}
    assert catalog == {r["patched_catalog_sha256"] for r in d108.values()}
    assert (
        f"sha256 `{stitch.pop()[:8]}…`" in t and f"sha256 `{catalog.pop()[:8]}…`" in t
    )
    hours = sum(sum(r["timing_s"].values()) for r in d["cubes"].values()) / 3600
    assert f"{hours:.1f} hours of prediction over the ten cubes" in t
    s = next(iter(d["cubes"].values()))["settings"]
    assert (
        s["threshold"],
        s["max_join_angle"],
        s["min_length"],
        s["margin"],
    ) == (60.0, 45.0, 100.0, 32)
    assert "(threshold 60, join angle 45°, minimum length 100, margin 32)" in t


def test_the_per_cube_table_is_the_record():
    d, t = record()["cubes"], flat()
    for c in sc.CUBES:
        r = d[c]["rows"]
        e = [r[f"real/{v}"]["tol4"]["erl_merge_penalized"] for v in V]
        m = " → ".join(str(r[f"real/{v}"]["tol2"]["merges"]) for v in V)
        dup = " → ".join(f"{r[f'real/{v}']['duplicated_share']:.3f}" for v in V)
        mark = " †" if c in sc.BASE_MODEL_UNSEEN else ""
        line = (f"| `{c}`{mark} | {d[c]['block']} | {e[0]} | {e[1]} | {e[2]} | "
                f"{pct(sc.gain(r, 'main', 'trim+dup', 'tol4'))} | {pct(sc.gain(r, 'main', 'trim+dup', 'tol2'))} | "
                f"{pct(sc.gain(r, 'trim', 'trim+dup', 'tol4'))} | {m} | {dup} |")  # fmt: skip
        assert line in t, c


def test_the_predictions_table_is_the_verdict():
    v, t = record()["verdict"], flat()
    yes = lambda held: "yes" if held else "no"  # noqa: E731
    p1, p2, p3 = (
        v["P1_both_tol4_up"],
        v["P2_median_gain_tol4"],
        v["P3_merges_tol2"],
    )
    p4, p5 = v["P4_over_trim_tol4_up"], v["P5_median_duplicated_share"]
    assert (f"| P1 (moderate) | both changes: ERLpen at τ = 4 above main's on at least {sc.P1_UP} of 10 cubes | "
            f"{p1[0]} of 10 | {yes(p1[1])} |") in t  # fmt: skip
    assert (f"| P2 (moderate) | median gain of both over main at τ = 4 at least {sc.P2_GAIN:.2f} | {p2[0]} | "
            f"{yes(p2[1])} |") in t  # fmt: skip
    assert (f"| P3 (moderate) | summed merges at τ = 2 with both at most {sc.P3_MERGES} × main's | "
            f"{p3[0][1]} against {p3[0][0]} | {yes(p3[1])} |") in t  # fmt: skip
    assert (f"| P4 (moderate) | ERLpen at τ = 4 with both above the trim's alone on at least {sc.P4_UP} of 10 cubes | "
            f"{p4[0]} of 10 | {yes(p4[1])} |") in t  # fmt: skip
    assert (f"| P5 (high) | median duplicated share with both at most {sc.P5_DUP} × main's | "
            f"{p5[0][1]} against {p5[0][0]} ({p5[0][1] / p5[0][0]:.2f} ×) | {yes(p5[1])} |") in t  # fmt: skip


def test_the_summary_table_is_the_record():
    R, t = rows(), section(flat(), "**Over the ten cubes**", "## The reported splits")

    def total(key, tol=None, arms=V):
        return [
            sum((r[f"real/{v}"][tol] if tol else r[f"real/{v}"])[key] for r in R)
            for v in arms
        ]

    def middle(key, tol=None, fmt=".4f"):
        return [
            format(
                med((r[f"real/{v}"][tol] if tol else r[f"real/{v}"])[key] for r in R),
                fmt,
            )
            for v in V
        ]

    lines = []
    for tol in ("tol2", "tol4"):
        lines.append(
            (
                f"merges, τ = {tol[-1]}, summed",
                *(f"{x:,}" for x in total("merges", tol)),
            )
        )
    lines.append(
        (
            "written length beside a same-family copy, median",
            *middle("duplicated_share", fmt=".3f"),
        )
    )
    one_written = sum(r["one/main"]["written"] for r in R)
    one_length = sum(r["one/main"]["length"] for r in R)
    lines.append(
        (
            f"fibers written, summed (one block: {one_written:,})",
            *(f"{x:,}" for x in total("written")),
        )
    )
    lines.append(
        (
            f"written length, voxels, summed (one block: {round(one_length):,})",
            *(f"{round(x):,}" for x in total("length")),
        )
    )
    x = {
        k: [sum(r[f"real/{v}"]["crossings"][k] for r in R) for v in V]
        for k in ("whole", "broken", "lost")
    }
    n = {sum(x[k][i] for k in x) for i in range(3)}
    (crossings,) = n
    assert crossings == sum(sum(r["one/main"]["crossings"].values()) for r in R)
    lines.append(
        (
            f"face crossings whole / broken / lost, of {crossings}",
            *(f"{x['whole'][i]} / {x['broken'][i]} / {x['lost'][i]}" for i in range(3)),
        )
    )
    for key in ("coverage", "precision"):
        for tol in ("tol4", "tol2"):
            lines.append((f"{key}, τ = {tol[-1]}, median", *middle(key, tol)))
    f = [
        [
            r[f"real/{v}"]["tol4"]["erl_merge_penalized"]
            / r["one/main"]["tol4"]["erl_merge_penalized"]
            for r in R
        ]
        for v in V
    ]
    lines.append(
        (
            "ERLpen at τ = 4 as a fraction of one block's, range (median)",
            *(f"{min(y):.3f} to {max(y):.3f} ({med(y):.3f})" for y in f),
        )
    )
    for name, *cells in lines:
        assert f"| {name} | {' | '.join(cells)} |" in t, name


def test_the_splits_table_is_the_record():
    t = section(flat(), "## The reported splits", "## Reading it")
    groups = (
        ("all", sc.CUBES),
        ("Scroll 1", tuple(c for c in sc.CUBES if c.startswith("s1_"))),
        ("Scroll 5", tuple(c for c in sc.CUBES if c.startswith("s5_"))),
        ("512³, blocks of 256", BIG),
        ("256³, blocks of 128", SMALL),
        ("`BASE_MODEL_UNSEEN`", sc.BASE_MODEL_UNSEEN),
        ("in the base model's training set", SEEN),
    )
    assert [len(g) for _, g in groups] == [10, 3, 7, 4, 6, 3, 7]
    for name, cubes in groups:
        R = rows(cubes)
        cells = [
            gains(R, "main", "trim+dup", "tol4"),
            gains(R, "main", "trim+dup", "tol2"),
            gains(R, "main", "trim", "tol4"),
            gains(R, "trim", "trim+dup", "tol4"),
        ]
        assert all(x > 0 for cell in cells for x in cell), name
        m = [sum(r[f"real/{v}"]["tol2"]["merges"] for r in R) for v in ("main", "trim+dup")]  # fmt: skip
        line = f"| {name} | {len(R)} | {' | '.join(span(c) for c in cells)} | {m[0]} → {m[1]} |"
        assert line in t, name
    assert "Every cube rose in every row." in t


def test_the_headline_is_the_record():
    v, head = record()["verdict"], REPORT.read_text().splitlines()[0]
    g = gains(rows(), "main", "trim+dup", "tol4")
    big = gains(rows(BIG), "main", "trim+dup", "tol4")
    m = v["P3_merges_tol2"][0]
    cov = [
        r["real/trim+dup"][tol]["coverage"] < r["real/main"][tol]["coverage"]
        for r in rows()
        for tol in ("tol4", "tol2")
    ]
    assert head.startswith("Finding 109: ") and head.endswith("(2026-11-10)")
    assert f"on {v['P1_both_tol4_up'][0]} of 10, by a median {pct(med(g))} at tolerance 4" in head  # fmt: skip
    assert f"({pct(med(big))} on the four cubes at Scroll 3's block size)" in head
    assert f"merges at tolerance 2 {m[0]} → {m[1]}" in head
    assert all(cov) and "coverage down on every cube" in head


def test_like_with_like_is_the_records():
    t = section(flat(), "## Reading it", "## What it cannot say")
    big = gains(rows(BIG), "main", "trim+dup", "tol4")
    d106 = json.loads(sc.RECORD_106.read_text())["cubes"]
    d108 = json.loads(sc.RECORD_108.read_text())["cubes"]
    s3 = [
        d108[c]["rows"]["trim+dup"]["tol4"]["erl_merge_penalized"]
        / d106[c]["rows"]["real/main"]["tol4"]["erl_merge_penalized"]
        - 1
        for c in bs.HELD_OUT
    ]
    assert {d108[c]["block"] for c in bs.HELD_OUT} == {256}
    assert (f"raise their ERLpen at τ = 4 by a median {span(big)}; on Scroll 3 the median was {span(s3)}") in t  # fmt: skip
    assert f"The ten-cube median, {pct(med(gains(rows(), 'main', 'trim+dup', 'tol4')))}, is carried by" in t  # fmt: skip
    dup = [
        med(r["real/main"]["duplicated_share"] for r in rows(g)) for g in (SMALL, BIG)
    ]
    assert f"their median written-twice share on main is {dup[0]:.3f}, against {dup[1]:.3f} on the 512³ cubes" in t  # fmt: skip


def test_the_duplicate_and_one_block_figures_are_the_record():
    R, t = rows(), section(flat(), "## Reading it", "## What it cannot say")
    v = record()["verdict"]["P5_median_duplicated_share"][0]
    one = max(r["one/main"]["duplicated_share"] for r in R)
    ratio = [
        r["real/trim+dup"]["duplicated_share"] / r["real/main"]["duplicated_share"]
        for r in R
    ]
    assert f"a median {v[0]:.3f} of the written length" in t
    assert f"no cube has more than {one}" in t
    assert f"With both changes the median is {v[1]:.3f}" in t
    assert f"falls to between {min(ratio):.2f} and {max(ratio):.2f} of its share on main" in t  # fmt: skip

    def frac(r, v_):
        return (
            r[f"real/{v_}"]["tol4"]["erl_merge_penalized"]
            / r["one/main"]["tol4"]["erl_merge_penalized"]
        )

    at_least = {v_: sum(frac(r, v_) >= 1 for r in R) for v_ in V}
    assert at_least["main"] == 0
    assert f"on {at_least['trim+dup']} of 10 cubes (main: none of 10)" in t
    worst = min(sc.CUBES, key=lambda c: frac(record()["cubes"][c]["rows"], "trim+dup"))
    w = record()["cubes"][worst]["rows"]
    assert f"**The exception is `{worst}`:** {frac(w, 'trim+dup'):.3f} of one block's ERLpen with both changes (main {frac(w, 'main'):.3f})" in t  # fmt: skip
    below = [
        c
        for c in sc.CUBES
        if all(
            record()["cubes"][c]["rows"][f"real/{v_}"]["tol4"]["coverage"]
            < record()["cubes"][c]["rows"]["one/main"]["tol4"]["coverage"]
            for v_ in V
        )
    ]
    assert below == [worst]
    assert (f"({w['real/trim+dup']['tol4']['coverage']:.3f} against {w['one/main']['tol4']['coverage']:.3f} "
            f"at τ = 4 with both)") in t  # fmt: skip


def test_the_costs_are_the_record():
    R, t = rows(), section(flat(), "## Reading it", "## What it cannot say")

    def cov(r, v_, tol):
        return r[v_][tol]["coverage"]

    loss = {
        tol: [1 - cov(r, "real/trim+dup", tol) / cov(r, "real/main", tol) for r in R]
        for tol in ("tol4", "tol2")
    }
    assert all(x > 0 for xs in loss.values() for x in xs)
    assert (f"below main's on 10 of 10 cubes at both tolerances, by a median {100 * med(loss['tol4']):.1f}% at τ = 4 "
            f"({100 * min(loss['tol4']):.1f}% to {100 * max(loss['tol4']):.1f}%) and "
            f"{100 * med(loss['tol2']):.1f}% at τ = 2") in t  # fmt: skip
    main_over_one = sum(
        cov(r, "real/main", "tol4") > cov(r, "one/main", "tol4") for r in R
    )
    diff = [cov(r, "real/trim+dup", "tol4") - cov(r, "one/main", "tol4") for r in R]
    assert f"Main's coverage was above the one-block run's on {main_over_one} of 10 cubes" in t  # fmt: skip
    assert sum(x > 0 for x in diff) == 9
    assert f"by {min(diff):+.3f} to {max(diff):+.3f} at τ = 4".replace("-", "−") in t
    up = {
        tol: sum(cov(r, "real/trim+dup", tol) > cov(r, "real/trim", tol) for r in R)
        for tol in ("tol4", "tol2")
    }
    assert f"above the trim's on {up['tol4']} of 10 at τ = 4 and on {up['tol2']} of 10 at τ = 2" in t  # fmt: skip
    p = {
        tol: [
            r["real/trim+dup"][tol]["precision"] - r["real/main"][tol]["precision"]
            for r in R
        ]
        for tol in ("tol4", "tol2")
    }
    assert (f"at τ = 2 rose on {sum(x > 0 for x in p['tol2'])} of 10 over main, by {min(p['tol2']):.3f} to "
            f"{max(p['tol2']):.3f}. At τ = 4 it rose on {sum(x > 0 for x in p['tol4'])} of 10, by at most "
            f"{max(p['tol4']):.3f}; the tenth fell {-min(p['tol4']):.4f}") in t  # fmt: skip


def test_the_merges_and_crossings_are_the_record():
    d, R, t = (
        record()["cubes"],
        rows(),
        section(flat(), "## Reading it", "## What it cannot say"),
    )

    def merges(r, v_, tol):
        return r[f"real/{v_}"][tol]["merges"]

    m4 = [merges(r, "trim+dup", "tol4") - merges(r, "main", "tol4") for r in R]
    m2 = [merges(r, "trim+dup", "tol2") - merges(r, "main", "tol2") for r in R]
    t4 = [sum(merges(r, v_, "tol4") for r in R) for v_ in ("main", "trim+dup")]
    assert all(x < 0 for x in m4)
    (same,) = [c for c, x in zip(sc.CUBES, m2, strict=True) if x == 0]
    assert sum(x < 0 for x in m2) == 9
    assert (f"fell on every cube at τ = 4 ({t4[0]} → {t4[1]}) and on 9 of 10 at τ = 2, where the tenth was "
            f"unchanged at {merges(d[same]['rows'], 'main', 'tol2')}") in t  # fmt: skip
    over_trim = {
        c: merges(d[c]["rows"], "trim+dup", "tol2")
        - merges(d[c]["rows"], "trim", "tol2")
        for c in sc.CUBES
    }
    rose = {c: x for c, x in over_trim.items() if x > 0}
    assert rose == {"s1_02494_01494_03994_512": 2, same: 1}
    a = d["s1_02494_01494_03994_512"]["rows"]
    assert (f"`s1_02494_01494_03994_512` gained 2 merges at τ = 2 ({merges(a, 'trim', 'tol2')} → "
            f"{merges(a, 'trim+dup', 'tol2')}) and `{same}` gained 1") in t  # fmt: skip
    x = {
        k: [sum(r[f"real/{v_}"]["crossings"][k] for r in R) for v_ in V]
        for k in ("whole", "broken", "lost")
    }
    total = sum(x[k][0] for k in x)
    assert (f"of the {total} places where a fiber of the cube run as one block crosses a block face, both changes "
            f"make {x['whole'][2]} whole, {x['broken'][2]} broken and {x['lost'][2]} lost, against main's "
            f"{x['whole'][0]} / {x['broken'][0]} / {x['lost'][0]}") in t  # fmt: skip
    assert x["lost"][2] > x["lost"][0] and "but more are lost than on main" in t
    g = {c: sc.gain(d[c]["rows"], "main", "trim+dup", "tol4") for c in sc.BASE_MODEL_UNSEEN}  # fmt: skip
    assert "rose " + ", ".join(pct(v_) for v_ in sorted(g.values())[:2]) + f" and {pct(max(g.values()))} at τ = 4" in t  # fmt: skip
    every = {c: sc.gain(d[c]["rows"], "main", "trim+dup", "tol4") for c in sc.CUBES}
    lowest = min(every, key=every.get)
    assert lowest in sc.BASE_MODEL_UNSEEN and f"(`{lowest}`, whose ERLpen is also the lowest on every arm)" in t  # fmt: skip
    for v_ in V:
        assert lowest == min(
            sc.CUBES,
            key=lambda c: d[c]["rows"][f"real/{v_}"]["tol4"]["erl_merge_penalized"],
        )


def test_what_it_cannot_say_matches_the_cubes():
    t = section(flat(), "## What it cannot say", "## Records")
    d = record()["cubes"]
    blocks = [d[c]["block"] for c in sc.CUBES]
    assert (blocks.count(256), blocks.count(128)) == (len(BIG), len(SMALL)) == (4, 6)
    assert "Four are at 256 and six at 128." in t
    assert len(SEEN) == 7 and "**Seven cubes are in the base model's training set.**" in t  # fmt: skip
    assert "**Nothing about reading.**" in t


def test_the_files_it_points_to_exist():
    for rel in re.findall(
        r"`((?:scripts|docs|reports|repro|tests)/[^`]+)`", REPORT.read_text()
    ):
        assert (ROOT / rel).exists(), rel


def carried_line() -> str:
    v = record()["verdict"]
    g = gains(rows(), "main", "trim+dup", "tol4")
    big = gains(rows(BIG), "main", "trim+dup", "tol4")
    m, dup = v["P3_merges_tol2"][0], v["P5_median_duplicated_share"][0]
    return (f"(ERLpen at τ = 4 above main's on {v['P1_both_tol4_up'][0]} of 10, median {pct(med(g))}, and "
            f"{pct(med(big))} on the four cubes at blocks of 256; above the trim's alone on "
            f"{v['P4_over_trim_tol4_up'][0]} of 10; merges at τ = 2 {m[0]} → {m[1]}; median duplicated share "
            f"{dup[0]:.3f} → {dup[1]:.3f}): `{v['decision']}`")  # fmt: skip


def test_the_registration_and_the_strategy_carry_the_verdict():
    line = carried_line()
    assert line in flat(REGISTRATION)
    strategy = flat(ROOT / "docs/RESEARCH_STRATEGY.md")
    assert line in strategy
    assert "was running at this review and is not reported here" not in strategy
    loss = [
        1 - r["real/trim+dup"]["tol4"]["coverage"] / r["real/main"]["tol4"]["coverage"]
        for r in rows()
    ]
    assert f"Coverage at τ = 4 is below main's on all ten, by a median {100 * med(loss):.1f}%" in strategy  # fmt: skip
