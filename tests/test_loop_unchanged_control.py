"""scripts/loop_unchanged_control.py and its registration (docs/preregistration/2026-10-27_loop_unchanged_control.md)."""

import datetime as dt
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = ROOT / "docs/preregistration/2026-10-27_loop_unchanged_control.md"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


U = _load("loop_unchanged_control")
REG = U.REGISTERED
STEPS = {"measures": {"val_f1": {"per_100_steps": -0.00005}, "roc_auc": {"per_100_steps": -0.00085}, "ap_lift": {"per_100_steps": -0.0045}}}  # fmt: skip


def _records(spec, start=REG["since"]):
    """spec: (tweak, val_f1, auc, lift, steps, **overrides) per cycle, 17 minutes apart from start."""
    t0 = dt.datetime.fromisoformat(start)
    out = []
    for i, (tweak, f1, auc, lift, steps, *more) in enumerate(spec):
        rec = {
            "started": (t0 + dt.timedelta(minutes=17 * i)).isoformat(),
            "tweak": tweak,
            "status": "REVERTED",
            "budget_s": 900,
            "incumbent_sha256": REG["incumbent_sha256"],
            "commit": "4a273ffe",
            "code_changes": [],
            "result": {
                "val_f1": f1,
                "roc_auc": auc,
                "ap_prevalence_lift": lift,
                "steps": steps,
                "promotion_blocked": None,
            },
        }
        for k, v in (more[0] if more else {}).items():
            rec[k] = v
        out.append(rec)
    return out


