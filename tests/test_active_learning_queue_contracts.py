"""Human-review suggestions must be finite, identify scored patches and preserve inputs."""

import json
import math
import os
import subprocess
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest
import torch

from scripts import active_learning_sampler as active


class Patches(torch.utils.data.Dataset):
    def __init__(self, coords=None):
        self.valid_coords = np.array(
            coords if coords is not None else [(0, 0), (0, 4), (0, 10), (0, 40)],
            dtype=np.int64,
        )
        self.shape = (2, 128, 128)
        self.jitter = False

    def __len__(self):
        return len(self.valid_coords)

    def __getitem__(self, index):
        return (
            torch.full((1, 2, 4, 4), index / 10),
            torch.zeros(4, 4),
            torch.zeros(4, 4),
        )


class Model(torch.nn.Module):
    def forward(self, x):
        return x[:, :, 0]


@pytest.mark.parametrize(
    "dtype", [torch.float16, torch.bfloat16, torch.float32, torch.float64]
)
def test_entropy_handles_exact_endpoints_in_every_float_dtype(dtype):
    values = active.calculate_entropy(torch.tensor([0, 0.5, 1], dtype=dtype))
    assert torch.isfinite(values).all()
    assert (values >= 0).all()
    assert values[0] == values[2] == 0
    assert values[1].item() == pytest.approx(math.log(2), abs=1e-6)


@pytest.fixture
def command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"checkpoint must survive")
    volume = tmp_path / "fragment" / "surface_volume.zarr"
    volume.mkdir(parents=True)
    labels = volume.parent / "inklabels.png"
    labels.write_bytes(b"labels must survive")
    patches = tmp_path / "patches.json"
    patches.write_text('{"patches": []}')
    calls = []
    datasets = []

    def load(*args):
        calls.append(args)
        return (
            Model(),
            {
                "num_layers": 2,
                "patch_size": 4,
                "use_ridges": False,
                "ridge_sigma": 2.0,
            },
            {"config": {}},
        )

    def dataset(*args, **kwargs):
        result = Patches()
        datasets.append(result)
        return result

    monkeypatch.setattr(active, "load_tool_checkpoint", load)
    monkeypatch.setattr(active, "VesuviusLabeledDataset", dataset)
    monkeypatch.setattr(active, "depth_band_for", lambda *args: None)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    def run(*extra):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "active",
                "--checkpoint",
                str(checkpoint),
                "--volume",
                str(volume),
                "--n_samples",
                "3",
                *extra,
            ],
        )
        return active.main()

    return tmp_path, checkpoint, volume, labels, patches, calls, datasets, run


@pytest.mark.parametrize(
    "target",
    [
        "checkpoint",
        "labels",
        "patches",
        "existing",
        "symlink",
        "hardlink",
        "inside_volume",
    ],
)
def test_queue_output_is_preflighted_before_loading_model(command, target):
    root, checkpoint, volume, labels, patches, calls, _, run = command
    output = root / "queue.json"
    if target == "checkpoint":
        output = checkpoint
    elif target == "labels":
        output = labels
    elif target == "patches":
        output = patches
    elif target == "existing":
        output.write_text("previous queue")
    elif target == "symlink":
        output.symlink_to(checkpoint)
    elif target == "hardlink":
        os.link(checkpoint, output)
    else:
        output = volume / "new-queue.json"
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="output|overlap"):
        run("--patches_json", str(patches), "--output", str(output))
    assert not calls
    for path, contents in before.items():
        assert path.read_bytes() == contents
    if target == "inside_volume":
        assert not output.exists()


@pytest.mark.parametrize("mode", ["file_uri", "local_colon_name"])
def test_local_volume_spellings_are_protected(command, mode):
    root, checkpoint, volume, _, _, calls, _, _ = command
    if mode == "file_uri":
        uri = volume.as_uri()
    else:
        uri = "scan:local.zarr"
        volume = root / uri
        volume.mkdir()
    output = volume / "new-queue.json"
    with pytest.raises(ValueError, match="overlap"):
        active.main(
            ["--checkpoint", str(checkpoint), "--volume", uri, "--output", str(output)]
        )
    assert not calls
    assert not output.exists()


