"""Checkpoint analysis must score loaded models and identify the actual patches."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from PIL import Image

from scripts import (
    active_learning_sampler as active,
    generate_pseudo_labels as pseudo,
    measure_ink_auc as auc,
    reevaluate_best_model as reevaluate,
)
from vesuvius_autoresearch.core import model_wrappers


class Heads(torch.nn.Module):
    def __init__(self, bad=None):
        super().__init__()
        self.bias = torch.nn.Parameter(torch.tensor(0.0))
        self.inputs = []
        self.bad = bad

    def forward(self, x, return_qc=False):
        self.inputs.append(x.detach().clone())
        ink = (x[:, :1].mean(2) - 0.5) * 10 + self.bias
        if self.bad == "inf":
            ink = ink + float("inf")
        elif self.bad == "channels":
            ink = ink.expand(-1, 2, -1, -1)
        qc = torch.zeros((len(x), 1))
        return (ink, qc) if return_qc else ink


class Patches(torch.utils.data.Dataset):
    def __init__(self, count=17, **kwargs):
        self.valid_coords = np.array([(0, i * 4) for i in range(count)])
        self.shape = (16, 4, count * 4)
        self.mask = np.ones(self.shape[1:], dtype=np.float32)
        self.labels = np.tile(np.array([[0, 1, 0, 1]], dtype=np.float32), (4, count))
        self.layers = kwargs.get("num_layers", 10)
        self.ridges = kwargs.get("use_ridges", False)
        self.jitter = kwargs.get("jitter", True)
        self.kwargs = kwargs

    def __len__(self):
        return len(self.valid_coords)

    def __getitem__(self, index):
        target = torch.from_numpy(self.labels[:, index * 4 : (index + 1) * 4])
        x = target.expand(2 if self.ridges else 1, self.layers, 4, 4).clone()
        return x, target, torch.zeros(1, 1, 4, 4)


@pytest.fixture
def tools_fixture(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    config = {
        "architecture": "gated_unet",
        "patch_size": 4,
        "num_layers": 2,
        "base_feat": 4,
        "use_ridges": False,
        "ridge_sigma": 3.0,
    }
    checkpoint = tmp_path / "best_model.pt"
    torch.save({"config": config, "model_state_dict": Heads().state_dict()}, checkpoint)
    (tmp_path / "config.json").write_text(
        json.dumps(
            {"patch_size": 16, "num_layers": 8, "base_feat": 32, "use_ridges": True}
        )
    )
    fragment = tmp_path / "fragment"
    fragment.mkdir()
    for name in ["inklabels.png", "mask.png"]:
        Image.fromarray(
            np.tile(np.array([[0, 255, 0, 255]], np.uint8), (4, 17))
            if name.startswith("ink")
            else np.full((4, 68), 255, np.uint8)
        ).save(fragment / name)
    models, settings, datasets = [], [], []

    def factory(**kwargs):
        settings.append(kwargs)
        model = Heads()
        models.append(model)
        return model

    def dataset(*args, **kwargs):
        # The analysis commands pass patch size/depth positionally.
        if len(args) > 4:
            kwargs["num_layers"] = args[4]
        ds = Patches(**kwargs)
        datasets.append(ds)
        return ds

    monkeypatch.setattr(model_wrappers, "build_inference_model", factory)
    for module in [auc, reevaluate, active]:
        monkeypatch.setattr(module, "build_inference_model", factory, raising=False)
    for module in [auc, active, sys.modules["train"]]:
        # Re-evaluation builds its dataset through train.build_validation_dataset.
        monkeypatch.setattr(module, "VesuviusLabeledDataset", dataset)
    from vesuvius_autoresearch.core import vesuvius_loader

    monkeypatch.setattr(vesuvius_loader, "VesuviusLabeledDataset", dataset)
    return checkpoint, fragment, models, settings, datasets


def run_auc(monkeypatch, checkpoint, fragment, *extra):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "measure_ink_auc",
            "--checkpoint",
            str(checkpoint),
            "--fragments",
            str(fragment),
            "--n",
            "3",
            *extra,
        ],
    )
    auc.main()


def test_auc_counts_exact_requested_patches(tools_fixture, monkeypatch, capsys):
    checkpoint, fragment, _, _, _ = tools_fixture
    run_auc(monkeypatch, checkpoint, fragment)
    assert "n=3" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["auc", "pseudo", "reevaluate"])
def test_partial_weights_cannot_be_scored(tools_fixture, monkeypatch, mode):
    checkpoint, fragment, _, _, _ = tools_fixture
    saved = torch.load(checkpoint, weights_only=False)
    saved["model_state_dict"] = {}
    torch.save(saved, checkpoint)
    with pytest.raises((ValueError, RuntimeError)):
        if mode == "auc":
            run_auc(monkeypatch, checkpoint, fragment)
        elif mode == "pseudo":
            pseudo._infer_region(
                str(checkpoint),
                str(fragment),
                str(fragment / "mask.png"),
                torch.device("cpu"),
                0.65,
                0.15,
            )
        else:
            reevaluate.reevaluate()


@pytest.mark.parametrize("mode", ["auc", "pseudo"])
def test_measurement_and_labels_do_not_require_current_config(
    tools_fixture, monkeypatch, mode
):
    checkpoint, fragment, _, _, _ = tools_fixture
    (checkpoint.parent / "config.json").unlink()
    if mode == "auc":
        run_auc(monkeypatch, checkpoint, fragment)
    else:
        pseudo._infer_region(
            str(checkpoint),
            str(fragment),
            str(fragment / "mask.png"),
            torch.device("cpu"),
            0.65,
            0.15,
        )


@pytest.mark.parametrize("recorded", [True, False])
@pytest.mark.parametrize("mode", ["auc", "pseudo", "sampler"])
def test_a_depth_band_applies_only_to_the_checkpoints_own_volumes(
    tools_fixture, monkeypatch, tmp_path, mode, recorded
):
    """A band names slices of the volumes it was set for (finding 87: [1, 27)
    is layers 17-42 in zarrs that start at layer 16). The measurement tools read
    another fragment over its whole depth, as before bands. Pseudo-labels are
    trained on again under the same band, so they keep it everywhere."""
    checkpoint, fragment, _, _, datasets = tools_fixture
    saved = torch.load(checkpoint, weights_only=False)
    # No surface_volume.zarr in the fixture: the tools read the bare level 0.
    # Recorded relative, as config.json does; the fixture runs in tmp_path.
    volume = "fragment/0" if recorded else "another/surface_volume.zarr"
    saved["config"].update(depth_band=[1, 5], val_uri=volume)
    torch.save(saved, checkpoint)
    if mode == "auc":
        run_auc(monkeypatch, checkpoint, fragment)
    elif mode == "pseudo":
        pseudo._infer_region(
            str(checkpoint),
            str(fragment),
            str(fragment / "mask.png"),
            torch.device("cpu"),
            0.65,
            0.15,
        )
    else:
        queue = tmp_path / "queue.json"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "active_learning_sampler",
                "--checkpoint",
                str(checkpoint),
                "--volume",
                str(fragment / "0"),
                "--labels",
                str(fragment / "inklabels.png"),
                "--n_samples",
                "2",
                "--output",
                str(queue),
            ],
        )
        active.main()
        assert json.loads(queue.read_text())["depth_band"] == (
            [1, 5] if recorded else None
        )
    expected = [1, 5] if recorded or mode == "pseudo" else None
    assert datasets[0].kwargs["depth_band"] == expected


def _stub_topology(monkeypatch):
    monkeypatch.setattr(
        reevaluate, "select_topology_threshold", lambda *args: (0.5, 1.0)
    )
    monkeypatch.setattr(reevaluate, "compute_skeleton_dist", lambda *args: 0.0)
    monkeypatch.setattr(
        reevaluate,
        "compute_centerline_dice",
        lambda *args, **kwargs: {"centerline_dice": 1.0},
    )
    monkeypatch.setattr(reevaluate, "compute_cc_diff", lambda *args: 0.0)


def test_reevaluation_uses_saved_input_settings(tools_fixture, monkeypatch):
    _, _, _, settings, datasets = tools_fixture
    _stub_topology(monkeypatch)
    reevaluate.reevaluate()
    assert settings[0]["patch_size"] == 4 and settings[0]["num_layers"] == 2
    assert datasets[0].kwargs["ridge_sigma"] == 3.0
    assert datasets[0].kwargs["use_ridges"] is False


def test_reevaluation_prints_the_all_ink_baseline(tools_fixture, monkeypatch, capsys):
    # A threshold-swept F1 has a floor set by the sample's ink prevalence p:
    # calling every pixel ink scores 2p/(1+p). Without it beside val_f1, a
    # re-score on a sample with more ink reads as a gain (2026-10-12: 0.468 ->
    # 0.727, when calling everything ink scored 0.731 on the new sample).
    _stub_topology(monkeypatch)
    reevaluate.reevaluate()
    # The fixture's labels alternate 0/1 columns, so p = 0.5 and 2p/(1+p) = 2/3.
    assert "all-ink baseline F1: 0.666667 (ink prevalence 0.5000;" in (
        capsys.readouterr().out
    )


def test_reevaluation_compares_margins_over_the_all_ink_baseline(
    tools_fixture, monkeypatch, capsys
):
    # Two samples with different prevalence have different F1 floors, so the
    # comparable quantity is each val_f1's margin over its own sample's floor.
    checkpoint = tools_fixture[0]
    saved = torch.load(checkpoint, weights_only=False)
    saved.update(val_f1=0.5, val_positive_rate=0.25)  # floor 0.4, margin +0.1
    torch.save(saved, checkpoint)
    _stub_topology(monkeypatch)
    reevaluate.reevaluate()
    lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if "val_f1 margin over all-ink:" in line
    ]
    assert len(lines) == 1 and "stored=+0.100000" in lines[0]


def _record_lasagna(checkpoint):
    saved = torch.load(checkpoint, weights_only=False)
    saved["config"]["use_lasagna"] = True
    torch.save(saved, checkpoint)


def test_reevaluation_applies_the_recorded_warp_by_default(tools_fixture, monkeypatch):
    checkpoint, _, _, _, datasets = tools_fixture
    _record_lasagna(checkpoint)
    _stub_topology(monkeypatch)
    reevaluate.reevaluate()
    assert datasets[0].kwargs["use_lasagna"] is True


def test_unwarped_reevaluation_scores_without_the_recorded_warp(
    tools_fixture, monkeypatch, capsys
):
    # The incumbent records use_lasagna: true, but the warp never ran on this
    # host (finding 86): it was trained on unwarped patches, so it is scored on
    # them, and strict reads refuse the warp anyway.
    checkpoint, _, _, _, datasets = tools_fixture
    _record_lasagna(checkpoint)
    _stub_topology(monkeypatch)
    reevaluate.reevaluate(unwarped=True)
    assert datasets[0].kwargs["use_lasagna"] is False
    assert "scoring unwarped" in capsys.readouterr().out


def test_unwarped_update_corrects_the_recorded_warp(tools_fixture, monkeypatch):
    # Rewrites the record so later re-scores and tools score it unwarped too, and
    # keeps what was recorded.
    checkpoint, _, _, _, _ = tools_fixture
    _record_lasagna(checkpoint)
    before = torch.load(checkpoint, weights_only=False)
    _stub_topology(monkeypatch)
    reevaluate.reevaluate(update_stored=True, unwarped=True)
    after = torch.load(checkpoint, weights_only=False)
    assert after["config"] == before["config"] | {"use_lasagna": False}
    assert after["reevaluation"]["input_settings"] == {"use_lasagna": False}
    assert after["reevaluation"]["overridden_input_settings"] == {"use_lasagna": True}


def test_a_rescore_records_the_inputs_a_candidate_is_compared_on(
    tools_fixture, monkeypatch
):
    """The remedy every refusal names (a re-score) must store the fingerprint a
    candidate scored on config.json's inputs will record."""
    from scripts.training import promotion
    from scripts.training.config import ExperimentConfig

    checkpoint, _, _, _, _ = tools_fixture
    _stub_topology(monkeypatch)
    reevaluate.reevaluate(update_stored=True)
    config = ExperimentConfig.load("config.json")
    expected = promotion.validation_inputs_fingerprint(
        config.val_uri, config.depth_band
    )
    stored = torch.load(checkpoint, weights_only=False)["validation_diag"]
    assert stored["inputs_sha256"] == expected
    val_f1, source = promotion.check_incumbent(
        str(checkpoint), config.val_uri, config.depth_band
    )
    assert source == "checkpoint"
    assert val_f1 == pytest.approx(torch.load(checkpoint, weights_only=False)["val_f1"])


