"""A coordinate-cache hit must select the same patches as a fresh search."""

import hashlib
import os
from pathlib import Path

import numpy as np
import pytest
import zarr
from PIL import Image

from vesuvius_autoresearch.core import patch_catalog
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

STAMP = 1_700_000_000_123_456_789


def write_selection(path, start=0, *, shape=(32, 32), stamp=STAMP):
    pixels = np.zeros(shape, np.uint8)
    pixels[start : start + 16, start : start + 16] = 255
    Image.fromarray(pixels).save(path)
    os.utime(path, ns=(stamp, stamp))


@pytest.fixture
def fragment(tmp_path):
    source = tmp_path / "ct.zarr"
    array = zarr.open(
        str(source), mode="w", shape=(4, 32, 32), chunks=(4, 16, 16), dtype="u1"
    )
    array[:] = 64
    labels, mask = tmp_path / "labels.png", tmp_path / "mask.png"
    write_selection(labels)
    write_selection(mask)
    return source, labels, mask


def dataset(fragment, cache, require_ink, **kwargs):
    source, labels, mask = fragment
    return VesuviusLabeledDataset(
        str(source),
        str(labels),
        mask_path=str(mask),
        patch_size=kwargs.pop("patch_size", 16),
        num_layers=4,
        cache_dir=str(cache),
        require_ink=require_ink,
        jitter=False,
        **kwargs,
    )


@pytest.mark.parametrize("require_ink", [False, True])
@pytest.mark.parametrize("change", ["other_path", "preserved_mtime", "same_second"])
def test_changed_selection_does_not_reuse_old_coordinates(
    fragment, tmp_path, require_ink, change
):
    cache = tmp_path / "shared"
    first = dataset(fragment, cache, require_ink)
    np.testing.assert_array_equal(first.valid_coords, [[0, 0]])
    source, labels, mask = fragment
    selected = labels if require_ink else mask
    if change == "other_path":
        selected = tmp_path / "replacement.png"
        fragment = (
            (source, selected, mask) if require_ink else (source, labels, selected)
        )
    stamp = STAMP + 100_000_000 if change == "same_second" else STAMP
    write_selection(selected, 16, stamp=stamp)
    warm = dataset(fragment, cache, require_ink)
    fresh = dataset(fragment, tmp_path / "fresh", require_ink)
    np.testing.assert_array_equal(fresh.valid_coords, [[16, 16]])
    np.testing.assert_array_equal(warm.valid_coords, fresh.valid_coords)
    if require_ink:
        assert warm[0][1].sum() == fresh[0][1].sum() == 256
    else:
        y, x = warm.valid_coords[0]
        assert warm.mask[y : y + 16, x : x + 16].sum() == 256


@pytest.mark.parametrize("row", [63, 64, 127, 128, 159])
def test_single_pixel_edit_across_hash_blocks_matches_fresh_selection(
    fragment, tmp_path, row
):
    source, labels, mask = fragment
    zarr.open(str(source), mode="a").resize((4, 160, 32))
    pixels = np.zeros((160, 32), np.uint8)
    pixels[:16, :16] = 255
    start = row // 16 * 16
    pixels[start : start + 16, 16:] = 255
    Image.fromarray(pixels).save(labels)
    Image.fromarray(np.full_like(pixels, 255)).save(mask)
    os.utime(labels, ns=(STAMP, STAMP))
    first = dataset(fragment, tmp_path / "shared", True, min_ink_ratio=1.0)
    np.testing.assert_array_equal(first.valid_coords, [[0, 0], [start, 16]])

    # One changed pixel removes just the distant, fully labeled patch. The
    # first patch still qualifies, so relaxed fallback cannot hide the edit.
    pixels[row, 16] = 0
    Image.fromarray(pixels).save(labels)
    os.utime(labels, ns=(STAMP, STAMP))
    warm = dataset(fragment, tmp_path / "shared", True, min_ink_ratio=1.0)
    fresh = dataset(fragment, tmp_path / "fresh", True, min_ink_ratio=1.0)
    np.testing.assert_array_equal(fresh.valid_coords, [[0, 0]])
    np.testing.assert_array_equal(warm.valid_coords, fresh.valid_coords)


def no_search(**_):
    pytest.fail("an unchanged selection should reuse its coordinate cache")