def test_spacing_selects_greedily_in_score_order_and_accepts_exact_boundary():
    loader = torch.utils.data.DataLoader(Patches(), batch_size=3)
    coords, scores = active.ActiveLearningSampler(
        Model(), "cpu"
    ).sample_uncertain_regions(loader, n_samples=4, min_distance=10)
    np.testing.assert_array_equal(coords, [[0, 0], [0, 10], [0, 40]])
    assert np.all(np.diff(scores) < 0)


def test_tied_scores_keep_evaluated_catalog_order():
    class Ties(Model):
        def forward(self, x):
            return torch.zeros_like(x[:, :, 0])

    loader = torch.utils.data.DataLoader(Patches(), batch_size=3)
    coords, _ = active.ActiveLearningSampler(Ties(), "cpu").sample_uncertain_regions(
        loader, 3
    )
    np.testing.assert_array_equal(coords, loader.dataset.valid_coords[:3])


@pytest.mark.parametrize("distance", [-1, float("nan"), float("inf"), True])
def test_invalid_spacing_is_rejected(distance):
    loader = torch.utils.data.DataLoader(Patches(), batch_size=3)
    with pytest.raises(ValueError, match="min_distance"):
        active.ActiveLearningSampler(Model(), "cpu").sample_uncertain_regions(
            loader, min_distance=distance
        )


def test_catalog_changes_during_scoring_are_rejected():
    dataset = Patches()

    class Mutating(Model):
        def forward(self, x):
            dataset.valid_coords[0] = [90, 90]
            return super().forward(x)

    loader = torch.utils.data.DataLoader(dataset, batch_size=4)
    with pytest.raises(ValueError, match="catalog.*changed"):
        active.ActiveLearningSampler(Mutating(), "cpu").sample_uncertain_regions(loader)


@pytest.mark.parametrize("mode", ["collate", "sampler_subclass", "unordered_workers"])
def test_loader_cannot_reorder_patch_identities(mode):
    dataset = Patches()
    kwargs = {}
    if mode == "collate":
        kwargs["collate_fn"] = lambda rows: torch.utils.data.default_collate(rows[::-1])
    elif mode == "sampler_subclass":

        class Reversed(torch.utils.data.SequentialSampler):
            def __iter__(self):
                return iter(range(len(self.data_source) - 1, -1, -1))

        kwargs["sampler"] = Reversed(dataset)
    loader = torch.utils.data.DataLoader(dataset, batch_size=4, **kwargs)
    if mode == "unordered_workers":
        # No worker processes are needed to check that unsupported ordering is rejected.
        loader.in_order = False
    with pytest.raises(ValueError, match="order|collat"):
        active.ActiveLearningSampler(Model(), "cpu").sample_uncertain_regions(loader)


def test_queue_records_spacing_budget_and_underfilled_selection(command):
    root, _, _, _, _, _, _, run = command
    run("--min-distance", "100", "--max-eval-patches", "3", "--output", "queue.json")
    report = json.loads((root / "queue.json").read_text())
    assert len(report["queue"]) == 1
    assert report["selection"]["requested_samples"] == 3
    assert report["selection"]["returned_samples"] == 1
    assert report["selection"]["catalog_patch_count"] == 4
    assert report["selection"]["evaluated_patch_count"] == 3
    assert report["selection"]["min_distance_pixels"] == 100
    assert report["selection"]["subsample_seed"] == 42
    assert report["timestamp"].endswith("+00:00")


def test_serialization_failure_leaves_no_queue_or_temporary_file(command, monkeypatch):
    root, _, _, _, _, _, _, run = command

    def fail(*args, **kwargs):
        raise RuntimeError("injected serializer failure")

    monkeypatch.setattr(active.json, "dump", fail)
    with pytest.raises(RuntimeError, match="serializer"):
        run("--output", "queue.json")
    assert not (root / "queue.json").exists()
    assert not list(root.glob(".queue-*"))


@pytest.mark.parametrize(
    "args",
    [
        ["--max-eval-patches", "0"],
        ["--max-eval-patches", "5001"],
        ["--min-distance", "nan"],
        ["--min-distance", "inf"],
        ["--min-distance", "-1"],
    ],
)
def test_bad_cli_limits_fail_before_loading_model(command, args):
    root, _, _, _, _, calls, _, run = command
    with pytest.raises(ValueError):
        run(*args, "--output", "new/queue.json")
    assert not calls
    assert not (root / "new").exists()