_HOLDER = (
    "import time\n"
    "from scripts.loop_control import acquire_lock\n"
    "lock = acquire_lock('autoresearch.lock')\n"
    "print('ready', flush=True)\n"
    "while True: time.sleep(.1)\n"
)
_REPO = Path(__file__).resolve().parents[1]
_ENV = {**os.environ, "PYTHONPATH": str(_REPO)}
needs_proc = pytest.mark.skipif(
    not Path("/proc/self/cwd").exists(), reason="loop_control reads /proc"
)


def _hold_lock(name):
    """A process registered in the working directory's lock, as the loop is."""
    Path(name).write_text(_HOLDER)
    holder = subprocess.Popen(
        [sys.executable, "-u", name], env=_ENV, stdout=subprocess.PIPE, text=True
    )
    assert holder.stdout is not None and holder.stdout.readline() == "ready\n"
    return holder


def _lock_is_free():
    """What the loop's start does, from another process (POSIX record locks do
    not exclude their own process)."""
    take = "from scripts.loop_control import acquire_lock; acquire_lock('autoresearch.lock')"
    return (
        subprocess.run(
            [sys.executable, "-c", take], env=_ENV, capture_output=True
        ).returncode
        == 0
    )


@needs_proc
def test_a_rescore_will_not_start_beside_this_checkouts_loop(
    tools_fixture, monkeypatch
):
    """A running cycle holds best_model.pt and may replace it, so --update-stored
    refuses before loading anything."""
    checkpoint, _, models, _, datasets = tools_fixture
    _stub_topology(monkeypatch)
    before = checkpoint.read_bytes()
    loop = _hold_lock("run_autoresearch_loop.py")
    try:
        with pytest.raises(RuntimeError, match=rf"\(PID {loop.pid}\) holds this"):
            reevaluate.reevaluate(update_stored=True)
    finally:
        loop.kill()
        loop.wait()
    assert checkpoint.read_bytes() == before
    assert not models and not datasets


