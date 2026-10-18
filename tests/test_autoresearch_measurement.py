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
import os
import pickle
import signal
import subprocess
import sys
import threading
import time
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
        # Ink-free patches are counted one by one, not with their batch.
        assert diag["usable_patches"] + diag["empty_target_patches"] == 400
    assert all(result == results[0] for result in results)


def _collect(data, protocol=promotion.VALIDATION_PROTOCOL):
    return train.collect_validation_predictions(
        MeanInk(), data, 8, torch.device("cpu"), batch_size=4, protocol=protocol
    )


def test_the_protocol_scores_every_patch_of_the_draw():
    # Finding 88: on its ink-containing patches alone, F1 could not tell the
    # project's detector from calling every pixel ink.
    probs, targets, diag = _collect(Catalogue(1000))
    ink = sum(float(t.sum()) >= 1.0 for t in targets)
    assert len(probs) == len(targets) == diag["scored_patches"] == 400
    assert diag["usable_patches"] == ink
    assert diag["empty_target_patches"] == 400 - ink > 0


def test_protocol_v2_scored_only_the_ink_containing_patches():
    v2 = promotion.validation_protocol(None, base=promotion.INK_ONLY_PROTOCOL)
    assert v2 == "seeded-sample-400-v2"
    probs, targets, diag = _collect(Catalogue(1000), protocol=v2)
    assert len(probs) == diag["usable_patches"] == diag["scored_patches"]
    assert diag["usable_patches"] + diag["empty_target_patches"] == 400
    assert all(float(t.sum()) >= 1.0 for t in targets)
    kept, kept_targets = train.ink_containing(*_collect(Catalogue(1000))[:2])
    assert all(torch.equal(a, b) for a, b in zip(kept, probs, strict=True))
    assert all(torch.equal(a, b) for a, b in zip(kept_targets, targets, strict=True))


def test_a_sample_under_an_unknown_protocol_is_refused():
    with pytest.raises(ValueError, match="unknown validation protocol"):
        _collect(Catalogue(1000), protocol="seeded-sample-400-v9")


def test_a_failed_read_makes_the_sample_incomplete():
    sample = promotion.validation_indices(1000)
    data = Catalogue(1000, fail={int(sample[5])})
    _, _, diag = train.collect_validation_predictions(
        MeanInk(), data, 8, torch.device("cpu"), batch_size=4
    )
    assert diag["batch_errors"] == 1 and not diag["complete"]


def _fragment(root, labels=b"ink"):
    frag = root / "frag"
    (frag / "surface_volume.zarr").mkdir(parents=True)
    (frag / "inklabels.png").write_bytes(labels)
    (frag / "mask.png").write_bytes(b"mask")
    return frag


def test_the_inputs_fingerprint_names_what_the_sample_is_drawn_from(
    tmp_path, monkeypatch
):
    """The protocol string names the draw; the fingerprint catches what it does
    not: another label file, mask, catalogue or fragment."""
    frag = _fragment(tmp_path)
    monkeypatch.chdir(tmp_path)
    uri = "frag/surface_volume.zarr"
    fingerprint = promotion.validation_inputs_fingerprint
    base = fingerprint(uri)
    assert len(base) == 64
    assert fingerprint(str(tmp_path / uri)) == base  # named, not resolved
    assert fingerprint(uri + "/") == base
    (frag / "notes.txt").write_text("unrelated")
    assert fingerprint(uri) == base
    assert fingerprint(uri, [1, 27]) != base
    (frag / "inklabels.png").write_bytes(b"ink, relabeled")
    relabeled = fingerprint(uri)
    assert relabeled != base
    # refine_labels_villa.py --in-place writes this beside inklabels.png, and
    # validation prefers it.
    (frag / "inklabels_refined.png").write_bytes(b"ink, relabeled")
    assert promotion.validation_label_path(uri).endswith("inklabels_refined.png")
    assert fingerprint(uri) not in (base, relabeled)
    refined = fingerprint(uri)
    (frag / "patches.json").write_text("{}")
    assert fingerprint(uri) != refined
    (frag / "patches.json").unlink()
    (frag / "mask.png").write_bytes(b"other mask")
    assert fingerprint(uri) != refined


def test_a_volume_rebuilt_in_place_changes_the_fingerprint(tmp_path, monkeypatch):
    frag = _fragment(tmp_path)
    monkeypatch.chdir(tmp_path)
    (frag / "surface_volume.zarr" / "0").mkdir()
    (frag / "surface_volume.zarr" / "0" / ".zarray").write_text('{"shape": [33]}')
    base = promotion.validation_inputs_fingerprint("frag/surface_volume.zarr")
    (frag / "surface_volume.zarr" / "0" / ".zarray").write_text('{"shape": [65]}')
    assert promotion.validation_inputs_fingerprint("frag/surface_volume.zarr") != base


def test_inputs_changed_while_the_dataset_reads_them_are_refused(tmp_path, monkeypatch):
    frag = _fragment(tmp_path)
    monkeypatch.chdir(tmp_path)

    def dataset(*args, **kwargs):
        (frag / "inklabels_refined.png").write_bytes(b"written meanwhile")
        return Catalogue(10)

    monkeypatch.setattr(train, "VesuviusLabeledDataset", dataset)
    config = ExperimentConfig(val_uri="frag/surface_volume.zarr")
    with pytest.raises(RuntimeError, match="changed while they were read"):
        train.build_validation_dataset(config)


def test_training_stops_before_its_budget_on_other_inputs(tmp_path):
    diag = {"protocol": promotion.VALIDATION_PROTOCOL, "inputs_sha256": "a" * 64}
    path = _checkpoint(tmp_path / "best_model.pt", validation_diag=diag)
    data = Catalogue(10)
    data.validation_inputs = "a" * 64
    train.check_validation_inputs(data, promotion.VALIDATION_PROTOCOL, str(path))
    data.validation_inputs = "b" * 64
    with pytest.raises(RuntimeError, match="re-score"):
        train.check_validation_inputs(data, promotion.VALIDATION_PROTOCOL, str(path))
    # Nothing to compare: no incumbent, or one scored before fingerprints.
    train.check_validation_inputs(data, promotion.VALIDATION_PROTOCOL, "absent.pt")
    older = _checkpoint(tmp_path / "older.pt")
    train.check_validation_inputs(data, promotion.VALIDATION_PROTOCOL, str(older))


def test_every_score_records_the_inputs_it_was_drawn_from(tmp_path, monkeypatch):
    frag = _fragment(tmp_path)
    monkeypatch.chdir(tmp_path)
    built = {}

    def dataset(uri, labels, mask, *args, **kwargs):
        built.update(labels=labels, mask=mask)
        return Catalogue(1000)

    monkeypatch.setattr(train, "VesuviusLabeledDataset", dataset)
    (frag / "inklabels_refined.png").write_bytes(b"refined")
    config = ExperimentConfig(
        val_uri="frag/surface_volume.zarr", num_layers=16, depth_band=[1, 27]
    )
    data = train.build_validation_dataset(config)
    assert built["labels"].endswith("inklabels_refined.png")
    expected = promotion.validation_inputs_fingerprint(config.val_uri, [1, 27])
    assert data.validation_inputs == expected
    _, _, diag = train.collect_validation_predictions(
        MeanInk(), data, 8, torch.device("cpu")
    )
    assert diag["inputs_sha256"] == expected


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


def _decide(path, val_f1=0.6, lift=1.5, submittable=True, complete=True, inputs=None):
    return train.promotion_decision(
        val_f1,
        lift,
        submittable=submittable,
        enforce_prize_gates=True,
        validation_complete=complete,
        protocol=promotion.VALIDATION_PROTOCOL,
        incumbent_path=str(path),
        inputs=inputs,
    )


