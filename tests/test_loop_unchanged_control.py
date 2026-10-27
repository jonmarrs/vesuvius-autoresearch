"""scripts/loop_unchanged_control.py and its registration (docs/preregistration/2026-10-27_loop_unchanged_control.md)."""

import datetime as dt
import hashlib
import importlib.util
import json
import os
import subprocess
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
BASE = {"aug_mode": "batchgeneratorsv2", "lr": 0.0005, "batch_size": 8}


def _config(tweak, base=BASE):
    if tweak == U.REGISTERED["control"]:
        return dict(base)
    if tweak == U.REGISTERED["reverse"]:
        return dict(base, aug_mode="albumentations")
    return dict(base, lr=0.001)


REG = U.REGISTERED
INPUTS = "75e57cf994a4b5d863c2277b05fa605aa5e5e70d19e908bee7d82e7d7cee2661"
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
            "code_sha256": "c" * 64,
            "baseline_config": dict(BASE),
            "baseline_config_sha256": U.configuration_fingerprint(BASE),
            "config": _config(tweak),
            "result": {
                "val_f1": f1,
                "roc_auc": auc,
                "ap_prevalence_lift": lift,
                "steps": steps,
                "promotion_blocked": None,
                "val_protocol": "seeded-sample-400-v3+z1-27",
                "validation_diag": {
                    "protocol": "seeded-sample-400-v3+z1-27",
                    "inputs_sha256": INPUTS,
                    "complete": True,
                    "batch_errors": 0,
                    "requested_patches": 400,
                    "scored_patches": 400,
                },
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


def test_the_first_completed_quota_freezes_the_entire_readout():
    records = _window(10, 10)
    before = U.read(records, STEPS)
    later = _records(
        [("later_tweak", 0.01, 0.02, 0.03, 1, {"status": "SUCCESS"})],
        start=(
            dt.datetime.fromisoformat(records[-1]["started"]) + dt.timedelta(hours=1)
        ).isoformat(),
    )
    assert U.read([*records, *later], STEPS) == before


def test_window_boundaries_compare_instants_and_preserve_the_registered_pdt_deadline():
    # The registration explicitly says PDT even though civil Pacific time is
    # PST by November 3. Keep that registered instant: 23:00 UTC, 15:00 PST.
    assert not U.status([], now="2026-11-03T22:59:59+00:00")["complete"]
    assert U.status([], now="2026-11-03T23:00:00+00:00")["complete"]
    before = _records([(REG["control"], 0.27, 0.59, 1.2, 990)])
    before[0]["started"] = "2026-10-27T22:59:59+00:00"
    assert U.status(before)["control_cycles"] == 0
    before[0]["started"] = "2026-10-27T23:00:00+00:00"
    assert U.status(before)["control_cycles"] == 1


@pytest.mark.parametrize("identity", [True, "unknown", "c" * 63])
def test_unverifiable_code_identity_is_not_evidence(identity):
    records = _window(1, 1, others=0)
    for record in records:
        record["code_sha256"] = identity
    assert U.status(records)["window_cycles"] == 0


@pytest.mark.parametrize(
    "damage", ["missing", "incomplete", "counts", "protocol", "inputs", "boolean"]
)
def test_only_the_registered_complete_validation_sample_counts(damage):
    records = _window(1, 1, others=0)
    for record in records:
        result = record["result"]
        if damage == "missing":
            result.pop("validation_diag")
        elif damage == "incomplete":
            result["validation_diag"]["complete"] = False
        elif damage == "counts":
            result["validation_diag"]["scored_patches"] = 399
        elif damage == "protocol":
            result["val_protocol"] = result["validation_diag"]["protocol"] = (
                "seeded-sample-400-v2+z1-27"
            )
        elif damage == "inputs":
            result["validation_diag"]["inputs_sha256"] = "a" * 64
        else:
            result["val_f1"] = True
    assert U.status(records)["window_cycles"] == 0


def test_out_of_order_records_cannot_choose_a_different_first_arm_cycle():
    records = _window(1, 1, others=0)
    with pytest.raises(ValueError, match="chronological"):
        U.status(list(reversed(records)))


def test_source_wall_clock_can_repeat_an_hour_when_pacific_summer_time_ends():
    records = _records([("other", 0.27, 0.59, 1.2, 990)] * 3)
    for record, stamp in zip(
        records,
        ("2026-11-01T01:59:00", "2026-11-01T01:00:00", "2026-11-01T01:01:00"),
        strict=True,
    ):
        record["started"] = stamp
    assert U.status(records)["window_cycles"] == 3


def test_validation_identity_is_bound_to_the_registered_starting_checkpoint():
    from scripts.promote_loop_candidate import checkpoint

    # A later loop promotion must not retarget this historical registration.
    saved_blob = subprocess.run(
        ["git", "cat-file", "blob", "e4251711249b93a5084b139f37ef42b98fab3457"],
        cwd=ROOT,
        capture_output=True,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
        check=False,
    )
    if saved_blob.returncode:
        pytest.skip("registered checkpoint blob absent in this shallow checkout")
    raw = saved_blob.stdout
    assert hashlib.sha256(raw).hexdigest() == REG["incumbent_sha256"]
    saved = checkpoint(raw)
    assert U.validation_key(saved) == U.REGISTERED_SAMPLE


@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
def test_cli_cannot_overwrite_its_source_journal(tmp_path, alias):
    cycles, steps = tmp_path / "cycles.jsonl", tmp_path / "steps.json"
    raw = "".join(json.dumps(r) + "\n" for r in _window(10, 10))
    cycles.write_text(raw)
    steps.write_text(json.dumps(STEPS))
    output = cycles if alias == "direct" else tmp_path / "output.json"
    if alias == "symlink":
        output.symlink_to(cycles)
    elif alias == "hardlink":
        os.link(cycles, output)
    with pytest.raises(SystemExit) as error:
        U.main(
            [
                "read",
                "--cycles",
                str(cycles),
                "--steps",
                str(steps),
                "--out",
                str(output),
            ]
        )
    assert error.value.code == 2
    assert cycles.read_text() == raw


def test_constant_arm_scores_keep_the_decision_and_emit_strict_json():
    records = _window(10, 10)
    for record in records:
        arm = record["tweak"]
        if arm in (REG["control"], REG["reverse"]):
            record["result"].update(
                val_f1=0.271 if arm == REG["control"] else 0.267,
                roc_auc=0.59,
                ap_prevalence_lift=1.2,
            )
    got = U.read(records, STEPS)
    assert got["verdict"]["reading"] == "F1_ONLY"
    assert all(
        effect["t"] is None and effect["p"] is None
        for effect in got["effects"].values()
    )
    json.dumps(got, allow_nan=False)


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
        r["code_sha256"] = "d" * 64
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


def test_the_window_opens_at_the_first_cycle_recorded_with_263s_identities():
    """Until #263 is pulled into the loop, its cycles carry no code_sha256 or baseline config: none counts, and the
    pull that brings it does not end the window."""
    old = _window(4, 4)
    for r in old:
        for k in ("code_sha256", "baseline_config", "baseline_config_sha256", "config"):
            del r[k]
        r["commit"] = "4a273ffe"
    new = _records(
        [
            (REG["control"], 0.2715, 0.59, 1.24, 990),
            (REG["reverse"], 0.2675, 0.58, 1.20, 1300),
        ],
        start=(
            dt.datetime.fromisoformat(old[-1]["started"]) + dt.timedelta(minutes=17)
        ).isoformat(),
    )
    st = U.status([*old, *new], now="2026-10-29T00:00:00")
    assert (st["control_cycles"], st["reverse_cycles"], st["ended_by"]) == (1, 1, None)


def test_a_new_baseline_ends_the_window_and_unverifiable_cycles_are_left_out():
    records = _window(4, 4)
    changed = [dict(r) for r in records]
    for r in changed[len(changed) // 2 :]:
        r["baseline_config"] = dict(BASE, lr=0.0001)
        r["baseline_config_sha256"] = U.configuration_fingerprint(r["baseline_config"])
    assert (
        U.status(changed, now="2026-10-29T00:00:00")["ended_by"]
        == "another baseline config"
    )
    forged = [dict(r) for r in records]
    for r in forged:
        if r["tweak"] == REG["control"]:
            r["baseline_config_sha256"] = "0" * 64  # does not match its config
    st = U.status(forged, now="2026-10-29T00:00:00")
    assert (st["control_cycles"], st["reverse_cycles"], st["ended_by"]) == (0, 4, None)
    wrong_arm = [dict(r) for r in records]
    for r in wrong_arm:
        if r["tweak"] == REG["reverse"]:
            r["config"] = dict(
                BASE, aug_mode="albumentations", lr=0.001
            )  # more than the one change
        if r["tweak"] == REG["control"]:
            r["config"] = dict(BASE, lr=0.001)  # not its baseline
    st = U.status(wrong_arm, now="2026-10-29T00:00:00")
    assert (st["control_cycles"], st["reverse_cycles"], st["ended_by"]) == (0, 0, None)