def test_an_unidentified_lock_holder_is_refused_too(tools_fixture, monkeypatch):
    def unidentified(repo):
        raise RuntimeError("lock PID does not identify this checkout's loop")

    monkeypatch.setattr(reevaluate, "running_pid", unidentified)
    with pytest.raises(RuntimeError, match="unidentified: lock PID .* not updated"):
        reevaluate.reevaluate(update_stored=True)


def test_a_rescore_holds_the_checkout_lock_until_it_has_written(
    tools_fixture, monkeypatch
):
    """The watchdog restarts a loop that is down but not paused; while the
    re-score holds the lock, neither it nor start.sh can."""
    checkpoint, _, _, _, _ = tools_fixture
    _stub_topology(monkeypatch)
    collect = reevaluate.collect_validation_predictions
    free_while_scoring = []

    def collect_and_check(*args, **kwargs):
        free_while_scoring.append(_lock_is_free())
        return collect(*args, **kwargs)

    monkeypatch.setattr(reevaluate, "collect_validation_predictions", collect_and_check)
    handler = signal.getsignal(signal.SIGTERM)
    reevaluate.reevaluate(update_stored=True)
    assert free_while_scoring == [False]
    assert _lock_is_free()
    assert signal.getsignal(signal.SIGTERM) is handler
    assert "reevaluation" in torch.load(checkpoint, weights_only=False)


