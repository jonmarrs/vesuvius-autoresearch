"""docs/preregistration/2026-11-02_seed_heading_confirmation.md: the registered predictions and decision rule, the
proposal's figures from finding 100, and what the chain pins."""

import ast
import json
import re
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_steep_heading as sh  # noqa: E402
import seed_heading_confirmation as m  # noqa: E402

DOC = ROOT / "docs" / "preregistration" / "2026-11-02_seed_heading_confirmation.md"
CHAIN = ROOT / "repro" / "fibers" / "run_seed_heading_confirmation_chain.sh"
CHECKS = (
    ROOT / "reports" / "evidence" / "fiber_skeletons_unshipped_checks_2026-11-02.json"
)
F100 = ROOT / "reports" / "neural_tracer_steep_heading.json"


def _text() -> str:
    return " ".join(DOC.read_text().split())


def _row(cov, prec=0.5, pen=10.0, merges=0):
    return {
        "coverage": cov,
        "precision": prec,
        "erl_merge_penalized": pen,
        "merges": merges,
    }


def _case(after_cov=None, s=None, prec_change=None, pen_factor=None, after_skips=None):
    """Every cube at coverage 0.4 before; per-cube overrides by name."""
    after_cov, s = after_cov or {}, s or {}
    prec_change, pen_factor, after_skips = (
        prec_change or {},
        pen_factor or {},
        after_skips or {},
    )
    rows = {"before": {}, "after": {}}
    records = {"before": {}, "after": {}}
    for c in m.CUBES:
        rows["before"][c] = _row(0.4)
        rows["after"][c] = _row(
            after_cov.get(c, 0.4),
            0.5 + prec_change.get(c, 0.0),
            10.0 * pen_factor.get(c, 1.0),
        )
        records["before"][c] = {
            "dots": 100_000,
            "no_heading": round(100_000 * s.get(c, 0.01)),
        }
        records["after"][c] = {"dots": 100_000, "no_heading": after_skips.get(c, 0)}
    return rows, records


A, B = m.CUBES[0], m.CUBES[1]


def test_all_low_skip_and_unchanged_leaves_the_gain_untested():
    v = m.verdict(*_case())
    assert (
        v["prediction_P1"],
        v["prediction_P2"],
        v["prediction_P3"],
        v["prediction_P5"],
    ) == (True, True, None, True)
    assert v["decision"] == "NO_HIGH_SKIP_CUBE" and v["high_skip_cubes"] == []
    assert "no unseen cube skips 0.20 of its dots" in v["reading"]
    assert m.status(True, [], v) == "OK"


def test_a_high_skip_cube_that_gains_replicates_and_one_that_does_not_fails():
    v = m.verdict(*_case(after_cov={A: 0.4 * 1.06}, s={A: 0.25}))
    assert (
        v["prediction_P3"] is True
        and v["decision"] == "REPLICATED"
        and v["high_skip_cubes"] == [A]
    )
    v = m.verdict(*_case(after_cov={A: 0.4 * 1.04}, s={A: 0.25}))
    assert v["prediction_P3"] is False and v["decision"] == "NOT_REPLICATED"
    assert "does not replicate" in v["reading"]


@pytest.mark.parametrize(
    "s,low,high",
    [
        (0.0199, True, False),
        (0.02, False, False),
        (0.1999, False, False),
        (0.20, False, True),
    ],
)
def test_the_skip_share_boundaries_are_as_registered(s, low, high):
    v = m.verdict(*_case(s={A: s}))
    assert (A in v["low_skip_cubes"], A in v["high_skip_cubes"]) == (low, high)


def test_a_precision_or_merge_penalized_cost_holds_the_draft():
    v = m.verdict(*_case(prec_change={A: -0.031}, after_cov={B: 0.4 * 1.2}, s={B: 0.3}))
    assert (
        v["prediction_P2"] is False
        and v["decision"] == "HOLD"
        and "precision" in v["reading"]
    )
    assert m.verdict(*_case(prec_change={A: -0.0299}))["prediction_P2"] is True
    v = m.verdict(*_case(pen_factor={A: 0.949}))
    assert (
        v["prediction_P5"] is False
        and v["decision"] == "HOLD"
        and "merge-penalized ERL: hold" in v["reading"]
    )


def test_p1_bounds_coverage_on_low_skip_cubes_both_ways_and_is_reported_not_decisive():
    for f in (0.989, 1.011):
        v = m.verdict(*_case(after_cov={A: 0.4 * f}))
        assert v["prediction_P1"] is False and v["decision"] == "NO_HIGH_SKIP_CUBE"
        assert v["reading"].endswith(
            "moves by more than 1% on a cube that skips under 2% of its dots"
        )
    assert m.verdict(*_case(after_cov={A: 0.4 * 1.0099}))["prediction_P1"] is True


