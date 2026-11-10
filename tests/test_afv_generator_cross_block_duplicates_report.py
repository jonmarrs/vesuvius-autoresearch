"""reports/afv_generator_cross_block_duplicates.md (finding 108): every figure from
reports/afv_generator_cross_block_duplicates.json, the record the runner's verdict step wrote once, and the gate's
comparisons from findings 106's and 107's records."""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_cross_block_duplicates as xd  # noqa: E402

ROOT = xd.ROOT
RECORD = ROOT / "reports/afv_generator_cross_block_duplicates.json"
REPORT = ROOT / "reports/afv_generator_cross_block_duplicates.md"
RECORD_106 = ROOT / "reports/afv_generator_block_seams.json"
RECORD_107 = ROOT / "reports/afv_generator_default_zone.json"
REGISTRATION = (
    ROOT / "docs/preregistration/2026-11-09_afv_generator_cross_block_duplicates.md"
)
V = xd.VARIANTS


def flat(path: Path = REPORT) -> str:
    return " ".join(path.read_text().split())


def record() -> dict:
    return json.loads(RECORD.read_text())


def rows(cubes=bs.HELD_OUT) -> list[dict]:
    d = record()["cubes"]
    return [d[c]["rows"] for c in cubes]


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%".replace("-", "−")


def med(xs) -> float:
    return statistics.median(xs)


def section(t: str, start: str, end: str | None = None) -> str:
    part = t.split(start, 1)[1]
    return part.split(end, 1)[0] if end else part


def test_the_verdict_is_the_registered_rule_applied_to_the_record():
    d, t = record(), flat()
    assert d["verdict"] == xd.verdict(d["cubes"])
    assert list(d["cubes"]) == list(bs.HELD_OUT)
    assert f"decision `{d['verdict']['decision']}`" in t
    for c, r in d["cubes"].items():
        assert r["identity_problems"] == [] and r["cut_end"] == 16.0
        assert (r["size"], r["block"]) == (512, 256)
        assert r["villa_main"] == "7e6b82164d014ed485aa027011f31070923fc0a9"
        assert set(r["rows"]) == set(V)
    stitch = {r["patched_stitch_sha256"] for r in d["cubes"].values()}
    catalog = {r["patched_catalog_sha256"] for r in d["cubes"].values()}
    assert len(stitch) == 1 and len(catalog) == 1
    assert (
        f"sha256 `{stitch.pop()[:8]}…`" in t and f"sha256 `{catalog.pop()[:8]}…`" in t
    )


def test_the_trim_arm_is_finding_106s_row_on_every_cube_and_107s_on_the_zone():
    d, d106 = record(), json.loads(RECORD_106.read_text())
    for c in bs.HELD_OUT:
        assert d["cubes"][c]["rows"]["trim"] == d106["cubes"][c]["rows"]["real/patched"]
    z, f107 = d["zone"], json.loads(RECORD_107.read_text())["result"]
    assert z["identity_problems"] == [] and (z["cube"], z["zone"], z["block"]) == (
        xd.DIAGNOSED,
        1024,
        512,
    )
    assert z["rows"]["trim"] == f107["rows"]["patched"]


def test_the_per_cube_table_is_the_record():
    d, t = record()["cubes"], flat()
    for c in bs.HELD_OUT:
        a, b = d[c]["rows"]["trim"], d[c]["rows"]["trim+dup"]
        g4, g2 = xd.gain(d[c]["rows"], "tol4"), xd.gain(d[c]["rows"], "tol2")
        line = (f"| `{c}` | {a['tol4']['erl_merge_penalized']} | {b['tol4']['erl_merge_penalized']} | {pct(g4)} | "
                f"{pct(g2)} | {a['tol2']['merges']} → {b['tol2']['merges']} | "
                f"{a['duplicated_share']:.3f} → {b['duplicated_share']:.3f} |")  # fmt: skip
        assert line in t, c


