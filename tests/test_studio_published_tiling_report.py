"""The finding-128 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/studio_published_tiling.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/studio_published_tiling.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/studio_tiling.py"
    spec = importlib.util.spec_from_file_location("studio_tiling_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


st = _load()


def test_the_verdict_follows_from_the_table_and_was_not_predicted():
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    v = st.verdict(RECORD["steps"]["infer"]["exit"], RECORD["numbers"])
    assert v == RECORD["verdict"] == "WINNERS_TILING_KEPT" != RECORD["predicted"]
    assert (
        f"**Verdict `{v}`**, not as predicted (I predicted `{RECORD['predicted']}`"
        in FLAT
    )


def test_the_registered_numbers_are_the_records():
    n = RECORD["numbers"]
    assert f"| {n['pixels']:,} |" in REPORT
    assert f"| **{round(n['r'], 4)}** (line {st.R_LINE}) |" in REPORT
    assert (
        f"| **{round(n['share_same_side_of_half'], 4)}** (line {st.SAME_SIDE_LINE}) |"
        in REPORT
    )
    a = n["abs_difference"]
    assert (
        f"| {round(a['p50'], 4)}, {round(a['p99'], 4)}, {round(a['max'], 4)} |"
        in REPORT
    )
    assert f"| {round(n['mean_ours'], 4)}, {round(n['mean_winner'], 4)} |" in REPORT
    fast, slow = RECORD["steps"]["infer"]["seconds"], RECORD["seconds_winners_tiling"]
    assert f"| {fast} s, {slow} s |" in REPORT and 30 <= fast <= 40
    assert f"{round(slow / fast, 1)} times faster" in FLAT
    assert f"{round(100 * n['share_same_side_of_half'], 2)}% of pixels" in FLAT


def test_the_seam_profile_is_the_records():
    p = RECORD["described_after_the_verdict"]["seam_profile"]
    assert p["period"] == 96 and p["pixels"] == RECORD["numbers"]["pixels"]
    for axis in ("columns", "rows"):
        assert (
            f"| along {axis} | {round(p[axis]['edge'], 4)} | {round(p[axis]['middle'], 4)} |"
            in REPORT
        )
    ratios = [p[a]["edge"] / p[a]["middle"] for a in ("columns", "rows")]
    assert f"{round(min(ratios), 1)} to {round(max(ratios), 1)} times as much" in FLAT
    assert (
        f"{round(100 * (1 - RECORD['numbers']['share_same_side_of_half']))}% of pixels do"
        in FLAT
    )


def test_the_costs_and_the_strategy():
    assert (
        f"(at most {RECORD['gpu_peak_mib_all_processes']:,} MiB of GPU memory)"
        in REPORT
    )
    assert f"| checksums | {RECORD['steps']['check']['seconds']} s |" in REPORT
    assert "reports/studio_published_tiling.md" in STRATEGY
    assert f"(`{RECORD['verdict']}`, not as predicted;" in STRATEGY
