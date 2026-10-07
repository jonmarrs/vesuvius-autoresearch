"""Surface adapters must preserve geometry, read errors, and supervision provenance."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
import tifffile

from repro.sota_data import render_cli as cli, render_surface as rs
from repro.sota_data.convert import convert_surface_volume, to_uint8
from repro.sota_data.qualitative import write_fragment


def _geometry(h=8, w=8, z=20):
    y, x = np.mgrid[:h, :w].astype(np.float32)
    return np.stack([x + 4, y + 4, np.full_like(x, z)], axis=-1)


def _tifxyz(tmp_path, xyz):
    path = tmp_path / "geometry"
    path.mkdir()
    for c, name in enumerate("xyz"):
        tifffile.imwrite(path / f"{name}.tif", xyz[..., c])
    return str(path)


def _volume(monkeypatch, vol):
    def factory(*args):
        def fetch(z0, z1, y0, y1, x0, x1):
            return vol[z0:z1, y0:y1, x0:x1]

        fetch.dtype = vol.dtype
        return fetch, vol.shape

    monkeypatch.setattr(rs, "zarr_fetch", factory)


def test_depth_clipping_is_counted():
    pm = _geometry(z=1)[..., ::-1]
    normals = np.zeros_like(pm)
    normals[..., 0] = 1
    vol = np.full((10, 20, 20), 50, np.uint8)
    layers, stats = rs.sample_layers(
        pm,
        np.ones((8, 8), bool),
        normals,
        lambda z0, z1, y0, y1, x0, x1: vol[z0:z1, y0:y1, x0:x1],
        n_layers=4,
        k0=-2,
    )
    assert np.all(layers[0] == 0)
    assert stats["clamped_frac"] == 0.25
    assert stats["valid_frac"] == 0


def test_all_invalid_normals_are_counted():
    pm = _geometry()[..., ::-1]
    layers, stats = rs.sample_layers(
        pm,
        np.ones((8, 8), bool),
        np.full_like(pm, np.nan),
        lambda *args: pytest.fail("invalid geometry must not fetch data"),
    )
    assert not layers.any()
    assert stats["clamped_frac"] == 1
    assert stats["valid_frac"] == 0


def test_saved_mask_excludes_nan_normal_neighbors(tmp_path, monkeypatch):
    xyz = _geometry()
    xyz[3, 3] = -1
    geometry = _tifxyz(tmp_path, xyz)
    _volume(monkeypatch, np.full((50, 20, 20), 50, np.uint8))
    out, stats = rs.render_region_tifxyz(
        "s", geometry, "volume", 0, 0, 8, 0, 1, tmp_path / "out"
    )
    mask = cv2.imread(f"{out}/s_render_mask.png", 0)
    assert mask[3, 2] == 0
    assert mask[0, 0] == 255
    assert stats["valid_frac"] == (mask > 0).mean()


@pytest.mark.parametrize("region", [(-1, 0, 4), (0, -1, 4), (6, 0, 4), (0, 6, 4)])
def test_tifxyz_region_must_fit(tmp_path, monkeypatch, region):
    path = _tifxyz(tmp_path, _geometry())
    _volume(monkeypatch, np.full((50, 20, 20), 50, np.uint8))
    y0, x0, size = region
    with pytest.raises(ValueError, match="region"):
        rs.render_region_tifxyz("s", path, "v", y0, x0, size, 0, 1, tmp_path / "out")
    assert not (tmp_path / "out" / "s_render").exists()


@pytest.mark.parametrize("sign", [0, 2, float("nan")])
def test_normals_require_a_direction_sign(sign):
    pm = _geometry()[..., ::-1]
    with pytest.raises(ValueError, match="sign"):
        rs.surface_normals(pm, np.ones((8, 8), bool), sign)


def test_writer_does_not_replace_existing_fragment(tmp_path):
    out = tmp_path / "s"
    out.mkdir()
    label = out / "s_inklabels.png"
    label.write_bytes(b"real existing label")
    with pytest.raises(FileExistsError):
        rs.write_render_fragment(
            np.ones((26, 8, 8), np.uint8), np.ones((8, 8), bool), tmp_path, "s", {}
        )
    assert label.read_bytes() == b"real existing label"
    assert not (out / "layers").exists()


def test_failed_png_write_does_not_publish_fragment(tmp_path, monkeypatch):
    monkeypatch.setattr(cv2, "imwrite", lambda *args: False)
    with pytest.raises(OSError, match="write"):
        rs.write_render_fragment(
            np.ones((26, 8, 8), np.uint8), np.ones((8, 8), bool), tmp_path, "s", {}
        )
    assert not (tmp_path / "s").exists()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("frag_id", ["../outside", "a/b", "..", "/absolute"])
def test_writer_rejects_unsafe_fragment_id(tmp_path, frag_id):
    with pytest.raises(ValueError, match="fragment"):
        rs.write_render_fragment(
            np.ones((26, 8, 8), np.uint8), np.ones((8, 8), bool), tmp_path, frag_id, {}
        )


def test_qualitative_fragment_has_no_synthetic_ground_truth(tmp_path):
    out = Path(write_fragment(np.ones((26, 8, 8), np.uint8), tmp_path, "s"))
    assert not (out / "s_inklabels.png").exists()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_pixels_cannot_become_uint8(value):
    with pytest.raises(ValueError, match="finite"):
        to_uint8(np.full((4, 4), value, np.float32))


def test_failed_conversion_leaves_no_fragment(tmp_path):
    src = tmp_path / "source"
    (src / "layers").mkdir(parents=True)
    for i in range(26):
        tifffile.imwrite(src / "layers" / f"{i:02d}.tif", np.ones((4, 4), np.uint8))
    with pytest.raises(ValueError, match="inklabels"):
        convert_surface_volume(src, "s", tmp_path / "out")
    assert not (tmp_path / "out" / "s").exists()


def _chunk_reader(monkeypatch, values, **overrides):
    import s3fs

    meta = {
        "zarr_format": 2,
        "shape": [4, 4, 4],
        "chunks": [2, 2, 2],
        "dtype": "|u1",
        "compressor": None,
        "fill_value": 7,
        "order": "C",
        "filters": None,
    }
    meta.update(overrides)

    class FS:
        def cat(self, keys, on_error="raise"):
            if isinstance(keys, str) and keys.endswith(".zarray"):
                return json.dumps(meta).encode()

            def get(key):
                value = values.get(
                    key.removeprefix("bucket/volume/0/"), FileNotFoundError(key)
                )
                if isinstance(value, Exception) and on_error == "raise":
                    raise value
                return value

            if isinstance(keys, str):
                return get(keys)
            return {
                key: get(key)
                for key in keys
                if on_error != "omit" or not isinstance(get(key), Exception)
            }

    monkeypatch.setattr(s3fs, "S3FileSystem", lambda **kwargs: FS())
    return rs.ChunkCachedZarrFetch("bucket/volume", 0)


@pytest.mark.parametrize("warm", [False, True])
def test_operational_chunk_errors_are_not_fill_values(monkeypatch, warm):
    reader = _chunk_reader(monkeypatch, {"0.0.0": PermissionError("denied")})
    with pytest.raises(OSError, match="denied"):
        if warm:
            reader.warm([(0, 2, 0, 2, 0, 2)])
        else:
            reader(0, 2, 0, 2, 0, 2)


@pytest.mark.parametrize("warm", [False, True])
def test_missing_chunks_use_declared_fill_value(monkeypatch, warm):
    reader = _chunk_reader(monkeypatch, {})
    if warm:
        reader.warm([(0, 2, 0, 2, 0, 2)])
    assert np.all(reader(0, 2, 0, 2, 0, 2) == 7)


def test_flat_scale_candidates_are_rejected(tmp_path, monkeypatch):
    def fake_render(*args, frag_id, **kwargs):
        return rs.write_render_fragment(
            np.full((26, 8, 8), 50, np.uint8),
            np.ones((8, 8), bool),
            args[8],
            frag_id,
            {},
        ), {}

    monkeypatch.setattr(cli, "render_region", fake_render)
    with pytest.raises(SystemExit, match="scale"):
        cli.infer_scale("s", "obj", "vol", str(tmp_path), 0, 0, 8, 0, 1)


def _obj(path):
    # Texture indices are deliberately shuffled relative to vertex order.
    path.write_text(
        "v 4 4 20\nv 11 4 20\nv 11 11 20\nv 4 11 20\n"
        "vt 1 1\nvt 0 1\nvt 0 0\nvt 1 0\nf 1/3 2/4 3/1 4/2\n"
    )
    return str(path)


def test_obj_crop_uses_full_grid_and_indexed_uvs(tmp_path, monkeypatch):
    obj = _obj(tmp_path / "s.obj")
    vol = np.broadcast_to(np.arange(20, dtype=np.uint8)[None, None], (50, 20, 20))
    _volume(monkeypatch, vol)
    out, stats = rs.render_region(
        "s",
        obj,
        "volume",
        2,
        3,
        (3, 4),
        0,
        1,
        tmp_path / "out",
        obj_grid_size=(8, 8),
        obj_level_div=1,
        extra_prov={"level": 99, "volume": "wrong"},
    )
    mid = tifffile.imread(f"{out}/layers/30.tif")
    assert np.array_equal(mid, np.broadcast_to(np.arange(7, 11), (3, 4)))
    provenance = json.loads(Path(out, "s_render_render_provenance.json").read_text())
    assert provenance["level"] == 0 and provenance["volume"] == "volume"
    assert provenance["obj_level_div"] == 1 and provenance["obj_grid_shape"] == [8, 8]
    assert provenance["region_px"] == [2, 3, [3, 4]]
    assert stats["valid_frac"] == 1


def test_point_map_crop_matches_full_grid():
    v = np.array([[0, 0, 20], [7, 0, 20], [7, 7, 20], [0, 7, 20]], float)
    vt = v[:, :2] / 7
    full, mask = rs.build_point_map(v, vt, (8, 10))
    crop, crop_mask = rs.build_point_map(
        v, vt, (3, 4), origin=(2, 3), grid_size=(8, 10)
    )
    assert np.array_equal(crop, full[2:5, 3:7])
    assert np.array_equal(crop_mask, mask[2:5, 3:7])


@pytest.mark.parametrize("div", [0, -1, float("nan"), float("inf")])
def test_invalid_divisor_fails_before_volume_read(tmp_path, monkeypatch, div):
    monkeypatch.setattr(
        rs, "zarr_fetch", lambda *args: pytest.fail("must validate first")
    )
    with pytest.raises(ValueError, match="divisor"):
        rs.render_region(
            "s", "unused", "vol", 0, 0, 8, 0, 1, tmp_path, obj_level_div=div
        )


def test_obj_offset_requires_full_grid(tmp_path):
    with pytest.raises(ValueError, match="obj_grid_size"):
        rs.render_region("s", "unused", "vol", 1, 0, 8, 0, 1, tmp_path)


@pytest.mark.parametrize("dtype", ["uint8", "uint16", ">u2"])
def test_render_preserves_source_intensity_scale(tmp_path, monkeypatch, dtype):
    xyz = _tifxyz(tmp_path, _geometry())
    value = 1 if dtype == "uint8" else 1024
    _volume(monkeypatch, np.full((50, 20, 20), value, dtype))
    out, _ = rs.render_region_tifxyz("s", xyz, "vol", 0, 0, 8, 0, 1, tmp_path / "out")
    expected = 1 if dtype == "uint8" else 4
    assert np.all(tifffile.imread(f"{out}/layers/30.tif") == expected)


def test_render_with_no_full_depth_support_is_not_published(tmp_path, monkeypatch):
    xyz = _tifxyz(tmp_path, _geometry(z=1))
    _volume(monkeypatch, np.full((50, 20, 20), 50, np.uint8))
    with pytest.raises(ValueError, match="every requested depth"):
        rs.render_region_tifxyz("s", xyz, "v", 0, 0, 8, 0, 1, tmp_path / "out")
    assert not (tmp_path / "out" / "s_render").exists()


@pytest.mark.parametrize(
    "data", [np.zeros((1, 1, 1), np.uint8), np.full((4, 4, 4), np.nan)]
)
def test_known_volume_shape_detects_bad_read_results(data):
    pm = _geometry()[..., ::-1]
    normal = np.zeros_like(pm)
    normal[..., 0] = 1
    with pytest.raises(ValueError, match="fetched"):
        rs.sample_layers(
            pm,
            np.ones((8, 8), bool),
            normal,
            lambda *args: data,
            n_layers=2,
            k0=0,
            volume_shape=(50, 20, 20),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"zarr_format": 3},
        {"shape": [4, 4]},
        {"chunks": [0, 2, 2]},
        {"dtype": "int32"},
        {"order": "wrong"},
        {"dimension_separator": "!"},
        {"fill_value": "NaN"},
        {"fill_value": 300},
        {"filters": [{"id": "delta"}]},
    ],
)
def test_unsupported_zarr_metadata_is_rejected(monkeypatch, overrides):
    with pytest.raises(ValueError):
        _chunk_reader(monkeypatch, {}, **overrides)


def test_compressed_chunks_and_missing_edges_match_zarr(monkeypatch):
    import numcodecs
    import zarr

    chunks = (2, 2, 2)
    codec = numcodecs.Blosc(cname="zstd")
    store = zarr.storage.MemoryStore()
    arr = zarr.create(
        shape=(3, 3, 3),
        chunks=chunks,
        dtype="uint8",
        fill_value=7,
        compressor=codec,
        store=store,
    )
    arr[:2, :2, :2] = np.arange(8).reshape(chunks)
    reader = _chunk_reader(
        monkeypatch,
        {"0.0.0": store["0.0.0"]},
        shape=[3, 3, 3],
        compressor=codec.get_config(),
    )
    reader.warm([(0, 3, 0, 3, 0, 3)])
    assert np.array_equal(reader(0, 3, 0, 3, 0, 3), arr[:])


def test_corrupt_chunk_is_not_published_as_fill(monkeypatch):
    reader = _chunk_reader(monkeypatch, {"0.0.0": b"bad"})
    with pytest.raises(ValueError, match="invalid Zarr chunk"):
        reader.warm([(0, 2, 0, 2, 0, 2)])


def test_chunk_cache_has_an_explicit_memory_cap(monkeypatch):
    reader = _chunk_reader(monkeypatch, {})
    reader.max_cache_bytes = 1
    with pytest.raises(MemoryError, match="budget"):
        reader.warm([(0, 2, 0, 2, 0, 2)])
    assert not reader.cache
    with pytest.raises(MemoryError, match="budget"):
        reader(0, 2, 0, 2, 0, 2)


def test_empty_outside_bbox_does_not_fetch_chunks(monkeypatch):
    reader = _chunk_reader(monkeypatch, {})
    assert reader.warm([(5, 6, 0, 2, 0, 2)]) == 0
    assert reader(5, 6, 0, 2, 0, 2).shape == (0, 2, 2)


def test_rectangular_scale_probes_clean_up_and_share_the_final_grid(
    tmp_path, monkeypatch
):
    calls = []

    def render(*args, frag_id, obj_level_div, obj_grid_size, **kwargs):
        calls.append((args[3:6], obj_grid_size))
        layers = np.full((26, 8, 12), 50, np.uint8)
        if obj_level_div <= 2:
            layers[:, ::2] = 100 * obj_level_div
        return rs.write_render_fragment(
            layers, np.ones((8, 12), bool), args[8], frag_id, {}
        ), {}

    monkeypatch.setattr(cli, "render_region", render)
    assert (
        cli.infer_scale(
            "s", "obj", "vol", tmp_path, 2, 3, (8, 12), 0, 1, obj_grid_size=(20, 30)
        )
        == 2
    )
    assert calls == [((2, 3, (8, 12)), (20, 30))] * 3
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "option",
    [
        ["--sign", "2"],
        ["--scale", "nan"],
        ["--level", "-1"],
        ["--region", "1", "0", "8"],
        ["--frag-id", "../x"],
    ],
)
def test_invalid_cli_options_fail_before_download(monkeypatch, tmp_path, option):
    monkeypatch.setattr(
        cli, "_fetch_obj_if_s3", lambda *args: pytest.fail("must validate first")
    )
    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--obj",
                "bucket/s.obj",
                "--volume",
                "vol",
                "--out",
                str(tmp_path),
                *option,
            ]
        )
    assert exc.value.code == 2


def test_obj_cache_keys_include_remote_identity(tmp_path, monkeypatch):
    import s3fs

    monkeypatch.chdir(tmp_path)

    class FS:
        def get(self, key, path):
            Path(path).write_text(key)

    monkeypatch.setattr(s3fs, "S3FileSystem", lambda **kwargs: FS())
    a = cli._fetch_obj_if_s3("s3://bucket/a/s.obj")
    b = cli._fetch_obj_if_s3("s3://bucket/b/s.obj")
    assert (
        a != b
        and Path(a).read_text() == "bucket/a/s.obj"
        and Path(b).read_text() == "bucket/b/s.obj"
    )
    assert cli._fetch_obj_if_s3("local/s.obj") == "local/s.obj"


def test_failed_obj_download_cannot_enter_cache(tmp_path, monkeypatch):
    import s3fs

    monkeypatch.chdir(tmp_path)

    class FS:
        def get(self, key, path):
            Path(path).write_text("partial")
            raise OSError("network failed")

    monkeypatch.setattr(s3fs, "S3FileSystem", lambda **kwargs: FS())
    with pytest.raises(OSError, match="network"):
        cli._fetch_obj_if_s3("s3://bucket/s.obj")
    assert not list(tmp_path.rglob("s.obj"))
    assert not list(tmp_path.rglob(".download-*"))


def test_qualitative_fragment_loads_for_inference_without_ground_truth(tmp_path):
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask, read_volume_mask

    write_fragment(np.full((26, 8, 8), 50, np.uint8), tmp_path, "s")
    cfg = DetectorConfig(data_root=str(tmp_path))
    image, mask, original_shape = read_volume_mask(cfg, "s")
    assert image.shape[-1] == 26 and original_shape == (8, 8) and mask.max() == 255
    with pytest.raises(ValueError, match="inklabels"):
        read_image_mask(cfg, "s")


def test_supplied_label_is_part_of_complete_publication(tmp_path):
    label = np.full((8, 8), 255, np.uint8)
    out = write_fragment(np.full((26, 8, 8), 50, np.uint8), tmp_path, "s", label=label)
    assert np.array_equal(cv2.imread(f"{out}/s_inklabels.png", 0), label)


def test_failed_label_write_does_not_publish_fragment(tmp_path, monkeypatch):
    original = cv2.imwrite

    def write(path, pixels):
        return False if "inklabels" in path else original(path, pixels)

    monkeypatch.setattr(cv2, "imwrite", write)
    with pytest.raises(OSError, match="inklabels"):
        write_fragment(
            np.ones((26, 8, 8), np.uint8),
            tmp_path,
            "s",
            label=np.zeros((8, 8), np.uint8),
        )
    assert not list(tmp_path.iterdir())


def test_failed_tiff_write_cleans_staging(tmp_path, monkeypatch):
    original = tifffile.imwrite
    count = 0

    def write(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 3:
            raise OSError("disk full")
        return original(*args, **kwargs)

    monkeypatch.setattr(tifffile, "imwrite", write)
    with pytest.raises(OSError, match="disk full"):
        write_fragment(np.ones((26, 8, 8), np.uint8), tmp_path, "s")
    assert not list(tmp_path.iterdir())


def test_nonfinite_provenance_cannot_be_published(tmp_path):
    with pytest.raises(ValueError):
        rs.write_render_fragment(
            np.ones((26, 8, 8), np.uint8),
            np.ones((8, 8), bool),
            tmp_path,
            "s",
            {"level": float("nan")},
        )
    assert not list(tmp_path.iterdir())


def _conversion_source(tmp_path):
    source = tmp_path / "source"
    (source / "layers").mkdir(parents=True)
    for i in range(40):
        tifffile.imwrite(source / "layers" / f"{i}.tif", np.full((4, 4), i, np.uint8))
    cv2.imwrite(str(source / "s_inklabels.png"), np.full((4, 4), 255, np.uint8))
    cv2.imwrite(str(source / "s_mask.png"), np.full((4, 4), 255, np.uint8))
    return source


def test_conversion_sorts_depth_indices_numerically(tmp_path):
    source = _conversion_source(tmp_path)
    out = convert_surface_volume(source, "s", tmp_path / "out")
    assert np.all(tifffile.imread(f"{out}/layers/17.tif") == 7)
    assert np.all(tifffile.imread(f"{out}/layers/42.tif") == 32)


@pytest.mark.parametrize(
    "failure",
    [
        "layer shape",
        "color layer",
        "mask shape",
        "mask unreadable",
        "ambiguous label",
        "depth gap",
        "duplicate depth",
    ],
)
def test_invalid_conversion_inputs_never_publish(tmp_path, failure):
    source = _conversion_source(tmp_path)
    if failure == "layer shape":
        tifffile.imwrite(source / "layers/12.tif", np.zeros((4, 5), np.uint8))
    elif failure == "color layer":
        tifffile.imwrite(
            source / "layers/12.tif", np.zeros((4, 4, 3), np.uint8), photometric="rgb"
        )
    elif failure == "mask shape":
        cv2.imwrite(str(source / "s_mask.png"), np.ones((20, 20), np.uint8))
    elif failure == "mask unreadable":
        (source / "s_mask.png").write_bytes(b"broken")
    elif failure == "ambiguous label":
        cv2.imwrite(str(source / "other_inklabels.png"), np.zeros((4, 4), np.uint8))
    elif failure == "depth gap":
        (source / "layers/12.tif").rename(source / "layers/50.tif")
    elif failure == "duplicate depth":
        tifffile.imwrite(source / "layers/00.tif", np.zeros((4, 4), np.uint8))
    with pytest.raises(ValueError):
        convert_surface_volume(source, "s", tmp_path / "out")
    assert not (tmp_path / "out" / "s").exists()


def test_reader_supports_fortran_order_and_slash_separator(monkeypatch):
    values = np.arange(8, dtype=np.uint8).reshape(2, 2, 2)
    reader = _chunk_reader(
        monkeypatch,
        {"0/0/0": values.tobytes(order="F")},
        order="F",
        dimension_separator="/",
    )
    reader.warm([(0, 2, 0, 2, 0, 2)])
    assert np.array_equal(reader(0, 2, 0, 2, 0, 2), values)


def test_sampler_rejects_nonunit_normals():
    pm = _geometry()[..., ::-1]
    normal = np.zeros_like(pm)
    with pytest.raises(ValueError, match="unit"):
        rs.sample_layers(
            pm,
            np.ones((8, 8), bool),
            normal,
            lambda *args: pytest.fail("must not read"),
        )


def test_clipped_uint16_sampling_is_identical_across_fetch_strategies():
    pm = _geometry(32, 32)[..., ::-1].copy()
    pm[:8, :, 0] = 1
    normals = np.zeros_like(pm)
    normals[..., 0] = 1
    vol = np.full((50, 50, 50), 1024, np.uint16)

    def fetch(z0, z1, y0, y1, x0, x1):
        return vol[z0:z1, y0:y1, x0:x1]

    params = {"tile": 8, "volume_shape": vol.shape, "return_valid": True}
    grouped = rs.sample_layers(pm, np.ones((32, 32), bool), normals, fetch, **params)
    individual = rs.sample_layers(
        pm, np.ones((32, 32), bool), normals, fetch, group_max_voxels=1, **params
    )
    assert np.array_equal(grouped[0], individual[0])
    assert grouped[1] == individual[1] and np.array_equal(grouped[2], individual[2])
    assert grouped[1]["valid_frac"] == 0.75 and grouped[1]["clamped_frac"] > 0


def test_scroll3_inference_never_touches_existing_labels(tmp_path, monkeypatch):
    import importlib

    from repro.sota_data import scroll3_render

    detector_infer = importlib.import_module("vesuvius_autoresearch.detector.infer")

    label = tmp_path / "s" / "s_inklabels.png"
    label.parent.mkdir()
    label.write_bytes(b"real label must survive")
    monkeypatch.setattr(detector_infer, "infer", lambda *args: np.zeros((4, 4)))
    assert scroll3_render.infer_no_label(str(tmp_path), "s").shape == (4, 4)
    assert label.read_bytes() == b"real label must survive"


def test_tiny_chunks_cannot_allocate_millions_of_index_objects(monkeypatch):
    reader = _chunk_reader(monkeypatch, {}, shape=[100, 100, 100], chunks=[1, 1, 1])
    with pytest.raises(MemoryError, match="chunk count budget"):
        reader.warm([(0, 100, 0, 100, 0, 100)])
    assert not reader.cache


@pytest.mark.parametrize("offset", [0.0, -0.25])
def test_interpolated_surface_respects_vertex_bounds_without_hiding_negative_geometry(
    offset,
):
    u, v = np.meshgrid(np.linspace(0, 1, 20), np.linspace(0, 1, 20))
    uv = np.stack([u.ravel(), v.ravel()], axis=1)
    vertices = np.stack(
        [
            100 * u.ravel() + offset,
            100 * v.ravel(),
            200 * u.ravel() + 300 * v.ravel() + 10,
        ],
        axis=1,
    )
    points, valid = rs.build_point_map(vertices, uv, 32)
    assert np.all(points[valid] >= vertices.min(axis=0))
    assert np.all(points[valid] <= vertices.max(axis=0))
    if offset < 0:
        with pytest.raises(ValueError, match="bounds"):
            rs.assert_bounds_fit(points, valid, (600, 600, 600))
    else:
        rs.assert_bounds_fit(points, valid, (600, 600, 600))
