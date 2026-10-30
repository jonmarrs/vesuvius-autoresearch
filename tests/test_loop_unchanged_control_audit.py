"""scripts/loop_unchanged_control_audit.py: checks beside the unchanged-control reading that change no reading."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = _load(
    "loop_unchanged_control_audit", ROOT / "scripts/loop_unchanged_control_audit.py"
)
T = _load("unchanged_control_fixtures", ROOT / "tests/test_loop_unchanged_control.py")
REG = T.REG


def _trend_window(effect, slope_per_cycle, early_reverse):
    """30 other cycles with a linear trend, 8 reverse and 7 control cycles placed early or late; the reverse arm sits
    `effect` below the trend at its own time, the control on it."""
    spec, n = [], 45
    reverse_at = set(range(1, 16, 2)) if early_reverse else set(range(29, 45, 2))
    control_at = set(range(30, 44, 2)) if early_reverse else set(range(0, 14, 2))
    for i in range(n):
        base = 0.270 + slope_per_cycle * i + 0.0002 * (i % 3)
        if i in reverse_at:
            spec.append(
                (REG["reverse"], base + effect, 0.58 + effect, 1.2 + effect, 1300)
            )
        elif i in control_at:
            spec.append((REG["control"], base, 0.58, 1.2, 1000))
        else:
            spec.append((f"t{i % 5}", base, 0.58, 1.2, 1100))
    return T._records(spec)


def test_time_matching_removes_a_timing_confound():
    """No arm effect, a drifting score, the reverse arm early: the raw difference is the drift; matched, it is gone."""
    records = _trend_window(effect=0.0, slope_per_cycle=-0.0002, early_reverse=True)
    rows, _ = A.U.window(records)
    control, reverse = A.U.arms(rows)
    raw = sum(r["result"]["val_f1"] for r in reverse) / len(reverse) - sum(
        r["result"]["val_f1"] for r in control
    ) / len(control)
    got = A.audit(records)["measures"]["val_f1"]
    assert raw > 0.004  # the early arm looks better only because it ran earlier
    assert abs(got["time_matched_diff"]) < 0.0005
    assert got["others_drift_per_day"] < 0 and got["others_drift_p"] < 0.001


def test_a_real_effect_survives_matching_and_leaving_one_out():
    records = _trend_window(effect=-0.004, slope_per_cycle=0.0, early_reverse=False)
    got = A.audit(records)["measures"]["val_f1"]
    assert got["time_matched_diff"] == pytest.approx(-0.004, abs=0.0005)
    assert got["leave_one_out"][1] < -0.003 and got["mann_whitney_p"] < 0.01
    assert got["threshold"] == REG["Q1_val_f1"]
    assert len(got["reverse"]) == 8 and len(got["control"]) == 7


def test_too_few_cycles_are_not_audited():
    records = T._window(3, 3)
    with pytest.raises(SystemExit, match="too few"):
        A.audit(records)


READOUT = ROOT / "reports/loop_unchanged_control_2026-10-30.json"
AUDIT = ROOT / "reports/loop_unchanged_control_audit_2026-10-30.json"
REPORT = ROOT / "reports/loop_unchanged_control_readout_2026-10-30.md"


def _num(x, places):
    return f"{x:.{places}f}".replace("-", "−")


def test_the_report_quotes_the_registered_readout():
    import json

    r = json.loads(READOUT.read_text())
    text = " ".join(REPORT.read_text().split())
    assert r["verdict"] == {"status": "OK", "predictions": {"Q1": True, "Q2": True, "Q3": True}, "reading": "BEATS_UNCHANGED"}  # fmt: skip
    assert r["ended_by"] == "a promotion" and (r["control_cycles"], r["reverse_cycles"], r["window_cycles"]) == (7, 8, 161)  # fmt: skip
    assert "**Reading: BEATS_UNCHANGED.**" in text
    for name, places in (("val_f1", 5), ("roc_auc", 5), ("ap_lift", 5)):
        e = r["effects"][name]
        row = f"| {_num(e['reverse_mean'], places)} | {_num(e['control_mean'], places)} | {_num(e['diff'], places)} |"
        assert row in text, (name, row)
    assert r["registered"] == {**A.U.REGISTERED}
    assert (
        r["sources"]["cycles"]["sha256"].startswith("ae552943")
        and "sha256 `ae552943…`" in text
    )


def test_the_report_quotes_the_audit():
    import json

    a = json.loads(AUDIT.read_text())
    text = " ".join(REPORT.read_text().split())
    assert (
        a["sources"]["cycles"]["sha256"]
        == json.loads(READOUT.read_text())["sources"]["cycles"]["sha256"]
    )
    assert a["cycles"] == {"control": 7, "reverse": 8, "others": 146}
    for name, places in (("val_f1", 5), ("roc_auc", 5), ("ap_lift", 5)):
        lo, hi = a["measures"][name]["leave_one_out"]
        assert f"[{_num(lo, places)}, {_num(hi, places)}]" in text, name
        # every leave-one-out difference is past the registered threshold, as the report says
        assert hi < a["measures"][name]["threshold"]
    for name in ("val_f1", "roc_auc"):
        m = a["measures"][name]
        assert m["time_matched_diff"] < m["threshold"]