def test_p4_is_spearman_over_the_ten():
    s = {c: 0.01 * (i + 1) for i, c in enumerate(m.CUBES)}
    rising = {c: 0.4 * (1 + 0.001 * (i + 1)) for i, c in enumerate(m.CUBES)}
    v = m.verdict(*_case(after_cov=rising, s=s))
    assert v["spearman_rho"] == pytest.approx(1.0) and v["prediction_P4"] is True
    falling = {c: 0.4 * (1 + 0.001 * (10 - i)) for i, c in enumerate(m.CUBES)}
    assert m.verdict(*_case(after_cov=falling, s=s))["prediction_P4"] is False
    assert m.verdict(*_case())["prediction_P4"] is None  # no spread in s


def test_an_after_run_that_still_skips_fails_the_manipulation():
    v = m.verdict(*_case(after_skips={A: 1}))
    assert (
        v["manipulation_ok"] is False and m.status(True, [], v) == "MANIPULATION_FAILED"
    )


def test_a_missing_run_or_smoke_leaves_it_incomplete():
    rows, records = _case()
    del rows["after"][A]
    v = m.verdict(rows, records)
    assert v["prediction_P2"] is None and v["decision"] is None
    assert m.status(True, ["after/" + A], v) == "INCOMPLETE"
    full = m.verdict(*_case())
    assert (
        m.status(None, [], full) == "INCOMPLETE"
        and m.status(False, [], full) == "SMOKE_FAILED"
    )


def test_the_box_and_the_padded_presence_are_the_cube_in_the_padded_grid():
    assert m.box("s5_05497_01997_02997_256") == "64,64,64,192,192,192"
    assert m.box("s1_02494_01494_03994_512") == "64,64,64,320,320,320"
    level = np.arange(128**3, dtype=np.uint32).reshape((128,) * 3).astype(np.uint8)
    out = m.padded_level(level, "s5_05497_01997_02997_256")
    assert out.shape == (256,) * 3 and np.array_equal(
        out[64:192, 64:192, 64:192], level
    )
    assert out.sum(dtype=np.int64) == level.sum(dtype=np.int64)
    with pytest.raises(ValueError):
        m.padded_level(level, "s1_02494_01494_03994_512")


def test_done_reads_the_last_event_and_the_closed_outputs(tmp_path):
    run = tmp_path / "after" / A
    (run / "tiles").mkdir(parents=True)
    for n in ("run.json", "tiles.jsonl"):
        (run / n).write_text("{}")
    (run / "tiles" / "0.npz").write_bytes(b"x")
    log = tmp_path / "chain.log"
    log.write_text(f"TRACE after {A}  t\nDONE after {A}  t\n")
    assert m.done(tmp_path, "after", A) and not m.done(tmp_path, "before", A)
    log.write_text(log.read_text() + f"TRACE after {A}  t\n")
    assert not m.done(tmp_path, "after", A)
    log.write_text(log.read_text() + f"DONE after {A}  t\n")
    (run / "tiles" / "1.partial.npz").write_bytes(b"x")
    assert not m.done(tmp_path, "after", A)


def test_the_cubes_are_the_checked_ten_outside_scrollgt():
    checks = json.loads(CHECKS.read_text())
    assert sorted(checks["cubes"]) == sorted(m.CUBES) and len(m.CUBES) == 10
    assert all(r["semantic_gate_ok"] and r["ct_corners_identical"] and r["padded_128_inside_scan"]
               for r in checks["cubes"].values())  # fmt: skip
    assert set(m.PRESENCE_HELD_OUT) < set(m.CUBES) and len(m.PRESENCE_HELD_OUT) == 3
    assert not set(m.CUBES) & set(sh.ALL_CUBES) and len(sh.ALL_CUBES) == 21
    assert all(
        v == {"tol2": True, "tol4": True}
        for v in checks["ground_truth_path"]["rows_identical"].values()
    )
    assert "/home/" not in CHECKS.read_text() and "spiral_out" not in CHECKS.read_text()


def test_the_chain_pins_what_the_script_pins():
    chain = CHAIN.read_text()
    assert f"VILLA_SHA={m.VILLA_SHA}" in chain and f"SMOKE={m.SMOKE}" in chain
    cubes = re.search(r'^CUBES="([^"]+)"', chain, re.M).group(1).split()
    assert tuple(cubes) == m.CUBES
    code = set(re.search(r'^CODE="([^"]+)"', chain, re.M).group(1).split())
    # the frozen copy imports its siblings from $W/code: every local import must be frozen with it
    seen, todo = set(), ["seed_heading_confirmation"]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse((ROOT / "scripts" / f"{name}.py").read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])  # fmt: skip
            todo += [
                n.split(".")[0]
                for n in names
                if (ROOT / "scripts" / f"{n.split('.')[0]}.py").exists()
            ]
    assert code == {f"{n}.py" for n in seen}
    assert (
        "--no-fibers" in chain
        and "--ct-level 0 --ct-grid-scale 1 --grid-scale 2" in chain
    )
    assert "--base-um 7.91" in chain and 'echo "64,64,64,$((64 + n / 2))' in chain
    assert m.rr.SOURCE["before"] / m.SMOKE == m.SMOKE_REFERENCE