def summary_lines(R: list[dict]) -> list[tuple[str, str, str]]:
    def total(key, tol=None):
        return [sum((r[v][tol] if tol else r[v])[key] for r in R) for v in V]

    def middle(key, tol=None, fmt=".4f"):
        return [
            format(med((r[v][tol] if tol else r[v])[key] for r in R), fmt) for v in V
        ]

    out = []
    for tol in ("tol2", "tol4"):
        m = total("merges", tol)
        out.append((f"merges, τ = {tol[-1]}, summed", f"{m[0]:,}", f"{m[1]:,}"))
    out.append(
        (
            "written length beside a same-family copy, median",
            *middle("duplicated_share", fmt=".3f"),
        )
    )
    w, length = total("written"), total("length")
    out.append(("fibers written, summed", f"{w[0]:,}", f"{w[1]:,}"))
    out.append(
        (
            "written length, voxels, summed",
            f"{round(length[0]):,}",
            f"{round(length[1]):,}",
        )
    )
    x = {
        k: [sum(r[v]["crossings"][k] for r in R) for v in V]
        for k in ("whole", "broken", "lost")
    }
    out.append(("face crossings whole / broken / lost", *(f"{x['whole'][i]:,} / {x['broken'][i]} / {x['lost'][i]}"
                                                         for i in (0, 1))))  # fmt: skip
    for key in ("coverage", "precision"):
        for tol in ("tol4", "tol2"):
            out.append((f"{key}, τ = {tol[-1]}, median", *middle(key, tol)))
    return out


def test_the_summary_table_is_the_record():
    t = section(flat(), "**Over the eight cubes**", "| prediction |")
    for name, x, y in summary_lines(rows()):
        assert f"| {name} | {x} | {y} |" in t, name


def test_the_predictions_table_is_the_verdict():
    v, t = record()["verdict"], flat()
    p1, p2, p3, p4 = (
        v[k]
        for k in (
            "P1_tol4_up",
            "P2_median_gain_tol4",
            "P3_merges_tol2",
            "P4_median_duplicated_share",
        )
    )
    yes = lambda held: "yes" if held else "no"  # noqa: E731
    assert (
        f"| P1 (moderate) | ERLpen at τ = 4 higher with the change on at least 6 of 8 cubes | {p1[0]} of 8 | {yes(p1[1])} |"
        in t
    )
    assert (
        f"| P2 (moderate) | median gain at τ = 4 at least 0.03 | {p2[0]} | {yes(p2[1])} |"
        in t
    )
    assert (f"| P3 (moderate) | summed merges at τ = 2 at most 1.05 × the trim's | {p3[0][1]} against {p3[0][0]} | "
            f"{yes(p3[1])} |") in t  # fmt: skip
    assert (f"| P4 (high) | median duplicated share at most 0.7 × the trim's | {p4[0][1]} against {p4[0][0]} "
            f"({p4[0][1] / p4[0][0]:.2f} ×) | {yes(p4[1])} |") in t  # fmt: skip


def test_the_headline_is_the_record():
    v, R = record()["verdict"], rows()
    head = REPORT.read_text().splitlines()[0]
    g4 = [xd.gain(r, "tol4") for r in R]
    dup = v["P4_median_duplicated_share"][0]
    assert head.startswith("Finding 108: ")
    assert f"on {v['P1_tol4_up'][0]} of 8 held-out cubes" in head
    assert f"by a median {pct(med(g4))} at tolerance 4" in head
    assert f"from {dup[0]:.3f} to {dup[1]:.3f}" in head


