"""The replicate rule in the live loop (scripts/training/replicate_rule.py, run_autoresearch_loop.py)."""

import ast
import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from scripts.training import replicate_rule as RL
from scripts.training.config import ExperimentConfig
from scripts.training.promotion import (
    validation_inputs_fingerprint,
    validation_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
INC = 0.265762


def _record(
    start, tweak, f1, auc, epoch="e1", inc=INC, status="REVERTED", budget=900, **result
):
    return {
        "started": start, "tweak": tweak, "commit": epoch, "code_changes": [], "status": status, "budget_s": budget,
        "incumbent_sha256": "a" * 64,
        "result": {"val_f1": f1, "roc_auc": auc, "incumbent_val_f1": inc, "promotion_blocked": None,
                   "val_protocol": validation_protocol(),
                   "validation_diag": {"complete": True, "protocol": validation_protocol(),
                                       "inputs_sha256": "shared-inputs", "requested_patches": 400,
                                       "scored_patches": 400, "batch_errors": 0}, **result},
    }  # fmt: skip


def test_replaying_the_window_fires_where_the_registered_test_did():
    """The confirmation's window (audited rows, #254), one cycle at a time as the loop would see it."""
    window = json.loads(
        (ROOT / "reports/loop_tweak_confirmation_corrected_2026-10-27.json").read_text()
    )
    registered = json.loads(
        (
            ROOT / "reports/loop_replicate_rule_window_corrected_2026-10-27.json"
        ).read_text()
    )
    rows = sorted(window["rows"], key=lambda r: r["start"])
    records = [
        _record(r["start"], r["tweak"], r["val_f1"], r["roc_auc"], epoch=r["epoch"])
        for r in rows
    ]
    fired = [
        j for j in range(len(records)) if RL.decide(records[:j], records[j])["fires"]
    ]
    first = registered["first_promotion"]
    assert (
        records[fired[0]]["started"] == first["start"]
        and records[fired[0]]["tweak"] == first["tweak"]
    )
    got = RL.decide(records[: fired[0]], records[fired[0]])
    assert (
        round(got["score"], 4) == first["score"]
        and got["tweak_cycles"] == first["tweak_cycles_so_far"]
    )
    assert {records[j]["tweak"] for j in fired} == {"aug_mode_batchgeneratorsv2"}


def test_only_scored_cycles_against_the_same_incumbent_at_the_same_budget_are_read():
    keep = [
        _record(f"2026-11-01T{h:02d}:00:00", f"t{h % 3}", 0.27, 0.58) for h in range(6)
    ]
    drop = [
        _record(
            "2026-11-01T07:00:00", "t0", 0.27, 0.58, inc=0.2710
        ),  # another incumbent
        _record("2026-11-01T08:00:00", "t0", 0.27, 0.58, budget=3600),
        _record("2026-11-01T09:00:00", "t0", 0.27, 0.58, status="CRASHED"),
        _record(
            "2026-11-01T10:00:00", "t0", 0.27, 0.58, promotion_blocked="inputs differ"
        ),
        {**_record("2026-11-01T11:00:00", "t0", 0.27, 0.58), "result": None},
    ]
    current = _record("2026-11-01T12:00:00", "t1", 0.27, 0.58)
    rows = RL.rows([*keep, *drop], current)
    assert [r["start"] for r in rows] == [r["started"] for r in [*keep, current]]
    assert len({r["epoch"] for r in rows}) == 1


@pytest.mark.parametrize(
    "change", ["checkpoint", "inputs", "protocol", "incomplete", "missing identity"]
)
def test_matching_f1_does_not_make_other_validation_or_checkpoint_records_comparable(
    change,
):
    prior = _record("2026-11-01T07:00:00", "t0", 0.27, 0.58)
    current = _record("2026-11-01T08:00:00", "t1", 0.27, 0.58)
    if change == "checkpoint":
        prior["incumbent_sha256"] = "b" * 64
    elif change == "missing identity":
        del prior["incumbent_sha256"]
    elif change == "inputs":
        prior["result"]["validation_diag"]["inputs_sha256"] = "another-input"
    elif change == "protocol":
        prior["result"]["val_protocol"] = "another protocol"
        prior["result"]["validation_diag"]["protocol"] = "another protocol"
    else:
        prior["result"]["validation_diag"]["complete"] = False
    assert RL.rows([prior], current) == RL.rows([], current)


@pytest.mark.parametrize("contents", ['{"partial":', "null\n"])
def test_a_corrupt_cycle_journal_is_refused_instead_of_selectively_dropping_observations(
    tmp_path, contents
):
    import run_autoresearch_loop as loop

    journal = tmp_path / "cycles.jsonl"
    journal.write_text(
        json.dumps(_record("2026-11-01T07:00:00", "t0", 0.27, 0.58)) + "\n" + contents
    )
    with pytest.raises(ValueError, match="cycle journal"):
        loop.read_cycle_records(journal)


@pytest.mark.parametrize(
    "change, reason",
    [
        ({"promotion_blocked": "the inputs differ"}, "blocked"),
        ({"validation_diag": {"complete": False}}, "incomplete"),
        ({"submittable": False}, "prize gates"),
        ({"ap_prevalence_lift": 1.02}, "AP lift"),
        ({"val_f1": INC}, "does not beat"),
    ],
)
def test_a_firing_promotes_only_a_candidate_that_passes_every_other_gate(
    change, reason
):
    ok = {"val_f1": 0.2712, "incumbent_val_f1": INC, "ap_prevalence_lift": 1.24, "submittable": True,
          "promotion_blocked": None, "validation_diag": {"complete": True}}  # fmt: skip
    assert RL.eligible(ok, enforce_prize_gates=True) is None
    assert reason in RL.eligible({**ok, **change}, enforce_prize_gates=True)
    if "submittable" in change:
        assert RL.eligible({**ok, **change}, enforce_prize_gates=False) is None


def test_the_gate_constant_is_train_pys():
    tree = ast.parse((ROOT / "scripts/training/train.py").read_text())
    margin = next(
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and getattr(n.targets[0], "id", None) == "LIFT_MARGIN"
    )
    assert margin == RL.LIFT_MARGIN


# One cycle of the real loop, with training replaced by what train.py writes.

PRIOR = 5  # earlier cycles of the tweak the loop runs; the cycle run is its 6th


def _history(tweak_f1, other_f1, inc=INC):
    out, t = [], 0
    for k in range(30):
        tw = (
            "lr_0.002"
            if k % 6 == 0 and sum(r["tweak"] == "lr_0.002" for r in out) < PRIOR
            else f"other_{k % 4}"
        )
        f1 = (
            tweak_f1 + 0.0004 * (k % 3)
            if tw == "lr_0.002"
            else other_f1 + 0.0004 * (k % 5 - 2)
        )
        auc = (
            0.590 + 0.001 * (k % 3) if tw == "lr_0.002" else 0.578 + 0.001 * (k % 5 - 2)
        )
        out.append(
            _record(
                f"2026-11-01T{t // 60:02d}:{t % 60:02d}:00",
                tw,
                f1,
                auc,
                epoch=None,
                inc=inc,
            )
        )
        t += 17
    for r in out:
        r["code_changes"] = None
    return out


def _cycle(
    tmp_path,
    monkeypatch,
    history,
    f1=0.2716,
    inc=INC,
    rule_on=True,
    broken=False,
    bad_candidate=False,
    invalid_header=None,
):
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(loop, "__file__", str(tmp_path / "run_autoresearch_loop.py"))
    monkeypatch.setattr(loop.signal, "signal", lambda *args: None)
    monkeypatch.setattr(loop.time, "sleep", lambda *args: None)
    hours = iter([12, 12, 20])  # one day cycle, then end the shift
    monkeypatch.setattr(
        loop.time, "localtime", lambda: SimpleNamespace(tm_hour=next(hours))
    )
    monkeypatch.setattr(
        loop, "tweak_templates", [{"family": "lr", "attr": "lr", "vals": [0.002]}]
    )
    monkeypatch.setattr(loop, "REPLICATE_RULE", rule_on)
    if broken:
        monkeypatch.setattr(RL, "decide", lambda records, current: 1 / 0)
    base = ExperimentConfig()
    base.save(tmp_path / "config.json")
    protocol = validation_protocol(base.depth_band)
    inputs = validation_inputs_fingerprint(base.val_uri, base.depth_band)
    weights = {"w": torch.zeros(2, 3)}
    common = {"val_protocol": protocol, "val_bpb": 0.36, "avg_skel_dist": 28.9, "avg_centerline_dice": 0.22,
              "avg_cc_diff": 1.392, "submittable": True, "window_ok": True, "window_mm": 0.512,
              "villa_metrics_ok": True, "roc_auc": 0.5905, "ap_prevalence_lift": 1.24,
              "validation_diag": {"complete": True, "inputs_sha256": inputs,
                                  "protocol": protocol, "requested_patches": 400,
                                  "scored_patches": 400, "batch_errors": 0}}  # fmt: skip
    torch.save({"model_state_dict": weights, "val_f1": inc, **common, "config": asdict(base)}, tmp_path / "best_model.pt")  # fmt: skip
    digest = hashlib.sha256((tmp_path / "best_model.pt").read_bytes()).hexdigest()
    for record in history:
        record["incumbent_sha256"] = digest
        record["result"]["val_protocol"] = protocol
        record["result"]["validation_diag"] = dict(common["validation_diag"])
    (tmp_path / "cycles.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in history)
    )
    if invalid_header:
        (tmp_path / invalid_header).write_text("invalid header\n")
    commits = []

    class FakeSupervisor:
        def run(self, command, **kwargs):
            if "--smoke" in command:
                return subprocess.CompletedProcess(command, 0)
            cfg = json.loads((tmp_path / "config_temp.json").read_text())
            saved = {"model_state_dict": weights, "val_f1": f1, **common, "config": cfg}
            if bad_candidate:
                saved["ap_prevalence_lift"] = 0.0
            torch.save(saved, tmp_path / "last_model.pt")
            row = ["2026-11-01 09:00:00", "0.360000", "28.900000", "0.220000", "1.392", "1.072", "0.3000",
                   "0.500000", "0.75", "10.227", "9087.7", json.dumps(cfg)]  # fmt: skip
            with open(tmp_path / "history.tsv", "a") as h:
                if h.tell() == 0:
                    h.write("\t".join(RL.HISTORY_COLUMNS) + "\n")
                h.write("\t".join(row) + "\n")
            result = {"is_success": False, "val_f1": f1, "roc_auc": 0.5905, "incumbent_val_f1": inc,
                      "ap_prevalence_lift": 1.24, "submittable": True, "promotion_blocked": None,
                      "val_protocol": protocol, "validation_diag": dict(common["validation_diag"])}  # fmt: skip
            (tmp_path / "run_result.json").write_text(json.dumps(result))
            return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(loop, "supervisor", FakeSupervisor())

    def commit(message):
        commits.append(message)
        return True

    monkeypatch.setattr(loop, "commit_promotion", commit)
    loop.main()
    record = json.loads((tmp_path / loop.CYCLES_FILE).read_text().splitlines()[-1])
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    return record, log, commits


def test_the_loop_promotes_a_tweaks_cycle_when_the_rule_fires(tmp_path, monkeypatch):
    record, log, commits = _cycle(tmp_path, monkeypatch, _history(0.2714, 0.2672))
    assert record["status"] == "SUCCESS" and record["replicate_rule"]["fires"]
    assert record["replicate_rule"]["tweak_cycles"] == PRIOR + 1
    assert (tmp_path / "best_model.pt").read_bytes() == (
        tmp_path / "last_model.pt"
    ).read_bytes()
    assert ExperimentConfig.load(tmp_path / "config.json").lr == 0.002
    (message,) = commits
    assert "replicate rule" in message and "lr_0.002" in message
    assert "## Cycle 1: lr_0.002 (SUCCESS)" in log and "replicate rule" in log
    assert len((tmp_path / "results.tsv").read_text().splitlines()) == 2
    assert next((tmp_path / "local_data/loop_promotions").iterdir()).is_dir()


def test_a_tweak_no_better_than_the_others_is_not_promoted(tmp_path, monkeypatch):
    record, log, commits = _cycle(
        tmp_path, monkeypatch, _history(0.2672, 0.2672), f1=0.2675
    )
    assert (
        record["status"] == "REVERTED"
        and not record["replicate_rule"]["fires"]
        and not commits
    )
    assert ExperimentConfig.load(tmp_path / "config.json").lr != 0.002


def test_the_checkpoint_must_match_the_result_that_made_the_rule_fire(
    tmp_path, monkeypatch
):
    record, log, commits = _cycle(
        tmp_path, monkeypatch, _history(0.2714, 0.2672), bad_candidate=True
    )
    assert record["status"] == "REVERTED" and not commits
    assert "candidate" in record["replicate_rule"]["error"]
    assert torch.load(tmp_path / "best_model.pt", weights_only=False)["val_f1"] == INC


@pytest.mark.parametrize("header", ["results.tsv", "prize_readiness.tsv"])
def test_log_header_refusals_do_not_exit_the_loop(tmp_path, monkeypatch, header):
    record, log, commits = _cycle(
        tmp_path, monkeypatch, _history(0.2714, 0.2672), invalid_header=header
    )
    assert record["status"] == "REVERTED" and not commits
    assert "header" in record["replicate_rule"]["error"]
    assert torch.load(tmp_path / "best_model.pt", weights_only=False)["val_f1"] == INC
    assert (tmp_path / header).read_text() == "invalid header\n"


def test_the_live_rule_installs_the_bytes_checked_before_the_path_changes(
    tmp_path, monkeypatch
):
    from scripts import promote_loop_candidate as P

    original_history = P.history_row
    checked = {}

    def replaced_after_checks(repo, candidate):
        row = original_history(repo, candidate)
        path = repo / "last_model.pt"
        checked["raw"] = path.read_bytes()
        path.write_bytes(b"changed after checks")
        return row

    monkeypatch.setattr(P, "history_row", replaced_after_checks)
    record, log, commits = _cycle(tmp_path, monkeypatch, _history(0.2714, 0.2672))
    assert record["status"] == "SUCCESS" and commits
    assert (tmp_path / "best_model.pt").read_bytes() == checked["raw"]
    kept = Path(record["replicate_rule"]["kept"])
    assert (
        record["incumbent_sha256"]
        == hashlib.sha256((kept / "best_model.pt").read_bytes()).hexdigest()
    )


def test_a_firing_whose_candidate_does_not_beat_the_incumbent_is_not_promoted(
    tmp_path, monkeypatch
):
    """The rule compares the tweak with the other tweaks; the incumbent here scored above all of them."""
    record, log, commits = _cycle(
        tmp_path, monkeypatch, _history(0.2714, 0.2672, inc=0.2750), inc=0.2750
    )
    assert record["replicate_rule"]["fires"]
    assert record["status"] == "REVERTED" and not commits
    assert "does not beat" in record["replicate_rule"]["refused"]


def test_the_rule_can_be_turned_off_and_never_stops_the_loop(
    tmp_path, monkeypatch, capsys
):
    (tmp_path / "off").mkdir()
    record, log, commits = _cycle(
        tmp_path / "off", monkeypatch, _history(0.2714, 0.2672), rule_on=False
    )
    assert (
        record["status"] == "REVERTED"
        and record.get("replicate_rule") is None
        and not commits
    )
    (tmp_path / "broken").mkdir()
    record, log, commits = _cycle(
        tmp_path / "broken", monkeypatch, _history(0.2714, 0.2672), broken=True
    )
    assert (
        record["status"] == "REVERTED"
        and "ZeroDivisionError" in record["replicate_rule"]["error"]
    )
    assert "the replicate rule failed" in capsys.readouterr().out