@needs_proc
def test_loop_control_names_a_rescore_so_stop_can_stop_it(tmp_path, monkeypatch):
    from scripts.loop_control import running_pid

    monkeypatch.chdir(tmp_path)
    rescore = _hold_lock("reevaluate_best_model.py")
    try:
        assert running_pid(tmp_path) == rescore.pid
    finally:
        rescore.kill()
        rescore.wait()


def test_a_stop_ends_a_rescore_before_it_writes(tools_fixture, monkeypatch):
    checkpoint, _, _, _, _ = tools_fixture
    _stub_topology(monkeypatch)
    before = checkpoint.read_bytes()

    def stopped(*args, **kwargs):
        os.kill(os.getpid(), signal.SIGTERM)  # ./stop.sh

    monkeypatch.setattr(reevaluate, "collect_validation_predictions", stopped)
    handler = signal.getsignal(signal.SIGTERM)
    with pytest.raises(KeyboardInterrupt):
        reevaluate.reevaluate(update_stored=True)
    assert checkpoint.read_bytes() == before
    assert _lock_is_free()
    assert signal.getsignal(signal.SIGTERM) is handler


@pytest.mark.parametrize(
    "name, refusal",
    [
        ("load_tool_checkpoint", "changed while it was being loaded"),
        ("collect_validation_predictions", "changed while it was being re-scored"),
    ],
)
def test_a_rescore_does_not_write_over_a_change_made_while_it_ran(
    tools_fixture, monkeypatch, name, refusal
):
    """The lock keeps the loop out, not a writer that takes none (a train.py run
    by hand, a checkout): writing the loaded model back would undo its change."""
    checkpoint, _, _, _, _ = tools_fixture
    _stub_topology(monkeypatch)
    original = getattr(reevaluate, name)

    def changing(*args, **kwargs):
        value = original(*args, **kwargs)
        changed = torch.load(checkpoint, weights_only=False)
        changed["val_f1"] = 0.9
        torch.save(changed, checkpoint)
        return value

    monkeypatch.setattr(reevaluate, name, changing)
    with pytest.raises(RuntimeError, match=refusal):
        reevaluate.reevaluate(update_stored=True)
    assert torch.load(checkpoint, weights_only=False)["val_f1"] == 0.9


