"""Pinned source identity, lossless CT layout and failure-safe publication."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import zarr
from PIL import Image

from vesuvius_autoresearch.core import surface_volume_import as importer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def source(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir()
    values = np.arange(80, dtype=np.uint16).reshape(8, 10) * 700
    values[0, 0], values[-1, -1] = 0, 65535
    for index in range(16, 19):
        Image.fromarray(values + np.uint16(index - 16)).save(
            folder / f"{index:02d}.tif"
        )
    labels = (np.indices((8, 10)).sum(axis=0) % 2 * 255).astype(np.uint8)
    Image.fromarray(labels).save(folder / "inklabels.png")
    Image.fromarray(np.full((8, 10), 255, np.uint8)).save(folder / "mask.png")
    return folder


def plan(source, **kwargs):
    options = {"mask": source / "mask.png", "aligned_labels": True, **kwargs}
    return importer.plan_import(source, source / "inklabels.png", 16, 19, **options)


def pin(source, tmp_path, **kwargs):
    manifest = tmp_path / "plan.json"
    importer.write_plan(plan(source, **kwargs), manifest)
    return manifest


def tree(path):
    return {
        str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()
    }


def test_lossless_values_binary_labels_and_consumer_normalization(source, tmp_path):
    manifest = pin(source, tmp_path)
    expected = np.stack(
        [np.array(Image.open(source / f"{z:02d}.tif")) for z in range(16, 19)]
    )
    old = tree(source)
    dest = importer.build_import(manifest, tmp_path / "prepared")
    array = zarr.open(str(dest / "surface_volume.zarr"), mode="r")
    assert array.shape == (3, 8, 10) and array.dtype == np.uint16
    np.testing.assert_array_equal(array[:], expected)
    assert (dest / "inklabels.png").read_bytes() == (
        source / "inklabels.png"
    ).read_bytes()
    assert (dest / "mask.png").read_bytes() == (source / "mask.png").read_bytes()
    record = json.loads((dest / "import.json").read_text())
    assert (
        record["input_manifest_sha256"]
        == hashlib.sha256(manifest.read_bytes()).hexdigest()
    )
    assert (
        record["ct_decoded_sha256"]
        == hashlib.sha256(expected.astype("<u2").tobytes()).hexdigest()
    )
    assert array.attrs["source_origin_zyx"] == [16, 0, 0]
    from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume

    reader = FastVesuviusVolume(
        str(dest / "surface_volume.zarr"), use_ridges=False, strict_reads=True
    )
    np.testing.assert_allclose(
        reader.read_ct(0, 0, 0, 3, 8, 10), expected.astype(np.float32) / 65535
    )
    assert tree(source) == old


def test_training_dataset_accepts_prepared_ct_labels_and_mask(source, tmp_path):
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    dest = importer.build_import(pin(source, tmp_path), tmp_path / "prepared")
    dataset = VesuviusLabeledDataset(
        str(dest / "surface_volume.zarr"),
        str(dest / "inklabels.png"),
        mask_path=str(dest / "mask.png"),
        patch_size=4,
        num_layers=3,
        seed=42,
        cache_dir=str(tmp_path / "cache"),
        jitter=False,
        strict_reads=True,
    )
    ct, labels, fibers = dataset[0]
    assert ct.shape == (1, 3, 4, 4) and fibers.shape == (1, 1, 4, 4)
    assert 0 <= float(ct.min()) <= float(ct.max()) <= 1
    assert set(labels.numpy().ravel()) == {0, 1}


@pytest.mark.parametrize("target", ["16.tif", "inklabels.png", "mask.png"])
def test_changed_source_hash_is_rejected_without_publication(source, tmp_path, target):
    manifest = pin(source, tmp_path)
    path = source / target
    path.write_bytes(path.read_bytes() + b"changed source")
    old = tree(source)
    with pytest.raises(ValueError, match="pinned manifest"):
        importer.build_import(manifest, tmp_path / "out")
    assert not (tmp_path / "out").exists() and tree(source) == old
    assert not list(tmp_path.glob(".out-*"))


@pytest.mark.parametrize(
    "name,kind", [("16.tif", "u1"), ("17.tif", "i2"), ("18.tif", "f4")]
)
def test_bad_ct_dtype_is_not_cast_into_training_data(source, name, kind):
    Image.fromarray(np.ones((8, 10), kind)).save(source / name)
    with pytest.raises(ValueError, match="uint16"):
        plan(source)


@pytest.mark.parametrize(
    "role,value", [("inklabels.png", 128), ("inklabels.png", 1), ("mask.png", 7)]
)
def test_nonbinary_png_is_not_reinterpreted_as_ground_truth(source, role, value):
    Image.fromarray(np.full((8, 10), value, np.uint8)).save(source / role)
    with pytest.raises(ValueError, match="0/255"):
        plan(source)


def test_palette_png_is_not_read_as_grayscale_label_indices(source):
    Image.new("P", (10, 8)).save(source / "inklabels.png")
    with pytest.raises(ValueError, match="scalar"):
        plan(source)


def test_explicit_alignment_and_matching_shapes_are_required(source):
    with pytest.raises(ValueError, match="aligned_labels"):
        plan(source, aligned_labels=False)
    Image.fromarray(np.zeros((7, 10), np.uint16)).save(source / "17.tif")
    with pytest.raises(ValueError, match="same XY shape"):
        plan(source)


@pytest.mark.parametrize(
    "field,value",
    [("max_file_bytes", 2), ("max_pixels", 79), ("max_volume_bytes", 479)],
)
def test_planning_resource_limits_fail_without_writes(source, tmp_path, field, value):
    before = tree(tmp_path)
    with pytest.raises(ValueError):
        plan(source, **{field: value})
    assert tree(tmp_path) == before


def test_manifest_cannot_raise_build_resource_limits(source, tmp_path):
    manifest = pin(source, tmp_path)
    value = json.loads(manifest.read_text())
    value["limits"]["max_volume_bytes"] = 10**100
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="geometry"):
        importer.build_import(manifest, tmp_path / "out", max_volume_bytes=479)
    assert not (tmp_path / "out").exists()


def test_plan_writer_obeys_the_reader_manifest_size_limit(
    source, tmp_path, monkeypatch
):
    value = plan(source)
    monkeypatch.setattr(importer, "MANIFEST_BYTES", 100)
    with pytest.raises(ValueError, match="manifest exceeds"):
        importer.write_plan(value, tmp_path / "plan.json")
    assert not (tmp_path / "plan.json").exists()


@pytest.mark.parametrize("change", ["order", "dtype", "index", "shape", "nonfinite"])
def test_edited_manifests_fail_closed(source, tmp_path, change):
    manifest = pin(source, tmp_path)
    value = json.loads(manifest.read_text())
    if change == "order":
        value["sources"]["layers"].reverse()
    elif change == "dtype":
        value["ct_dtype"] = "uint8"
    elif change == "index":
        value["sources"]["layers"][1]["path"] = value["sources"]["layers"][0]["path"]
    elif change == "shape":
        value["shape_zyx"][1] = True
    else:
        value["limits"]["max_pixels"] = float("nan")
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        importer.build_import(manifest, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_existing_outputs_and_input_aliases_remain_unchanged(source, tmp_path):
    manifest = pin(source, tmp_path)
    for destination in [source, manifest, source / "16.tif"]:
        before = tree(tmp_path)
        with pytest.raises(ValueError):
            importer.build_import(manifest, destination)
        assert tree(tmp_path) == before
    with pytest.raises(ValueError):
        importer.write_plan(plan(source), source / "inklabels.png")


def test_write_failure_removes_staging_without_publishing(
    source, tmp_path, monkeypatch
):
    manifest = pin(source, tmp_path)
    write = zarr.Array.__setitem__

    def fail(self, key, value):
        write(self, key, value)
        raise OSError("simulated disk failure")

    monkeypatch.setattr(zarr.Array, "__setitem__", fail)
    with pytest.raises(OSError, match="disk failure"):
        importer.build_import(manifest, tmp_path / "out")
    assert not (tmp_path / "out").exists() and not list(tmp_path.glob(".out-*"))


@pytest.mark.parametrize("changed", ["manifest", "labels"])
def test_changes_after_capture_prevent_publication(
    source, tmp_path, monkeypatch, changed
):
    manifest = pin(source, tmp_path)
    write = zarr.Array.__setitem__
    target = manifest if changed == "manifest" else source / "inklabels.png"

    def mutate(self, key, value):
        write(self, key, value)
        target.write_bytes(target.read_bytes() + b" ")

    monkeypatch.setattr(zarr.Array, "__setitem__", mutate)
    with pytest.raises(ValueError, match="changed during import"):
        importer.build_import(manifest, tmp_path / "out")
    assert not (tmp_path / "out").exists() and not list(tmp_path.glob(".out-*"))


def test_big_endian_tiff_values_survive_import(source, tmp_path):
    values = np.arange(80, dtype=np.uint16).reshape(8, 10) * 811
    values[0, 0], values[-1, -1] = 0, 65535
    Image.fromarray(values.astype(">u2")).save(source / "16.tif")
    manifest = pin(source, tmp_path)
    result = importer.build_import(manifest, tmp_path / "out")
    array = zarr.open(str(result / "surface_volume.zarr"), mode="r")
    np.testing.assert_array_equal(array[0], values)


def test_cli_plan_build_and_existing_output_refusal(source, tmp_path):
    command = [sys.executable, str(ROOT / "scripts/training/prepare_surface_volume.py")]
    manifest, destination = tmp_path / "plan.json", tmp_path / "out"
    planned = subprocess.run(
        [
            *command,
            "plan",
            "--layers",
            str(source),
            "--labels",
            str(source / "inklabels.png"),
            "--z-start",
            "16",
            "--z-stop",
            "19",
            "--aligned-labels",
            "--output",
            str(manifest),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert planned.returncode == 0, planned.stderr
    assert json.loads(planned.stdout)["path"] == str(manifest)
    build = [
        *command,
        "build",
        "--manifest",
        str(manifest),
        "--output",
        str(destination),
    ]
    built = subprocess.run(
        build, cwd=tmp_path, capture_output=True, text=True, timeout=30
    )
    assert built.returncode == 0, built.stderr
    assert json.loads(built.stdout)["path"] == str(destination)
    assert zarr.open(str(destination / "surface_volume.zarr"), mode="r").shape == (
        3,
        8,
        10,
    )
    assert not (destination / "mask.png").exists()
    before = tree(destination)
    repeated = subprocess.run(
        build, cwd=tmp_path, capture_output=True, text=True, timeout=30
    )
    assert repeated.returncode == 2 and "already exists" in repeated.stderr
    assert tree(destination) == before


@pytest.mark.parametrize("module", [False, True])
def test_help_needs_no_scientific_imports(tmp_path, module):
    traps = tmp_path / "traps"
    traps.mkdir()
    for name in ["numpy", "torch", "cupy", "zarr"]:
        (traps / f"{name}.py").write_text("raise AssertionError('scientific import')\n")
    command = (
        ["-m", "scripts.training.prepare_surface_volume"]
        if module
        else [str(ROOT / "scripts/training/prepare_surface_volume.py")]
    )
    result = subprocess.run(
        [sys.executable, "-B", *command, "--help"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": os.pathsep.join([str(traps), str(ROOT)])},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0 and "scientific import" not in result.stderr