def test_an_incumbent_scored_on_other_inputs_blocks_promotion(tmp_path):
    diag = {"protocol": promotion.VALIDATION_PROTOCOL, "inputs_sha256": "a" * 64}
    path = _checkpoint(tmp_path / "best_model.pt", validation_diag=diag)
    assert _decide(path, inputs="a" * 64) == (True, 0.47, None)
    promote, incumbent, reason = _decide(path, inputs="b" * 64)
    assert not promote and incumbent == 0.47
    assert "differ" in reason and "reevaluate_best_model.py" in reason
    promote, _, reason = _decide(path, inputs=None)
    assert not promote and "no validation-input fingerprint" in reason
    # Before fingerprints, the incumbent is compared on its protocol alone.
    older = _checkpoint(tmp_path / "older.pt")
    assert _decide(older, inputs="b" * 64) == (True, 0.47, None)
    # A fingerprint stored with another protocol's diagnostic does not describe
    # this score: refused, not ignored.
    stale = _checkpoint(
        tmp_path / "stale.pt", validation_diag={**diag, "protocol": "older"}
    )
    promote, _, reason = _decide(stale, inputs="a" * 64)
    assert not promote and "do not belong" in reason
    assert promotion.read_incumbent(str(path), promotion.VALIDATION_PROTOCOL) == (
        0.47,
        "a" * 64,
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


def test_a_saved_checkpoint_keeps_normal_file_permissions(tmp_path):
    """The temporary file mkstemp creates is 0600, and it was renamed as it was:
    every promoted best_model.pt and last_model.pt was readable by its owner
    alone. A replaced file keeps its mode; a new one gets the umask's."""
    import os
    import stat

    path = _checkpoint(tmp_path / "best_model.pt")
    os.chmod(path, 0o640)
    promotion.save_checkpoint_atomic({"val_f1": 0.9}, str(path))
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o640

    umask = os.umask(0o022)
    try:
        fresh = tmp_path / "last_model.pt"
        promotion.save_checkpoint_atomic({"val_f1": 0.9}, str(fresh))
        assert stat.S_IMODE(os.stat(fresh).st_mode) == 0o644
    finally:
        os.umask(umask)


@pytest.mark.parametrize(
    "checkpoint_out, promoted, written",
    [
        (None, False, ["last_model.pt"]),
        (None, True, ["last_model.pt", "best_model.pt"]),
        ("experiments/run.pt", True, ["experiments/run.pt"]),
    ],
)
def test_every_cycle_saves_its_candidate_and_a_promotion_the_incumbent(
    tmp_path, monkeypatch, checkpoint_out, promoted, written
):
    """last_model.pt is the cycle's candidate (scripts/snapshot_loop_candidates.sh
    copies it); a promoted cycle used to write only best_model.pt, so promoted
    candidates were missing from the snapshots. best_model.pt is written last,
    so a run stopped between the two leaves the incumbent the loop records."""
    monkeypatch.chdir(tmp_path)
    saved = []
    monkeypatch.setattr(
        train,
        "save_checkpoint_atomic",
        lambda record, path: saved.append((path, record)),
    )
    record = {"val_f1": 0.5}
    assert train.save_cycle_checkpoints(record, checkpoint_out, promoted) == written
    assert saved == [(path, record) for path in written]
    if checkpoint_out:
        assert (tmp_path / "experiments").is_dir()


def test_train_saves_one_record_through_save_cycle_checkpoints():
    """The three hand-copied payloads had drifted apart (last_model.pt lacked
    avg_mean_ap, checkpoint_out prize_gate_failures). train() now builds one
    record and saves it only through save_cycle_checkpoints."""
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(train.train)))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    names = [getattr(c.func, "id", None) for c in calls]
    assert names.count("save_checkpoint_atomic") == 0
    (save,) = [
        c for c in calls if getattr(c.func, "id", None) == "save_cycle_checkpoints"
    ]
    assert [ast.unparse(a) for a in save.args] == [
        "checkpoint",
        "ckpt_out",
        "is_improvement",
    ]
    (record,) = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and [ast.unparse(t) for t in n.targets] == ["checkpoint"]
        and isinstance(n.value, ast.Dict)
    ]
    keys = {k.value for k in record.keys}
    assert {"model_state_dict", "avg_mean_ap", "prize_gate_failures", "config"} <= keys


# --- loop ---------------------------------------------------------------------


def _drive_loop(
    tmp_path,
    monkeypatch,
    cycles,
    result=None,
    commands=None,
    on_cycle=None,
    run=None,
    preflight_returncode=0,
    commit=lambda message: True,
    signals=None,
):
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(loop, "__file__", str(tmp_path / "run_autoresearch_loop.py"))
    monkeypatch.setattr(
        loop.signal,
        "signal",
        (lambda sig, handler: signals.append(sig))
        if signals is not None
        else (lambda *args: None),
    )
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
    monkeypatch.setattr(loop, "commit_promotion", commit)
    launched = []

    class FakeSupervisor:
        def run(self, command, **kwargs):
            if commands is not None:
                commands.append(list(command))
            # The preflight and the every-5th-cycle benchmark are not training runs.
            if "--smoke" in command:
                if preflight_returncode:
                    kwargs["stdout"].write("PREFLIGHT FAILED: model build error\n")
                return subprocess.CompletedProcess(command, preflight_returncode)
            if "scripts/inference/predict.py" in command:
                return subprocess.CompletedProcess(command, 0)
            launched.append(json.loads((tmp_path / "config_temp.json").read_text()))
            if on_cycle is not None:
                on_cycle(len(launched))
            if run is not None:
                return run(command, kwargs["stdout"])
            if result is None:
                return subprocess.CompletedProcess(command, 1)
            (tmp_path / "run_result.json").write_text(json.dumps(result))
            return subprocess.CompletedProcess(command, 0)

        def stop(self):
            pass

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


def _fingerprinted_incumbent(tmp_path):
    frag = _fragment(tmp_path)
    uri = str(frag / "surface_volume.zarr")
    ExperimentConfig(val_uri=uri).save(tmp_path / "config.json")
    diag = {
        "protocol": promotion.VALIDATION_PROTOCOL,
        "inputs_sha256": promotion.validation_inputs_fingerprint(uri),
    }
    _checkpoint(tmp_path / "best_model.pt", validation_diag=diag)
    return frag


def test_the_loop_stops_before_a_cycle_once_the_validation_labels_change(
    tmp_path, monkeypatch, capsys
):
    """A refined label file written mid-shift (refine_labels_villa.py --in-place)
    would have every later cycle scored on other targets than the incumbent."""
    frag = _fingerprinted_incumbent(tmp_path)

    def refine(cycle):
        (frag / "inklabels_refined.png").write_bytes(b"refined")

    result = {"is_success": False, "val_f1": 0.5}
    launched = _drive_loop(tmp_path, monkeypatch, 3, result=result, on_cycle=refine)
    assert len(launched) == 1
    assert "Stopping before cycle 2" in capsys.readouterr().out
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "Stopped before cycle 2" in log and "re-score" in log


def test_the_loop_will_not_start_on_other_validation_inputs(
    tmp_path, monkeypatch, capsys
):
    frag = _fingerprinted_incumbent(tmp_path)
    (frag / "mask.png").write_bytes(b"another mask")
    assert _drive_loop(tmp_path, monkeypatch, cycles=1) == []
    out = capsys.readouterr().out
    assert "Not starting" in out and "best_model.pt is compared on" in out


def _legacy_incumbent(tmp_path):
    frag = _fragment(tmp_path)
    ExperimentConfig(val_uri=str(frag / "surface_volume.zarr")).save(
        tmp_path / "config.json"
    )
    _checkpoint(tmp_path / "best_model.pt")  # scored before fingerprints
    return frag


def test_an_older_incumbent_is_held_to_the_inputs_found_at_first_use(
    tmp_path, monkeypatch, capsys
):
    """Today's incumbent records no fingerprint, and may stay the incumbent for
    a long time: the loop records the inputs it finds and holds it to them."""
    frag = _legacy_incumbent(tmp_path)

    def refine(cycle):
        (frag / "inklabels_refined.png").write_bytes(b"refined")

    result = {"is_success": False, "val_f1": 0.5}
    launched = _drive_loop(tmp_path, monkeypatch, 3, result=result, on_cycle=refine)
    out = capsys.readouterr().out
    assert "no validation-input fingerprint" in out and "inputs.json" in out
    assert len(launched) == 1 and "Stopping before cycle 2" in out
    # train.py's promotion check reads the same record.
    record = promotion.first_use_record(str(tmp_path / "best_model.pt"))
    assert json.loads(Path(record).read_text())["protocol"] == (
        promotion.VALIDATION_PROTOCOL
    )
    promote, _, reason = _decide(tmp_path / "best_model.pt", inputs="b" * 64)
    assert not promote and "differ" in reason


