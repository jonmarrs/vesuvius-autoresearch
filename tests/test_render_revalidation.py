"""Current-mask renderer comparison and captured-input revalidation contracts."""

import hashlib
import io
import json
import urllib.error

import numpy as np
import pytest

from repro.sota_data import (
    render_surface as renderer,
    revalidate_render_1667_v2 as study,
)


def arrays():
    rng = np.random.default_rng(1729)
    center = rng.uniform(20, 180, (32, 64)).astype(np.float32)
    layers = np.repeat(center[None], study.DESIGN["layers"], axis=0)
    return layers, np.ones(center.shape, bool), np.repeat(center[None], 5, axis=0)


def test_comparison_uses_full_depth_support_not_geometry_validity():
    rng = np.random.default_rng(3)
    volume = rng.integers(0, 255, (40, 40, 72), dtype=np.uint8)
    yy, xx = np.mgrid[3:35, 3:67]
    pointmap = np.stack([np.full_like(yy, 20), yy, xx], axis=-1).astype(np.float32)
    pointmap[:, :3, 0] = 8  # center readable, early depth samples outside CT
    geometry = np.ones(yy.shape, bool)
    normals = np.zeros_like(pointmap)
    normals[..., 0] = 1
    layers, stats, supported = renderer.sample_layers(
        pointmap,
        geometry,
        normals,
        lambda z0, z1, y0, y1, x0, x1: volume[z0:z1, y0:y1, x0:x1],
        volume_shape=volume.shape,
        return_valid=True,
    )
    assert stats["geometry_valid_frac"] == 1 and stats["valid_frac"] < 1
    assert not supported[:, :3].any() and supported[:, 3:].all()
    refs = np.repeat(layers[13][None], 5, axis=0)
    refs[:, ~supported] = 255
    correct = study.compare_center(layers, supported, refs)
    old_mask = study.compare_center(layers, geometry, refs)
    assert correct["best_ncc"] == pytest.approx(1)
    assert correct["best_ncc"] - old_mask["best_ncc"] > 0.05
    assert correct["supported_pixels"] == 32 * 61
    assert correct["verdict"] == "PASS"


def test_excluded_nonfinite_pixels_do_not_enter_any_comparison():
    layers, mask, refs = arrays()
    mask[:, :2] = False
    layers[:, ~mask] = np.nan
    refs[:, ~mask] = np.nan
    result = study.compare_center(layers, mask, refs)
    assert result["ncc_by_depth"] == pytest.approx([1] * 5)
    assert result["best_reference_depth"] == 50  # fixed order on true ties


def test_gate_compares_full_precision_and_records_all_fixed_depths():
    layers, mask, refs = arrays()
    x = layers[13].astype(np.float64)
    x -= x.mean()
    x /= np.linalg.norm(x)
    noise = np.random.default_rng(4).normal(size=x.shape)
    noise -= noise.mean()
    noise -= (noise * x).sum() * x
    noise /= np.linalg.norm(noise)
    for correlation, expected in ((0.59996, "FAIL"), (0.60004, "PASS")):
        target = correlation * x + np.sqrt(1 - correlation**2) * noise
        refs = np.repeat(target[None], 5, axis=0)
        result = study.compare_center(layers, mask, refs)
        assert result["verdict"] == expected
        assert result["best_ncc"] == pytest.approx(correlation)
        assert result["reference_depths"] == [50, 52, 54, 56, 58]


@pytest.mark.parametrize("bad", ["coverage", "count", "constant", "constant_ref"])
def test_undefined_or_insufficient_comparisons_are_indeterminate(bad):
    layers, mask, refs = arrays()
    if bad == "coverage":
        mask[:, :16] = False
    elif bad == "count":
        layers, mask, refs = layers[:, :16, :32], mask[:16, :32], refs[:, :16, :32]
    elif bad == "constant":
        layers[:] = 1
    else:
        refs[2] = 1  # cannot silently drop an unusable planned reference
    result = study.compare_center(layers, mask, refs)
    assert result["verdict"] == "INDETERMINATE"
    assert result["best_ncc"] is None and result["best_reference_depth"] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("bad", ["mask_dtype", "layers_shape", "refs_shape", "nan"])
def test_malformed_inputs_are_refused(bad):
    layers, mask, refs = arrays()
    if bad == "mask_dtype":
        mask = mask.astype(np.uint8)
    elif bad == "layers_shape":
        layers = layers[:-1]
    elif bad == "refs_shape":
        refs = refs[:-1]
    else:
        layers[0, 0, 0] = np.nan  # all requested depths must be finite
    with pytest.raises(ValueError):
        study.compare_center(layers, mask, refs)


class Response(io.BytesIO):
    status = 200

    def __init__(self, raw, count=None):
        super().__init__(raw)
        self.headers = {"Content-Length": str(len(raw) if count is None else count)}


class Opener:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def open(self, url, timeout):
        self.calls.append((url, timeout))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def source(tmp_path, response, *, total=32, per_object=16):
    src = study.SnapshotSource(
        tmp_path, max_total_bytes=total, max_object_bytes=per_object
    )
    src.opener = Opener(response)
    return src


def test_transport_records_exact_captured_bytes_and_reuses_the_capture(tmp_path):
    src = source(tmp_path, Response(b"original"))
    key = study.RAW + "/2/.zarray"
    assert src.cat(key) == b"original"
    assert src.cat([key])[key] == b"original"
    assert len(src.opener.calls) == 1
    assert src.records[key]["sha256"] == hashlib.sha256(b"original").hexdigest()
    assert src.total_bytes == 8
    src.path(key).write_bytes(b"modified")
    with pytest.raises(ValueError, match="changed"):
        src.verify()


