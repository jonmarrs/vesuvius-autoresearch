"""The no-change control in the loop's tweak sampler (run_autoresearch_loop.py)."""

import json
import subprocess
from dataclasses import asdict
from types import SimpleNamespace

import run_autoresearch_loop as loop
from scripts.training.config import ExperimentConfig

CONTROL = next(t for t in loop.tweak_templates if t.get("control"))
LR = {"family": "lr", "attr": "lr", "vals": [0.002]}


def test_the_control_is_offered_beside_the_tweaks_while_config_json_fits_the_cap():
    config = ExperimentConfig()
    active, _ = loop.tweak_proposals(config)
    assert CONTROL in active and CONTROL["family"] == "control"
    assert any(not t.get("control") for t in active)
    over, _ = loop.tweak_proposals(config, cap=loop.complexity_score(config) - 0.01)
    assert CONTROL not in over


def _one_cycle(tmp_path, monkeypatch, templates, pick, cycles=1):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(loop, "__file__", str(tmp_path / "run_autoresearch_loop.py"))
    monkeypatch.setattr(loop.signal, "signal", lambda *args: None)
    monkeypatch.setattr(loop.time, "sleep", lambda *args: None)
    hours = iter([12] * (cycles + 1) + [20])
    monkeypatch.setattr(loop.time, "localtime", lambda: SimpleNamespace(tm_hour=next(hours)))  # fmt: skip
    monkeypatch.setattr(loop, "tweak_templates", templates)
    monkeypatch.setattr(loop.random, "choices", lambda population, weights, k: [pick(population) if callable(pick) else pick])  # fmt: skip
    ExperimentConfig().save(tmp_path / "config.json")
    ran = []

    class FakeSupervisor:
        def run(self, command, **kwargs):
            if "--smoke" in command:
                return subprocess.CompletedProcess(command, 0)
            ran.append(json.loads((tmp_path / "config_temp.json").read_text()))
            (tmp_path / "run_result.json").write_text(json.dumps({"is_success": False, "val_f1": 0.27}))  # fmt: skip
            return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(loop, "supervisor", FakeSupervisor())
    monkeypatch.setattr(loop, "commit_promotion", lambda message: True)
    loop.main()
    path = tmp_path / loop.CYCLES_FILE
    records = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []  # fmt: skip
    return ran, records


def test_a_control_cycle_runs_config_json_unchanged_and_is_named_so(
    tmp_path, monkeypatch
):
    ran, records = _one_cycle(tmp_path, monkeypatch, [LR, CONTROL], CONTROL)
    (record,) = records
    assert (record["tweak"], record["family"], record["attr"], record["value"]) == (
        loop.CONTROL_TWEAK, "control", None, None,
    )  # fmt: skip
    base = asdict(ExperimentConfig.load(tmp_path / "config.json"))
    volatile = ("pinned", "time_budget")
    assert {k: v for k, v in ran[0].items() if k not in volatile} == {k: v for k, v in base.items() if k not in volatile}  # fmt: skip
    assert record["config"] == record["baseline_config"] == ran[0]
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert f"## Cycle 1: {loop.CONTROL_TWEAK} (REVERTED)" in log


def test_the_sprint_still_ends_when_no_tweak_fits(tmp_path, monkeypatch, capsys):
    ran, records = _one_cycle(tmp_path, monkeypatch, [CONTROL], CONTROL)
    assert not ran and not records
    assert "No tweak differs from the baseline" in capsys.readouterr().out


def test_control_cooldown_survives_retry_exhaustion_and_expires_after_twenty_cycles(
    tmp_path, monkeypatch
):
    # Prefer the control whenever it is offered. With just one other config,
    # retries exhaust every subsequent cycle; that must not reset its cooldown.
    ran, records = _one_cycle(
        tmp_path,
        monkeypatch,
        [LR, CONTROL],
        lambda population: CONTROL if CONTROL in population else LR,
        cycles=22,
    )
    assert len(ran) == 22
    assert [i + 1 for i, r in enumerate(records) if r["family"] == "control"] == [1, 22]
    assert len(json.loads((tmp_path / loop.RECENT_CONFIGS_FILE).read_text())) == 20