def test_the_gains_and_their_ranges_are_the_record():
    t = flat()
    for tol, tau in (("tol4", "4"), ("tol2", "2")):
        g = [xd.gain(r, tol) for r in rows()]
        assert (f"at τ = {tau}, up on {sum(x > 0 for x in g)} of 8, by a median {pct(med(g))} "
                f"({pct(min(g))} to {pct(max(g))})") in t  # fmt: skip
    up = {
        tol: sum(
            r["trim+dup"][tol]["coverage"] > r["trim"][tol]["coverage"] for r in rows()
        )
        for tol in ("tol4", "tol2")
    }

    def change(key: str) -> list[float]:
        return [
            r["trim+dup"][tol][key] - r["trim"][tol][key]
            for r in rows()
            for tol in ("tol4", "tol2")
        ]

    assert (f"Coverage rose on {up['tol4']} of 8 at τ = 4 and on {up['tol2']} of 8 at τ = 2, by at most "
            f"{max(change('coverage')):.3f}. Precision moved by at most {max(map(abs, change('precision'))):.4f} either way") in t  # fmt: skip
    m = [r["trim+dup"]["tol2"]["merges"] - r["trim"]["tol2"]["merges"] for r in rows()]
    (rose,) = [c for c, x in zip(bs.HELD_OUT, m, strict=True) if x > 0]
    a, b = (
        record()["cubes"][rose]["rows"]["trim"],
        record()["cubes"][rose]["rows"]["trim+dup"],
    )
    assert (f"Merges at τ = 2 fell on {['zero', 'one', 'two', 'three', 'four', 'five'][sum(x < 0 for x in m)]} cubes, held on "
            f"{['zero', 'one', 'two', 'three', 'four'][sum(x == 0 for x in m)]} and rose by {max(m)} on one (`{rose}`, "
            f"{a['tol2']['merges']} → {b['tol2']['merges']})") in t  # fmt: skip


def test_the_seven_cubes_without_the_diagnosed_one_are_the_record():
    seven = [c for c in bs.HELD_OUT if c != xd.DIAGNOSED]
    R, t = rows(seven), section(flat(), "**Without `" + xd.DIAGNOSED + "`")
    g4, g2 = [xd.gain(r, "tol4") for r in R], [xd.gain(r, "tol2") for r in R]
    m = [sum(r[v]["tol2"]["merges"] for r in R) for v in V]
    d = [med(r[v]["duplicated_share"] for r in R) for v in V]
    assert len(R) == 7
    assert (
        f"up on {sum(x > 0 for x in g4)} of 7 at τ = 4, by a median {pct(med(g4))}" in t
    )
    assert f"and {pct(med(g2))} at τ = 2" in t
    assert (
        f"merges at τ = 2 {m[0]} → {m[1]}" in t
        and f"median duplicated share {d[0]:.3f} → {d[1]:.3f}" in t
    )


def test_the_zone_table_is_the_record():
    z, t = (
        record()["zone"]["rows"],
        section(flat(), "## The 1024³ zone", "## Reading it"),
    )
    a, b = z["trim"], z["trim+dup"]
    lines = [
        ("fibers written", f"{a['zone']['written']:,}", f"{b['zone']['written']:,}"),
        ("written length, voxels", f"{round(a['zone']['length']):,}", f"{round(b['zone']['length']):,}"),
        ("written length beside a same-family copy", f"{a['zone']['duplicated_share']:.3f}",
         f"{b['zone']['duplicated_share']:.3f}"),
        ("fibers written inside the cube", f"{a['cube']['written_inside']:,}", f"{b['cube']['written_inside']:,}"),
        ("written length beside a same-family copy, inside the cube", f"{a['cube']['duplicated_share']:.3f}",
         f"{b['cube']['duplicated_share']:.3f}"),
    ]  # fmt: skip
    for tol in ("tol4", "tol2"):
        e, x, y = f"τ = {tol[-1]}", a["cube"][tol], b["cube"][tol]
        g = y["erl_merge_penalized"] / x["erl_merge_penalized"] - 1
        lines += [
            (f"merge-penalized ERL, {e}", f"{x['erl_merge_penalized']}", f"{y['erl_merge_penalized']} ({pct(g)})"),
            (f"merges, {e}", f"{x['merges']}", f"{y['merges']}"),
            (f"coverage, {e}", f"{x['coverage']:.4f}", f"{y['coverage']:.4f}"),
            (f"precision, {e}", f"{x['precision']:.4f}", f"{y['precision']:.4f}"),
        ]  # fmt: skip
    for name, x, y in lines:
        assert f"| {name} | {x} | {y} |" in t, name


