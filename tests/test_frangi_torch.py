"""The Frangi fiber target computed in the training step (torch, any device)
must be the target the loader computed with skimage, patch by patch."""

import os

import numpy as np
import pytest
import torch

from vesuvius_autoresearch.core.frangi_torch import frangi_vesselness_zcollapsed_torch
from vesuvius_autoresearch.core.vesuvius_loader import frangi_vesselness_zcollapsed

# Vesselness lies in [0, 1]. Where two eigenvalues are nearly equal or nearly
# zero, Frangi's ratios divide rounding noise (skimage's float32 eigvalsh
# against a float64 closed form), so a few voxels may differ by more than
# float32 precision; a wrong filter changes most of them.
CLOSE, FEW, WORST = 1e-5, 1e-3, 1e-3


def _assert_matches(got, want):
    diff = np.abs(got - want)
    assert diff.max() <= WORST, f"max difference {diff.max():.2e}"
    assert (diff > CLOSE).mean() <= FEW, f"{(diff > CLOSE).mean():.2%} differ"


def _skimage(batch):
    return np.stack([frangi_vesselness_zcollapsed(p, sigma=2.0) for p in batch])


def _torch(batch):
    out = frangi_vesselness_zcollapsed_torch(torch.from_numpy(batch), sigma=2.0)
    assert out.dtype == torch.float32 and out.shape == batch.shape[:1] + batch.shape[2:]
    return out.numpy()


def _fibrous(rng, z, h, w, scale):
    """Bright fibers at random angles, drifting through z, over noise."""
    vol = rng.random((z, h, w)).astype(np.float32) * 0.2
    zz, yy, xx = np.mgrid[:z, :h, :w]
    for _ in range(4):
        angle, offset = rng.uniform(0, np.pi), rng.uniform(-h / 3, h / 3)
        drift = rng.uniform(-0.5, 0.5)
        dist = np.abs(
            np.cos(angle) * (yy - h / 2)
            + np.sin(angle) * (xx - w / 2)
            - offset
            - drift * zz
        )
        vol += np.exp(-(dist**2) / 4.0).astype(np.float32)
    return vol * scale


@pytest.mark.parametrize("shape", [(24, 64, 64), (12, 32, 32)])
def test_matches_skimage_patch_by_patch(shape):
    rng = np.random.default_rng(0)
    # Contrasts 100x apart: Frangi's gamma is each patch's own.
    z, h, w = shape
    batch = np.stack([_fibrous(rng, z, h, w, scale) for scale in (1.0, 0.01, 0.3)])
    _assert_matches(_torch(batch), _skimage(batch))


def test_matches_skimage_on_noise():
    """(A line constant along two axes is not a test: two of its eigenvalues
    are exactly zero, and Frangi's ratio of them is rounding noise.)"""
    rng = np.random.default_rng(1)
    batch = rng.random((2, 12, 32, 32)).astype(np.float32)
    _assert_matches(_torch(batch), _skimage(batch))


def test_autocast_does_not_lower_its_precision():
    rng = np.random.default_rng(5)
    batch = np.stack([_fibrous(rng, 12, 32, 32, 1.0)])
    with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
        out = frangi_vesselness_zcollapsed_torch(torch.from_numpy(batch), sigma=2.0)
    _assert_matches(out.numpy(), _skimage(batch))


def test_it_convolves_in_float64(monkeypatch):
    """cuDNN runs float32 convolutions in TF32 by default (not on this CPU)."""
    from vesuvius_autoresearch.core import frangi_torch

    seen = set()
    conv1d = frangi_torch.F.conv1d

    def recording(x, w, *args, **kwargs):
        seen.add((x.dtype, w.dtype))
        return conv1d(x, w, *args, **kwargs)

    monkeypatch.setattr(frangi_torch.F, "conv1d", recording)
    _torch(np.random.default_rng(6).random((1, 12, 16, 16)).astype(np.float32))
    assert seen == {(torch.float64, torch.float64)}


def test_a_blank_patch_gives_zeros():
    out = _torch(np.zeros((2, 12, 16, 16), np.float32))
    assert np.array_equal(out, np.zeros_like(out))


