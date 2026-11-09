"""reports/afv_generator_default_zone.md (finding 107): every figure from reports/afv_generator_default_zone.json, the
record the runner's verdict step wrote once, and finding 106's from its own record."""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_default_zone as dz  # noqa: E402

ROOT = dz.ROOT
RECORD = ROOT / "reports/afv_generator_default_zone.json"
REPORT = ROOT / "reports/afv_generator_default_zone.md"
RECORD_106 = ROOT / "reports/afv_generator_block_seams.json"


def flat() -> str:
    return " ".join(REPORT.read_text().split())


def record() -> dict:
    return json.loads(RECORD.read_text())


def rows() -> tuple[dict, dict]:
    r = record()["result"]["rows"]
    return r["main"], r["patched"]


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def change(m: float, p: float) -> float:
    return p / m - 1


def test_the_verdict_is_the_registered_rule_applied_to_the_result():
    d, t = record(), flat()
    assert d["verdict"] == dz.verdict(d["result"])
    assert (
        d["verdict"]["decision"] == "BITES_AT_DEFAULTS"
        and "decision `BITES_AT_DEFAULTS`" in t
    )
    assert d["result"]["identity_problems"] == []
    assert d["result"]["cube"] == dz.CUBE and f"`{dz.CUBE}`" in t
    assert (d["result"]["zone"], d["result"]["block"], d["result"]["cut_end"]) == (
        1024,
        512,
        16.0,
    )
    s = d["result"]["settings"]
    assert (s["threshold"], s["max_join_angle"], s["min_length"], s["mirror"], s["extend"], s["margin"]) == (
        60.0, 45.0, 100.0, False, False, 32
    )  # fmt: skip
    assert s["revision"].startswith("e189af75") and s["villa_main"].startswith(
        "7e6b82164"
    )
    assert d["result"]["patched_stitch_sha256"] == dz.PATCHED_STITCH_SHA256
    assert f"sha256 `{dz.PATCHED_STITCH_SHA256[:8]}…`" in t


def test_the_result_table_is_the_record():
    (m, p), t = rows(), flat()
    zone = [
        ("fibers written", f"{m['zone']['written']:,}", f"{p['zone']['written']:,}"),
        ("written length, voxels", f"{round(m['zone']['length']):,}", f"{round(p['zone']['length']):,}"),
        ("written length beside a same-family copy", f"{m['zone']['duplicated_share']:.3f}",
         f"{p['zone']['duplicated_share']:.3f}"),
    ]  # fmt: skip
    cube = [
        ("fibers written inside", f"{m['cube']['written_inside']:,}", f"{p['cube']['written_inside']:,}"),
        ("written length beside a same-family copy", f"{m['cube']['duplicated_share']:.3f}",
         f"{p['cube']['duplicated_share']:.3f}"),
    ]  # fmt: skip
    for tol in ("tol4", "tol2"):
        a, b = m["cube"][tol], p["cube"][tol]
        e = f"τ = {tol[-1]}"
        g = change(a["erl_merge_penalized"], b["erl_merge_penalized"])
        cube.append(
            (
                f"merge-penalized ERL, {e}",
                f"{a['erl_merge_penalized']}",
                f"{b['erl_merge_penalized']} ({pct(g)})",
            )
        )
        cube.append((f"merges, {e}", f"{a['merges']}", f"{b['merges']}"))
        cube.append((f"coverage, {e}", f"{a['coverage']:.4f}", f"{b['coverage']:.4f}"))
        cube.append(
            (f"precision, {e}", f"{a['precision']:.4f}", f"{b['precision']:.4f}")
        )
    a, b = m["cube"]["tol4"], p["cube"]["tol4"]
    cube.append(("splits, τ = 4", f"{a['splits']:,}", f"{b['splits']:,}"))
    zone_part, cube_part = t.split("**Inside the hand-traced 512³ cube**", 1)
    for name, x, y in zone:
        assert f"| {name} | {x} | {y} |" in zone_part, name
    for name, x, y in cube:
        assert f"| {name} | {x} | {y} |" in cube_part.split("| prediction |", 1)[0], (
            name
        )


def test_the_predictions_table_and_the_headline_are_the_verdict():
    v, (m, p), t = record()["verdict"], rows(), flat()
    p1, p2 = v["P1_main_zone_duplicated_share"], v["P2_patched_over_main_duplicated"]
    p3, p4 = v["P3_gain_tol4"], v["P4_merges_tol2"]
    assert all(c[1] for c in (p1, p2, p3, p4))
    assert f"| P1 (high) | main's zone duplicated share ≥ 0.05 | {p1[0]} | yes |" in t
    assert (
        f"| P2 (moderate) | with the trim, ≤ 0.6 of main's | {p2[0]} of main's | yes |"
        in t
    )
    assert (
        f"| P3 (moderate) | ERLpen at τ = 4 higher with the trim | {pct(p3[0])} | yes |"
        in t
    )
    assert (
        f"| P4 (moderate) | merges at τ = 2 ≤ 1.05 × main's | {p4[0][1]} against {p4[0][0]} | yes |"
        in t
    )
    zm, zp = m["zone"]["duplicated_share"], p["zone"]["duplicated_share"]
    head = t.split(" The result of ", 1)[0]
    assert (
        f"writes {100 * zm:.1f}% of its fiber length beside a same-family copy" in head
    )
    assert (
        f"cuts that to {100 * zp:.1f}%" in head
        and f"by {100 * p3[0]:.1f}% at tolerance 4" in head
    )
    assert f"On main, {100 * zm:.1f}% of the zone's written length" in t
    assert f"The zone's share falls to {p2[0]} of main's" in t