@pytest.mark.parametrize("hold", ["the incumbent", "another file"])
def test_a_rescore_settles_a_hold_left_by_a_killed_loop_as_its_start_would(
    tools_fixture, monkeypatch, hold
):
    """A loop killed mid-cycle leaves .best_model.pt.held. If best_model.pt is
    still that file, the hold is released (as the loop's start does) and the
    re-score proceeds; otherwise which to keep is the operator's call, and a
    re-score would hide that from the loop's next start."""
    checkpoint, _, _, _, _ = tools_fixture
    _stub_topology(monkeypatch)
    held = checkpoint.with_name(".best_model.pt.held")
    if hold == "the incumbent":
        os.link(checkpoint, held)
        reevaluate.reevaluate(update_stored=True)
        assert not held.exists()
        assert "reevaluation" in torch.load(checkpoint, weights_only=False)
    else:
        held.write_bytes(b"the incumbent before the killed cycle")
        before = checkpoint.read_bytes()
        with pytest.raises(RuntimeError, match="not updated: .*mid-cycle"):
            reevaluate.reevaluate(update_stored=True)
        assert checkpoint.read_bytes() == before and held.exists()


def test_a_dry_run_beside_the_loop_reads_only(tools_fixture, monkeypatch, capsys):
    # Without --update-stored nothing is written, so the lock is not consulted.
    checkpoint, _, _, _, _ = tools_fixture
    _stub_topology(monkeypatch)
    monkeypatch.setattr(reevaluate, "running_pid", lambda repo: 4321)
    before = checkpoint.read_bytes()
    reevaluate.reevaluate()
    assert checkpoint.read_bytes() == before
    assert "TODAY'S MEASUREMENT" in capsys.readouterr().out
    assert not Path("autoresearch.lock").exists()


