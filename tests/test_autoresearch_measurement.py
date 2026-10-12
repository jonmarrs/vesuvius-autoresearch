"""What a loop cycle measures and what a promotion compares.

Before 2026-10-12: training read the patch catalogue in raster order from index 0,
so every cycle fine-tuned on the same strip at the top of the fragment; the
validation that decides promotion read the first 100 *batches*, so its patches
depended on batch_size; the step-based LR schedule assumed 0.2 s/step and ended
every production cycle inside warmup; and an unreadable best_model.pt let any
candidate replace it. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-12_AUTORESEARCH_LOOP.md.
"""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train  # noqa: E402

from scripts.training import promotion  # noqa: E402
from scripts.training.config import ExperimentConfig  # noqa: E402


class Catalogue(torch.utils.data.Dataset):
    """Patch i is ink-free when i % 3 == 0; ``fail`` lists unreadable patches."""

    def __init__(self, size, fail=()):
        self.size, self.fail, self.reads = size, set(fail), []

    def __len__(self):
        return self.size

    def __getitem__(self, i):
        self.reads.append(i)
        if i in self.fail:
            raise RuntimeError(f"failed to read labeled patch {i}")
        x = torch.full((1, 12, 4, 4), float(i % 7) / 7)
        label = torch.zeros(4, 4) if i % 3 == 0 else (x[0, 0] > 0.4).float()
        label[0, 0] = 0.0 if i % 3 == 0 else 1.0
        return x, label, torch.zeros(1, 1, 4, 4)


class MeanInk(torch.nn.Module):
    def forward(self, x):
        return (x[:, :1].mean(2) - 0.4) * 8, None


# --- validation sample --------------------------------------------------------


def test_validation_sample_is_fixed_and_spread_over_the_catalogue():
    first = promotion.validation_indices(6466)
    assert np.array_equal(first, promotion.validation_indices(6466))
    assert len(first) == promotion.VALIDATION_SAMPLE_PATCHES == len(set(first))
    # v1 used the first 400 entries (raster order: the top of the fragment).
    assert first.max() > 0.9 * 6466 and first.min() < 0.1 * 6466
    assert np.array_equal(promotion.validation_indices(17), np.arange(17))
    with pytest.raises(ValueError, match="empty"):
        promotion.validation_indices(0)


def test_batch_size_does_not_change_what_validation_scores():
    results = []
    for batch_size in (1, 4, 8, 16, 24):
        data = Catalogue(1000)
        probs, targets, diag = train.collect_validation_predictions(
            MeanInk(), data, 8, torch.device("cpu"), batch_size=batch_size
        )
        metrics = train.pooled_segmentation_metrics(probs, targets)
        results.append((sorted(data.reads), diag["usable_patches"], metrics["val_f1"]))
        assert diag["complete"] and diag["requested_patches"] == 400
        # Ink-free patches are dropped one by one, not with their batch.
        assert diag["usable_patches"] + diag["empty_target_patches"] == 400
    assert all(result == results[0] for result in results)


def test_a_failed_read_makes_the_sample_incomplete():
    sample = promotion.validation_indices(1000)
    data = Catalogue(1000, fail={int(sample[5])})
    _, _, diag = train.collect_validation_predictions(
        MeanInk(), data, 8, torch.device("cpu"), batch_size=4
    )
    assert diag["batch_errors"] == 1 and not diag["complete"]


# --- training sample ----------------------------------------------------------


def _indices(loader, steps):
    seen = []
    for batch in itertools.islice(loader, steps):
        seen.extend(int(i) for i in batch)
    return seen


def test_a_cycle_trains_on_patches_from_the_whole_catalogue():
    """7,345 is the production catalogue; ~250 day-shift steps at batch 4."""
    catalogue = list(range(7345))
    seen = _indices(train.shuffled_loader(catalogue, 4, seed=11), 250)
    assert len(set(seen)) == 1000
    assert max(seen) > 0.9 * 7345 and min(seen) < 0.1 * 7345  # was 0..999
    other = _indices(train.shuffled_loader(catalogue, 4, seed=12), 250)
    assert len(set(seen) & set(other)) < 300  # successive cycles differ
    assert seen == _indices(train.shuffled_loader(catalogue, 4, seed=11), 250)


def test_each_pass_over_the_catalogue_is_a_fresh_permutation():
    loader = train.shuffled_loader(list(range(50)), 5, seed=3)
    first, second = _indices(loader, 10), _indices(loader, 10)
    assert sorted(first) == sorted(second) == list(range(50))
    assert first != second


# --- learning-rate schedule ---------------------------------------------------


def test_lr_schedule_follows_the_time_budget_not_a_step_estimate():
    factor = train.budget_lr_factor
    assert factor(0.0) == 0.0
    assert factor(train.WARMUP_FRACTION / 2) == pytest.approx(0.5)
    assert factor(train.WARMUP_FRACTION) == pytest.approx(1.0)
    assert factor((1 + train.WARMUP_FRACTION) / 2) == pytest.approx(0.5)
    assert factor(1.0) == pytest.approx(0.0, abs=1e-12)
    assert factor(1.7) == pytest.approx(0.0, abs=1e-12)
    # A 900 s cycle at 3.6 s/step (~250 steps) now peaks and anneals; the old
    # step schedule ended at 250/562 of warmup.
    peaks = [factor(step * 3.6 / 900) for step in range(250)]
    assert max(peaks) > 0.99 and peaks[-1] < 0.01


# --- incumbent and promotion --------------------------------------------------