@pytest.mark.parametrize("require_ink", [False, True])
def test_identical_pixels_at_a_new_path_and_timestamp_reuse_cache(
    fragment, tmp_path, monkeypatch, require_ink
):
    cache = tmp_path / "shared"
    first = dataset(fragment, cache, require_ink)
    source, labels, mask = fragment
    copy = tmp_path / "same-pixels.png"
    write_selection(copy, stamp=STAMP + 5_000_000_000)
    fragment = (source, copy, mask) if require_ink else (source, labels, copy)
    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    second = dataset(fragment, cache, require_ink)
    np.testing.assert_array_equal(second.valid_coords, first.valid_coords)


@pytest.mark.parametrize("require_ink", [False, True])
def test_editing_the_unused_selection_image_does_not_recompute(
    fragment, tmp_path, monkeypatch, require_ink
):
    cache = tmp_path / "shared"
    first = dataset(fragment, cache, require_ink)
    unused = fragment[2] if require_ink else fragment[1]
    write_selection(unused, 16, stamp=STAMP + 5_000_000_000)
    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    second = dataset(fragment, cache, require_ink)
    np.testing.assert_array_equal(second.valid_coords, first.valid_coords)


def test_effective_fitted_grid_is_the_cache_input(fragment, tmp_path, monkeypatch):
    source, labels, mask = fragment
    write_selection(labels, shape=(34, 34))
    first = dataset(fragment, tmp_path / "shared", True)
    pixels = np.asarray(Image.open(labels)).copy()
    pixels[32:, :] = pixels[:, 32:] = 255  # cropped away by the existing grid fit
    Image.fromarray(pixels).save(labels)
    os.utime(labels, ns=(STAMP + 5_000_000_000,) * 2)
    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    second = dataset(fragment, tmp_path / "shared", True)
    np.testing.assert_array_equal(second.valid_coords, first.valid_coords)


def test_implicit_full_volume_selection_tracks_grid_shape(fragment, tmp_path):
    source = fragment[0]

    def full(cache):
        return VesuviusLabeledDataset(
            str(source),
            None,
            patch_size=16,
            num_layers=4,
            cache_dir=str(cache),
            jitter=False,
        )

    first = full(tmp_path / "shared")
    assert len(first) == 4
    zarr.open(str(source), mode="a").resize((4, 48, 48))
    warm, fresh = full(tmp_path / "shared"), full(tmp_path / "fresh")
    assert len(fresh) == 9
    np.testing.assert_array_equal(warm.valid_coords, fresh.valid_coords)


def test_ct_intensity_edits_do_not_change_coordinate_identity(
    fragment, tmp_path, monkeypatch
):
    first = dataset(fragment, tmp_path / "shared", True)
    zarr.open(str(fragment[0]), mode="a")[:] = 128
    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    second = dataset(fragment, tmp_path / "shared", True)
    np.testing.assert_array_equal(second.valid_coords, first.valid_coords)
    assert second[0][0].mean().item() == pytest.approx(128 / 255)


@pytest.mark.parametrize(
    "settings", [{"patch_size": 8}, {"min_mask_ratio": 0.9, "min_ink_ratio": 0.9}]
)
def test_changed_sampler_settings_match_a_fresh_search(fragment, tmp_path, settings):
    dataset(fragment, tmp_path / "shared", True)
    warm = dataset(fragment, tmp_path / "shared", True, **settings)
    fresh = dataset(fragment, tmp_path / "fresh", True, **settings)
    np.testing.assert_array_equal(warm.valid_coords, fresh.valid_coords)


def test_explicit_json_coordinates_bypass_automatic_cache(
    fragment, tmp_path, monkeypatch
):
    import json

    catalogue = tmp_path / "patches.json"
    catalogue.write_text(json.dumps({"patches": [{"y": 16, "x": 16}]}))
    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    result = dataset(fragment, tmp_path / "cache", True, patches_json=str(catalogue))
    np.testing.assert_array_equal(result.valid_coords, [[16, 16]])
    assert not (tmp_path / "cache").exists()


def test_legacy_timestamp_cache_is_ignored_and_preserved(fragment, tmp_path):
    source, labels, mask = fragment
    write_selection(labels, 16)
    cache = tmp_path / "shared"
    cache.mkdir()
    uri_hash = hashlib.md5(str(source).encode()).hexdigest()[:8]
    seconds = STAMP // 1_000_000_000
    legacy = (
        cache
        / f"valid_coords_villa_grid_{uri_hash}_16_{seconds}_{seconds}_1_0.05_0.01.npy"
    )
    np.save(legacy, np.array([[0, 0]], np.int32))
    before = legacy.read_bytes()
    current = dataset(fragment, cache, True)
    np.testing.assert_array_equal(current.valid_coords, [[16, 16]])
    assert legacy.read_bytes() == before