def test_a_first_use_record_lapses_when_the_incumbent_is_replaced(tmp_path):
    frag = _legacy_incumbent(tmp_path)
    uri = str(frag / "surface_volume.zarr")
    path = str(tmp_path / "best_model.pt")
    assert promotion.check_incumbent(path, uri) == (0.47, "recorded now")
    assert promotion.check_incumbent(path, uri) == (0.47, "first use")
    _checkpoint(tmp_path / "best_model.pt", val_f1=0.5)  # another incumbent
    assert promotion.read_incumbent(path, promotion.VALIDATION_PROTOCOL) == (0.5, None)


def test_unreadable_validation_inputs_stop_the_loop_cleanly(tmp_path):
    frag = _legacy_incumbent(tmp_path)
    path = str(tmp_path / "best_model.pt")
    with pytest.raises(promotion.IncumbentUnavailable, match="cannot be read"):
        promotion.check_incumbent(path, None)
    (frag / "mask.png").unlink()
    (frag / "mask.png").mkdir()  # isfile() is False: hashed as absent, not raised
    promotion.check_incumbent(path, str(frag / "surface_volume.zarr"))


def _history(tmp_path):
    return json.loads((tmp_path / "autoresearch_history.json").read_text())


def test_the_family_weight_decay_is_saved_after_a_reverted_cycle(tmp_path, monkeypatch):
    """Each cycle decays every active family by 5%. Only SUCCESS and CRASH
    saved the weights, so after REVERTED cycles (the usual outcome) the next
    restart put back the weights from before the decay."""
    ExperimentConfig().save(tmp_path / "config.json")
    (tmp_path / "autoresearch_history.json").write_text(json.dumps({"lr": 2.0}))
    seen = []
    result = {"is_success": False, "val_f1": 0.5}
    launched = _drive_loop(
        tmp_path,
        monkeypatch,
        cycles=3,
        result=result,
        on_cycle=lambda n: seen.append(_history(tmp_path)["lr"]),
    )
    assert len(launched) == 3
    # Each cycle's decay is on disk before the next cycle trains.
    assert seen == pytest.approx([2.0, 2.0 * 0.95, 2.0 * 0.95**2])
    assert _history(tmp_path)["lr"] == pytest.approx(2.0 * 0.95**3)


def test_a_promotion_saves_the_decay_and_the_reward(tmp_path, monkeypatch):
    ExperimentConfig().save(tmp_path / "config.json")
    (tmp_path / "autoresearch_history.json").write_text(json.dumps({"lr": 2.0}))
    _drive_loop(tmp_path, monkeypatch, 1, result={"is_success": True, "val_f1": 0.6})
    assert _history(tmp_path)["lr"] == pytest.approx(2.0 * 0.95 + 1)


def test_a_stop_while_recent_configs_are_saved_leaves_the_previous_file(
    tmp_path, monkeypatch
):
    """recent_configs.json was written in place: a stop mid-write left it cut
    short, and the next start read no recent configs at all."""
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    loop.save_recent_configs([{"lr": 1e-3}])
    before = (tmp_path / "recent_configs.json").read_text()
    dump = json.dump

    def stopped_mid_write(data, stream, **kwargs):
        stream.write('[{"lr": ')
        raise SystemExit(0)  # stop.sh: the loop's handler exits, mid-write

    monkeypatch.setattr(loop.json, "dump", stopped_mid_write)
    with pytest.raises(SystemExit):
        loop.save_recent_configs([{"lr": 1e-3}, {"lr": 5e-4}])
    monkeypatch.setattr(loop.json, "dump", dump)
    assert (tmp_path / "recent_configs.json").read_text() == before
    assert loop.load_recent_configs() == [{"lr": 1e-3}]
    assert not list(tmp_path.glob(".recent_configs.json.*"))  # no temporary


def test_the_atomic_json_writer_keeps_the_files_mode(tmp_path, monkeypatch):
    """mkstemp creates 0600: renamed over a tracked 0644 file, it narrowed who
    can read the loop's state."""
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    (tmp_path / "recent_configs.json").write_text("[]")
    os.chmod(tmp_path / "recent_configs.json", 0o644)
    loop.save_recent_configs([{"lr": 1e-3}])
    assert (tmp_path / "recent_configs.json").stat().st_mode & 0o777 == 0o644
    assert loop.load_recent_configs() == [{"lr": 1e-3}]


def test_the_atomic_json_writer_gives_a_new_file_the_umasks_mode(tmp_path, monkeypatch):
    """A first write (no file yet) kept mkstemp's 0600."""
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    umask = os.umask(0o022)
    try:
        loop.save_history({"lr": 1.0})
    finally:
        os.umask(umask)
    assert (tmp_path / "autoresearch_history.json").stat().st_mode & 0o777 == 0o644


def test_a_crashed_cycle_leaves_the_family_weights_alone(tmp_path, monkeypatch):
    """A crash ran no experiment: a broken environment must not wear the
    weights down to the floor, as the per-cycle decay used to."""
    ExperimentConfig().save(tmp_path / "config.json")
    (tmp_path / "autoresearch_history.json").write_text(json.dumps({"lr": 2.0}))
    launched = _drive_loop(tmp_path, monkeypatch, cycles=2)  # no result: crashes
    assert len(launched) == 2
    assert _history(tmp_path)["lr"] == 2.0


def test_an_unreadable_history_is_moved_aside_not_overwritten(
    tmp_path, monkeypatch, capsys
):
    ExperimentConfig().save(tmp_path / "config.json")
    (tmp_path / "autoresearch_history.json").write_text('{"lr": 7.')  # cut short
    _drive_loop(tmp_path, monkeypatch, 1, result={"is_success": False, "val_f1": 0.5})
    (aside,) = tmp_path.glob("autoresearch_history.json.unreadable-*")
    assert aside.read_text() == '{"lr": 7.'
    assert _history(tmp_path) == {"lr": 1.0}
    assert "unreadable" in capsys.readouterr().out
    assert not list(tmp_path.glob(".autoresearch_history.json.*"))  # no temporary


def _promoting_run(tmp_path, returncode=0, result=True, timeout=False):
    """A training run that promotes as train.py does (best_model.pt replaced by
    os.replace, then run_result.json), then exits or is killed at the timeout."""

    def run(command, log):
        _checkpoint(tmp_path / "candidate.pt", val_f1=0.9)
        os.replace(tmp_path / "candidate.pt", tmp_path / "best_model.pt")
        for name in ("results.tsv", "prize_readiness.tsv"):  # train.py's rows
            with open(tmp_path / name, "a") as f:
                f.write("promoted\t0.9\n")
        if result:
            (tmp_path / "run_result.json").write_text(
                json.dumps({"is_success": True, "val_f1": 0.9})
            )
        log.write("RuntimeError: teardown failed\n")
        if timeout:
            raise subprocess.TimeoutExpired(command, 1200)
        return subprocess.CompletedProcess(command, returncode)

    return run


@pytest.mark.parametrize(
    "returncode, result, timeout, failure",
    [
        (1, True, False, "exited with code 1 after writing run_result.json"),
        (-9, False, False, "was killed by SIGKILL"),
        (0, True, True, "killed at the 1200 s timeout after writing run_result.json"),
        (0, False, True, "killed at the 1200 s timeout"),
    ],
)
def test_a_run_that_fails_after_promoting_leaves_the_incumbent(
    tmp_path, monkeypatch, returncode, result, timeout, failure
):
    """A failed run promotes neither the config (2026-10-01) nor the model:
    train.py had already replaced best_model.pt, which the next cycle would
    have warm-started from and been compared with, with no config or commit
    recording it. Its model is kept aside; the incumbent is put back."""
    config = ExperimentConfig()
    config.save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")  # val_f1 0.47
    (tmp_path / "results.tsv").write_text("timestamp\tval_f1\nearlier\t0.47\n")
    run = _promoting_run(tmp_path, returncode, result, timeout)
    assert len(_drive_loop(tmp_path, monkeypatch, 1, run=run)) == 1
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.47
    (aside,) = tmp_path.glob("best_model.pt.failed-run-*")
    assert torch.load(aside)["val_f1"] == 0.9
    assert not os.path.lexists(tmp_path / ".best_model.pt.held")
    assert ExperimentConfig.load(tmp_path / "config.json") == config
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert f"Training crashed ({failure})" in log
    assert "the incumbent was restored" in log
    assert "- **Last log line**: `RuntimeError: teardown failed`" in log
    # The reports read no promotion the loop undid.
    assert "its rows were removed from results.tsv, prize_readiness.tsv" in log
    assert (
        tmp_path / "results.tsv"
    ).read_text() == "timestamp\tval_f1\nearlier\t0.47\n"
    assert not (tmp_path / "prize_readiness.tsv").exists()