def _checkpoint(path, **fields):
    payload = {
        "model_state_dict": {"w": torch.zeros(300, 300)},
        "val_f1": 0.47,
        "val_protocol": promotion.VALIDATION_PROTOCOL,
    }
    payload.update(fields)
    torch.save(payload, path)
    return path


def _decide(path, val_f1=0.6, lift=1.5, submittable=True, complete=True):
    return train.promotion_decision(
        val_f1,
        lift,
        submittable=submittable,
        enforce_prize_gates=True,
        validation_complete=complete,
        incumbent_path=str(path),
    )


def test_a_truncated_incumbent_blocks_promotion_instead_of_being_replaced(tmp_path):
    path = _checkpoint(tmp_path / "best_model.pt")
    path.write_bytes(path.read_bytes()[:50_000])
    promote, incumbent, reason = _decide(path, val_f1=0.20)
    assert not promote and np.isnan(incumbent)
    assert "cannot be read" in reason


@pytest.mark.parametrize(
    "fields,message",
    [
        ({"val_protocol": None}, "v1 (unrecorded)"),
        ({"val_protocol": "older"}, "older"),
        ({"val_f1": float("nan")}, "no finite val_f1"),
        ({"val_f1": None}, "no finite val_f1"),
    ],
)
def test_an_incomparable_incumbent_blocks_promotion(tmp_path, fields, message):
    path = _checkpoint(tmp_path / "best_model.pt", **fields)
    promote, _, reason = _decide(path)
    assert not promote
    assert message in reason and "reevaluate_best_model.py" in reason


def test_promotion_compares_like_with_like(tmp_path):
    path = _checkpoint(tmp_path / "best_model.pt")
    assert _decide(path, val_f1=0.47 + 2 * train.F1_NOISE_TOLERANCE) == (
        True,
        0.47,
        None,
    )
    assert _decide(path, val_f1=0.48) == (False, 0.47, None)
    assert _decide(path, submittable=False) == (False, 0.47, None)
    promote, _, reason = _decide(path, complete=False)
    assert not promote and "incomplete" in reason
    assert _decide(tmp_path / "absent.pt", val_f1=0.2)[:2] == (True, float("-inf"))


def test_an_interrupted_save_leaves_the_previous_checkpoint(tmp_path, monkeypatch):
    path = _checkpoint(tmp_path / "best_model.pt")
    before = path.read_bytes()
    real_save = torch.save

    def dies_midway(payload, handle):
        real_save({"partial": True}, handle)
        raise KeyboardInterrupt("SIGTERM during save")

    monkeypatch.setattr(torch, "save", dies_midway)
    with pytest.raises(KeyboardInterrupt):
        promotion.save_checkpoint_atomic({"val_f1": 0.9}, str(path))
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["best_model.pt"]
    monkeypatch.setattr(torch, "save", real_save)
    promotion.save_checkpoint_atomic({"val_f1": 0.9}, str(path))
    assert torch.load(path)["val_f1"] == 0.9


# --- loop ---------------------------------------------------------------------


def _drive_loop(tmp_path, monkeypatch, cycles, result=None):
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(loop, "__file__", str(tmp_path / "run_autoresearch_loop.py"))
    monkeypatch.setattr(loop.signal, "signal", lambda *args: None)
    monkeypatch.setattr(loop.time, "sleep", lambda *args: None)
    hours = iter([12] * (cycles + 1) + [20])
    monkeypatch.setattr(
        loop.time, "localtime", lambda: SimpleNamespace(tm_hour=next(hours))
    )
    monkeypatch.setattr(
        loop,
        "tweak_templates",
        [{"family": "lr", "attr": "lr", "vals": [1e-3, 5e-4, 1e-4, 5e-5]}],
    )
    monkeypatch.setattr(loop.os, "system", lambda command: 0)
    launched = []

    class FakeSupervisor:
        def run(self, command, **kwargs):
            if "--smoke" in command:
                return subprocess.CompletedProcess(command, 0)
            launched.append(json.loads((tmp_path / "config_temp.json").read_text()))
            if result is None:
                return subprocess.CompletedProcess(command, 1)
            (tmp_path / "run_result.json").write_text(json.dumps(result))
            return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(loop, "supervisor", FakeSupervisor())
    loop.main()
    return launched


def test_every_cycle_is_a_tweak_of_the_promoted_config(tmp_path, monkeypatch):
    """Cycle 10 used to inject a timesformer/patch-256 config that the VRAM gate
    always skipped and that, had it run, could have been promoted."""
    ExperimentConfig(architecture="resenc_unet", lr=2e-3).save(tmp_path / "config.json")
    launched = _drive_loop(tmp_path, monkeypatch, cycles=10)
    assert len(launched) == 10
    assert {c["architecture"] for c in launched} == {"resenc_unet"}
    assert {c["patch_size"] for c in launched} == {64}
    assert not any(c["pinned"] for c in launched)


def test_loop_will_not_start_over_an_incomparable_incumbent(
    tmp_path, monkeypatch, capsys
):
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt", val_protocol=None)
    launched = _drive_loop(tmp_path, monkeypatch, cycles=1)
    assert launched == []
    assert "Not starting" in capsys.readouterr().out
    assert not (tmp_path / "sprint_logs").exists()


def test_a_blocked_promotion_is_recorded_in_the_sprint_log(tmp_path, monkeypatch):
    ExperimentConfig().save(tmp_path / "config.json")
    result = {"is_success": False, "val_f1": 0.5, "promotion_blocked": "why"}
    _drive_loop(tmp_path, monkeypatch, cycles=1, result=result)
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "REVERTED" in log and "Promotion blocked: why" in log