def test_the_command_line_passes_unwarped(monkeypatch):
    calls = []
    monkeypatch.setattr(reevaluate, "reevaluate", lambda **kwargs: calls.append(kwargs))
    reevaluate.main(["--update-stored", "--unwarped"])
    reevaluate.main([])
    assert calls == [
        {"update_stored": True, "unwarped": True},
        {"update_stored": False, "unwarped": False},
    ]


@pytest.mark.parametrize(
    "low,high", [(0.8, 0.2), (0.3, 0.3), (-0.1, 0.8), (0.1, 1.1), (float("nan"), 0.9)]
)
def test_pseudo_thresholds_must_be_ordered_probabilities(low, high):
    with pytest.raises(ValueError):
        pseudo.prob_to_pseudo_png(
            np.array([[0.5]], dtype=np.float32), np.ones((1, 1), bool), high, low
        )


@pytest.mark.parametrize(
    "prob", [np.array([[float("nan")]]), np.array([[1.1]]), np.ones((2, 2))]
)
def test_pseudo_rejects_invalid_or_misaligned_maps(prob):
    with pytest.raises(ValueError):
        pseudo.prob_to_pseudo_png(prob, np.ones((1, 1), bool))


@pytest.mark.parametrize("n", [0, -1, True])
def test_active_sample_count_is_positive(n):
    loader = torch.utils.data.DataLoader(Patches(jitter=False), batch_size=8)
    with pytest.raises(ValueError):
        active.ActiveLearningSampler(Heads(), "cpu").sample_uncertain_regions(loader, n)


def test_active_refuses_jittered_patch_coordinates():
    loader = torch.utils.data.DataLoader(Patches(jitter=True), batch_size=8)
    with pytest.raises(ValueError, match="jitter"):
        active.ActiveLearningSampler(Heads(), "cpu").sample_uncertain_regions(loader, 3)


# The sampler no longer reads the QC head (it is not a confidence score), so an
# invalid QC output is not its concern.
@pytest.mark.parametrize("bad", ["inf", "channels"])
def test_active_rejects_invalid_heads(bad):
    loader = torch.utils.data.DataLoader(Patches(jitter=False), batch_size=8)
    with pytest.raises(ValueError):
        active.ActiveLearningSampler(Heads(bad), "cpu").sample_uncertain_regions(
            loader, 3
        )


@pytest.mark.parametrize("mode", ["auc", "pseudo", "reevaluate"])
@pytest.mark.parametrize("bad", ["inf", "channels"])
def test_auxiliary_tools_reject_bad_ink_before_outputs(
    tools_fixture, monkeypatch, mode, bad
):
    checkpoint, fragment, _, _, _ = tools_fixture
    monkeypatch.setattr(
        model_wrappers, "build_inference_model", lambda **kwargs: Heads(bad)
    )
    before = checkpoint.read_bytes()
    with pytest.raises((ValueError, RuntimeError, SystemExit)):
        if mode == "auc":
            run_auc(monkeypatch, checkpoint, fragment)
        elif mode == "pseudo":
            pseudo._infer_region(
                str(checkpoint),
                str(fragment),
                str(fragment / "mask.png"),
                torch.device("cpu"),
                0.65,
                0.15,
            )
        else:
            reevaluate.reevaluate(update_stored=True)
    assert checkpoint.read_bytes() == before


def test_auc_failure_when_requested_sample_cannot_be_met(
    tools_fixture, monkeypatch, capsys
):
    checkpoint, fragment, _, _, _ = tools_fixture
    with pytest.raises(SystemExit):
        run_auc(monkeypatch, checkpoint, fragment, "--n", "18")
    assert "17/18" in capsys.readouterr().err


def test_auc_uses_only_pixels_in_fragment_mask(tools_fixture, monkeypatch):
    checkpoint, fragment, _, _, _ = tools_fixture
    original = auc.VesuviusLabeledDataset

    def factory(*args, **kwargs):
        ds = original(*args, **kwargs)
        ds.mask = 1 - ds.labels  # only background is inside the mask
        return ds

    monkeypatch.setattr(auc, "VesuviusLabeledDataset", factory)
    with pytest.raises(SystemExit):
        run_auc(monkeypatch, checkpoint, fragment)


