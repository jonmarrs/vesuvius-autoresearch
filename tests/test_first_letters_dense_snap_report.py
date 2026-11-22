"""The finding-130 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_dense_snap.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_dense_snap.json").read_text())


def _load():
    path = ROOT / "repro/first_letters/eligible_band/dense_snap.py"
    spec = importlib.util.spec_from_file_location("dense_snap_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ds = _load()


def _signed(x: float) -> str:
    return f"+{x}" if x >= 0 else str(x)


def test_every_step_exited_zero_and_the_verdict_follows_from_the_table():
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    rows = RECORD["windings"]
    gains = [r["gain"] for r in rows.values()]
    on_tri = [r["dense2"]["on_snapped_triangles"] for r in rows.values()]
    assert (
        ds.verdict(gains, on_tri, True)
        == RECORD["verdict"]
        == RECORD["predicted"]
        == "DENSE_SNAP_HELPS"
    )
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT
    assert list(rows) == ["w020", "w030", "w040", "w050", "w060", "w070"]
    for r in rows.values():
        assert r["gain"] == round(
            r["dense2"]["final_within_2"] - r["outer80"]["final_within_2"], 4
        )


def test_the_registered_table_is_the_records():
    for name, r in RECORD["windings"].items():
        row = f"| {name} | {r['outer80']['final_within_2']} | {r['dense2']['final_within_2']} | {_signed(r['gain'])} |"
        assert row in REPORT, row
    s = RECORD["summary"]
    assert s["gain_median"] == round(
        float(np.median([r["gain"] for r in RECORD["windings"].values()])), 4
    )
    assert (
        f"| **median** | **{s['final_within_2_median']['outer80']}** | **{s['final_within_2_median']['dense2']}** | "
        f"**{_signed(s['gain_median'])}** |" in REPORT
    )
    assert f"is {_signed(s['gain_median'])} (rule: at least +0.05)" in FLAT
    assert (
        f"median share on its snapped triangles is {s['on_snapped_triangles_median']['dense2']}"
        in FLAT
    )


def test_the_described_numbers_are_the_records():
    s = RECORD["summary"]
    for key, label in (
        (
            "snapped_within_2_median",
            "snapped nodes within 2 voxels of the predicted sheet",
        ),
        (
            "on_snapped_triangles_median",
            "final nodes within 2 voxels of the snapped triangles",
        ),
    ):
        assert f"| {label} | {s[key]['outer80']} | {s[key]['dense2']} |" in REPORT, key
    t = s["final_within_2_by_radius_tercile_median"]
    for k, third in enumerate(("inner", "middle", "outer")):
        assert (
            f"| final within 2 voxels, {third} third of radii | {t['outer80'][k]} | {t['dense2'][k]} |"
            in REPORT
        )
    rise = round(
        s["snapped_within_2_median"]["dense2"]
        - s["snapped_within_2_median"]["outer80"],
        3,
    )
    assert f"rose by +{rise}" in FLAT


def test_the_costs_are_the_records():
    steps = RECORD["steps"]
    flat = [v["seconds"] for k, v in steps.items() if k.startswith("flatten_")]
    assert f"| {min(flat)} to {max(flat)} s" in REPORT
    assert (
        f"| snap, about four times the nodes | {steps['snap']['seconds']} s |" in REPORT
    )
    peak = max(v.get("gpu_peak_mib_all_processes", 0) for v in steps.values())
    assert f"{peak:,} MiB" in REPORT
    assert (
        f"| comparison | {RECORD['compare_gate']['seconds']} s |" in REPORT
        and RECORD["compare_gate"]["exit"] == 0
    )
