"""The finding-122 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_gp_timesformer.md").read_text()
FLAT = " ".join(REPORT.split())  # line breaks and list indentation as single spaces
RECORD = json.loads(
    (ROOT / "reports/first_letters_0211_gp_timesformer.json").read_text()
)
F118 = json.loads((ROOT / "reports/first_letters_0211_reader_control.json").read_text())
F120 = json.loads((ROOT / "reports/first_letters_0211_reader_v3.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/gp_timesformer.py"
    spec = importlib.util.spec_from_file_location("gp_timesformer_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gp = _load()


def _n(value) -> str:
    return str(value).replace("-", "−")


def test_every_step_exited_zero_and_the_checkpoint_passed_its_audit():
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    assert RECORD["checkpoint"]["audit_passes"] is True
    imported = set(RECORD["checkpoint"]["pickle_imports"]["archive/data.pkl"])
    assert imported == {
        "collections.OrderedDict", "torch._utils._rebuild_tensor_v2", "torch.FloatStorage",
        "torch.optim.lr_scheduler.CosineAnnealingLR", "torch.optim.adamw.AdamW", "collections.defaultdict",
        "__builtin__.dict", "torch._utils._rebuild_parameter",
    }  # fmt: skip
    assert RECORD["checkpoint"]["sha256"].startswith("93f56e56")
    assert RECORD["windows"] == gp.WINDOWS and RECORD["reading_side"] == gp.READING


def test_the_verdict_follows_from_the_registered_table():
    reg = RECORD["registered"]
    assert (
        gp.verdict(reg["ensemble"], reg["gp_timesformer"], RECORD["cell_share"])
        == RECORD["verdict"]
    )
    assert RECORD["verdict"] == RECORD["predicted"] == "GP_FARTHER"
    assert reg["ensemble"]["r"] == F118["registered"]["r"]
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT


def test_the_registered_numbers_in_the_report_are_the_records():
    reg = RECORD["registered"]
    e, g = reg["ensemble"], reg["gp_timesformer"]
    assert (
        f"| {e['r']} | {g['r']} | **{_n(reg['delta_r'])}** (margin −0.10) |" in REPORT
    )
    assert (
        f"| {_n(e['control_wrong_side'])} | {_n(g['control_wrong_side'])} |" in REPORT
    )
    assert (
        f"| {e['control_slid']['largest_absolute']} | {g['control_slid']['largest_absolute']} |"
        in REPORT
    )
    assert (
        f"| {e['overlap']} | {g['overlap']} | **{_n(reg['delta_overlap'])}** (margin −0.05) |"
        in REPORT
    )
    assert (
        f"| {e['control_overlap_slid']['largest']} | {g['control_overlap_slid']['largest']} |"
        in REPORT
    )
    assert f"{RECORD['cells']:,} of {RECORD['mask_cells']:,}" in REPORT
    assert f"{RECORD['winner_ink_cells']:,}" in REPORT
    assert (
        f"0.{abs(round(reg['delta_r'] * 1000)):03d} below the ensemble's in r" in FLAT
    )


def test_the_described_numbers_in_the_report_are_the_records():
    d = RECORD["described"]
    fwd = d["forward_order_as_reading_side"]
    assert f"r is {_n(fwd['r'])} and the overlap {fwd['overlap']}" in FLAT
    boot = d["r_difference_bootstrap"]
    assert f"{_n(boot['low'])} to {_n(boot['high'])}" in FLAT and boot["high"] < -0.10
    assert (
        f"r {d['gp_r_with_ensemble']} with the ensemble and {d['gp_r_with_reader_v3']} with Reader V3"
        in FLAT
    )
    assert d["reader_v3"]["r"] == F120["registered"]["reader_v3"]["r"]
    assert f"r {d['reader_v3']['r']}, overlap {d['reader_v3']['overlap']}" in FLAT


def test_the_costs_in_the_report_are_the_records():
    s = RECORD["steps"]
    assert (
        f"| {s['infer_v9fwd']['seconds']} s / {s['infer_v9rev']['seconds']} s |"
        in REPORT
    )
    assert (
        f"| segments (26 layers in each order, 353 MB) | {s['segments']['seconds']} s |"
        in REPORT
    )
    total = sum(v["seconds"] for v in s.values())
    assert f"{total // 60} min {total % 60} s in all" in REPORT
    assert (
        f"GPU for {s['infer_v9fwd']['seconds'] + s['infer_v9rev']['seconds']} s"
        in REPORT
    )


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_gp_timesformer.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
