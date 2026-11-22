"""The finding-131 report states its record's numbers and the verdict its registered rule gives them."""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "repro/first_letters/pherc0211_control"))

import dense_read  # noqa: E402

REPORT = (ROOT / "reports/first_letters_0211_dense_read.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0211_dense_read.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
ARMS = ("f124", "rerun", "dense2")


def test_the_record_is_finding_131s_and_names_no_home_path():
    assert RECORD["finding"] == 131 and RECORD["registration_commit"] == "f242f84f"
    assert (ROOT / RECORD["registration"]).exists()
    assert "/home/" not in json.dumps(RECORD)
    assert all(g["exit"] == 0 for g in RECORD["steps"].values())
    assert RECORD["f124_reproduced_on_its_own_cells"] is True
    assert (
        RECORD["described"]["each_arm_on_its_own_cells"]["f124"]["r"]
        == dense_read.F124_R
    )


def test_the_verdict_follows_the_registered_rule():
    reg = RECORD["registered"]
    r = reg["r"]
    assert reg["noise_rerun_minus_f124"] == round(r["rerun"] - r["f124"], 4)
    assert reg["margin"] == dense_read.margin(r["rerun"] - r["f124"]) == 0.02
    change = reg["change_dense2_minus_rerun"]
    assert (
        change == round(r["dense2"] - r["rerun"], 4)
        and -reg["margin"] < change < reg["margin"]
    )
    assert RECORD["verdict"] == "DENSE_READS_SAME"
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT
    assert abs(reg["noise_rerun_minus_f124"]) < 0.01
    assert f"held ({abs(reg['noise_rerun_minus_f124'])})" in FLAT


def test_the_registered_tables_are_the_records():
    r = RECORD["registered"]["r"]
    for arm in ARMS:
        assert f"| {r[arm]} |" in REPORT, arm
    reg = RECORD["registered"]
    assert (
        f"| noise, r(`rerun`) − r(`f124`) | {reg['noise_rerun_minus_f124']} | |".replace(
            "-", "−"
        )
        in REPORT
    )
    assert (
        f"| change, r(`dense2`) − r(`rerun`) | {reg['change_dense2_minus_rerun']} |".replace(
            "-", "−"
        )
        in REPORT
    )
    assert (
        f"On the {RECORD['cells']:,} of the winner's {RECORD['mask_cells']:,} mask cells"
        in FLAT
    )
    assert f"(share {RECORD['cell_share']})" in FLAT
    cosines = [c for a in RECORD["arms"].values() for c in a["normal_cosine_median"]]
    assert max(cosines) < 0
    assert f"{max(cosines)} to {min(cosines)}".replace("-", "−") in FLAT


def test_the_geometry_table_and_the_slope_arithmetic():
    shares = RECORD["described"]["final_nodes_within_2_of_the_predicted_sheet"]
    gains = []
    for w in RECORD["windings"]:
        gain = round(shares["dense2"][w] - shares["rerun"][w], 4)
        gains.append(gain)
        assert (
            f"| {w} | {shares['f124'][w]} | {shares['rerun'][w]} | {shares['dense2'][w]} | +{gain} |"
            in REPORT
        )
        assert gain > 0
    median = round(float(np.median(gains)), 4)
    assert (
        f"The median gain is +{median}" in FLAT
        and f"+{median} at the median" in STRATEGY
    )
    assert round(0.61 * median, 2) == 0.02  # "would have predicted about +0.02"


def test_the_described_tables_are_the_records():
    own = RECORD["described"]["each_arm_on_its_own_cells"]
    common = RECORD["described"]["each_arm_on_the_common_cells"]
    assert (
        f"| r, own cells | {own['f124']['r']} ({own['f124']['cells']:,} cells) | {own['rerun']['r']} "
        f"({own['rerun']['cells']:,}) | {own['dense2']['r']} ({own['dense2']['cells']:,}) |"
    ) in REPORT
    for label, key in (
        ("r with the background in, common cells", "r_with_background"),
        ("reversed planes (control), common cells", "control_wrong_side"),
        ("ink overlap, common cells", "overlap"),
    ):
        row = " | ".join(str(common[a][key]) for a in ARMS)
        assert f"| {label} | {row} |".replace("-", "−") in REPORT, label
    slid = " | ".join(str(common[a]["control_slid"]["largest_absolute"]) for a in ARMS)
    assert f"| slid (control), largest, common cells | {slid} |" in REPORT
    t = RECORD["described"]["transfer_distance_voxels"]
    row = " | ".join(f"{t[a]['p50']}, {t[a]['p95']}" for a in ARMS)
    assert (
        f"| transfer distance, median and 95th percentile (voxels) | {row} |" in REPORT
    )
    extra = own["dense2"]["cells"] - own["rerun"]["cells"]
    assert f"reaches {extra:,} more cells" in FLAT
    assert f"(−{abs(round(own['dense2']['r'] - own['rerun']['r'], 4))})" in FLAT


def test_the_rerun_and_the_costs_are_the_records():
    same = RECORD["rerun_byte_identical_to_finding_121"]
    assert all(v["snap"] and not v["final"] for v in same.values()) and len(same) == 4
    s = RECORD["steps"]
    assert RECORD["seconds"] == sum(g["seconds"] for g in s.values())
    m, sec = divmod(RECORD["seconds"], 60)
    assert f"{m} min {sec} s in all" in FLAT
    assert f"peaked at {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT
    for arm in ("rerun", "dense2"):
        assert f"{s[f'snap_e2e_{arm}']['seconds']} s" in REPORT
    rerun = [s[f"flatten_e2e_rerun_{w}"]["seconds"] for w in RECORD["windings"]]
    dense = {s[f"flatten_e2e_dense2_{w}"]["seconds"] for w in RECORD["windings"]}
    assert (
        f"| flatten, per winding | {min(rerun)} to {max(rerun)} s | {dense.pop()} s |"
        in REPORT
        and not dense
    )
    for step in ("render", "studio"):
        assert (
            f"{s[f'{step}_e2e_rerun']['seconds']} s | {s[f'{step}_e2e_dense2']['seconds']} s |"
            in REPORT
        ), step


def test_the_strategy_carries_the_finding():
    assert (
        "reports/first_letters_0211_dense_read.md" in STRATEGY
        and "finding 131" in STRATEGY
    )
    r = RECORD["registered"]["r"]
    assert f"give r {r['dense2']} against {r['rerun']}" in STRATEGY