def test_a_promotion_keeps_its_model_and_releases_the_hold(tmp_path, monkeypatch):
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    _drive_loop(tmp_path, monkeypatch, 1, run=_promoting_run(tmp_path))
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.9
    assert not list(tmp_path.glob("best_model.pt.failed-run-*"))
    assert not os.path.lexists(tmp_path / ".best_model.pt.held")
    assert "(SUCCESS)" in next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert (tmp_path / "results.tsv").read_text() == "promoted\t0.9\n"


def _fix_the_clock(monkeypatch):
    """Noon on one day for the loop's log names: _drive_loop sets the hour the
    shift is decided by, but the log is named by the real clock."""
    import datetime

    import run_autoresearch_loop as loop

    class Noon(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 15, 12, 0, 0)

    monkeypatch.setattr(
        loop, "datetime", SimpleNamespace(datetime=Noon, timedelta=datetime.timedelta)
    )


def test_a_restart_within_the_shift_goes_on_with_its_sprint_log(
    tmp_path, monkeypatch, capsys
):
    """The check looked for "day shift" in a name spelled "day_shift", so every
    restart within a shift (a crash, a stop and start) began another log: one
    day shift of 2026-07-06 left three."""
    _fix_the_clock(monkeypatch)
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    result = {"is_success": False, "val_f1": 0.5}
    _drive_loop(tmp_path, monkeypatch, 1, result=result)
    _drive_loop(tmp_path, monkeypatch, 1, result=result)
    logs = list((tmp_path / "sprint_logs").glob("*.md"))
    assert len(logs) == 1
    assert "Resuming existing shift log" in capsys.readouterr().out
    text = logs[0].read_text()
    assert text.count("# Day Shift Sprint") == 1  # one header
    first, second = text.split("## Resumed at")
    assert "## Cycle 1: " in first and "## Cycle 1: " in second  # both starts' cycles
    assert second.startswith(" ") and "cycles count from 1 again" in second


def test_restarts_that_run_no_cycle_mark_the_log_once(tmp_path, monkeypatch):
    """With no tweak under the VRAM cap the loop ends at once, and the watchdog
    starts it again every few minutes: each start added a "Resumed at" line."""
    import run_autoresearch_loop as loop

    _fix_the_clock(monkeypatch)
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    _drive_loop(tmp_path, monkeypatch, 1, result={"is_success": False, "val_f1": 0.5})
    monkeypatch.setattr(loop, "tweak_proposals", lambda *args, **kwargs: ([], []))
    for _ in range(3):
        assert _drive_loop(tmp_path, monkeypatch, 1) == []
    (log,) = (tmp_path / "sprint_logs").glob("*.md")
    assert log.read_text().count("## Resumed at") == 1


def test_a_night_shift_past_midnight_is_the_evening_s_shift(tmp_path, monkeypatch):
    """A night shift begins at 19:00 and ends at 07:00 the next day; a restart
    after midnight compared that day's date with the evening's log."""
    import datetime

    from run_autoresearch_loop import shift_log_to_resume

    monkeypatch.chdir(tmp_path)  # the loop's pointer names sprint_logs/<log>
    (tmp_path / "sprint_logs").mkdir()

    def log(name):
        path = f"sprint_logs/{name}"
        Path(path).write_text("# log\n")
        return path

    def resumed(path, shift, *when):
        return shift_log_to_resume(path, shift, datetime.datetime(2026, *when))

    evening = log("sprint_log_2026-10-14_19-05-08_night_shift.md")
    after_midnight = log("sprint_log_2026-10-15_01-30-00_night_shift.md")
    morning = log("sprint_log_2026-10-15_07-05-09_day_shift.md")
    assert resumed(evening, "night_shift", 10, 14, 23, 0) == evening
    assert resumed(evening, "night_shift", 10, 15, 3, 0) == evening
    assert resumed(after_midnight, "night_shift", 10, 15, 6, 59) == after_midnight
    assert resumed(morning, "day_shift", 10, 15, 18, 0) == morning
    # Another night, or the other shift.
    assert resumed(evening, "night_shift", 10, 15, 20, 0) is None
    assert resumed(after_midnight, "night_shift", 10, 15, 19, 30) is None
    assert resumed(morning, "night_shift", 10, 15, 20, 0) is None
    assert resumed(evening, "day_shift", 10, 15, 8, 0) is None
    # Begun as the night shift ended (07:00:00): not that evening's shift.
    stray = log("sprint_log_2026-10-15_07-00-00_night_shift.md")
    assert resumed(stray, "night_shift", 10, 15, 19, 30) is None
    # Not a log the loop wrote: missing, elsewhere, another name, a bad date.
    assert (
        resumed(
            "sprint_logs/sprint_log_2026-10-15_08-00-00_day_shift.md",
            "day_shift",
            10,
            15,
            9,
            0,
        )
        is None
    )
    elsewhere = tmp_path / "sprint_log_2026-10-15_08-00-00_day_shift.md"
    elsewhere.write_text("# log\n")
    assert resumed(str(elsewhere), "day_shift", 10, 15, 9, 0) is None
    assert resumed(log("notes.md"), "day_shift", 10, 15, 9, 0) is None
    impossible = log("sprint_log_2026-02-30_08-00-00_day_shift.md")
    assert resumed(impossible, "day_shift", 10, 15, 9, 0) is None
    assert resumed("", "day_shift", 10, 15, 9, 0) is None


def test_a_lejepa_checkpoint_maps_by_prefix_as_villa_maps_it():
    """train.py stripped "encoder." wherever it occurred and took nothing
    else: a DDP or compiled checkpoint ("module.encoder...") loaded nothing."""
    weights = {
        "module.encoder.a.weight": 1,
        "_orig_mod.module.encoder.b.encoder.c": 2,
        "shared_encoder.d": 3,
        "projector.e": 4,
        "decoder.f": 5,
    }
    assert train.foundation_encoder_state(weights) == {
        "a.weight": 1,
        "b.encoder.c": 2,
        "d": 3,
    }


def test_a_foundation_model_that_does_not_load_stops_the_run(tmp_path):
    """A missing path was skipped without a word and a failed load was a
    printed warning: either way the run trained from scratch under its name."""
    import torch.nn as nn

    class Primus(nn.Module):  # PrimusNetwork's shape: backbone.shared_encoder
        def __init__(self):
            super().__init__()
            self.backbone = nn.Module()
            self.backbone.shared_encoder = nn.Linear(3, 2)

    model = Primus()
    with pytest.raises(FileNotFoundError):
        train.load_foundation_model(model, str(tmp_path / "missing.pth"))
    path = tmp_path / "lejepa.pth"
    weight, bias = torch.full((2, 3), 0.5), torch.full((2,), 0.25)
    encoder = {"module.encoder.weight": weight, "module.encoder.bias": bias}
    torch.save({"model": {**encoder, "projector.w": 1}}, path)
    train.load_foundation_model(model, str(path))
    assert torch.equal(model.backbone.shared_encoder.weight, weight)
    assert torch.equal(model.backbone.shared_encoder.bias, bias)
    # An encoder of another size fits only part of shared_encoder.
    torch.save(
        {"model": {"encoder.weight": weight, "encoder.bias": torch.ones(5)}}, path
    )
    with pytest.raises(ValueError, match="only 1 of 2"):
        train.load_foundation_model(model, str(path))
    torch.save({"model": {"encoder.weight": torch.zeros(4, 4)}}, path)  # no fit
    with pytest.raises(ValueError, match="only 0 of 2"):
        train.load_foundation_model(model, str(path))
    path.write_bytes(b"not a checkpoint")
    with pytest.raises(pickle.UnpicklingError):  # no longer a printed warning
        train.load_foundation_model(model, str(path))
    torch.save([weight], path)
    with pytest.raises(TypeError, match="not a state dict"):
        train.load_foundation_model(model, str(path))
    plain = nn.Linear(3, 2)  # any other model: by name
    torch.save({"state_dict": {"weight": weight}}, path)
    train.load_foundation_model(plain, str(path))
    assert torch.equal(plain.weight, weight)