@pytest.mark.parametrize("warm", [False, True])
@pytest.mark.parametrize(
    "settings",
    [
        {"patch_size": 16.0},
        {"patch_size": 16.5},
        {"patch_size": "16"},
        {"patch_size": True},
        {"patch_size": 0},
        {"min_mask_ratio": "0.05"},
        {"min_ink_ratio": "0.01"},
        {"min_mask_ratio": float("nan")},
        {"min_ink_ratio": float("inf")},
    ],
)
def test_invalid_settings_cannot_alias_a_valid_warm_cache(
    fragment, tmp_path, warm, settings
):
    cache = tmp_path / "shared"
    if warm:
        dataset(fragment, cache, True)
    with pytest.raises(ValueError, match="coordinate-cache"):
        dataset(fragment, cache, True, **settings)


def test_numpy_integer_and_real_settings_remain_supported(
    fragment, tmp_path, monkeypatch
):
    first = dataset(fragment, tmp_path / "shared", True)
    settings = {
        "patch_size": np.int64(16),
        "min_mask_ratio": np.float64(0.05),
        "min_ink_ratio": np.float64(0.01),
    }
    second = dataset(fragment, tmp_path / "shared", True, **settings)
    np.testing.assert_array_equal(second.valid_coords, first.valid_coords)
    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    repeated = dataset(fragment, tmp_path / "shared", True, **settings)
    np.testing.assert_array_equal(repeated.valid_coords, second.valid_coords)


@pytest.mark.parametrize("warm", [False, True])
def test_narrow_integer_patch_size_matches_python_integer(fragment, tmp_path, warm):
    source, labels, mask = fragment
    zarr.open(str(source), mode="a").resize((4, 160, 32))
    write_selection(labels, shape=(160, 32))
    write_selection(mask, shape=(160, 32))
    cache = tmp_path / "shared"
    expected = dataset(
        fragment, cache if warm else tmp_path / "reference", True, strict_reads=True
    )
    # Grid height exceeds int8's range, even though the patch size fits. Both
    # cached and fresh sampling must use the integer represented by the key.
    actual = dataset(fragment, cache, True, patch_size=np.int8(16), strict_reads=True)
    np.testing.assert_array_equal(actual.valid_coords, expected.valid_coords)
    expected.jitter = actual.jitter = True
    np.testing.assert_array_equal(actual[0][0], expected[0][0])
    np.testing.assert_array_equal(actual[0][1], expected[0][1])


@pytest.mark.skipif(
    np.finfo(np.longdouble).eps >= np.finfo(float).eps,
    reason="longdouble has no precision beyond float64 on this platform",
)
def test_higher_precision_threshold_does_not_alias_a_float_cache(fragment, tmp_path):
    source, labels, mask = fragment
    pixels = np.zeros((32, 32), np.uint8)
    pixels[0, 0] = 255  # exactly 1/256 of the first 16px patch
    Image.fromarray(pixels).save(labels)
    threshold = 1 / 256
    first = dataset(
        fragment, tmp_path / "shared", True, min_mask_ratio=0.0, min_ink_ratio=threshold
    )
    np.testing.assert_array_equal(first.valid_coords, [[0, 0]])
    precise = np.longdouble(threshold) + np.finfo(np.longdouble).eps
    assert precise > threshold and float(precise) == threshold
    for cache in [tmp_path / "shared", tmp_path / "fresh"]:
        with pytest.raises(ValueError, match="coverage"):
            dataset(fragment, cache, True, min_mask_ratio=0.0, min_ink_ratio=precise)


@pytest.mark.parametrize(
    "settings", [{"min_mask_ratio": True}, {"min_ink_ratio": False}]
)
def test_boolean_ratios_are_refused_like_a_boolean_patch_size(
    fragment, tmp_path, settings
):
    # bool is a numbers.Real, so only the explicit check keeps True from meaning 1.
    with pytest.raises(ValueError, match="coordinate-cache"):
        dataset(fragment, tmp_path / "cache", True, **settings)


def test_the_target_dtype_is_part_of_the_selection_identity(tmp_path):
    from vesuvius_autoresearch.core.vesuvius_loader import _coordinate_cache_path

    # The same bytes mean 255 as uint8 and -1 as int8, which a threshold can treat
    # differently, so the two must not share coordinates.
    unsigned = np.full((32, 32), 255, np.uint8)

    def key(target):
        return _coordinate_cache_path(
            str(tmp_path), "ct.zarr", (4, 32, 32), 16, target, 0.5, 0.5
        )

    assert key(unsigned) != key(unsigned.view(np.int8))
    assert key(unsigned) == key(unsigned.copy())