def test_the_doc_registers_the_scripts_numbers():
    t = _text()
    assert "**Status: PROPOSED 2026-11-02, not registered.**" in t
    assert (
        f"on every cube with s < {m.LOW_SKIP}, coverage factor in {m.P1_BAND[0]}–{m.P1_BAND[1]}"
        in t
    )
    assert f"precision at most {m.P2_DROP} lower on every cube" in t
    assert (
        f"on every cube with s ≥ {m.HIGH_SKIP:.2f}, coverage factor at least {m.P3_FACTOR}"
        in t
    )
    assert (
        f"Spearman ρ between s and the coverage factor at least {m.P4_RHO}, over the ten"
        in t
    )
    assert f"merge-penalized ERL factor at least {m.P5_PEN} on every cube" in t
    assert f"villa's own CLI at `{m.VILLA_SHA[:8]}`" in t
    for d in (
        "`HOLD`, if P2 or P5 fails",
        "`REPLICATED`",
        "`NOT_REPLICATED`",
        "`NO_HIGH_SKIP_CUBE`",
        "`MANIPULATION_FAILED`",
    ):
        assert d in t
    for c in m.CUBES:
        assert f"`{c}`" in t
    held = t.split("**Three were first released in Dataset003**")[1].split(
        "**The tracer's"
    )[0]
    assert all(f"`{c}`" in held for c in m.PRESENCE_HELD_OUT)


def test_the_doc_quotes_finding_100_as_recorded():
    d = json.loads(F100.read_text())
    b, keep, base = (
        d["baseline_records"],
        d["rows_tol2"]["keep"],
        d["baseline_rows_tol2"],
    )
    s = {c: b[c]["no_heading_share"] for c in b}
    assert all(
        abs(s[c] - b[c]["no_heading"] / b[c]["dots"]) < 1e-12 for c in b
    )  # the registered s
    cov = {c: keep[c]["coverage"] / base[c]["coverage"] for c in b}
    prec = {c: keep[c]["precision"] - base[c]["precision"] for c in b}
    pen = {
        c: keep[c]["erl_merge_penalized"] / base[c]["erl_merge_penalized"] for c in b
    }
    from scipy.stats import spearmanr

    t = _text()
    assert (
        f"Spearman ρ = {spearmanr(list(s.values()), list(cov.values())).statistic:.2f}"
        in t
    )

    def span(cubes, f, fmt):
        return f"{fmt.format(min(f[c] for c in cubes))}–{fmt.format(max(f[c] for c in cubes))}".replace(
            "-", "−"
        )

    groups = {
        "the 11 in-sample cubes": sh.IN_SAMPLE,
        "the 8 held-out Scroll-3 cubes": [c for c in sh.HELD if c.startswith("s3_")],
    }
    assert len(groups["the 8 held-out Scroll-3 cubes"]) == 8 and len(sh.IN_SAMPLE) == 11
    assert (
        f"| the 11 in-sample cubes | {span(sh.IN_SAMPLE, s, '{:.3f}')} | {span(sh.IN_SAMPLE, cov, '{:.4f}')} |"
        in t
    )
    s3 = groups["the 8 held-out Scroll-3 cubes"]
    assert (
        f"| the 8 held-out Scroll-3 cubes | {span(s3, s, '{:.3f}')} | {span(s3, cov, '{:.4f}')} |"
        in t
    )
    s5 = sorted(c for c in sh.HELD if c.startswith("s5_"))
    assert (
        f"| {s[s5[0]]:.3f}, {s[s5[1]]:.3f} | {cov[s5[0]]:.3f}, {cov[s5[1]]:.3f} |" in t
    )
    assert (
        f"between {max(s[c] for c in s if s[c] < 0.2):.3f} and {min(s[c] for c in s if s[c] >= 0.2):.3f}"
        in t
    )
    assert (
        f"ERL factor lies in {min(pen.values()):.3f}–{max(pen.values()):.3f} on all 21 cubes"
        in t
    )
    low = [c for c in b if s[c] < m.LOW_SKIP]
    assert (
        f"| {min(cov[c] for c in low):.4f}–{max(cov[c] for c in low):.4f} on the {len(low)} such cubes |"
        in t
    )
    assert f"at most {-min(prec.values()):.3f} lower on all 21" in t
    high = [c for c in b if s[c] >= m.HIGH_SKIP]
    assert (
        f"| {min(cov[c] for c in high):.3f} and {max(cov[c] for c in high):.3f} on the 2 such cubes |"
        in t
    )
    assert all(
        r["no_heading"] == 0 for r in d["records"]["keep"].values()
    )  # the manipulation check's precedent
    assert (
        statistics.median(cov.values()) > 1
    )  # the fix has not lowered coverage on the median cube
