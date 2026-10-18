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


def _fragment(root, label_hw=(32, 32), dtype="u1", label_mode="L", shape=(8, 32, 32)):
    import zarr

    volume = zarr.open(
        str(root / "surface_volume.zarr"),
        mode="w",
        shape=shape,
        chunks=(4, 16, 16),
        dtype=dtype,
    )
    volume[:] = (np.arange(np.prod(shape)).reshape(shape) % 251).astype(dtype)
    labels = np.zeros(label_hw, np.uint8)
    labels[8:24, 8:24] = 255
    image = Image.fromarray(labels)
    if label_mode != "L":
        image = image.convert(label_mode)
    image.save(root / "inklabels.png")
    return str(root / "surface_volume.zarr"), str(root / "inklabels.png")


def _mask(root, hw=(32, 32), mode="L"):
    Image.fromarray(np.full(hw, 255, np.uint8)).convert(mode).save(root / "mask.png")
    return str(root / "mask.png")


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
    with pytest.raises(RuntimeError, match=r"a \(2, 8, 8\) patch is too small"):
        ridge_channel(thin, 1.0, "thin.zarr", strict=True)
    assert torch.all(ridge_channel(thin, 1.0, "thin.zarr") == 0)
    assert "too small for ridge detection" in capsys.readouterr().out


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


@pytest.mark.parametrize(
    "stored, ink",
    [
        (np.uint8, 255),  # 8-bit 0/255
        (np.uint8, 1),  # 0/1
        (np.uint16, 65535),  # 16-bit 0/65535: was read as 257
        (np.uint16, 255),  # 8-bit values in a 16-bit file
    ],
)
def test_labels_and_masks_are_scaled_to_unit_range_by_bit_depth(
    tmp_path, monkeypatch, stored, ink
):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path)
    values = np.zeros((32, 32), stored)
    values[8:24, 8:24] = ink
    Image.fromarray(values).save(labels)
    Image.fromarray(np.full((32, 32), ink, stored)).save(tmp_path / "mask.png")
    dataset = VesuviusLabeledDataset(
        volume_uri,
        labels,
        str(tmp_path / "mask.png"),
        patch_size=16,
        num_layers=4,
    )
    assert dataset.labels.max() == 1.0 and dataset.labels.min() == 0.0
    assert dataset.labels[8:24, 8:24].min() == 1.0
    assert np.all(dataset.mask == 1.0)
    _, label, _ = dataset[0]
    assert float(label.max()) <= 1.0


def test_a_label_outside_any_bit_depth_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path)
    values = np.zeros((32, 32), np.int32)
    values[0, 0] = 1 << 20  # a 32-bit integer image (PNG mode I)
    Image.fromarray(values).save(labels.replace(".png", ".tif"))
    with pytest.raises(ValueError, match="8-bit or 16-bit"):
        VesuviusLabeledDataset(
            volume_uri, labels.replace(".png", ".tif"), patch_size=16, num_layers=4
        )


def test_an_unnormalised_ct_dtype_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, dtype="i2")
    with pytest.raises(ValueError, match="unsupported CT dtype"):
        VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)


# --- second review pass ---------------------------------------------------------


def test_cupy_without_a_device_is_the_quiet_cpu_path(monkeypatch, ridge_calls, capsys):
    from vesuvius_autoresearch.fibers import detection

    def no_device():
        raise RuntimeError("cudaErrorNoDevice")

    fake = SimpleNamespace(
        cuda=SimpleNamespace(runtime=SimpleNamespace(getDeviceCount=no_device))
    )
    monkeypatch.setattr(detection, "HAS_CUPY", True)
    monkeypatch.setattr(detection, "cp", fake, raising=False)
    monkeypatch.setattr(vesuvius_loader, "_CUPY", vesuvius_loader._CUPY_UNSET)
    assert vesuvius_loader._cupy() is None
    ridge_channel(np.zeros((4, 8, 8), np.float32), 1.0, "cpu-host.zarr")
    assert ridge_calls == ["ndarray"]
    assert "Warning" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "ct,reason",
    [
        (np.zeros((4, 2, 8), np.float32), "too small"),
        (np.full((4, 8, 8), np.nan, np.float32), "non-finite"),
    ],
)
def test_input_problems_are_reported_once_not_as_gpu_failures(
    monkeypatch, ridge_calls, ct, reason
):
    monkeypatch.setattr(vesuvius_loader, "_CUPY", FAKE_CUPY)
    with pytest.raises(RuntimeError, match=reason):
        ridge_channel(ct, 1.0, "x.zarr", strict=True)
    assert torch.all(ridge_channel(ct, 1.0, "x.zarr") == 0)
    assert ridge_calls == []
    assert vesuvius_loader.warning_counts() == {"ridge_fallback": 1}


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "LA"])
def test_a_multichannel_mask_still_places_patches(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path)
    ds = VesuviusLabeledDataset(
        volume_uri, labels, _mask(tmp_path, mode=mode), patch_size=16, num_layers=4
    )
    assert len(ds) > 0


def test_a_mask_replaced_by_patches_json_is_not_checked(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path)
    mask = _mask(tmp_path, hw=(28, 32))  # 4 px short: refused when it places patches
    with pytest.raises(ValueError, match="mask shape"):
        VesuviusLabeledDataset(volume_uri, labels, mask, patch_size=16, num_layers=4)
    catalogue = tmp_path / "patches.json"
    catalogue.write_text(
        json.dumps({"patches": [{"y": 0, "x": 0}, {"y": 16, "x": 16}]})
    )
    ds = VesuviusLabeledDataset(
        volume_uri,
        labels,
        mask,
        patch_size=16,
        num_layers=4,
        patches_json=str(catalogue),
    )
    assert len(ds) == 2


def test_a_width_by_depth_label_is_named_as_transposed(tmp_path, monkeypatch):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, label_hw=(40, 8), shape=(8, 32, 40))
    with pytest.raises(ValueError, match="transposed"):
        VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)


@pytest.mark.parametrize("dtype,scale", [(">u2", 65535.0), (">f4", 1.0)])
def test_big_endian_volumes_are_read_and_normalised(
    tmp_path, monkeypatch, dtype, scale
):
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "c"))
    volume_uri, labels = _fragment(tmp_path, dtype=dtype)
    ds = VesuviusLabeledDataset(volume_uri, labels, patch_size=16, num_layers=4)
    patch, _, _ = ds[0]
    assert patch.dtype == torch.float32 and float(patch.max()) <= 250.0 / scale