def test_each_patch_is_computed_alone():
    rng = np.random.default_rng(2)
    batch = np.stack([_fibrous(rng, 12, 32, 32, s) for s in (1.0, 5.0)])
    together = _torch(batch)
    for i in range(2):
        assert np.array_equal(together[i], _torch(batch[i : i + 1])[0])


FR47 = "local_data/PHercParis2Fr47/surface_volume.zarr"


@pytest.mark.skipif(not os.path.exists(FR47), reason="Fr47 is not in this checkout")
def test_matches_skimage_on_real_patches():
    """The loop's own input: 24 slices of Fr47 scaled as the loader scales them."""
    import zarr

    volume = zarr.open(FR47, mode="r")
    volume = volume["0"] if hasattr(volume, "keys") else volume
    rng = np.random.default_rng(3)
    patches = []
    for _ in range(6):
        y, x = rng.integers(2000, 6000), rng.integers(1500, 4500)
        z0 = int(rng.integers(0, 8))
        raw = np.asarray(volume[z0 : z0 + 24, y : y + 64, x : x + 64])
        patches.append(raw.astype(np.float32) / np.iinfo(raw.dtype).max)
    batch = np.stack(patches)
    _assert_matches(_torch(batch), _skimage(batch))


def test_the_training_step_computes_the_target_the_loader_did(tmp_path):
    """train.fiber_target on a batch of the training loader's reads equals the
    Frangi target the loader itself computed for them (target_fiber_source
    "frangi", the path before 2026-10-15), ridge channel and margins included."""
    import json

    import train
    import zarr
    from PIL import Image
    from torch.utils.data import default_collate

    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    rng = np.random.default_rng(4)
    volume = tmp_path / "surface_volume.zarr"
    array = zarr.open(str(volume), mode="w", shape=(32, 96, 96), dtype="u2")
    array[:] = (np.clip(_fibrous(rng, 32, 96, 96, 0.5), 0, 1) * 65535).astype("u2")
    labels = tmp_path / "inklabels.png"
    Image.fromarray(np.zeros((96, 96), np.uint8)).save(labels)
    catalog = tmp_path / "patches.json"
    origins = [(8, 8), (24, 16), (16, 32), (32, 24)]
    catalog.write_text(json.dumps({"patches": [{"y": y, "x": x} for y, x in origins]}))
    dataset = VesuviusLabeledDataset(
        str(volume),
        str(labels),
        patch_size=32,
        num_layers=24,
        patches_json=str(catalog),
        cache_dir=str(tmp_path / "cache"),
        seed=0,
        use_ridges=True,
        target_fiber_source="frangi",
        target_fiber_sigma=2.0,
    )
    x_raw, _, from_loader = default_collate([dataset[i] for i in range(len(origins))])
    assert x_raw.shape[1] == 2  # CT and ridges
    step = train.fiber_target(x_raw, x_raw[:, :, 4:20], "frangi", 2.0)
    assert step.shape == from_loader.shape
    _assert_matches(step.numpy(), from_loader.numpy())
    assert from_loader.abs().sum() > 0


@pytest.mark.parametrize(
    "heads,configured,expected",
    [
        ({"fiber"}, "frangi", "frangi"),
        ({"qc"}, "frangi", "frangi"),
        ({"fiber"}, "sobel_z", "sobel_z"),
        (set(), "frangi", "sobel_z"),  # no head trains on it
        ({"ink"}, "frangi", "sobel_z"),
    ],
)
def test_the_frangi_target_only_for_a_head_that_uses_it(heads, configured, expected):
    import train

    class Config:
        target_fiber_source = configured

    assert train.fiber_source(heads, Config()) == expected


def test_matches_skimage_at_a_small_scale():
    """skimage truncates its Gaussian derivatives at 100 standard deviations for a
    Frangi scale of 1 or less, and 8 above it; this filter uses 8 at every scale.
    At 1 the tail past 8 is about exp(-36), so it still matches, as it should."""
    rng = np.random.default_rng(2)
    batch = np.stack([_fibrous(rng, 12, 32, 32, scale) for scale in (1.0, 0.3)])
    want = np.stack([frangi_vesselness_zcollapsed(p, sigma=1.0) for p in batch])
    got = frangi_vesselness_zcollapsed_torch(torch.from_numpy(batch), sigma=1.0)
    _assert_matches(got.numpy(), want)
