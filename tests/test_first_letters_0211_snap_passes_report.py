"""The finding-134 report states its record's numbers and the verdict and consequence its registered rules give."""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "repro/first_letters/pherc0211_control"))

import snap_passes_read as f134  # noqa: E402

REPORT = (ROOT / "reports/first_letters_0211_snap_passes.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0211_snap_passes.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
ARMS = ("f124", "rerun", "dense2", "dense2s3")


def _signed(x: float) -> str:
    return f"+{x}" if x > 0 else str(x).replace("-", "−")


def test_the_record_is_finding_134s_and_names_no_home_path():
    assert RECORD["finding"] == 134 and RECORD["registration_commit"] == "0bf4748a"
    assert (ROOT / RECORD["registration"]).exists()
    assert "/home/" not in json.dumps(RECORD)
    assert all(g["exit"] == 0 for g in RECORD["steps"].values())
    assert RECORD["f124_reproduced_on_its_own_cells"] is True
    own = RECORD["described"]["each_arm_on_its_own_cells"]
    assert own["f124"]["r"] == f134.f131.F124_R
    assert all(RECORD["first_pass_byte_identical_to_finding_131"].values())


def test_the_verdict_and_consequence_follow_the_registered_rules():
    reg = RECORD["registered"]
    r = reg["r"]
    verdict = f134.verdict(
        r["f124"], r["rerun"], r["dense2"], r["dense2s3"], RECORD["cell_share"], True
    )
    assert verdict == RECORD["verdict"] == "SNAP3_READS_SAME"
    shares = RECORD["described"]["final_nodes_within_2_of_the_predicted_sheet"]
    gain = f134.geometry_gain(shares)
    assert gain == RECORD["geometry_gain_dense2s3_minus_dense2"] > 0
    assert f134.consequence(verdict, gain) == RECORD["consequence"] == "three_passes"
    assert f"**Verdict `{verdict}`**, as predicted" in REPORT
    assert f"The registered geometry gain is +{gain}, above 0" in FLAT
    assert "**So the registered consequence is `three_passes`**" in REPORT
    assert 0.02 <= gain <= 0.06 and f"held (+{gain})" in FLAT  # prediction 2


def test_the_registered_tables_are_the_records():
    reg = RECORD["registered"]
    for arm in ARMS:
        assert f"| {reg['r'][arm]} |" in REPORT, arm
    assert (
        f"| noise, r(`rerun`) − r(`f124`) | {_signed(reg['noise_rerun_minus_f124'])} | |"
        in REPORT
    )
    assert f"| margin | {reg['margin']} |" in REPORT
    assert (
        f"| change, r(`dense2s3`) − r(`dense2`) | {_signed(reg['change_dense2s3_minus_dense2'])} |"
        in REPORT
    )
    assert (
        f"On the {RECORD['cells']:,} of the winner's {RECORD['mask_cells']:,} mask cells"
        in FLAT
    )
    assert f"(share {RECORD['cell_share']})" in FLAT
    cosines = [c for a in RECORD["arms"].values() for c in a["normal_cosine_median"]]
    assert max(cosines) < 0
    assert f"{_signed(max(cosines))} to {_signed(min(cosines))}" in FLAT


def test_the_geometry_table_and_the_arithmetic():
    shares = RECORD["described"]["final_nodes_within_2_of_the_predicted_sheet"]
    gains = {}
    for w in RECORD["windings"]:
        gains[w] = round(shares["dense2s3"][w] - shares["dense2"][w], 4)
        assert (
            f"| {w} | {shares['rerun'][w]} | {shares['dense2'][w]} | {shares['dense2s3'][w]} | +{gains[w]} |"
            in REPORT
        )
    least = sorted(RECORD["windings"], key=lambda w: shares["dense2"][w])[:2]
    assert set(least) == set(
        sorted(gains, key=gains.get)[-2:]
    )  # the least on the sheet gained most
    gain = RECORD["geometry_gain_dense2s3_minus_dense2"]
    assert round(float(np.median(list(gains.values()))), 4) == gain
    assert f"It gives +{round(0.61 * gain, 3)} for this gain" in FLAT
    r = RECORD["registered"]["r"]
    assert f"read {round(r['rerun'] - r['dense2s3'], 4)} lower" in FLAT
    over_rerun = [
        round(shares["dense2s3"][w] - shares["rerun"][w], 4) for w in RECORD["windings"]
    ]
    assert f"They sit {min(over_rerun)} to {max(over_rerun)} more on the sheet" in FLAT
    assert f"within {round(max(r.values()) - min(r.values()), 4)} of each other" in FLAT


def test_the_described_tables_are_the_records():
    own = RECORD["described"]["each_arm_on_its_own_cells"]
    common = RECORD["described"]["each_arm_on_the_common_cells"]
    cells = " | ".join(
        f"{own[a]['r']} ({own[a]['cells']:,} cells)"
        if a == "f124"
        else f"{own[a]['r']} ({own[a]['cells']:,})"
        for a in ARMS
    )
    assert f"| r, own cells | {cells} |" in REPORT
    for label, key in (
        ("r with the background in, common cells", "r_with_background"),
        ("reversed planes (control), common cells", "control_wrong_side"),
        ("ink overlap, common cells", "overlap"),
    ):
        row = " | ".join(
            _signed(common[a][key]) if common[a][key] < 0 else str(common[a][key])
            for a in ARMS
        )
        assert f"| {label} | {row} |" in REPORT, label
    slid = " | ".join(str(common[a]["control_slid"]["largest_absolute"]) for a in ARMS)
    assert f"| slid (control), largest, common cells | {slid} |" in REPORT
    t = RECORD["described"]["transfer_distance_voxels"]
    row = " | ".join(f"{t[a]['p50']}, {t[a]['p95']}" for a in ARMS)
    assert (
        f"| transfer distance, median and 95th percentile (voxels) | {row} |" in REPORT
    )


def test_the_costs_are_the_records():
    s = RECORD["steps"]
    assert RECORD["seconds"] == sum(g["seconds"] for g in s.values())
    m, sec = divmod(RECORD["seconds"], 60)
    assert f"{m} min {sec} s in all" in FLAT
    assert f"peaked at {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT
    assert f"| snap, three passes, four windings | {s['snap']['seconds']} s |" in REPORT
    flat = [s[f"flatten_{w}"]["seconds"] for w in RECORD["windings"]]
    assert f"| flatten, per winding | {min(flat)} to {max(flat)} s |" in REPORT
    assert f"took {min(flat)} to {max(flat)} s a winding" in FLAT
    for step, label in (("render", "render, four windings"), ("studio", "Studio, four windings in both orders"),
                        ("compare", "compare")):  # fmt: skip
        assert f"| {label} | {s[step]['seconds']} s |" in REPORT, step


def test_the_strategy_carries_the_finding():
    assert (
        "reports/first_letters_0211_snap_passes.md" in STRATEGY
        and "finding 134" in STRATEGY
    )
    r = RECORD["registered"]["r"]
    assert f"give r {r['dense2s3']} against {r['dense2']}" in STRATEGY