def _stubbed_training(tmp_path, monkeypatch, foundation):
    """train() as far as it goes without data, for a config whose
    foundation_model_path is ``foundation``: the datasets, loaders and logging
    are stubbed, and the optimizer, built after the model, ends the run."""
    config = ExperimentConfig(
        architecture="resenc_unet",
        patch_size=8,
        num_layers=4,
        base_feat=2,
        uris=["fake/ct.zarr"],
        val_uri="fake_val/ct.zarr",
        unlabeled_uris=[],
        use_uamt=False,
        checkpoint_out=str(tmp_path / "candidate.pt"),
        cache_dir=str(tmp_path / "cache"),
        foundation_model_path=str(foundation),
    )
    built = []

    def build_validation_dataset(cfg):
        built.append("val")
        return object()

    model = train.build_model(config, train.build_vconfig(config), "cpu")
    monkeypatch.setattr(train, "training_label_path", lambda *a: "fake/labels.png")
    monkeypatch.setattr(train, "build_validation_dataset", build_validation_dataset)
    monkeypatch.setattr(train, "probe_validation_read", lambda dataset: None)
    monkeypatch.setattr(train, "check_validation_inputs", lambda *a: None)
    monkeypatch.setattr(train, "VesuviusLabeledDataset", lambda *a, **k: object())
    monkeypatch.setattr(train, "shuffled_loader", lambda *a, **k: [])
    monkeypatch.setattr(train, "build_model", lambda *a: model)
    monkeypatch.setattr(train.wandb_tracking, "init_run", lambda *a, **k: None)
    monkeypatch.setattr(train.wandb_tracking, "watch_model", lambda *a, **k: None)

    def optimizer(*args, **kwargs):
        raise RuntimeError("reached the optimizer")

    monkeypatch.setattr(torch.optim, "AdamW", optimizer)
    monkeypatch.chdir(tmp_path)
    return config, built


def test_train_stops_at_once_on_a_missing_foundation_model(tmp_path, monkeypatch):
    """Checked with the label files, before the validation catalogue is built
    (the --smoke preflight runs the same check)."""
    config, built = _stubbed_training(tmp_path, monkeypatch, tmp_path / "missing.pth")
    with pytest.raises(FileNotFoundError, match="foundation_model_path"):
        train.train(config)
    assert built == []


def test_train_stops_on_a_foundation_model_that_does_not_fit(tmp_path, monkeypatch):
    """The load at model build raises; it used to print a warning and go on."""
    path = tmp_path / "foundation.pth"
    torch.save({"state_dict": {"no.such.tensor": torch.zeros(1)}}, path)
    config, built = _stubbed_training(tmp_path, monkeypatch, path)
    with pytest.raises(ValueError, match="only 0 of"):
        train.train(config)
    assert built == ["val"]  # it got as far as the model


def test_the_smoke_preflight_stops_on_a_foundation_model_that_does_not_fit(tmp_path):
    """The loop's preflight builds the model, so it loads the foundation model
    too: a checkpoint that does not fit fails the cycle in seconds."""
    path = tmp_path / "foundation.pth"
    torch.save({"state_dict": {"no.such.tensor": torch.zeros(1)}}, path)
    config = ExperimentConfig(
        architecture="resenc_unet",
        patch_size=8,
        num_layers=4,
        base_feat=2,
        foundation_model_path=str(path),
    )
    with pytest.raises(ValueError, match="only 0 of"):
        train.preflight_smoke(config)
    config.foundation_model_path = None
    train.preflight_smoke(config)  # the same config passes without it


def test_a_failed_preflight_is_named_in_the_sprint_log(tmp_path, monkeypatch):
    """Every failure used to read "Training crashed (Unknown error)": 264 runs
    killed at the timeout from 2026-06-29 to 2026-07-07 showed only in the
    spacing of their timestamps."""
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    launched = _drive_loop(tmp_path, monkeypatch, 1, preflight_returncode=2)
    assert launched == []
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "Training crashed (preflight exited with code 2)" in log
    # The preflight's own last line, not the loop's marker after it.
    assert "- **Last log line**: `PREFLIGHT FAILED: model build error`" in log
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.47
    assert not os.path.lexists(tmp_path / ".best_model.pt.held")


def test_a_promotion_log_rotated_during_the_run_is_moved_back(tmp_path, monkeypatch):
    """append_tsv_row moves a log whose header changed aside and starts a new
    one with the run's row; the old one is put back."""
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    (tmp_path / "results.tsv").write_text("old header\nrow\n")
    before = loop._log_ends()
    os.replace(tmp_path / "results.tsv", tmp_path / "results.until-x.tsv")
    (tmp_path / "results.tsv").write_text("new header\npromoted\n")
    assert loop._undo_promotion_rows(before) == (["results.tsv"], [])
    assert (tmp_path / "results.tsv").read_text() == "old header\nrow\n"
    assert not (tmp_path / "results.until-x.tsv").exists()


def test_a_promotion_log_rewritten_during_the_run_is_left(tmp_path, monkeypatch):
    """A log replaced by other content during the run (a git checkout of the
    tracked prize_readiness.tsv can reuse its inode number) is not cut: the
    length recorded before the run would fall mid-row in it."""
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    (tmp_path / "prize_readiness.tsv").write_text("ts\tsubmittable\n")
    before = loop._log_ends()
    (tmp_path / "prize_readiness.tsv").unlink()
    (tmp_path / "prize_readiness.tsv").write_text(
        "ts\tsubmittable\twindow_ok\npulled\n"
    )
    with open(tmp_path / "prize_readiness.tsv", "a") as f:
        f.write("promoted\n")
    assert loop._undo_promotion_rows(before) == ([], ["prize_readiness.tsv"])
    assert (tmp_path / "prize_readiness.tsv").read_text().endswith("pulled\npromoted\n")


def test_a_stop_mid_cycle_settles_the_run(tmp_path, monkeypatch):
    """stop.sh sends SIGTERM, almost always mid-cycle. The handler settles the
    run, so what is done while the loop is stopped (a re-score) is not taken for
    that run's model at the next start."""
    import run_autoresearch_loop as loop

    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    promote = _promoting_run(tmp_path, result=False)

    def stopped(command, log):
        promote(command, log)
        loop.signal_handler(15, None)

    with pytest.raises(SystemExit):
        _drive_loop(tmp_path, monkeypatch, 1, run=stopped)
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.47
    (aside,) = tmp_path.glob("best_model.pt.failed-run-*")
    assert torch.load(aside)["val_f1"] == 0.9
    assert not os.path.lexists(tmp_path / ".best_model.pt.held")
    assert not (tmp_path / "results.tsv").exists()  # the stopped run's rows
    assert not (tmp_path / "prize_readiness.tsv").exists()
    # Re-scored while stopped: the next start keeps it.
    _checkpoint(tmp_path / "rescored.pt", val_f1=0.48)
    os.replace(tmp_path / "rescored.pt", tmp_path / "best_model.pt")
    result = {"is_success": False, "val_f1": 0.5}
    assert len(_drive_loop(tmp_path, monkeypatch, 1, result=result)) == 1
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.48


def test_a_repeated_stop_does_not_cut_the_settle_short(tmp_path, monkeypatch):
    """Ctrl-C pressed again while the loop settles a stopped run: the second
    handler exited inside the first one's settle, leaving the stopped run's rows
    in results.tsv and prize_readiness.tsv. It now only kills the run."""
    import run_autoresearch_loop as loop

    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    promote = _promoting_run(tmp_path, result=False)
    undo = loop._undo_promotion_rows

    def undo_while_stopped_again(before):
        loop.signal_handler(2, None)
        return undo(before)

    def stopped(command, log):
        promote(command, log)
        loop.signal_handler(15, None)

    monkeypatch.setattr(loop, "_undo_promotion_rows", undo_while_stopped_again)
    with pytest.raises(SystemExit):
        _drive_loop(tmp_path, monkeypatch, 1, run=stopped)
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.47
    assert not (tmp_path / "results.tsv").exists()
    assert not (tmp_path / "prize_readiness.tsv").exists()
    assert not os.path.lexists(tmp_path / ".best_model.pt.held")


_TRAINING = "import time\ntime.sleep(120)\n"


