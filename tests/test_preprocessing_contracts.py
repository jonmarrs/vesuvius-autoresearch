"""Requested preprocessing must succeed before a strict sample can be scored."""

import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch
import train
from PIL import Image

from scripts import reevaluate_best_model as reevaluate
from vesuvius_autoresearch.core import vesuvius_loader, villa_modules
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


@pytest.fixture
def fragment(tmp_path, monkeypatch):
    import zarr

    volume = tmp_path / "surface_volume.zarr"
    zarr.open(str(volume), mode="w", shape=(12, 8, 8), dtype="u1")[:] = 128
    labels = tmp_path / "inklabels.png"
    Image.fromarray((np.indices((8, 8)).sum(0) % 2 * 255).astype("u1")).save(labels)
    catalog = tmp_path / "patches.json"
    catalog.write_text(json.dumps({"patches": [{"y": 0, "x": 0}]}))
    # These tests exercise CPU behavior and explicit synthetic GPU results.
    try:
        import cupy
    except ImportError:
        pass
    else:
        monkeypatch.setattr(cupy, "asarray", _failure)

    def dataset(**options):
        return VesuviusLabeledDataset(
            str(volume),
            str(labels),
            patch_size=8,
            num_layers=12,
            patches_json=str(catalog),
            cache_dir=str(tmp_path / "cache"),
            jitter=False,
            **options,
        )

    return dataset


def _failure(*args, **kwargs):
    raise RuntimeError("backend unavailable")


def _break_preprocessing(monkeypatch, operation):
    if operation == "lasagna":
        monkeypatch.setattr(villa_modules, "load_villa_leaf", _failure)
        return {"use_lasagna": True}
    if operation == "ridges":
        monkeypatch.setattr(vesuvius_loader, "detect_ridges", _failure)
        return {"use_ridges": True}
    monkeypatch.setattr(vesuvius_loader, "frangi_vesselness_zcollapsed", _failure)
    return {"target_fiber_source": "frangi"}


@pytest.mark.parametrize("operation", ["lasagna", "ridges", "frangi"])
def test_strict_preprocessing_failure_cannot_be_returned_as_a_sample(
    fragment, monkeypatch, operation
):
    options = _break_preprocessing(monkeypatch, operation)
    dataset = fragment(strict_reads=True, **options)
    with pytest.raises(RuntimeError, match="failed to read labeled patch") as error:
        dataset[0]
    assert "backend unavailable" in str(error.value)


@pytest.mark.parametrize("operation", ["lasagna", "ridges", "frangi"])
def test_permissive_preprocessing_failure_preserves_the_legacy_sample(
    fragment, monkeypatch, operation
):
    options = _break_preprocessing(monkeypatch, operation)
    dataset = fragment(strict_reads=False, **options)
    sample, target, fiber = dataset[0]
    assert torch.allclose(sample[0], torch.full((12, 8, 8), 128 / 255))
    assert target.sum() == 32
    assert torch.count_nonzero(fiber) == 0
    if operation == "ridges":
        assert torch.count_nonzero(sample[1]) == 0


def test_a_successful_gpu_ridge_result_is_used_without_recomputing_on_cpu(
    fragment, monkeypatch
):
    cupy = pytest.importorskip("cupy")
    monkeypatch.setattr(cupy, "asarray", lambda tensor: tensor.numpy())
    monkeypatch.setattr(cupy, "asnumpy", np.asarray)
    calls = []

    def detect(array, sigma):
        calls.append(sigma)
        return np.full(array.shape, 0.25, dtype=np.float32)

    monkeypatch.setattr(vesuvius_loader, "detect_ridges", detect)
    sample, _, _ = fragment(strict_reads=True, use_ridges=True)[0]
    assert calls == [2.0], "a valid GPU result was discarded and recomputed"
    assert torch.all(sample[1] == 0.25)
    assert sample.device == sample[1].device


def test_strict_ridges_allow_a_successful_cpu_fallback(fragment, monkeypatch):
    monkeypatch.setattr(
        vesuvius_loader,
        "detect_ridges",
        lambda array, sigma: np.full(array.shape, 0.5, dtype=np.float32),
    )
    sample, _, _ = fragment(strict_reads=True, use_ridges=True)[0]
    assert torch.all(sample[1] == 0.5)


