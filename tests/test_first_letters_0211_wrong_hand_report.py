"""The finding-137 report states its record's numbers and the verdict its registered rules give; the checks written
after the result measure what they say on a synthetic scroll."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_wrong_hand.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0211_wrong_hand.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
REG = RECORD["registered"]
DESC = RECORD["described"]
AUDIT = RECORD["audit_after_the_result"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


wh = _load(
    "wrong_hand_for_report",
    ROOT / "repro/first_letters/pherc0211_control/wrong_hand.py",
)
audit = _load(
    "wrong_hand_audit_for_report",
    ROOT / "repro/first_letters/pherc0211_control/wrong_hand_audit.py",
)


def _signed(x: float) -> str:
    return f"+{x}" if x > 0 else str(x).replace("-", "−")


def test_the_record_is_finding_137s_and_names_no_home_path():
    assert RECORD["finding"] == 137 and RECORD["registration_commit"] == "e51b57e3"
    assert RECORD["amendment_1_commit"] == "dc232051"
    assert (ROOT / RECORD["registration"]).exists()
    assert "/home/" not in json.dumps(RECORD)
    assert all(g["exit"] == 0 for g in RECORD["steps"].values())
    assert RECORD["f124_reproduced"] is True and REG["right"]["r"] == wh.F124_R
    assert RECORD["arms"]["right"]["windings"] == ["w033", "w034", "w035", "w036"]
    assert RECORD["arms"]["wrong"]["windings"] == RECORD["choice"]["wrong"]["chosen"]
    assert AUDIT["registered"] is False


def test_the_verdict_follows_the_registered_rules():
    v = wh.verdict(REG["right"], REG["wrong"], RECORD["f124_reproduced"])
    assert v == RECORD["verdict"] == "WRONG_HAND_READS_ALIKE"
    assert (
        f"**Verdict `{v}`**, by the registered table; `WRONG_HAND_READS_PARTLY` was predicted"
        in FLAT
    )
    for name in ("right", "wrong"):
        a = RECORD["arms"][name]
        assert wh.sampled_along_the_winner(a["normal_cosine_median"], a["flipped"])
    right, wrong = (
        RECORD["arms"][n]["normal_cosine_median"] for n in ("right", "wrong")
    )
    assert all(RECORD["arms"]["right"]["flipped"]) and not any(
        RECORD["arms"]["wrong"]["flipped"]
    )
    assert f"median cosines {_signed(max(right))} to {_signed(min(right))}" in FLAT
    assert f"at {_signed(min(wrong))} to {_signed(max(wrong))}" in FLAT


def test_the_registered_tables_are_the_records():
    assert f"of {RECORD['mask_cells']:,}" in FLAT
    own = DESC["each_arm_on_its_own_cells"]
    for name, label in (("right", "right (finding 121's)"), ("wrong", "wrong")):
        g, o = REG[name], own[name]
        wind = ", ".join(RECORD["arms"][name]["windings"])
        row = (
            f"| {label} | {wind} | {o['cells']:,} | {g['cell_share']} | {g['r']} | "
            f"{_signed(g['control_wrong_side'])} | {g['control_slid']['largest_absolute']} |"
        )
        assert row in REPORT, row
    r, w = REG["right"], REG["wrong"]
    need_r = round(r["r"] - wh.MARGIN, 4)
    need_share = round(wh.SHARE_ALIKE * r["cell_share"], 4)
    controls = [abs(w["control_wrong_side"]), w["control_slid"]["largest_absolute"]]
    need_ratio = round(wh.RATIO * max(controls), 4)
    assert f"| r at least the right arm's minus 0.05 | {need_r} | {w['r']} |" in REPORT
    assert (
        f"| cell share at least 0.8 of the right arm's | {need_share} | {w['cell_share']} |"
        in REPORT
    )
    assert (
        f"| r at least twice the absolute value of each control | {need_ratio} | {w['r']} |"
        in REPORT
    )
    assert w["r"] >= need_r and w["cell_share"] >= need_share and w["r"] >= need_ratio


def test_the_predictions_are_scored_from_the_record():
    c = DESC["both_arms_on_their_common_cells"]
    gap = round(c["wrong"]["r"] - c["right"]["r"], 4)
    assert abs(gap) < 0.05  # prediction 2
    assert (
        f"On {c['cells']:,} cells (share {c['cell_share']}), r is {c['right']['r']} for arm right and "
        f"{c['wrong']['r']} for arm wrong, {gap} apart" in FLAT
    )
    share = REG["wrong"]["cell_share"]
    assert not 0.40 <= share <= 0.75 and f"not held ({share})" in FLAT  # prediction 3
    assert (
        f"The wrong arm's r is {round(REG['wrong']['r'] - REG['right']['r'], 4)} above"
        in FLAT
    )


def test_the_described_numbers_are_the_records():
    own = DESC["each_arm_on_its_own_cells"]
    common = DESC["both_arms_on_their_common_cells"]["cells"]
    only_right = round((own["right"]["cells"] - common) / RECORD["mask_cells"], 4)
    assert (
        f"Only the wrong arm reaches {DESC['only_the_wrong_arm_reaches']} of the mask cells and only the "
        f"right arm {only_right}" in FLAT
    )
    t = DESC["transfer_distance_voxels"]
    assert f"medians {t['right']['p50']} and {t['wrong']['p50']} voxels" in FLAT
    assert f"95th percentiles {t['right']['p95']} and {t['wrong']['p95']}" in FLAT
    assert (
        f"r is {own['right']['r_with_background']} (right) and {own['wrong']['r_with_background']} (wrong)"
        in FLAT
    )
    for name in ("right", "wrong"):
        by = DESC["by_winding"][name]
        assert sum(v["cells"] for v in by.values()) == own[name]["cells"]
        assert max(v["cells"] for v in by.values()) / own[name]["cells"] < 0.36
        for wnd, v in by.items():
            assert f"| {name} | {wnd} | {v['cells']:,} | {v['r']} |" in REPORT
    ch = RECORD["choice"]
    pts = list(ch["wrong"]["points_within_accept"].values())
    assert ", ".join(f"{p:,}" for p in pts[:3]) + f" and {pts[3]:,}" in FLAT
    assert f"(the fifth, w037, {pts[4]:,})" in FLAT
    reg = ch["right_as_registered"]
    assert (
        f"{ch['wrong']['described']['winner_points_within_2_of_any_winding']} and "
        f"{ch['wrong']['described']['winner_points_within_accept_of_any_winding']} of the winner's points, "
        f"against {reg['winner_points_within_2_of_any_winding']} and "
        f"{reg['winner_points_within_accept_of_any_winding']}" in FLAT
    )
    reg_text = (ROOT / RECORD["registration"]).read_text()
    assert (
        "220,362, 152,314, 59,464 and 48,445" in reg_text
        and "0.2616 and 0.8189" in reg_text
    )
    snap = RECORD["snap_report"]
    for wnd in ("w033", "w034", "w035", "w036"):
        r, w = snap["right"][wnd], snap["wrong"][wnd]
        row = (
            f"| {wnd} | {r['median_abs_off']} | {w['median_abs_off']} | "
            f"{r['frac_already_on']} | {w['frac_already_on']} |"
        )
        assert row in REPORT, row


def test_the_checks_after_the_result_are_the_records():
    turns = AUDIT["turn_degrees"]
    right = [d for v in turns["right"].values() for d in v]
    wrong = [d for v in turns["wrong"].values() for d in v]
    assert max(right) < 0 < min(wrong)  # the two fits turn opposite ways
    assert f"turn {_signed(max(right))} to {_signed(min(right))} degrees" in FLAT
    assert f"turn {_signed(min(wrong))} to {_signed(max(wrong))} degrees" in FLAT
    by = AUDIT["seams"]["by_winding"]
    share = sorted(v["share_within_accept"] for v in by.values())
    net = sorted(v["net_dk_per_row"] for v in by.values())
    assert (
        f"{share[0]} to {share[-1]} of its lattice points lie within 4 voxels" in FLAT
    )
    assert f"the net change is {net[0]} to {net[-1]} sheets a row" in FLAT
    assert f"a net {net[0]} to {net[-1]} sheets a turn" in FLAT
    out = sorted(v["crossing_dk_counts"].get("1", 0) for v in by.values())
    inw = sorted(v["crossing_dk_counts"].get("-1", 0) for v in by.values())
    big = sorted(
        sum(c for k, c in v["crossing_dk_counts"].items() if abs(int(k)) >= 2)
        for v in by.values()
    )
    assert (
        f"{out[0]} to {out[-1]} steps outward per winding, offset by {inw[0]} to {inw[-1]} inward"
        in FLAT
    )
    assert f"only {big[0]} to {big[-1]} steps of two or three sheets" in FLAT
    assert all(abs(int(k)) <= 3 for v in by.values() for k in v["crossing_dk_counts"])
    assert "w020 to w050" in AUDIT["seams"]["stands_in_for_the_sheets"]


def test_the_meaning_numbers_and_the_costs_are_the_records():
    dr = round(REG["wrong"]["r"] - REG["right"]["r"], 4)
    ds = round(REG["wrong"]["cell_share"] - REG["right"]["cell_share"], 4)
    assert f"moved r by {_signed(dr)} and the cell share by {_signed(ds)}" in FLAT
    s = RECORD["steps"]
    assert RECORD["seconds"] == sum(g["seconds"] for g in s.values())
    h, rest = divmod(RECORD["seconds"], 3600)
    m, sec = divmod(rest, 60)
    assert f"{h} h {m} min {sec} s in all" in FLAT
    for step, g in s.items():
        label = "fit (30,000 steps)" if step == "fit" else step
        assert f"| {label} | {g['seconds']:,} s |" in REPORT, step
    assert (
        RECORD["fit"]["steps"] == 30000
        and RECORD["fit"]["seconds"] == s["fit"]["seconds"]
    )
    assert (
        f"The fit peaked at {RECORD['fit']['gpu_peak_mib_all_processes']:,} MiB" in FLAT
    )
    assert f"the run at {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT


def test_the_strategy_carries_the_finding():
    assert (
        "reports/first_letters_0211_wrong_hand.md" in STRATEGY
        and "finding 137" in STRATEGY
    )
    r, w = REG["right"], REG["wrong"]
    assert (
        f"at r {w['r']} on {w['cell_share']} of the mask cells, against {r['r']} on {r['cell_share']}"
        in STRATEGY
    )
    net = sorted(v["net_dk_per_row"] for v in AUDIT["seams"]["by_winding"].values())
    assert f"a net {net[0]} to {net[-1]} of them a turn" in STRATEGY


# The checks written after the result, on a synthetic scroll whose answer is known.

STEP = 20.0  # voxels between grid nodes (tifxyz scale 0.05)


def _write(mesh: Path, x, y, z):
    mesh.mkdir(parents=True)
    for name, a in zip("xyz", (x, y, z), strict=True):
        tifffile.imwrite(mesh / f"{name}.tif", a.astype(np.float32))


def _ring(radius_of_angle, sign, rows=11, cols=64):
    """One winding: rows by z, columns a full turn around (500, 500), the angle running with `sign`."""
    theta = sign * np.linspace(0, 2 * np.pi, cols) + np.pi
    rad = radius_of_angle(np.linspace(0, 1, cols))
    z = 100 + STEP * np.arange(rows)[:, None] * np.ones(cols)
    x = 500 + rad * np.cos(theta) * np.ones((rows, 1))
    y = 500 + rad * np.sin(theta) * np.ones((rows, 1))
    return x, y, z


def _scroll(tmp_path):
    band = tmp_path / "band"
    (band / "dataset").mkdir(parents=True)
    (band / "dataset/umbilicus.json").write_text(
        json.dumps(
            {
                "control_points": [
                    {"x": 500, "y": 500, "z": 0},
                    {"x": 500, "y": 500, "z": 1000},
                ]
            }
        )
    )
    right = band / "work/fit_full/p_0-patch/meshes/fitted"
    wrong = band / "work/fit_full-otherhand/p_0-patch/meshes/fitted"
    for k in range(28, 42):  # concentric sheets 10 voxels apart, turning negatively
        _write(
            right / f"w{k:03d}",
            *_ring(lambda f, k=k: 200 + 10.0 * (k - 30) + 0 * f, -1),
        )
    for k in (
        33,
        34,
        35,
        36,
    ):  # the other way round, stepping out one sheet half way round
        r0 = 200 + 10.0 * (k - 30)
        _write(wrong / f"w{k:03d}", *_ring(lambda f, r0=r0: r0 + 10.0 * (f > 0.5), +1))
    return band


def test_the_audit_finds_the_turn_and_a_single_step_on_a_synthetic_scroll(tmp_path):
    band = _scroll(tmp_path)
    rec = audit.main(band, tmp_path / "audit.json")
    assert json.loads((tmp_path / "audit.json").read_text()) == rec
    for w, degrees in rec["turn_degrees"]["right"].items():
        assert degrees and all(abs(d + 360) < 0.5 for d in degrees), w
    for w, degrees in rec["turn_degrees"]["wrong"].items():
        assert degrees and all(abs(d - 360) < 0.5 for d in degrees), w
    for w, s in rec["seams"]["by_winding"].items():
        assert s["crossing_dk_counts"] == {"1": s["rows"]}, (
            w
        )  # one outward step a row, of one sheet
        assert s["net_dk_per_row"] == 1.0 and s["published_seams_passed"] == 0
        assert s["share_within_accept"] > 0.9