def _training_run(directory, command=None, own=False):
    """A process that looks to /proc like a training run working in directory;
    own: a session leader, as the loop's supervisor starts its runs."""
    script = directory / "scripts" / "training" / "train.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(_TRAINING)
    command = command or [
        sys.executable,
        "-u",
        "scripts/training/train.py",
        "--config",
        "config_temp.json",
    ]
    run = subprocess.Popen(command, cwd=directory, start_new_session=own)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if b"train.py" in Path(f"/proc/{run.pid}/cmdline").read_bytes():
                break
        except FileNotFoundError:
            pass
        time.sleep(0.02)
    return run


def _end(*runs):
    for run in runs:
        run.kill()
        run.wait()


needs_proc = pytest.mark.skipif(
    not Path("/proc/self/cwd").exists(), reason="reads /proc"
)


@needs_proc
def test_the_loop_will_not_start_beside_a_training_run_it_does_not_supervise(
    tmp_path, monkeypatch, capsys
):
    """A loop killed without its handler (SIGKILL, a closed terminal) leaves its
    run going in a session of its own. The watchdog's restart then released the
    hold and started a cycle beside a run that could still replace
    best_model.pt and write run_result.json."""
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    os.link(tmp_path / "best_model.pt", tmp_path / ".best_model.pt.held")
    elsewhere = tmp_path / "other_checkout"
    elsewhere.mkdir()
    runs = []
    try:
        runs.append(_training_run(tmp_path))
        runs.append(_training_run(elsewhere))
        # Absolute path, same checkout: it writes the same files.
        absolute = tmp_path / "scripts" / "training" / "train.py"
        runs.append(_training_run(tmp_path, [sys.executable, str(absolute)]))
        assert _drive_loop(tmp_path, monkeypatch, cycles=1) == []
        out = capsys.readouterr().out
        assert "Not starting" in out
        assert f"PID {runs[0].pid} (started by hand" in out
        assert f"PID {runs[2].pid} (" in out
        assert f"PID {runs[1].pid} (" not in out
        assert "kill -TERM" in out and "watchdog tries again" in out
        # The hold waits for the operator or the run's end, untouched.
        assert os.path.samefile(
            tmp_path / "best_model.pt", tmp_path / ".best_model.pt.held"
        )
    finally:
        _end(*runs)
    # Once it has ended, the loop starts (and releases the unchanged hold).
    result = {"is_success": False, "val_f1": 0.5}
    assert len(_drive_loop(tmp_path, monkeypatch, 1, result=result)) == 1
    assert not os.path.lexists(tmp_path / ".best_model.pt.held")


@needs_proc
def test_an_editor_on_the_training_script_is_not_a_run(tmp_path, monkeypatch):
    """`tail -f`, an editor or a pager open on train.py named it among its
    arguments, and kept the loop from starting for as long as it stayed open."""
    ExperimentConfig().save(tmp_path / "config.json")
    viewer = _training_run(tmp_path, ["tail", "-f", "scripts/training/train.py"])
    try:
        result = {"is_success": False, "val_f1": 0.5}
        assert len(_drive_loop(tmp_path, monkeypatch, 1, result=result)) == 1
    finally:
        _end(viewer)


@needs_proc
def test_a_loops_run_past_any_cycles_timeout_is_stopped(tmp_path, monkeypatch, capsys):
    """Its supervisor died with the loop, and with it the run's timeout: a run
    hung at its end (wandb.finish) kept every later start refused. A loop's own
    run (a session leader) past the longest cycle's timeout is stopped, as the
    supervisor would have; a run started by hand never is."""
    import run_autoresearch_loop as loop

    ExperimentConfig().save(tmp_path / "config.json")
    monkeypatch.setattr(loop, "LONGEST_RUN_SECONDS", -1)  # every run is past it
    own = _training_run(tmp_path, own=True)
    by_hand = _training_run(tmp_path)
    try:
        assert _drive_loop(tmp_path, monkeypatch, cycles=1) == []
        out = capsys.readouterr().out
        assert f"PID {own.pid} (started by a loop or ablation" in out
        assert "stopped now" in out
        assert own.wait(timeout=10) == -signal.SIGTERM
        assert by_hand.poll() is None  # left to the operator
    finally:
        _end(own, by_hand)


@pytest.mark.parametrize("ignored", [False, True])
def test_a_closed_terminal_stops_the_loop_like_stop_sh(tmp_path, monkeypatch, ignored):
    """SIGHUP ended a loop run in a terminal at once, leaving its run going;
    under nohup (start.sh) it is ignored, and stays so."""
    ExperimentConfig().save(tmp_path / "config.json")
    real_signal = signal.signal
    previous = real_signal(signal.SIGHUP, signal.SIG_IGN if ignored else signal.SIG_DFL)
    registered: list = []
    try:
        result = {"is_success": False, "val_f1": 0.5}
        _drive_loop(tmp_path, monkeypatch, 1, result=result, signals=registered)
    finally:
        real_signal(signal.SIGHUP, signal.SIG_DFL if previous is None else previous)
    assert signal.SIGTERM in registered and signal.SIGINT in registered
    assert (signal.SIGHUP in registered) is not ignored


class _ClosedTerminal:
    """A terminal after a hangup: it is still one, and every write fails."""

    def isatty(self):
        return True

    def write(self, text):
        raise OSError(5, "Input/output error")

    def flush(self):
        raise OSError(5, "Input/output error")


@pytest.mark.parametrize("recording", [False, True])
def test_a_hangup_moves_the_loops_output_off_the_closed_terminal(
    tmp_path, monkeypatch, recording
):
    """The handler's first message to the closed terminal raised EIO before it
    stopped the run or settled the cycle; during a cycle's recording the error
    broke the recording itself. Its output now goes to autoresearch.out."""
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdout", _ClosedTerminal())
    monkeypatch.setattr(sys, "stderr", _ClosedTerminal())
    stopped = []
    monkeypatch.setattr(
        loop, "supervisor", SimpleNamespace(stop=lambda: stopped.append(1))
    )
    for key, value in {"active": recording, "signal": None, "stopping": False}.items():
        monkeypatch.setitem(loop.STOP_DEFERRED, key, value)
    if recording:
        loop.signal_handler(signal.SIGHUP, None)  # deferred: the cycle goes on
        print("- **Result**: recorded")  # the recording's own output
        assert loop.STOP_DEFERRED["signal"] == signal.SIGHUP and not stopped
    else:
        with pytest.raises(SystemExit) as exited:
            loop.signal_handler(signal.SIGHUP, None)
        assert exited.value.code == 0 and stopped == [1]
    sys.stdout.flush()
    output = (tmp_path / "autoresearch.out").read_text()
    assert f"Caught signal {int(signal.SIGHUP)}" in output
    if recording:
        assert "recorded" in output


def test_a_hold_left_by_a_killed_loop_is_the_operators_call(
    tmp_path, monkeypatch, capsys
):
    """Killed mid-cycle (no handler ran), the loop cannot tell whether that run
    or the operator changed best_model.pt since, so it does not start and says
    how to keep either; it changes nothing."""
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    os.link(tmp_path / "best_model.pt", tmp_path / ".best_model.pt.held")
    _checkpoint(tmp_path / "candidate.pt", val_f1=0.9)
    os.replace(tmp_path / "candidate.pt", tmp_path / "best_model.pt")
    assert _drive_loop(tmp_path, monkeypatch, 1) == []
    out = capsys.readouterr().out
    assert "Not starting: .best_model.pt.held remains" in out
    assert "rm .best_model.pt.held" in out and "mv .best_model.pt.held" in out
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.9
    assert os.path.lexists(tmp_path / ".best_model.pt.held")


def test_a_hold_of_an_unchanged_incumbent_is_released(tmp_path, monkeypatch):
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    os.link(tmp_path / "best_model.pt", tmp_path / ".best_model.pt.held")
    result = {"is_success": False, "val_f1": 0.5}
    assert len(_drive_loop(tmp_path, monkeypatch, 1, result=result)) == 1
    assert not os.path.lexists(tmp_path / ".best_model.pt.held")


