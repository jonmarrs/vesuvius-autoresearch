"""The finding-124 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_studio_e2e.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0211_studio_e2e.json").read_text())
F121 = json.loads((ROOT / "reports/first_letters_0211_end_to_end.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/studio_e2e.py"
    spec = importlib.util.spec_from_file_location("studio_e2e_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


se = _load()


def _n(value) -> str:
    return str(value).replace("-", "−")


def test_every_step_exited_zero_on_finding_121s_cells():
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    assert (RECORD["cells"], RECORD["mask_cells"]) == (
        F121["cells"],
        F121["mask_cells"],
    )
    assert RECORD["layers"] == list(se.LAYERS) == list(range(41, 25, -1))
    assert all(o["normal_cosine_median"] < 0 for o in RECORD["ours"])


def test_the_verdict_follows_from_the_registered_table():
    assert (
        se.verdict(RECORD["registered"], RECORD["cell_share"])
        == RECORD["verdict"]
        == "STUDIO_E2E_CLOSE"
    )
    assert RECORD["predicted"] == RECORD["verdict"]
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT


def test_the_registered_numbers_in_the_report_are_the_records():
    reg = RECORD["registered"]
    slid = reg["control_slid"]
    assert f"| **{reg['r']}** |" in REPORT
    assert f"| {_n(reg['control_wrong_side'])} |" in REPORT
    assert (
        f"| {slid['largest_absolute']} (down {slid['down']}, up {slid['up']}, right {slid['right']}, "
        f"left {slid['left']}) |" in REPORT
    )
    assert f"{RECORD['cells']:,} of {RECORD['mask_cells']:,}" in REPORT
    assert f"{100 * RECORD['cell_share']:.1f}% of the winner's mask cells" in FLAT


def test_the_described_numbers_in_the_report_are_the_records():
    d = RECORD["described"]
    for key, label in (
        ("whole_pipeline", "our windings, carried (the registered map)"),
        ("our_render_of_the_winners_surface", "our render of the winner's surface"),
    ):
        x = d[key]
        assert (
            f"| {label} | {x['r']} | {x['r_with_background']} | {x['overlap']} | "
            f"{x['control_overlap_slid']['largest']} |" in REPORT
        ), key
    assert f"at r {d['r_whole_pipeline_with_our_render']}" in FLAT
    for name, row in d["by_winding"].items():
        assert f"{name.removesuffix('.tifxyz')} {row['r']} ({row['cells']:,}" in FLAT, (
            name
        )
    assert f"columns 0 to 181, r {d['by_part']['columns_0_181']['r']}" in FLAT
    assert f"columns 193 to 300, r {d['by_part']['columns_193_300']['r']}" in FLAT
    t = d["transfer_distance_voxels"]
    assert f"median distance {t['p50']} voxels, 95th percentile {t['p95']}" in FLAT


def test_the_costs_in_the_report_are_the_records():
    s = RECORD["steps"]
    m, sec = divmod(s["infer"]["seconds"], 60)
    assert f"| {m} min {sec} s |" in REPORT
    assert (
        f"| {s['planes']['seconds']} s |" in REPORT
        and f"| {s['compare']['seconds']} s |" in REPORT
    )
    assert f"{RECORD['gpu_peak_mib_all_processes']:,} MiB" in REPORT


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_studio_e2e.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