def test_the_zone_against_main_is_finding_107s_record():
    z, t = record()["zone"]["rows"]["trim+dup"], flat()
    m = json.loads(RECORD_107.read_text())["result"]["rows"]["main"]
    g = [
        z["cube"][tol]["erl_merge_penalized"] / m["cube"][tol]["erl_merge_penalized"]
        - 1
        for tol in ("tol4", "tol2")
    ]
    assert (f"cut the zone's written length beside a same-family copy from main's {m['zone']['duplicated_share']:.3f} "
            f"to {z['zone']['duplicated_share']:.3f}") in t  # fmt: skip
    assert f"raise ERLpen {pct(g[0])} at τ = 4 and {pct(g[1])} at τ = 2 over main" in t
    assert (
        f"merges at τ = 2 {m['cube']['tol2']['merges']} → {z['cube']['tol2']['merges']}"
        in t
    )
    p = json.loads(RECORD_107.read_text())["result"]["rows"]["patched"]
    c = [
        -(x["cube"]["tol4"]["coverage"] / m["cube"]["tol4"]["coverage"] - 1)
        for x in (z, p)
    ]
    assert (
        f"Coverage at τ = 4 stays {100 * c[0]:.1f}% below main's (finding 107: {100 * c[1]:.1f}% below"
        in t
    )


def test_the_files_it_points_to_exist():
    for rel in re.findall(
        r"`((?:scripts|docs|reports|repro|tests)/[^`]+)`", REPORT.read_text()
    ):
        assert (ROOT / rel).exists(), rel


def test_the_registration_and_the_strategy_carry_the_verdict():
    v, R = record()["verdict"], rows()
    g4 = med(xd.gain(r, "tol4") for r in R)
    m, dup = v["P3_merges_tol2"][0], v["P4_median_duplicated_share"][0]
    line = (f"(ERLpen at τ = 4 up on {v['P1_tol4_up'][0]} of 8, median {pct(g4)}; merges at τ = 2 {m[0]} → {m[1]}; "
            f"median duplicated share {dup[0]:.3f} → {dup[1]:.3f}): `{v['decision']}`")  # fmt: skip
    assert line in flat(REGISTRATION)
    strategy = flat(ROOT / "docs/RESEARCH_STRATEGY.md")
    assert line in strategy
    d, d106 = record()["cubes"], json.loads(RECORD_106.read_text())["cubes"]
    erl = lambda c, rows_, k: rows_[c]["rows"][k]["tol4"]["erl_merge_penalized"]  # noqa: E731
    both = [erl(c, d, "trim+dup") / erl(c, d106, "one/main") for c in bs.HELD_OUT]
    main = [erl(c, d106, "real/main") / erl(c, d106, "one/main") for c in bs.HELD_OUT]
    assert (f"eight blocks reach {min(both):.3f} to {max(both):.3f} of one block's ERLpen at tolerance 4 "
            f"(main: {min(main):.3f} to {max(main):.3f})") in strategy  # fmt: skip


