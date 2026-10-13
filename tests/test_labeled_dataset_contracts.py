"""What VesuviusLabeledDataset hands to training and validation.

Before 2026-10-13 the ridge channel was computed on the GPU and then discarded
(the result was moved with an attribute the class never sets) and recomputed on
the CPU, and a CPU failure became an all-zero channel without any message; a
label or mask up to 20% larger or smaller than its volume was accepted as
aligned (and one a few pixels short crashed collation at the edge); an RGB label
passed the shape check; and a CT dtype other than uint8/uint16/float reached the
model unnormalised. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-13_LABELED_DATASET.md.
"""

from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from PIL import Image
from torch.utils.data import default_collate

from vesuvius_autoresearch.core import vesuvius_loader
from vesuvius_autoresearch.core.vesuvius_loader import (
    FastVesuviusVolume,
    VesuviusLabeledDataset,
    ridge_channel,
)


def _fragment(root, label_hw=(32, 32), dtype="u1", label_mode="L"):
    import zarr

    volume = zarr.open(
        str(root / "surface_volume.zarr"),
        mode="w",
        shape=(8, 32, 32),
        chunks=(4, 16, 16),
        dtype=dtype,
    )
    volume[:] = (np.arange(8 * 32 * 32).reshape(8, 32, 32) % 251).astype(dtype)
    labels = np.zeros(label_hw, np.uint8)
    labels[8:24, 8:24] = 255
    image = Image.fromarray(labels)
    if label_mode != "L":
        image = image.convert(label_mode)
    image.save(root / "inklabels.png")
    return str(root / "surface_volume.zarr"), str(root / "inklabels.png")


class GpuArray(np.ndarray):
    pass


FAKE_CUPY = SimpleNamespace(
    asarray=lambda a: np.asarray(a).view(GpuArray), asnumpy=np.asarray
)


@pytest.fixture
def ridge_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    monkeypatch.setattr(vesuvius_loader, "_WARNING_COUNTS", defaultdict(int))
    monkeypatch.setattr(vesuvius_loader, "_CUPY", None)
    calls = []

    def ridges(volume, sigma):
        calls.append(type(volume).__name__)
        return np.asarray(volume, dtype=np.float32) * 0 + 0.5

    monkeypatch.setattr(vesuvius_loader, "detect_ridges", ridges)
    return calls


def _dataset(tmp_path, **kwargs):
    volume_uri, labels = _fragment(tmp_path)
    return VesuviusLabeledDataset(
        volume_uri, labels, patch_size=16, num_layers=4, use_ridges=True, **kwargs
    )


# --- ridge channel --------------------------------------------------------------


def test_gpu_ridges_are_used_not_recomputed_on_the_cpu(
    tmp_path, monkeypatch, ridge_calls
):
    monkeypatch.setattr(vesuvius_loader, "_CUPY", FAKE_CUPY)
    patch, _, _ = _dataset(tmp_path)[0]
    assert ridge_calls == ["GpuArray"]  # was ["GpuArray", "ndarray"]
    assert patch.shape[0] == 2 and torch.all(patch[1] == 0.5)


def test_without_cupy_ridges_come_from_the_cpu_quietly(tmp_path, ridge_calls, capsys):
    patch, _, _ = _dataset(tmp_path)[0]
    assert ridge_calls == ["ndarray"]
    assert torch.all(patch[1] == 0.5)
    assert "Warning" not in capsys.readouterr().out


def test_a_gpu_failure_warns_and_uses_the_cpu(
    tmp_path, monkeypatch, ridge_calls, capsys
):
    monkeypatch.setattr(vesuvius_loader, "_CUPY", FAKE_CUPY)

    def cpu_only(volume, sigma):
        if isinstance(volume, GpuArray):
            raise RuntimeError("cuSolver eigvalsh failed")
        ridge_calls.append("ndarray")
        return np.full(volume.shape, 0.25, np.float32)

    monkeypatch.setattr(vesuvius_loader, "detect_ridges", cpu_only)
    patch, _, _ = _dataset(tmp_path)[0]
    assert ridge_calls == ["ndarray"] and torch.all(patch[1] == 0.25)
    assert "GPU ridge detection failed" in capsys.readouterr().out


