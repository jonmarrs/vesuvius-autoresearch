"""Pinned acquisition is transactional; palette colors, not IDs, define labels."""

import hashlib
import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from scripts.training import fetch_fragment_example as cli
from vesuvius_autoresearch.core import fragment_example as example
from vesuvius_autoresearch.core.surface_volume_import import (
    build_import,
    plan_import,
    write_plan,
)


def _image(values, *, palette=None, transparency=None, orientation=None, fmt="PNG"):
    image = Image.fromarray(values)
    if palette is not None:
        image = Image.fromarray(values, mode="P")
        image.putpalette(palette + [0] * (768 - len(palette)))
    options = {}
    if transparency is not None:
        options["transparency"] = transparency
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        options["exif"] = exif
    raw = io.BytesIO()
    image.save(raw, format=fmt, **options)
    return raw.getvalue()


@pytest.fixture
def source(tmp_path, monkeypatch):
    shape = [2, 6, 8]
    values = (np.arange(48, dtype=np.uint16).reshape(6, 8) * 1000).astype(">u2")
    binary = (np.indices((6, 8)).sum(axis=0) % 2).astype(np.uint8)
    payloads = {
        "inklabels.png": _image(binary, palette=[0, 0, 0, 255, 255, 255]),
        "mask.png": _image(np.ones((6, 8), np.uint8), palette=[0, 0, 0, 255, 255, 255]),
        "surface_volume/meta.json": json.dumps(
            {"height": 6, "width": 8, "slices": 65, "voxelsize": 3.24}
        ).encode(),
        "surface_volume/16.tif": _image(values, fmt="TIFF"),
        "surface_volume/17.tif": _image(values + np.uint16(1), fmt="TIFF"),
    }
    base = "https://dl.ash2txt.org/fragments/Frag1/Example.volpkg/working/reference/"
    plan = {
        "schema_version": 1,
        "kind": "official_surface_fragment_example",
        "fragment_id": "Example",
        "base_url": base,
        "source_z_range": [16, 18],
        "shape_zyx": shape,
        "voxel_size_um": 3.24,
        "label_semantics": "black_background_white_ink",
        "mask_semantics": "black_excluded_white_included",
        "pin_observed_utc": "2026-11-16",
        "pin_basis": "synthetic test fixture",
        "files": [
            {
                "relative_path": name,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            for name, raw in payloads.items()
        ],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(plan))
    calls, behavior = [], {}

    class Response(io.BytesIO):
        def __init__(self, url, data):
            super().__init__(data)
            self.url = behavior.get("url", url)
            self.status = behavior.get("status", 200)
            self.headers = {
                "Content-Length": behavior.get("length", str(len(data))),
                "ETag": "synthetic",
            }

        def geturl(self):
            return self.url

    def open_request(request, timeout):
        calls.append(request.full_url)
        assert timeout == 30 and request.get_header("Accept-encoding") == "identity"
        if "error" in behavior:
            raise behavior["error"]
        name = request.full_url.removeprefix(base)
        return Response(request.full_url, behavior.get("payload", payloads[name]))

    monkeypatch.setattr(
        example.urllib.request,
        "build_opener",
        lambda *a: SimpleNamespace(open=open_request),
    )
    return SimpleNamespace(
        manifest=manifest,
        plan=plan,
        payloads=payloads,
        calls=calls,
        behavior=behavior,
        output=tmp_path / "download",
    )


def test_download_preserves_tiffs_and_prepares_importer_compatible_binary_labels(
    source, tmp_path
):
    target = example.fetch_example(source.manifest, source.output)
    assert target == source.output
    assert len(source.calls) == 5
    for name, raw in source.payloads.items():
        assert (target / "raw" / name).read_bytes() == raw
    labels = np.asarray(Image.open(target / "labels/inklabels.png"))
    assert set(np.unique(labels)) == {0, 255}
    receipt = json.loads((target / "source.json").read_text())
    assert receipt["manifest"] == source.plan
    assert (
        receipt["captured_manifest_sha256"]
        == hashlib.sha256(source.manifest.read_bytes()).hexdigest()
    )
    plan = plan_import(
        target / "raw/surface_volume",
        target / "labels/inklabels.png",
        16,
        18,
        mask=target / "labels/mask.png",
        aligned_labels=True,
    )
    path = write_plan(plan, tmp_path / "import.json")
    prepared = build_import(path, tmp_path / "prepared")
    import zarr

    array = zarr.open(str(prepared / "surface_volume.zarr"), mode="r")
    assert array.shape == (2, 6, 8) and array.dtype == np.dtype("<u2")
    np.testing.assert_array_equal(
        array[0],
        np.asarray(Image.open(io.BytesIO(source.payloads["surface_volume/16.tif"]))),
    )
    assert array.attrs["source_origin_zyx"] == [16, 0, 0]


def test_palette_conversion_uses_rgb_colors_even_when_indices_are_reversed():
    indices = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    raw = _image(indices, palette=[255, 255, 255, 0, 0, 0])
    encoded, shape = example.canonical_binary_png(raw, "labels.png")
    assert shape == (2, 2)
    np.testing.assert_array_equal(
        np.asarray(Image.open(io.BytesIO(encoded))), (1 - indices) * 255
    )


@pytest.mark.parametrize(
    "bad", ["gray_palette", "transparency", "soft_gray", "rgb", "orientation"]
)
def test_ambiguous_labels_are_not_reinterpreted(bad):
    values = np.array([[0, 1]], dtype=np.uint8)
    options = {"palette": [0, 0, 0, 255, 255, 255]}
    if bad == "gray_palette":
        options["palette"] = [0, 0, 0, 128, 128, 128]
    elif bad == "transparency":
        options["transparency"] = 0
    elif bad == "soft_gray":
        options = {}
        values[:] = 128
    elif bad == "rgb":
        options = {}
        values = np.zeros((1, 2, 3), np.uint8)
    else:
        options["orientation"] = 3
    with pytest.raises(ValueError):
        example.canonical_binary_png(_image(values, **options), "labels.png")


@pytest.mark.parametrize(
    "bad",
    ["truncated", "long", "hash", "header_length", "redirect", "status", "network"],
)
def test_bad_responses_never_publish_a_partial_directory(source, bad):
    expected = source.payloads["inklabels.png"]
    if bad == "truncated":
        source.behavior.update(payload=expected[:-1], length=str(len(expected)))
    elif bad == "long":
        source.behavior.update(payload=expected + b"x", length=str(len(expected)))
    elif bad == "hash":
        source.behavior["payload"] = expected[:-1] + b"x"
    elif bad == "header_length":
        source.behavior["length"] = "1"
    elif bad == "redirect":
        source.behavior["url"] = "https://different.invalid/image.png"
    elif bad == "status":
        source.behavior["status"] = 206
    else:
        source.behavior["error"] = urllib.error.URLError("synthetic network failure")
    with pytest.raises((ValueError, urllib.error.URLError)):
        example.fetch_example(source.manifest, source.output)
    assert not source.output.exists()
    assert not list(source.output.parent.glob(".download-*"))


@pytest.mark.parametrize(
    "options",
    [{"max_download_bytes": 1}, {"max_file_bytes": 1}, {"max_download_bytes": 0}],
)
def test_resource_limits_refuse_before_network_or_output(source, options):
    with pytest.raises(ValueError):
        example.fetch_example(source.manifest, source.output, **options)
    assert not source.calls and not source.output.exists()


@pytest.mark.parametrize(
    "bad",
    [
        "filename",
        "duplicate",
        "host",
        "fragment_id",
        "shape",
        "scale",
        "span",
        "missing",
        "digest",
        "bool_bytes",
    ],
)
def test_bad_source_manifests_refuse_before_network(source, bad):
    plan = source.plan
    if bad == "filename":
        plan["files"][0]["relative_path"] = "../inklabels.png"
    elif bad == "duplicate":
        plan["files"][1] = plan["files"][0]
    elif bad == "host":
        plan["base_url"] = plan["base_url"].replace("dl.ash2txt.org", "evil.invalid")
    elif bad == "fragment_id":
        plan["fragment_id"] = "Other"
    elif bad == "shape":
        plan["shape_zyx"] = [2, 100000, 100000]
    elif bad == "scale":
        plan["voxel_size_um"] = float("inf")
    elif bad == "span":
        plan["source_z_range"] = [18, 16]
    elif bad == "missing":
        plan["files"].pop()
    elif bad == "digest":
        plan["files"][0]["sha256"] = "0"
    else:
        plan["files"][0]["bytes"] = True
    source.manifest.write_text(json.dumps(plan))
    with pytest.raises(ValueError):
        example.fetch_example(source.manifest, source.output)
    assert not source.calls and not source.output.exists()


@pytest.mark.parametrize("bad", ["metadata", "png_grid", "tiff_type"])
def test_matching_hashes_do_not_bypass_decoded_contracts(source, bad):
    if bad == "metadata":
        name = "surface_volume/meta.json"
        raw = b'{"height":7,"width":8,"slices":65,"voxelsize":3.24}'
    elif bad == "png_grid":
        name = "mask.png"
        raw = _image(np.ones((2, 2), np.uint8) * 255)
    else:
        name = "surface_volume/16.tif"
        raw = _image(np.ones((6, 8), np.uint8), fmt="TIFF")
    source.payloads[name] = raw
    record = next(r for r in source.plan["files"] if r["relative_path"] == name)
    record.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    source.manifest.write_text(json.dumps(source.plan))
    with pytest.raises(ValueError):
        example.fetch_example(source.manifest, source.output)
    assert not source.output.exists()


def test_new_directory_only_and_cli_failure(source, capsys):
    source.output.mkdir()
    sentinel = source.output / "keep"
    sentinel.write_text("existing")
    assert (
        cli.main(["--manifest", str(source.manifest), "--output", str(source.output)])
        == 2
    )
    assert "fragment example fetch:" in capsys.readouterr().err
    assert not source.calls and sentinel.read_text() == "existing"


def test_local_readback_corruption_refuses_publication(source, monkeypatch):
    original = example._download

    def corrupt(url, path, expected):
        record = original(url, path, expected)
        if expected["relative_path"] == "inklabels.png":
            path.write_bytes(path.read_bytes() + b"changed after download")
        return record

    monkeypatch.setattr(example, "_download", corrupt)
    with pytest.raises(ValueError, match="captured download no longer matches"):
        example.fetch_example(source.manifest, source.output)
    assert not source.output.exists()


def test_help_without_scientific_imports(tmp_path):
    result = subprocess.run(
        [sys.executable, "-S", str(Path(cli.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0 and "pinned official" in result.stdout


def test_bundled_source_manifest_passes_default_preflight_without_network():
    path = cli.ROOT / "configs/data/fr47_two_layers.json"
    plan = example._manifest(
        path.read_bytes(), example.DEFAULT_DOWNLOAD_BYTES, example.DEFAULT_FILE_BYTES
    )
    assert plan["fragment_id"] == "PHercParis2Fr47"
    assert plan["source_z_range"] == [16, 18]