@pytest.mark.parametrize("bad", ["oversize", "total", "short", "missing", "redirect"])
def test_incomplete_or_unavailable_sources_are_never_fill_values(tmp_path, bad):
    response = Response(b"abcdef")
    kwargs = {}
    if bad == "oversize":
        kwargs["per_object"] = 5
    elif bad == "total":
        kwargs["total"] = 5
    elif bad == "short":
        response = Response(b"abc", count=6)
    else:
        code = 404 if bad == "missing" else 302
        response = urllib.error.HTTPError("https://public.test", code, "no", {}, None)
    src = source(tmp_path, response, **kwargs)
    key = study.RAW + "/2/0/0/0"
    result = src.cat([key], on_error="return")
    assert isinstance(result[key], (OSError, ValueError))
    assert src.records == {} and not src.path(key).exists()


def test_snapshot_keys_cannot_escape_source_tree(tmp_path):
    src = source(tmp_path, Response(b"x"))
    for key in ("other/file", study.RAW + "/../outside", study.RAW + "//file"):
        with pytest.raises(ValueError, match="study source"):
            src.cat(key)
    assert not src.opener.calls


def test_explicit_transport_uses_production_chunk_decoder_without_s3fs(
    tmp_path, monkeypatch
):
    import builtins

    raw = np.arange(8, dtype=np.uint8).reshape(2, 2, 2)
    meta = {
        "zarr_format": 2,
        "shape": [2, 2, 2],
        "chunks": [2, 2, 2],
        "dtype": "|u1",
        "compressor": None,
        "fill_value": 0,
        "filters": None,
        "order": "C",
    }

    class FS:
        def cat(self, keys, on_error="raise"):
            if isinstance(keys, str):
                return (
                    json.dumps(meta).encode()
                    if keys.endswith(".zarray")
                    else raw.tobytes()
                )
            return {key: self.cat(key) for key in keys}

    original = builtins.__import__

    def guard(name, *args, **kwargs):
        assert name != "s3fs", "explicit source unexpectedly imports S3 transport"
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    reader = renderer.ChunkCachedZarrFetch("bucket/ct", 0, fs=FS())
    reader.warm([(0, 2, 0, 2, 0, 2)])
    np.testing.assert_array_equal(reader(0, 2, 0, 2, 0, 2), raw)


def plan(tmp_path):
    path = tmp_path / "plan.json"
    value = {
        "protocol": study.PROTOCOL,
        "baseline_commit": "a" * 40,
        "design": study.DESIGN,
        "source_sha256": study.source_hashes(),
    }
    path.write_text(json.dumps(value))
    return path, value


def test_plan_binds_design_and_selected_source_bytes_before_network_or_output(
    tmp_path, monkeypatch
):
    path, value = plan(tmp_path)
    _, actual, digest = study.read_plan(path)
    assert actual == value and digest == hashlib.sha256(path.read_bytes()).hexdigest()
    value["source_sha256"][study.SOURCES[0]] = "0" * 64
    path.write_text(json.dumps(value))
    monkeypatch.setattr(study, "SnapshotSource", lambda *a, **k: pytest.fail("network"))
    out = tmp_path / "result"
    with pytest.raises(ValueError, match="selected sources"):
        study.run(path, out)
    assert not out.exists()


def test_measurement_error_cleans_up_and_preserves_existing_output(
    tmp_path, monkeypatch
):
    path, _ = plan(tmp_path)
    out = tmp_path / "result"

    def fail(*args):
        raise OSError("incomplete source")

    monkeypatch.setattr(study, "measure", fail)
    with pytest.raises(OSError, match="incomplete"):
        study.run(path, out)
    assert not out.exists()
    out.mkdir()
    (out / "keep").write_bytes(b"existing evidence")
    with pytest.raises(ValueError, match="already exists"):
        study.run(path, out)
    assert (out / "keep").read_bytes() == b"existing evidence"


def test_complete_fixture_publishes_arrays_with_matching_hashes(tmp_path, monkeypatch):
    path, _ = plan(tmp_path)
    layers, mask, refs = arrays()
    monkeypatch.setattr(
        study,
        "measure",
        lambda source: (
            layers,
            mask,
            refs,
            {"sampling": {}, "comparison": study.compare_center(layers, mask, refs)},
        ),
    )
    out = tmp_path / "result"
    report = study.run(path, out)
    assert report["comparison"]["verdict"] == "PASS"
    assert json.loads((out / "report.json").read_bytes()) == report
    for name, expected in zip(
        ("layers.npy", "supported.npy", "references.npy"),
        (layers, mask, refs),
        strict=True,
    ):
        np.testing.assert_array_equal(np.load(out / name, allow_pickle=False), expected)
        assert (
            report["array_files"][name]
            == hashlib.sha256((out / name).read_bytes()).hexdigest()
        )


def test_plan_rewrite_after_capture_prevents_publication(tmp_path, monkeypatch):
    path, _ = plan(tmp_path)
    layers, mask, refs = arrays()

    def measured(source):
        path.write_bytes(
            path.read_bytes() + b"\n"
        )  # same parsed contents, new identity
        return (
            layers,
            mask,
            refs,
            {"comparison": study.compare_center(layers, mask, refs)},
        )

    monkeypatch.setattr(study, "measure", measured)
    out = tmp_path / "result"
    with pytest.raises(ValueError, match="plan changed"):
        study.run(path, out)
    assert not out.exists()