def test_a_failed_run_that_wrote_the_first_incumbent_leaves_none(tmp_path, monkeypatch):
    ExperimentConfig().save(tmp_path / "config.json")
    _drive_loop(tmp_path, monkeypatch, 1, run=_promoting_run(tmp_path, returncode=1))
    assert not (tmp_path / "best_model.pt").exists()
    (aside,) = tmp_path.glob("best_model.pt.failed-run-*")
    assert torch.load(aside)["val_f1"] == 0.9
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "there was none before it" in log
    assert not (tmp_path / "results.tsv").exists()


def test_without_a_hard_link_the_cycle_runs_unheld(tmp_path, monkeypatch, capsys):
    """Where the filesystem refuses a hard link, a failed run's model stays, as
    before the hold existed; the cycle still runs."""
    import run_autoresearch_loop as loop

    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")

    def no_link(*args):
        raise OSError("hard links not supported")

    monkeypatch.setattr(loop.os, "link", no_link)
    _drive_loop(tmp_path, monkeypatch, 1, run=_promoting_run(tmp_path, returncode=1))
    assert "could not hold best_model.pt" in capsys.readouterr().out
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.9
    assert not list(tmp_path.glob("best_model.pt.failed-run-*"))


def test_a_tracking_error_at_the_end_of_a_run_is_not_a_failed_run(monkeypatch, capsys):
    from scripts import wandb_tracking

    def finish():
        raise RuntimeError("upload failed")

    monkeypatch.setitem(sys.modules, "wandb", SimpleNamespace(finish=finish))
    wandb_tracking.finish_run(object())
    assert (
        "wandb.finish failed (RuntimeError: upload failed)" in capsys.readouterr().out
    )


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def _scratch_repo(tmp_path, monkeypatch):
    """A repository of its own: no locator variables inherited from a hook that
    may be running these tests, no global or system git config."""
    for name in (
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "loop@example.com")
    _git(tmp_path, "config", "user.name", "loop")
    names = ["config.json", "best_model.pt", "autoresearch_history.json", "work.py"]
    for name in names:
        (tmp_path / name).write_text("before\n")
    (tmp_path / "reports" / "figures").mkdir(parents=True)
    (tmp_path / "reports" / "figures" / "plot.svg").write_text("before\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "start")
    for name in names:
        (tmp_path / name).write_text("after\n")
    (tmp_path / "reports" / "figures" / "plot.svg").write_text("after\n")
    _git(tmp_path, "add", "work.py")  # the operator's staged work...
    (tmp_path / "work.py").write_text("after, and more\n")  # ...partly staged
    monkeypatch.chdir(tmp_path)


def test_a_promotion_commits_only_the_loops_files(tmp_path, monkeypatch):
    """`git add ... && git commit` committed the whole index: on 2026-04-25 a
    promotion commit carried a staged 248-line vesuvius_loader.py change, and
    35 of 50 carried reports/figures/, which the loop does not write."""
    import run_autoresearch_loop as loop

    _scratch_repo(tmp_path, monkeypatch)
    assert loop.commit_promotion("DAY SHIFT: lr_0.001 improved model") is True
    committed = _git(tmp_path, "show", "--name-only", "--format=%s", "HEAD").split()
    assert committed[-3:] == [
        "autoresearch_history.json",
        "best_model.pt",
        "config.json",
    ]
    assert "work.py" not in committed and "reports/figures/plot.svg" not in committed
    # The operator's work is as it was: staged part staged, the rest not.
    assert _git(tmp_path, "diff", "--cached", "--name-only").split() == ["work.py"]
    assert _git(tmp_path, "show", ":work.py") == "after\n"
    assert "work.py" in _git(tmp_path, "diff", "--name-only").split()


def test_a_failed_promotion_commit_names_the_cause_and_unstages(tmp_path, monkeypatch):
    """A failed commit leaves the index as it found it (or the operator's next
    commit would take in the loop's files), and the reason is git's own."""
    import run_autoresearch_loop as loop

    _scratch_repo(tmp_path, monkeypatch)
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/bin/sh\necho 'error: lint failed' >&2\necho 'cleanup done'\nexit 1\n"
    )
    hook.chmod(0o755)
    failure = loop.commit_promotion("DAY SHIFT: lr_0.001 improved model")
    assert failure.startswith("git commit exited 1: error: lint failed")
    assert _git(tmp_path, "diff", "--cached", "--name-only").split() == ["work.py"]
    assert _git(tmp_path, "log", "--format=%s").split("\n")[0] == "start"


def test_a_hung_git_is_stopped_without_leaving_its_lock(tmp_path, monkeypatch):
    """A SIGKILL at the timeout left .git/index.lock, and every later git
    command, the operator's included, failed until it was removed by hand."""
    import run_autoresearch_loop as loop

    _scratch_repo(tmp_path, monkeypatch)
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nsleep 3\n")
    hook.chmod(0o755)
    code, reason = loop._run_git(
        "commit", "--only", "-m", "hangs", "--", "config.json", timeout=1
    )
    assert code is None and reason == "timed out after 1 s"
    assert not list((tmp_path / ".git").glob("*.lock"))


def _alive(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] not in "ZX"
    except FileNotFoundError:
        return False


def test_a_hung_hook_does_not_hold_up_the_loop(tmp_path, monkeypatch):
    """Signalling git alone left its hook running with the output pipes open,
    and the last wait for them had no end: the loop hung there, and a stop
    deferred behind it never came. git runs in a process group of its own."""
    import run_autoresearch_loop as loop

    _scratch_repo(tmp_path, monkeypatch)
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho $$ > hook.pid\nexec sleep 600\n")
    hook.chmod(0o755)
    started = time.monotonic()
    code, reason = loop._run_git(
        "commit", "--only", "-m", "hangs", "--", "config.json", timeout=1
    )
    assert code is None and reason == "timed out after 1 s"
    assert time.monotonic() - started < 20
    pid = int((tmp_path / "hook.pid").read_text())
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(pid)
    assert not list((tmp_path / ".git").glob("*.lock"))


def test_a_stop_delivered_during_a_real_commit_waits_for_it(tmp_path, monkeypatch):
    """The real handler, a real SIGTERM, a real commit with a hook that prints
    and takes a second: the handler runs inside communicate(), which carries on
    (PEP 475), and the commit is made; the stop is kept for the cycle's end."""
    import run_autoresearch_loop as loop

    _scratch_repo(tmp_path, monkeypatch)
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho checking\nsleep 1\necho done\n")
    hook.chmod(0o755)
    previous = signal.signal(signal.SIGTERM, loop.signal_handler)
    loop.STOP_DEFERRED.update(active=True, signal=None)
    stop = threading.Timer(0.3, os.kill, (os.getpid(), signal.SIGTERM))
    try:
        stop.start()
        assert loop.commit_promotion("DAY SHIFT: lr_0.001 improved model") is True
        stop.join()
        assert loop.STOP_DEFERRED["signal"] == signal.SIGTERM
    finally:
        stop.cancel()
        signal.signal(signal.SIGTERM, previous)
        loop.STOP_DEFERRED.update(active=False, signal=None)
    subject = _git(tmp_path, "log", "-1", "--format=%s").strip()
    assert subject == "DAY SHIFT: lr_0.001 improved model"


def test_a_failed_promotion_commit_is_recorded(tmp_path, monkeypatch):
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)  # not a git repository
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert loop.commit_promotion("message").startswith("git add exited 128: fatal:")
    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    messages = []

    def commit(message):
        messages.append(message)
        return "git commit exited 1: error: hook failed"

    _drive_loop(tmp_path, monkeypatch, 1, run=_promoting_run(tmp_path), commit=commit)
    (message,) = messages
    assert message.startswith("DAY SHIFT: lr_") and message.endswith(
        "improved model to val_f1 0.9"
    )
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert (
        "- **Commit**: failed (git commit exited 1: error: hook failed); "
        "config.json, best_model.pt and autoresearch_history.json are promoted on "
        "disk but not committed.\n- **Result**: Improvement detected" in log
    )