def test_output_appearing_during_inference_is_preserved(command, monkeypatch):
    root, _, _, _, _, _, _, run = command
    original = active.ActiveLearningSampler.sample_uncertain_regions

    def reserve(*args, **kwargs):
        result = original(*args, **kwargs)
        (root / "queue.json").write_text("other writer")
        return result

    monkeypatch.setattr(
        active.ActiveLearningSampler, "sample_uncertain_regions", reserve
    )
    with pytest.raises(ValueError, match="output already exists"):
        run("--output", "queue.json")
    assert (root / "queue.json").read_text() == "other writer"


def test_default_outputs_are_separate_and_labels_handle_trailing_slash(
    command, monkeypatch
):
    root, checkpoint, volume, labels, _, _, _, _ = command
    args = [
        "--checkpoint",
        str(checkpoint),
        "--volume",
        str(volume) + "/",
        "--n-samples",
        "2",
    ]
    first, second = active.main(args), active.main(args)
    assert first != second
    assert first.parent == second.parent == root / "reports"
    for output in (first, second):
        report = json.loads(output.read_text())
        assert report["labels"] == str(labels)
        assert report["selection"]["subsample_seed"] is None


def test_native_cpu_queue_with_complete_weights_and_real_zarr(tmp_path, monkeypatch):
    import zarr

    from vesuvius_autoresearch.core import model_wrappers, vesuvius_loader

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "cache"))
    settings = {
        "architecture": "gated_unet",
        "patch_size": 16,
        "num_layers": 16,
        "base_feat": 8,
        "use_ridges": False,
    }
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(11)
        model = model_wrappers.build_inference_model(**settings)
    checkpoint = tmp_path / "model.pt"
    torch.save({"config": settings, "model_state_dict": model.state_dict()}, checkpoint)
    checkpoint_bytes = checkpoint.read_bytes()
    volume = tmp_path / "surface_volume.zarr"
    array = zarr.open(
        str(volume), mode="w", shape=(16, 16, 64), chunks=(16, 16, 16), dtype="u1"
    )
    values = np.random.default_rng(11).integers(0, 256, array.shape, dtype=np.uint8)
    array[:] = values
    patches = tmp_path / "patches.json"
    patches.write_text(
        json.dumps({"patches": [{"y": 0, "x": x} for x in (0, 8, 16, 32, 48)]})
    )
    output = active.main(
        [
            "--checkpoint",
            str(checkpoint),
            "--volume",
            str(volume),
            "--patches-json",
            str(patches),
            "--n-samples",
            "5",
            "--min-distance",
            "16",
            "--max-eval-patches",
            "4",
            "--output",
            str(tmp_path / "queue.json"),
        ]
    )
    report = json.loads(output.read_text())
    assert report["selection"]["catalog_patch_count"] == 5
    assert report["selection"]["evaluated_patch_count"] == 4
    rows = report["queue"]
    assert 2 <= len(rows) <= 4
    assert report["selection"]["returned_samples"] == len(rows)
    assert all(0 <= row["uncertainty_score"] <= math.log(2) + 1e-6 for row in rows)
    assert [row["uncertainty_score"] for row in rows] == sorted(
        [row["uncertainty_score"] for row in rows], reverse=True
    )
    assert all(math.dist(a["y_x"], b["y_x"]) >= 16 for a, b in combinations(rows, 2))
    assert checkpoint.read_bytes() == checkpoint_bytes
    np.testing.assert_array_equal(array[:], values)


@pytest.mark.parametrize("mode", ["checkpoint_alias", "invalid_limit"])
def test_cli_errors_are_concise_and_preserve_inputs(command, mode):
    root, checkpoint, volume, _, _, _, _, _ = command
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(repo), str(repo / "src"), env.get("PYTHONPATH", "")]
    )
    env["CUDA_VISIBLE_DEVICES"] = ""
    args = [
        sys.executable,
        "-m",
        "scripts.active_learning_sampler",
        "--checkpoint",
        str(checkpoint),
        "--volume",
        str(volume),
    ]
    if mode == "checkpoint_alias":
        args.extend(["--output", str(checkpoint)])
    else:
        args.extend(["--max-eval-patches", "0"])
    result = subprocess.run(args, cwd=root, env=env, text=True, capture_output=True)
    assert result.returncode == 1
    assert "Active learning failed:" in result.stderr
    assert "Traceback" not in result.stderr
    assert checkpoint.read_bytes() == b"checkpoint must survive"
