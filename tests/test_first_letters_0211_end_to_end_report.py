"""The finding-121 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_end_to_end.md").read_text()
FLAT = REPORT.replace("\n", " ")
RECORD = json.loads((ROOT / "reports/first_letters_0211_end_to_end.json").read_text())
F120 = json.loads((ROOT / "reports/first_letters_0211_reader_v3.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/end_to_end.py"
    spec = importlib.util.spec_from_file_location("end_to_end_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


e2e = _load()


def _n(value) -> str:
    """A number as the report prints it: a minus sign, not a hyphen."""
    return str(value).replace("-", "−")


def _clock(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m} min {s} s" if m else f"{s} s"


def test_every_step_exited_zero_and_every_render_was_flipped_from_the_geometry():
    assert all(step["exit"] == 0 for step in RECORD["chain_steps"].values())
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    for w in RECORD["windings"]:
        assert RECORD["steps"][f"render_{w}"]["flipped"] is True
        assert RECORD["orientation"][f"{w}.tifxyz"]["render"] == "flip"
    assert all(o["render_flipped"] for o in RECORD["ours"])
    assert set(RECORD["snap_same_as_finding_119"].values()) == {"yes"}


def test_the_verdict_follows_from_the_registered_table():
    assert (
        e2e.verdict(RECORD["registered"], RECORD["cell_share"])
        == RECORD["verdict"]
        == "E2E_AGREES"
    )
    assert RECORD["predicted"] == RECORD["verdict"]
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT


def test_the_registered_numbers_in_the_report_are_the_records():
    reg = RECORD["registered"]
    slid = reg["control_slid"]
    assert f"| **{reg['r']}** |" in REPORT
    assert f"| {_n(reg['control_wrong_side'])} |" in REPORT
    assert (
        f"| {slid['largest_absolute']} (down {slid['down']}, up {slid['up']}, "
        f"right {slid['right']}, left {slid['left']}) |" in REPORT
    )
    assert f"{RECORD['cells']:,} of {RECORD['mask_cells']:,}" in REPORT
    assert f"{100 * RECORD['cell_share']:.1f}% of the winner's mask cells" in FLAT


def test_the_described_numbers_in_the_report_are_the_records():
    d = RECORD["described"]
    same = d["finding_118_on_these_cells"]
    assert (
        f"give r = {same['r']} against the winner's map; ours give {RECORD['registered']['r']}"
        in FLAT
    )
    assert f"at r = {d['r_with_finding_118_maps']}" in FLAT
    v3 = d["reader_v3"]
    assert (
        f"gives r = {v3['r']} (other side {_n(v3['control_wrong_side'])}, largest slide "
        f"{v3['control_slid']['largest_absolute']}), against {F120['registered']['reader_v3']['r']}"
        in FLAT
    )
    assert (
        f"cost the four models {round(same['r'] - RECORD['registered']['r'], 3)} in r"
        in FLAT
    )
    ov = d["ensemble_overlap"]
    assert (
        f"| our ensemble | {ov['overlap']} | {ov['control_overlap_slid']['largest']} |"
        in REPORT
    )
    assert (
        f"| finding 118's maps, same cells | {same['overlap']} | {same['control_overlap_slid']['largest']} |"
        in REPORT
    )
    assert (
        f"| Reader V3 through our geometry | {v3['overlap']} | {v3['control_overlap_slid']['largest']} |"
        in REPORT
    )
    t = d["transfer_distance_voxels"]
    assert f"{t['p50']} voxels; 95th percentile {t['p95']}" in FLAT


def test_the_per_winding_and_per_part_tables_are_the_records():
    d = RECORD["described"]
    cosine = {Path(o["mesh"]).name: o["normal_cosine_median"] for o in RECORD["ours"]}
    for name, row in d["by_winding"].items():
        w = name.removesuffix(".tifxyz")
        assert (
            f"| {w} | {_n(cosine[name])} | {row['cells']:,} | {row['r']} |" in REPORT
        ), w
    for label, words in (
        ("columns_0_181", "columns 0 to 181"),
        ("columns_193_300", "columns 193 to 300"),
    ):
        p = d["by_part"][label]
        assert f"{words}, {p['cells']:,} cells, r {p['r']}" in FLAT, label
        assert f"{p['r_finding_118_maps']})" in FLAT
    given = d["by_winding"]
    between = given["w034.tifxyz"]["cells"] + given["w036.tifxyz"]["cells"]
    assert between > RECORD["cells"] / 3 and "more than a third of the cells" in FLAT


def test_the_costs_in_the_report_are_the_records():
    chain = RECORD["chain_steps"]
    for kind, label in (
        ("flatten", "flatten (lasagna)"),
        ("render", "render, 66 layers, flipped"),
    ):
        seconds = [chain[f"{kind}_{w}"]["seconds"] for w in RECORD["windings"]]
        assert f"| {label} | {min(seconds)} to {max(seconds)} s" in REPORT, kind
        assert f"| {_clock(sum(seconds))} |" in REPORT, kind
    ink = [chain[f"ink_{w}"]["seconds"] for w in RECORD["windings"]]
    assert f"{_clock(min(ink))} to {_clock(max(ink))} | {_clock(sum(ink))} |" in REPORT
    v3 = [chain[f"reader_v3_{w}"]["seconds"] for w in RECORD["windings"]]
    assert f"{min(v3)} to {max(v3)} s | {_clock(sum(v3))} |" in REPORT
    assert f"| snap of four windings | | {chain['snap']['seconds']} s |" in REPORT
    start, end = RECORD["run"]["first_step_start"], RECORD["run"]["last_step_exit"]
    assert f"({start[11:19]} to {end[11:19]})" in REPORT


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_end_to_end.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
