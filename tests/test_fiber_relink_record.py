"""docs/FIBER_RELINKING.md's CPU replay, bound to its record (reports/evidence/fiber_relink_cpu_2026-11-05.json) and
to the harness that wrote it, and the research plan's account of the findings that close the refit retry."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "docs/FIBER_RELINKING.md").read_text()
DOC = " ".join(RAW.split())
E = json.loads((ROOT / "reports/evidence/fiber_relink_cpu_2026-11-05.json").read_text())
HARNESS = (ROOT / "repro/fibers/benchmark_relink.py").read_text()
CUBES = {
    "s1_00497_01497_03997_256": "Scroll 1 cube above",
    "s5_03997_01497_03997_256": "Scroll 5 cube above",
}


def test_the_record_is_consistent_with_itself():
    assert (E["accuracy_measured"], E["gpu_used"]) == (False, False)
    assert [Path(r["input"]).stem for r in E["rows"]] == list(CUBES)
    for row in E["rows"]:
        assert row["exact_geometry"] is True
        for name, times in row["seconds"].items():
            assert len(times) == E["repeats"]
            assert row["median_seconds"][name] == statistics.median(times)
        m = row["median_seconds"]
        assert row["median_speedup"] == m["baseline"] / m["candidate"]


def test_the_table_quotes_the_record():
    for row in E["rows"]:
        m = row["median_seconds"]
        line = (
            f"| {CUBES[Path(row['input']).stem]} | {row['input_fragments']} | {m['baseline']:.3f} s "
            f"| {m['candidate']:.3f} s | {row['median_speedup']:.1f}× |"
        )
        assert line in RAW, line


def test_the_command_and_settings_are_the_records():
    assert f"--baseline-ref {E['baseline_ref']}" in DOC
    assert f"--repeats {E['repeats']}" in DOC
    skeletons = [Path(a).name for a in E["command"] if a.endswith(".npz")]
    assert skeletons == [f"{c}.npz" for c in CUBES]
    for name in skeletons:
        assert f"--skeleton /path/to/inputs/{name}" in DOC
        assert f"→ `{name}`" in DOC
    assert (
        "max_gap=10.0, max_link_angle_deg=30.0, max_tangent_angle_deg=35.0"
        in " ".join(HARNESS.split())
    )
    assert "gap 10, link angle 30 and tangent angle 35" in DOC
    assert "segment = np.asarray(stretch[first : first + 48]" in HARNESS
    assert "range(0, len(stretch), 64)" in HARNESS
    assert "retains 48 samples out of each 64" in DOC


def test_the_plan_names_the_findings_that_close_the_refit_retry():
    # Finding 103 is the seed-heading confirmation; 101, 102 and 104 are the confidence-stop line.
    plan = " ".join((ROOT / "docs/research_plan.md").read_text().split())
    strategy = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
    assert "[Finding 103](../reports/seed_heading_confirmation.md)" in strategy
    assert "[Finding 104](../reports/neural_tracer_refit_retry.md)" in strategy
    assert (
        "Findings 101, 102 and 104 in the strategy close the existing refit retry"
        in plan
    )