@pytest.mark.parametrize("operation", ["lasagna", "ridges", "frangi"])
def test_invalid_preprocessing_results_are_not_strict_samples(
    fragment, monkeypatch, operation
):
    if operation == "lasagna":
        monkeypatch.setattr(
            villa_modules,
            "load_villa_leaf",
            lambda *args: SimpleNamespace(
                grid_sample_3d_u8=lambda vol, *a: torch.full_like(
                    vol, float("nan"), dtype=torch.float32
                )
            ),
        )
        options: dict[str, bool | str] = {"use_lasagna": True}
    elif operation == "ridges":
        monkeypatch.setattr(
            vesuvius_loader,
            "detect_ridges",
            lambda array, **k: np.full(array.shape, np.nan, dtype=np.float32),
        )
        options = {"use_ridges": True}
    else:
        monkeypatch.setattr(
            vesuvius_loader,
            "frangi_vesselness_zcollapsed",
            lambda array, **k: np.full(array.shape[1:], np.nan, dtype=np.float32),
        )
        options = {"target_fiber_source": "frangi"}
    with pytest.raises(RuntimeError, match="failed to read labeled patch"):
        fragment(strict_reads=True, **options)[0]


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("operation", ["lasagna", "ridges"])
def test_thin_patch_preprocessing_is_explicit(fragment, strict, operation):
    options = {"use_lasagna": True} if operation == "lasagna" else {"use_ridges": True}
    dataset = fragment(strict_reads=strict, **options)
    dataset.num_layers = 2
    if strict:
        with pytest.raises(RuntimeError, match="failed to read labeled patch"):
            dataset[0]
    else:
        sample, _, _ = dataset[0]
        assert sample.shape[1] == 2
        assert torch.allclose(sample[0], torch.full((2, 8, 8), 128 / 255))


def test_successful_flattening_is_a_complete_validation_sample(fragment, monkeypatch):
    monkeypatch.setattr(
        villa_modules,
        "load_villa_leaf",
        lambda *args: SimpleNamespace(grid_sample_3d_u8=lambda vol, *a: vol + 1),
    )
    dataset = fragment(strict_reads=True, use_lasagna=True)
    probabilities, targets, diag = train.collect_validation_predictions(
        MeanInk(), dataset, 4, torch.device("cpu"), batch_size=1
    )
    assert diag["complete"] and diag["usable_patches"] == 1
    assert len(probabilities) == len(targets) == 1


def test_strict_frangi_uses_a_successfully_computed_target(fragment, monkeypatch):
    monkeypatch.setattr(
        vesuvius_loader,
        "frangi_vesselness_zcollapsed",
        lambda array, **k: np.full(array.shape[1:], 0.5, dtype=np.float32),
    )
    _, _, fiber = fragment(strict_reads=True, target_fiber_source="frangi")[0]
    assert fiber.shape == (1, 1, 8, 8) and torch.all(fiber == 0.5)


class MeanInk(torch.nn.Module):
    def forward(self, x):
        return x[:, :1].mean(2)


def test_failed_flattening_marks_validation_incomplete(fragment, monkeypatch):
    _break_preprocessing(monkeypatch, "lasagna")
    dataset = fragment(strict_reads=True, use_lasagna=True)
    probabilities, targets, diag = train.collect_validation_predictions(
        MeanInk(), dataset, 4, torch.device("cpu"), batch_size=1
    )
    assert not diag["complete"] and diag["batch_errors"] == 1
    assert not probabilities and not targets


def test_failed_flattening_cannot_rewrite_incumbent_scores(
    fragment, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    checkpoint = tmp_path / "best_model.pt"
    checkpoint.write_bytes(b"incumbent must survive")
    _break_preprocessing(monkeypatch, "lasagna")
    dataset = fragment(strict_reads=True, use_lasagna=True)
    monkeypatch.setattr(reevaluate, "build_validation_dataset", lambda config: dataset)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(
        reevaluate,
        "load_tool_checkpoint",
        lambda *args: (
            MeanInk(),
            {"patch_size": 8, "num_layers": 4, "use_ridges": False},
            {"config": {"use_lasagna": True}},
        ),
    )
    monkeypatch.setattr(reevaluate, "select_topology_threshold", lambda *a: (0.5, 1))
    monkeypatch.setattr(reevaluate, "compute_skeleton_dist", lambda *a: 0.0)
    monkeypatch.setattr(
        reevaluate, "compute_centerline_dice", lambda *a, **k: {"centerline_dice": 1}
    )
    monkeypatch.setattr(reevaluate, "compute_cc_diff", lambda *a: 0.0)
    with pytest.raises(RuntimeError, match="sample is incomplete"):
        reevaluate.reevaluate(update_stored=True)
    assert checkpoint.read_bytes() == b"incumbent must survive"