@pytest.mark.parametrize(
    "metric", ["compute_cc_diff", "compute_skeleton_dist", "compute_centerline_dice"]
)
def test_failed_metrics_leave_checkpoint_unchanged(tools_fixture, monkeypatch, metric):
    checkpoint, _, _, _, _ = tools_fixture
    before = checkpoint.read_bytes()
    monkeypatch.setattr(
        reevaluate, "select_topology_threshold", lambda *args: (0.5, 1.0)
    )
    monkeypatch.setattr(reevaluate, "compute_skeleton_dist", lambda *args: 0.0)
    monkeypatch.setattr(
        reevaluate,
        "compute_centerline_dice",
        lambda *args, **kwargs: {"centerline_dice": 1.0},
    )
    monkeypatch.setattr(reevaluate, "compute_cc_diff", lambda *args: 0.0)

    def fail(*args, **kwargs):
        raise RuntimeError("broken metric")

    monkeypatch.setattr(reevaluate, metric, fail)
    with pytest.raises(RuntimeError, match="measurement failed"):
        reevaluate.reevaluate(update_stored=True)
    assert checkpoint.read_bytes() == before


def test_nonfinite_topology_leaves_checkpoint_unchanged(tools_fixture, monkeypatch):
    checkpoint, _, _, _, _ = tools_fixture
    before = checkpoint.read_bytes()
    monkeypatch.setattr(
        reevaluate, "select_topology_threshold", lambda *args: (0.5, 1.0)
    )
    monkeypatch.setattr(reevaluate, "compute_skeleton_dist", lambda *args: float("nan"))
    with pytest.raises(RuntimeError):
        reevaluate.reevaluate(update_stored=True)
    assert checkpoint.read_bytes() == before


def test_active_cli_saved_sigma_no_jitter_and_bare_output(tools_fixture, monkeypatch):
    checkpoint, fragment, _, _, datasets = tools_fixture
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "active",
            "--checkpoint",
            str(checkpoint),
            "--volume",
            str(fragment / "0"),
            "--n_samples",
            "3",
            "--output",
            "queue.json",
        ],
    )
    active.main()
    queue = json.loads((checkpoint.parent / "queue.json").read_text())
    assert len(queue["queue"]) == 3
    assert datasets[0].jitter is False
    assert datasets[0].kwargs["ridge_sigma"] == 3.0
    assert queue["inference_settings"]["num_layers"] == 2


def test_active_empty_dataset_is_explicit_failure():
    loader = torch.utils.data.DataLoader(Patches(count=0, jitter=False), batch_size=8)
    with pytest.raises(ValueError, match="no patches"):
        active.ActiveLearningSampler(Heads(), "cpu").sample_uncertain_regions(loader)


@pytest.mark.parametrize("strict", [False, True])
def test_strict_dataset_reads_do_not_replace_errors_with_zero_patches(strict):
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    ds = VesuviusLabeledDataset.__new__(VesuviusLabeledDataset)
    ds.valid_coords = np.array([[0, 0]])
    ds.seed, ds.jitter, ds.strict_reads = 0, False, strict
    ds.shape, ds.num_layers, ds.patch_size = (10, 4, 4), 10, 4
    ds.use_ridges = False
    ds.volume = SimpleNamespace(uri="broken volume")
    # This backend cannot be sliced, which raises inside the guarded read.
    if strict:
        with pytest.raises(RuntimeError, match="failed to read labeled patch"):
            ds[0]
    else:
        x, target, _ = ds[0]
        assert torch.all(x == 0) and torch.all(target == 0)


