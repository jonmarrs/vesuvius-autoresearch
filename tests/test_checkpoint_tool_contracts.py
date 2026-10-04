"""Checkpoint analysis must score loaded models and identify the actual patches."""

import json
import sys
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
        if self.bad == "qc":
            qc[:] = float("nan")
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


def test_reevaluation_uses_saved_input_settings(tools_fixture, monkeypatch):
    _, _, _, settings, datasets = tools_fixture
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
    reevaluate.reevaluate()
    assert settings[0]["patch_size"] == 4 and settings[0]["num_layers"] == 2
    assert datasets[0].kwargs["ridge_sigma"] == 3.0
    assert datasets[0].kwargs["use_ridges"] is False


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


@pytest.mark.parametrize("bad", ["inf", "channels", "qc"])
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