def _failing_ridges(monkeypatch):
    def broken(volume, sigma):
        raise np.linalg.LinAlgError("eigvalsh failed")

    monkeypatch.setattr(vesuvius_loader, "detect_ridges", broken)


def test_a_ridge_failure_is_reported_not_silently_zeroed(
    tmp_path, monkeypatch, ridge_calls, capsys
):
    _failing_ridges(monkeypatch)
    patch, _, _ = _dataset(tmp_path)[0]
    assert torch.all(patch[1] == 0)
    assert "using zero ridges" in capsys.readouterr().out
    assert vesuvius_loader.warning_counts()["ridge_fallback"] == 1


def test_a_ridge_failure_is_fatal_under_strict_reads(
    tmp_path, monkeypatch, ridge_calls
):
    _failing_ridges(monkeypatch)
    with pytest.raises(RuntimeError, match="failed to read labeled patch") as caught:
        _dataset(tmp_path, strict_reads=True)[0]
    assert "ridge detection failed: LinAlgError" in str(caught.value.__cause__)


def test_too_few_slices_for_ridges_is_reported(ridge_calls, capsys):
    thin = np.zeros((2, 8, 8), np.float32)
    with pytest.raises(RuntimeError, match="2 slices are too few"):
        ridge_channel(thin, 1.0, "thin.zarr", strict=True)
    assert torch.all(ridge_channel(thin, 1.0, "thin.zarr") == 0)
    assert "too few for ridge detection" in capsys.readouterr().out


def test_the_volume_reader_shares_the_ridge_implementation(
    tmp_path, monkeypatch, ridge_calls
):
    monkeypatch.setattr(vesuvius_loader, "_CUPY", FAKE_CUPY)
    volume_uri, _ = _fragment(tmp_path)
    patch = FastVesuviusVolume(volume_uri, use_ridges=True)[0:4, 0:8, 0:8]
    assert ridge_calls == ["GpuArray"] and patch.shape == (2, 4, 8, 8)


# --- label/volume alignment ----------------------------------------------------


@pytest.mark.parametrize("label_hw", [(32, 32), (33, 32), (32, 34), (30, 32), (31, 30)])
def test_export_rounding_is_accepted_and_fitted_to_the_volume_grid(
    tmp_path, monkeypatch, label_hw
):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, label_hw)
    ds = VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)
    assert ds.labels.shape == (32, 32)
    h, w = min(label_hw[0], 32), min(label_hw[1], 32)
    assert ds.labels[:h, :w].sum() == 16 * 16  # the ink square, unmoved
    assert not ds.labels[h:, :].any() and not ds.labels[:, w:].any()
    # Every patch, including those at the far edge, collates.
    batch = default_collate([ds[i] for i in range(len(ds))])
    assert batch[1].shape[-2:] == (16, 16)


@pytest.mark.parametrize(
    "label_hw,message",
    [
        ((29, 32), "different crop or scale"),  # 9% short: accepted before
        ((32, 38), "different crop or scale"),
        ((8, 32), "transposed"),  # (depth, W)
        ((9, 32), "transposed"),  # (depth, W) with a pixel of rounding
        ((32, 8), "transposed"),
    ],
)
def test_a_label_of_another_size_is_refused(tmp_path, monkeypatch, label_hw, message):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, label_hw)
    with pytest.raises(ValueError, match=message):
        VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)


def test_a_multichannel_label_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, label_mode="RGB")
    with pytest.raises(ValueError, match="single-channel"):
        VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)


def test_an_unnormalised_ct_dtype_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, dtype="i2")
    with pytest.raises(ValueError, match="unsupported CT dtype"):
        VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)