def test_real_resenc_pseudo_label_roundtrip_without_current_config(
    tmp_path, monkeypatch
):
    import zarr

    from vesuvius_autoresearch.core import vesuvius_loader

    monkeypatch.chdir(tmp_path)
    config = {
        "architecture": "resenc_unet",
        "patch_size": 8,
        "num_layers": 8,
        "base_feat": 4,
    }
    torch.manual_seed(3)
    model = model_wrappers.build_inference_model(**config).eval()
    checkpoint = tmp_path / "model.pt"
    torch.save({"config": config, "model_state_dict": model.state_dict()}, checkpoint)
    data = np.random.default_rng(5).integers(0, 256, (16, 8, 8), dtype=np.uint8)
    zarr.open(
        str(tmp_path / "surface_volume.zarr"), mode="w", shape=data.shape, dtype="u1"
    )[:] = data
    Image.fromarray(np.full((8, 8), 255, np.uint8)).save(tmp_path / "mask.png")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"patches": [{"y": 0, "x": 0}]}))
    original = vesuvius_loader.VesuviusLabeledDataset
    monkeypatch.setattr(
        vesuvius_loader,
        "VesuviusLabeledDataset",
        lambda *args, **kwargs: original(*args, **kwargs, patches_json=str(catalog)),
    )
    with torch.no_grad():
        batch = torch.from_numpy(data.astype(np.float32) / 255)[None, None, 4:12]
        probabilities = torch.sigmoid(model(batch))[0, 0].numpy()
    actual = pseudo._infer_region(
        str(checkpoint),
        str(tmp_path),
        str(tmp_path / "mask.png"),
        torch.device("cpu"),
        0.65,
        0.15,
    )
    np.testing.assert_array_equal(
        actual, pseudo.prob_to_pseudo_png(probabilities, np.ones((8, 8), bool))
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("patch_size", 4.5),
        ("num_layers", True),
        ("use_ridges", "false"),
        ("multi_task_heads", "false"),
        ("ridge_sigma", float("nan")),
        ("num_heads", 0),
    ],
)
def test_invalid_checkpoint_settings_fail_before_dataset(
    tools_fixture, monkeypatch, field, value
):
    from vesuvius_autoresearch.core.checkpoint_tools import load_tool_checkpoint

    checkpoint, _, models, _, datasets = tools_fixture
    saved = torch.load(checkpoint, weights_only=False)
    saved["config"][field] = value
    torch.save(saved, checkpoint)
    with pytest.raises(ValueError):
        load_tool_checkpoint(checkpoint, "cpu")
    assert not models and not datasets


def test_empty_reevaluation_cannot_update_checkpoint(tools_fixture, monkeypatch):
    checkpoint, _, _, _, _ = tools_fixture
    before = checkpoint.read_bytes()

    def blank(self, index):
        return (
            torch.zeros(1, self.layers, 4, 4),
            torch.zeros(4, 4),
            torch.zeros(1, 1, 4, 4),
        )

    monkeypatch.setattr(Patches, "__getitem__", blank)
    with pytest.raises(ValueError, match="zero usable"):
        reevaluate.reevaluate(update_stored=True)
    assert checkpoint.read_bytes() == before


def test_valid_reevaluation_updates_metrics_and_records_provenance(
    tools_fixture, monkeypatch
):
    checkpoint, _, _, _, _ = tools_fixture
    before = torch.load(checkpoint, weights_only=False)
    monkeypatch.setattr(
        reevaluate, "select_topology_threshold", lambda *args: (0.5, 1.0)
    )
    monkeypatch.setattr(reevaluate, "compute_skeleton_dist", lambda *args: 0.0)
    monkeypatch.setattr(
        reevaluate,
        "compute_centerline_dice",
        lambda *args, **kwargs: {"centerline_dice": 1.0},
    )
    monkeypatch.setattr(reevaluate, "compute_cc_diff", lambda *args: 0.0)
    reevaluate.reevaluate(update_stored=True)
    after = torch.load(checkpoint, weights_only=False)
    assert after["config"] == before["config"]
    torch.testing.assert_close(
        after["model_state_dict"]["bias"], before["model_state_dict"]["bias"]
    )
    assert after["val_bpb"] == 0.0 and after["avg_centerline_dice"] == 1.0
    assert after["reevaluation"]["model_settings"]["num_layers"] == 2
    assert not list(checkpoint.parent.glob(".reevaluation-*"))