def _window(
    n_control, n_reverse, f1=-0.004, auc=-0.011, lift=-0.04, others=20, extra=()
):
    """Interleaved cycles: the control and the reverse tweak among others; the reverse arm is lower by f1/auc/lift."""
    spec, k = [], 0
    arms = [REG["control"]] * n_control + [REG["reverse"]] * n_reverse
    for j, arm in enumerate(arms):
        for _ in range(others // max(len(arms), 1)):
            spec.append((f"t{k % 5}", 0.270 + 0.0003 * (k % 3), 0.585, 1.20, 1300))
            k += 1
        low = arm == REG["reverse"]
        spec.append((arm, 0.2715 + (f1 if low else 0) + 0.0004 * (j % 3), 0.590 + (auc if low else 0) + 0.002 * (j % 2),
                     1.24 + (lift if low else 0) + 0.01 * (j % 2), 1300 if low else 990))  # fmt: skip
    return _records([*spec, *extra])


def test_status_counts_only_until_the_window_is_complete():
    records = _window(5, 7)
    st = U.status(records, now="2026-10-28T12:00:00")
    assert (st["control_cycles"], st["reverse_cycles"], st["complete"]) == (5, 7, False)
    assert not any(k in json.dumps(st) for k in ("val_f1", "roc_auc", "mean"))
    with pytest.raises(SystemExit, match="not complete"):
        U.read(records, STEPS, now="2026-10-28T12:00:00")


@pytest.mark.parametrize(
    "shift, reading, predictions",
    [
        ({}, "BEATS_UNCHANGED", {"Q1": True, "Q2": True, "Q3": True}),
        ({"auc": -0.001}, "F1_ONLY", {"Q1": True, "Q2": False, "Q3": True}),
        (
            {"f1": -0.001, "lift": -0.001},
            "NOT_SHOWN",
            {"Q1": False, "Q2": True, "Q3": False},
        ),
    ],
)
def test_the_registered_reading(shift, reading, predictions):
    got = U.read(_window(10, 10, **shift), STEPS, now="2026-10-30T12:00:00")
    assert (got["verdict"]["status"], got["verdict"]["reading"]) == ("OK", reading)
    assert got["verdict"]["predictions"] == predictions


def test_each_arm_keeps_its_first_ten_cycles():
    records = _window(12, 11)
    st = U.status(records, now="2026-10-30T12:00:00")
    assert (st["control_cycles"], st["reverse_cycles"], st["complete"]) == (
        10,
        10,
        True,
    )


def test_the_window_ends_at_a_promotion_another_incumbent_or_code_and_the_deadline():
    base = _window(8, 8)
    promoted = [dict(r) for r in base]
    j = next(i for i, r in enumerate(promoted) if r["tweak"] == REG["control"])
    promoted[j] = dict(promoted[j], status="SUCCESS")
    st = U.status(promoted, now="2026-10-30T12:00:00")
    assert (
        st["ended_by"] == "a promotion" and st["control_cycles"] == 1 and st["complete"]
    )
    moved = [dict(r) for r in base]
    for r in moved[len(moved) // 2 :]:
        r["commit"] = "beefcafe"
    assert (
        U.status(moved, now="2026-10-30T12:00:00")["ended_by"] == "another code epoch"
    )
    early = U.status(base[:6], now=REG["deadline"])
    assert early["complete"] and early["ended_by"] == "the deadline"
    got = U.read(base[:6], STEPS, now=REG["deadline"])
    assert got["verdict"] == {"status": "INCOMPLETE", "reading": None}


def test_only_scored_cycles_on_the_registered_incumbent_and_budget_from_the_start_count():
    before = _records(
        [(REG["control"], 0.27, 0.59, 1.2, 990)], start="2026-10-27T15:00:00"
    )
    other_budget = _records(
        [(REG["control"], 0.27, 0.59, 1.2, 990, {"budget_s": 3600})]
    )
    crashed = _records([(REG["control"], 0.27, 0.59, 1.2, 990, {"status": "CRASHED"})])
    blocked = _records([(REG["control"], 0.27, 0.59, 1.2, 990)])
    blocked[0]["result"]["promotion_blocked"] = "inputs differ"
    for records in (before, other_budget, crashed, blocked):
        assert U.status(records, now="2026-10-28T00:00:00")["control_cycles"] == 0
    stale = _records(
        [(REG["control"], 0.27, 0.59, 1.2, 990, {"incumbent_sha256": "0" * 64})]
    )
    assert U.status(stale, now="2026-10-28T00:00:00")["ended_by"] == "another incumbent"


def test_the_step_gap_is_reported_beside_the_reading():
    got = U.read(_window(10, 10), STEPS, now="2026-10-30T12:00:00")
    gap = got["steps"]["reverse_minus_control"]
    assert gap == pytest.approx(310)
    assert got["steps"]["roc_auc"]["from_the_step_gap"] == pytest.approx(-0.00085 * 3.1)


def test_the_registration_states_the_scripts_rule():
    text = " ".join(REGISTRATION.read_text().split())
    assert f"**{REG['since'].replace('T', ' ')} PDT**" in text
    assert REG["incumbent_sha256"] in text
    for key, label in (("Q1_val_f1", "Q1"), ("Q2_roc_auc", "Q2"), ("Q3_ap_lift", "Q3")):
        assert f"{label}" in text and f"≤ {REG[key]:+}".replace("-", "−") in text
    assert (
        f"first {REG['cut_at']} cycles" in text
        and f"fewer than {REG['min_each']}" in text
    )
    assert REG["deadline"].replace("T", " ") in text
    assert (
        "python3 scripts/loop_unchanged_control.py status --cycles cycles.jsonl" in text
    )


def test_the_registration_quotes_the_confirmations_effects():
    v = json.loads(
        (ROOT / "reports/loop_tweak_confirmation_corrected_2026-10-27.json").read_text()
    )["verdict"]
    e = v["effects"]
    text = " ".join(REGISTRATION.read_text().split())
    assert v["reading"] == "CONFIRMED"
    assert (
        f"val_f1 +{e['val_f1']:.4f}, ROC AUC +{e['roc_auc']:.4f}, AP prevalence lift +{e['ap_lift']:.3f}"
        in text
    )
    assert f"(−{e['val_f1']:.4f}, −{e['roc_auc']:.4f})" in text
    # the thresholds are about half the confirmation's effects, reversed
    for key, measure in (
        ("Q1_val_f1", "val_f1"),
        ("Q2_roc_auc", "roc_auc"),
        ("Q3_ap_lift", "ap_lift"),
    ):
        assert -e[measure] * 0.7 <= REG[key] <= -e[measure] * 0.3
