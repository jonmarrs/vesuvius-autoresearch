"""What VesuviusLabeledDataset hands to training and validation.

Before 2026-10-13 the ridge channel was computed on the GPU and then discarded
(the result was moved with an attribute the class never sets) and recomputed on
the CPU, and a CPU failure became an all-zero channel without any message; and a
label or mask up to 20% larger or smaller than its volume was accepted as
aligned. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-13_LABELED_DATASET.md.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from PIL import Image

from vesuvius_autoresearch.core import vesuvius_loader
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def _fragment(root, label_hw=(32, 32)):
    import zarr

    volume = zarr.open(
        str(root / "surface_volume.zarr"),
        mode="w",
        shape=(8, 32, 32),
        chunks=(4, 16, 16),
        dtype="u1",
    )
    volume[:] = np.arange(8 * 32 * 32, dtype=np.uint32).reshape(8, 32, 32) % 251
    labels = np.zeros(label_hw, np.uint8)
    labels[8:24, 8:24] = 255
    Image.fromarray(labels).save(root / "inklabels.png")
    return str(root / "surface_volume.zarr"), str(root / "inklabels.png")


@pytest.fixture
def ridge_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    monkeypatch.setattr(vesuvius_loader, "_WARNING_COUNTS", defaultdict(int))
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


def test_gpu_ridges_are_used_not_recomputed_on_the_cpu(
    tmp_path, monkeypatch, ridge_calls
):
    class GpuArray(np.ndarray):
        pass

    fake_cupy = SimpleNamespace(
        asarray=lambda a: np.asarray(a).view(GpuArray), asnumpy=np.asarray
    )
    monkeypatch.setitem(sys.modules, "cupy", fake_cupy)
    patch, _, _ = _dataset(tmp_path)[0]
    assert ridge_calls == ["GpuArray"]  # was ["GpuArray", "ndarray"]
    assert patch.shape[0] == 2 and torch.all(patch[1] == 0.5)


def test_without_cupy_ridges_come_from_the_cpu_quietly(
    tmp_path, monkeypatch, ridge_calls, capsys
):
    monkeypatch.setitem(sys.modules, "cupy", None)  # import raises ImportError
    patch, _, _ = _dataset(tmp_path)[0]
    assert ridge_calls == ["ndarray"]
    assert torch.all(patch[1] == 0.5)
    assert "Warning" not in capsys.readouterr().out


def _failing_ridges(monkeypatch):
    monkeypatch.setitem(sys.modules, "cupy", None)

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


def test_a_ridge_failure_is_fatal_under_strict_reads(
    tmp_path, monkeypatch, ridge_calls
):
    _failing_ridges(monkeypatch)
    with pytest.raises(RuntimeError, match="failed to read labeled patch"):
        _dataset(tmp_path, strict_reads=True)[0]


@pytest.mark.parametrize("label_hw", [(32, 32), (33, 32), (32, 34)])
def test_export_rounding_is_accepted(tmp_path, monkeypatch, label_hw):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, label_hw)
    VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)


@pytest.mark.parametrize(
    "label_hw,message",
    [
        ((29, 32), "different crop or scale"),  # 9% short: accepted before
        ((32, 38), "different crop or scale"),
        ((8, 32), "axis order"),  # (depth, W): a transposed volume
    ],
)
def test_a_label_of_another_size_is_refused(tmp_path, monkeypatch, label_hw, message):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, label_hw)
    with pytest.raises(ValueError, match=message):
        VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)