def test_the_comparisons_with_main_and_one_block_are_finding_106s_record():
    d, d106, t = record()["cubes"], json.loads(RECORD_106.read_text())["cubes"], flat()
    both = {c: d[c]["rows"]["trim+dup"] for c in bs.HELD_OUT}
    main = {c: d106[c]["rows"]["real/main"] for c in bs.HELD_OUT}
    one = {c: d106[c]["rows"]["one/main"] for c in bs.HELD_OUT}
    erl = lambda r, tol="tol4": r[tol]["erl_merge_penalized"]  # noqa: E731
    g = {
        tol: [erl(both[c], tol) / erl(main[c], tol) - 1 for c in bs.HELD_OUT]
        for tol in ("tol4", "tol2")
    }
    assert all(x > 0 for x in g["tol4"] + g["tol2"])
    assert (f"over main, by a median {pct(med(g['tol4']))} at τ = 4 ({pct(min(g['tol4']))} to {pct(max(g['tol4']))}) "
            f"and {pct(med(g['tol2']))} at τ = 2") in t  # fmt: skip
    m = (
        sum(main[c]["tol2"]["merges"] for c in bs.HELD_OUT),
        sum(both[c]["tol2"]["merges"] for c in bs.HELD_OUT),
    )
    assert f"merges at τ = 2 {m[0]} → {m[1]}" in t
    for name, rows_ in (
        ("main", main),
        ("the trim", {c: d[c]["rows"]["trim"] for c in bs.HELD_OUT}),
        ("both", both),
    ):
        f = [erl(rows_[c]) / erl(one[c]) for c in bs.HELD_OUT]
        assert f"{name}, {min(f):.3f} to {max(f):.3f}" in t, name
    cov = [
        both[c]["tol4"]["coverage"] - one[c]["tol4"]["coverage"] for c in bs.HELD_OUT
    ]
    assert (
        f"within {min(cov):+.3f} to {max(cov):+.3f} of one block's".replace("-", "−")
        in t
    )
    x = {
        k: [sum(r[c]["crossings"][k] for c in bs.HELD_OUT) for r in (main, both)]
        for k in ("whole", "broken", "lost")
    }
    assert (f"against main's {x['whole'][0]} / {x['broken'][0]} / {x['lost'][0]}") in t
    assert sum(x[k][0] for k in x) == sum(x[k][1] for k in x) == 1304 and "1,304" in t


def test_the_dev_screen_s_proportion_is_its_evidence():
    e = json.loads(
        (
            ROOT
            / "reports/evidence/afv_generator_cross_block_duplicates_dev_2026-11-09.json"
        ).read_text()
    )
    r = e["dev_screen"]["rows"].values()
    dev = [med(x[v]["dup_share"] for x in r) for v in ("E16", "E16P")]
    held = record()["verdict"]["P4_median_duplicated_share"][0]
    t = flat()
    assert (
        f"the dev screen's {dev[0]:.3f} → {dev[1]:.3f} ({dev[1] / dev[0]:.2f} ×)" in t
    )
    assert f"({held[1] / held[0]:.2f} ×)" in t


def test_the_reading_s_other_figures_are_the_records():
    t, d106 = flat(), json.loads(RECORD_106.read_text())["cubes"]
    one = max(d106[c]["rows"]["one/main"]["duplicated_share"] for c in bs.HELD_OUT)
    held = record()["verdict"]["P4_median_duplicated_share"][0]
    assert (
        f"the held-out cubes' median written-twice share is {held[1]:.3f}; run as one block, the same cubes have at most {one}"
        in t
    )
    e = json.loads(
        (
            ROOT
            / "reports/evidence/afv_generator_cross_block_duplicates_dev_2026-11-09.json"
        ).read_text()
    )
    dev = med(x["E16"]["dup_share"] for x in e["dev_screen"]["rows"].values())
    assert f"({held[0]:.3f} against {dev:.3f})" in t
    lost = [sum(r[v]["crossings"]["lost"] for r in rows()) for v in V]
    assert f"Lost crossings fall by {lost[0] - lost[1]} net" in t
    diag = json.loads(
        (ROOT / "reports/evidence/afv_generator_seam_diag_2026-11-07.json").read_text()
    )["totals"]["real"]
    joins, reasons = diag["worse_by_join"], diag["reasons_chained_only_in_main"]
    n = joins["chained only in main"]
    assert (f"{reasons['one copy lies along the other, but the catalogue keeps both']} of the {n} joins main made that "
            f"the trimmed copies miss had one copy lying along the other while the catalogue kept both") in t  # fmt: skip
    assert (f"shorter than `MIN_OVERLAP` ({reasons['the overlap is shorter than 24 voxels']} of the {n}) and the "
            f"{joins['chained in neither']} crossings never chained") in t  # fmt: skip