def test_a_stop_during_a_promotions_commit_waits_for_the_cycle_to_be_recorded(
    tmp_path, monkeypatch
):
    """stop.sh landing while a promotion was committed exited inside the
    commit: config.json and best_model.pt promoted, the commit possibly half
    done (the files staged), and no sprint-log entry for the cycle."""
    import run_autoresearch_loop as loop

    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    tried, commits = [], []
    promote = _promoting_run(tmp_path)

    def run(command, log):
        tried.append(json.loads((tmp_path / "config_temp.json").read_text()))
        return promote(command, log)

    def commit(message):
        loop.signal_handler(15, None)  # stop.sh, mid-commit
        commits.append(message)
        return True

    with pytest.raises(SystemExit):
        _drive_loop(tmp_path, monkeypatch, 3, run=run, commit=commit)
    assert len(tried) == 1 and len(commits) == 1  # committed; no second cycle
    assert json.loads((tmp_path / "config.json").read_text()) == tried[0]
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.9
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "(SUCCESS)" in log and "Improvement detected" in log
    assert not loop.STOP_DEFERRED["active"]


def test_a_stop_just_after_a_clean_run_does_not_discard_it(tmp_path, monkeypatch):
    """A stop between the run's clean exit and its settle (reading its result,
    or the supervisor's clean-up) settled the run as failed: its model moved
    aside, its rows removed, no entry. The run had ended; it is recorded."""
    import run_autoresearch_loop as loop

    ExperimentConfig().save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    load = json.load
    stops = []

    def load_and_stop(stream, *args, **kwargs):
        if os.path.basename(getattr(stream, "name", "")) == "run_result.json":
            stops.append(True)
            loop.signal_handler(15, None)
        return load(stream, *args, **kwargs)

    monkeypatch.setattr(loop.json, "load", load_and_stop)
    with pytest.raises(SystemExit):
        _drive_loop(tmp_path, monkeypatch, 3, run=_promoting_run(tmp_path))
    assert stops == [True]
    assert torch.load(tmp_path / "best_model.pt")["val_f1"] == 0.9
    assert not list(tmp_path.glob("best_model.pt.failed-run-*"))
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert log.count("## Cycle") == 1 and "(SUCCESS)" in log


def test_a_stop_while_a_cycle_is_recorded_keeps_its_entry(tmp_path, monkeypatch):
    """The same for a cycle that is not promoted: its family decay and its
    entry are written, then the loop stops."""
    import run_autoresearch_loop as loop

    ExperimentConfig().save(tmp_path / "config.json")
    (tmp_path / "autoresearch_history.json").write_text(json.dumps({"lr": 2.0}))
    save_history = loop.save_history

    def stopped_while_saving(counts):
        loop.signal_handler(15, None)
        save_history(counts)

    monkeypatch.setattr(loop, "save_history", stopped_while_saving)
    result = {"is_success": False, "val_f1": 0.5}
    with pytest.raises(SystemExit):
        _drive_loop(tmp_path, monkeypatch, 3, result=result)
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert log.count("## Cycle") == 1 and "(REVERTED)" in log
    history = json.loads((tmp_path / "autoresearch_history.json").read_text())
    assert history["lr"] == pytest.approx(1.9)  # decayed once


def test_a_blocked_promotion_is_recorded_in_the_sprint_log(tmp_path, monkeypatch):
    ExperimentConfig().save(tmp_path / "config.json")
    result = {"is_success": False, "val_f1": 0.5, "promotion_blocked": "why"}
    _drive_loop(tmp_path, monkeypatch, cycles=1, result=result)
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "REVERTED" in log and "Promotion blocked: why" in log


def test_a_baseline_with_no_tweak_under_the_vram_cap_ends_without_logging(
    tmp_path, monkeypatch, capsys
):
    """The watchdog restarts an ended loop every few minutes, so the reason goes to
    stdout (like "Not starting"), not into the sprint log once per restart."""
    ExperimentConfig(batch_size=24).save(tmp_path / "config.json")  # scores 3.0
    launched = _drive_loop(tmp_path, monkeypatch, cycles=1)
    assert launched == []
    assert (
        "No tweak differs from the baseline within VRAM cap" in capsys.readouterr().out
    )
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "VRAM cap" not in log


def test_the_benchmark_leaves_the_depth_to_predict(tmp_path, monkeypatch):
    """predict.py centres the checkpoint's window in its depth band on the
    checkpoint's own volumes (the benchmark volume is the validation fragment),
    else in the volume's depth, so the loop passes no --z."""
    ExperimentConfig().save(tmp_path / "config.json")
    commands: list = []
    _drive_loop(tmp_path, monkeypatch, cycles=5, commands=commands)
    benchmarks = [c for c in commands if "scripts/inference/predict.py" in c]
    assert len(benchmarks) == 1 and "--z" not in benchmarks[0]


def test_skipped_updates_reach_the_sprint_log(tmp_path, monkeypatch):
    ExperimentConfig().save(tmp_path / "config.json")
    result = {"is_success": False, "val_f1": 0.5, "skipped_updates": 3}
    _drive_loop(tmp_path, monkeypatch, cycles=1, result=result)
    log = next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert "- **Skipped updates**: 3" in log


# --- depth band ---------------------------------------------------------------


@pytest.mark.parametrize(
    "band", [[17], [17, 17], [-1, 30], [17.0, 43], [30, 17], [True, 40], [17, 30]]
)
def test_a_malformed_or_too_narrow_depth_band_is_refused(band):
    # [17, 30] is narrower than the default num_layers (24).
    with pytest.raises(ValueError, match="depth_band"):
        ExperimentConfig(depth_band=band)


@pytest.mark.parametrize("band", [[0, 16], [3, 19]])
def test_a_band_whose_widened_read_cannot_hold_the_context_is_refused(band):
    """[0, 16] fits the 16-slice window but not the 24-slice read (clamped at 0),
    which the dataset would refuse on every cycle."""
    with pytest.raises(ValueError, match="context"):
        ExperimentConfig(num_layers=16, depth_band=band)
    ExperimentConfig(num_layers=16, depth_band=[4, 20])  # 0-24 holds it


def test_the_depth_band_round_trips_and_names_the_protocol(tmp_path):
    config = ExperimentConfig(num_layers=16, depth_band=(17, 43))
    config.save(tmp_path / "config.json")
    loaded = ExperimentConfig.load(tmp_path / "config.json")
    assert loaded.depth_band == [17, 43]
    assert promotion.validation_protocol(None) == "seeded-sample-400-v3"
    assert promotion.validation_protocol(loaded.depth_band) == (
        "seeded-sample-400-v3+z17-43"
    )


def test_an_incumbent_scored_on_the_ink_only_sample_must_be_rescored(tmp_path):
    band = [1, 27]
    v2 = promotion.validation_protocol(band, base=promotion.INK_ONLY_PROTOCOL)
    path = _checkpoint(tmp_path / "best_model.pt", val_protocol=v2)
    with pytest.raises(promotion.IncumbentUnavailable, match="--update-stored"):
        promotion.read_incumbent(str(path), promotion.validation_protocol(band))


def test_an_incumbent_scored_on_the_whole_depth_is_not_comparable(tmp_path):
    path = _checkpoint(tmp_path / "best_model.pt")  # the current protocol, whole depth
    banded = promotion.validation_protocol([17, 43])
    with pytest.raises(promotion.IncumbentUnavailable, match=r"\+z17-43"):
        promotion.read_incumbent(str(path), banded)[0]
    promote, _, reason = train.promotion_decision(
        0.9,
        2.0,
        submittable=True,
        enforce_prize_gates=True,
        validation_complete=True,
        incumbent_path=str(path),
        protocol=banded,
    )
    assert not promote and "re-score" in reason
    _checkpoint(path, val_protocol=banded)
    assert promotion.read_incumbent(str(path), banded)[0] == 0.47


def test_the_loop_will_not_start_until_the_incumbent_is_scored_in_the_band(
    tmp_path, monkeypatch, capsys
):
    ExperimentConfig(num_layers=16, depth_band=[17, 43]).save(tmp_path / "config.json")
    _checkpoint(tmp_path / "best_model.pt")
    assert _drive_loop(tmp_path, monkeypatch, cycles=1) == []
    out = capsys.readouterr().out
    assert "Not starting" in out and "seeded-sample-400-v3+z17-43" in out


def test_an_invalid_config_band_is_a_clear_refusal_not_a_crash(
    tmp_path, monkeypatch, capsys
):
    config = ExperimentConfig().__dict__ | {"depth_band": [17, 30]}
    config["auxiliary_config"] = None
    (tmp_path / "config.json").write_text(json.dumps(config))
    assert _drive_loop(tmp_path, monkeypatch, cycles=1) == []
    assert "Not starting: depth_band [17, 30]" in capsys.readouterr().out