def test_the_comparisons_with_finding_106_are_its_record():
    d106, (m, p), t = json.loads(RECORD_106.read_text()), rows(), flat()
    R = [d106["cubes"][c]["rows"] for c in bs.HELD_OUT]
    assert f"had at most {max(r['one/main']['duplicated_share'] for r in R):.4f}" in t
    dup = [
        statistics.median(r[f"real/{v}"]["duplicated_share"] for r in R)
        for v in ("main", "patched")
    ]
    assert f"median share went from {dup[0]:.3f} to {dup[1]:.3f}" in t
    same = d106["cubes"][dz.CUBE]["rows"]
    g106 = [bs.gain(same, "real", tol) for tol in ("tol4", "tol2")]
    g107 = [
        change(
            m["cube"][tol]["erl_merge_penalized"], p["cube"][tol]["erl_merge_penalized"]
        )
        for tol in ("tol4", "tol2")
    ]
    assert (
        f"gained {pct(g106[0])} at τ = 4 and {pct(g106[1])} at τ = 2. This one gained {pct(g107[0])} and {pct(g107[1])}"
        in t
    )
    assert g107[0] > g106[0] and g107[1] > g106[1]
    assert (f"({m['cube']['tol4']['erl_merge_penalized']} against finding 106's "
            f"{same['real/main']['tol4']['erl_merge_penalized']})") in t  # fmt: skip


def test_the_coverage_cost_and_its_qualification_are_the_records():
    d106, (m, p), t = json.loads(RECORD_106.read_text()), rows(), flat()
    c = [
        change(m["cube"][tol]["coverage"], p["cube"][tol]["coverage"])
        for tol in ("tol4", "tol2")
    ]
    assert (
        f"Coverage falls {-100 * c[0]:.1f}% at τ = 4 and {-100 * c[1]:.1f}% at τ = 2"
        in t
    )
    R = [d106["cubes"][cube]["rows"] for cube in bs.HELD_OUT]
    cov = lambda r, k, tol: r[k][tol]["coverage"]  # noqa: E731
    falls = [
        change(cov(r, "real/main", "tol4"), cov(r, "real/patched", "tol4")) for r in R
    ]
    assert all(f < 0 for f in falls)
    assert (
        f"on all eight cubes ({pct(max(falls)).replace('-', '−')} to {pct(min(falls)).replace('-', '−')} at τ = 4)"
        in t
    )
    assert all(
        cov(r, "real/main", tol) > cov(r, "one/main", tol)
        for r in R
        for tol in ("tol2", "tol4")
    )
    assert (
        "main's eight blocks covered more of the hand tracing than the cube run as one block, at both tolerances"
        in t
    )
    back = [cov(r, "real/patched", "tol4") - cov(r, "one/main", "tol4") for r in R]
    assert (
        f"within {min(back):.3f} to +{max(back):.3f} of one block at τ = 4".replace(
            "-", "−"
        )
        in t
    )


def test_the_timing_is_the_record():
    tm, t = record()["result"]["timing_s"], flat()
    blocks = [tm[f"block_{i}"] for i in range(8)]
    assert len(tm) == 8
    assert (
        f"took {sum(blocks):,.1f} s to predict the eight blocks ({min(blocks):,.1f} to {max(blocks):,.1f} s each)"
        in t
    )


def test_the_files_it_points_to_exist():
    for rel in re.findall(
        r"`((?:scripts|docs|reports|repro|tests)/[^`]+)`", REPORT.read_text()
    ):
        assert (ROOT / rel).exists(), rel


def test_the_registration_and_the_strategy_carry_the_verdict():
    d, (m, p) = record(), rows()
    v = d["verdict"]
    reg = " ".join(
        (ROOT / "docs/preregistration/2026-11-08_afv_generator_default_zone.md")
        .read_text()
        .split()
    )
    g4 = change(
        m["cube"]["tol4"]["erl_merge_penalized"],
        p["cube"]["tol4"]["erl_merge_penalized"],
    )
    g2 = change(
        m["cube"]["tol2"]["erl_merge_penalized"],
        p["cube"]["tol2"]["erl_merge_penalized"],
    )
    mg = v["P4_merges_tol2"][0]
    assert (f"(zone duplicated share {v['P1_main_zone_duplicated_share'][0]}, {v['P2_patched_over_main_duplicated'][0]} "
            f"of it with the trim; ERLpen {pct(g4)} at τ = 4; merges at τ = 2 {mg[0]} → {mg[1]}): "
            f"`{v['decision']}`") in reg  # fmt: skip
    strat = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
    c = change(m["cube"]["tol4"]["coverage"], p["cube"]["tol4"]["coverage"])
    assert (f"On main, {m['zone']['duplicated_share']:.3f} of the zone's written length lies beside a same-family copy, "
            f"and {p['zone']['duplicated_share']:.3f} with the trim. In the cube, ERLpen rose {100 * g4:.1f}% at "
            f"tolerance 4 and {100 * g2:.1f}% at tolerance 2, with merges at tolerance 2 {mg[0]} → {mg[1]} and coverage "
            f"{pct(c)[:-1].replace('-', '−').lstrip('+')}% at tolerance 4. Decision `{v['decision']}`") in strat  # fmt: skip
