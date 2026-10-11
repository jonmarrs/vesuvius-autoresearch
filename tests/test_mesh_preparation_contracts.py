"""Mesh preparation must preserve sampled geometry and publish complete artifacts."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import tifffile

from scripts import automate_arap_flattening as flattening, subsample_mesh as sampling

REPO = Path(__file__).resolve().parents[1]


def surface(tmp_path, shape=(7, 10), *, mask=False):
    src = tmp_path / "source"
    src.mkdir()
    y, x = np.indices(shape, dtype=np.float32)
    planes = {"x": x + 10, "y": y + 20, "z": x + y + 30}
    for name, values in planes.items():
        tifffile.imwrite(src / f"{name}.tif", values, photometric="minisblack")
    metadata = {
        "type": "seg",
        "format": "tifxyz",
        "uuid": "original-segment",
        "scale": [0.5, 0.25],
        "tiff_dimensions": [shape[1], shape[0]],
        "bbox": [[0, 0, 0], [999, 999, 999]],
        "area": 123456,
        "description": "synthetic test surface",
    }
    (src / "meta.json").write_text(json.dumps(metadata))
    if mask:
        values = np.full(shape, 255, np.uint8)
        values[0, 0] = 0
        tifffile.imwrite(src / "mask.tif", values)
    return src, planes, metadata


@pytest.mark.parametrize("stride", [-1, 0, True, 1.5, 100])
def test_invalid_stride_creates_no_output(tmp_path, stride):
    src, _, _ = surface(tmp_path)
    dst = tmp_path / "coarse"
    with pytest.raises(ValueError):
        sampling.subsample(src, dst, stride)
    assert not dst.exists()


def test_mask_is_preserved_without_restoring_excluded_geometry(tmp_path):
    src, planes, _ = surface(tmp_path, mask=True)
    dst = tmp_path / "coarse"
    sampling.subsample(src, dst, 3)
    mask = tifffile.imread(dst / "mask.tif")
    np.testing.assert_array_equal(mask, tifffile.imread(src / "mask.tif")[::3, ::3])
    for name, values in planes.items():
        actual = tifffile.imread(dst / f"{name}.tif")
        assert actual[0, 0] == -1
        np.testing.assert_array_equal(actual[mask > 0], values[::3, ::3][mask > 0])
        np.testing.assert_array_equal(tifffile.imread(src / f"{name}.tif"), values)


def test_derived_metadata_has_actual_dimensions_and_a_separate_identity(tmp_path):
    src, _, old = surface(tmp_path)
    dst = tmp_path / "coarse"
    sampling.subsample(src, dst, 3)
    meta = json.loads((dst / "meta.json").read_text())
    assert meta["uuid"] != old["uuid"]
    assert meta["tiff_dimensions"] == [4, 3]
    assert meta["bbox"] == [[10, 20, 30], [19, 26, 45]]
    assert "area" not in meta
    np.testing.assert_array_equal(meta["scale"], [0.5 / 3, 0.25 / 3])
    assert meta["subsampled_from"]["src"] == str(src.resolve())


@pytest.mark.parametrize("bad", ["missing", "shape", "nan", "metadata", "scale"])
def test_invalid_source_leaves_no_partial_mesh(tmp_path, bad):
    src, planes, meta = surface(tmp_path)
    if bad == "missing":
        (src / "z.tif").unlink()
    elif bad == "shape":
        tifffile.imwrite(src / "z.tif", planes["z"][:-1])
    elif bad == "nan":
        planes["y"][1, 1] = np.nan  # Validate points that would be discarded too.
        tifffile.imwrite(src / "y.tif", planes["y"])
    elif bad == "metadata":
        (src / "meta.json").write_text("{")
    else:
        meta["scale"] = [0, 1]
        (src / "meta.json").write_text(json.dumps(meta))
    dst = tmp_path / "coarse"
    with pytest.raises((OSError, ValueError)):
        sampling.subsample(src, dst, 3)
    assert not dst.exists()
    assert not list(tmp_path.glob(".coarse-*"))


def test_output_cannot_be_created_inside_source(tmp_path):
    src, _, _ = surface(tmp_path)
    with pytest.raises(ValueError):
        sampling.subsample(src, src / "coarse", 2)
    assert not (src / "coarse").exists()


def test_unsupported_flatten_selector_cannot_publish_a_temporary_winner(
    tmp_path, monkeypatch, capsys
):
    # The previous selector treated nonempty files as candidates, then deleted
    # their temporary directory before writing a "winner" referring to it.
    repo = tmp_path / "checkout"
    binary = repo / "villa/volume-cartographer/build/bin/vc_flatten"
    binary.parent.mkdir(parents=True)
    binary.touch()
    script = repo / "scripts/automate_arap_flattening.py"
    script.parent.mkdir()
    monkeypatch.setattr(flattening, "__file__", str(script))
    input_path, output = tmp_path / "input.obj", tmp_path / "results"
    input_path.write_text("this is not a mesh\n")
    monkeypatch.setattr(
        sys, "argv", [str(script), "--input", str(input_path), "--output", str(output)]
    )
    invoked = []

    def fake_producer(cmd, **kwargs):
        invoked.append(cmd)
        if "--output" in cmd:
            Path(cmd[cmd.index("--output") + 1]).write_text("not a mesh either\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_producer)
    assert flattening.main() == 1
    assert not invoked
    assert not output.exists()
    assert "unsupported" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("stride", [1, 2, 3])
def test_valid_samples_and_xy_scale_preserve_the_index_frame(tmp_path, stride):
    src, planes, old = surface(tmp_path)
    dst = tmp_path / "coarse"
    record = sampling.subsample(str(src), str(dst), np.int64(stride))
    for name, values in planes.items():
        np.testing.assert_array_equal(
            tifffile.imread(dst / f"{name}.tif"), values[::stride, ::stride]
        )
    shape = tifffile.imread(dst / "x.tif").shape
    for size, old_scale, new_scale in zip(
        shape[::-1], old["scale"], record["scale"], strict=True
    ):
        np.testing.assert_allclose(
            np.arange(size) / new_scale, np.arange(size) * stride / old_scale
        )
    assert shape == tuple((n + stride - 1) // stride for n in planes["x"].shape)
    assert record == json.loads((dst / "meta.json").read_text())
    assert record["subsampled_from"]["source_metadata"] == old
    for name, fingerprint in record["subsampled_from"]["files"].items():
        data = (src / name).read_bytes()
        assert fingerprint == {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    np.testing.assert_array_equal(
        tifffile.imread(dst / "mask.tif"), np.full(shape, 255, np.uint8)
    )


@pytest.mark.parametrize("explicit_mask", [True, False])
def test_invalid_sentinels_remain_invalid(tmp_path, explicit_mask):
    src, planes, _ = surface(tmp_path, mask=explicit_mask)
    for name, values in planes.items():
        values[3, 3] = -1
        tifffile.imwrite(src / f"{name}.tif", values)
    dst = tmp_path / "coarse"
    sampling.subsample(src, dst, 3)
    mask = tifffile.imread(dst / "mask.tif")
    assert mask[1, 1] == 0
    for name in "xyz":
        assert tifffile.imread(dst / f"{name}.tif")[1, 1] == -1


@pytest.mark.parametrize("explicit_mask", [True, False])
def test_z_zero_uses_explicit_mask_or_upstream_fallback(tmp_path, explicit_mask):
    src, planes, _ = surface(tmp_path, mask=explicit_mask)
    planes["z"][3, 3] = 0
    tifffile.imwrite(src / "z.tif", planes["z"])
    dst = tmp_path / "coarse"
    sampling.subsample(src, dst, 3)
    assert tifffile.imread(dst / "mask.tif")[1, 1] == (255 if explicit_mask else 0)
    assert tifffile.imread(dst / "z.tif")[1, 1] == (0 if explicit_mask else -1)


@pytest.mark.parametrize(
    "bad",
    [
        "integer",
        "float64",
        "complex",
        "stack",
        "thin",
        "negative",
        "partial_sentinel",
        "invalid",
        "discarded_valid",
    ],
)
def test_bad_coordinate_layout_or_values_are_refused(tmp_path, bad):
    src, planes, _ = surface(tmp_path)
    if bad in {"integer", "float64", "complex"}:
        planes["x"] = planes["x"].astype(
            {"integer": np.int32, "float64": np.float64, "complex": np.complex64}[bad]
        )
    elif bad == "stack":
        planes["x"] = planes["x"][None]
    elif bad == "thin":
        planes["x"] = planes["x"][:1]
    elif bad == "negative":
        planes["x"][0, 0] = -2
    elif bad == "partial_sentinel":
        planes["x"][0, 0] = -1
    else:
        for values in planes.values():
            values[:] = -1
            if bad == "discarded_valid":
                values[1, 1] = 30
    for name, values in planes.items():
        tifffile.imwrite(src / f"{name}.tif", values, photometric="minisblack")
    with pytest.raises(ValueError):
        sampling.subsample(src, tmp_path / "coarse", 3)
    assert not (tmp_path / "coarse").exists()


@pytest.mark.parametrize("bad", ["shape", "float", "nonbinary", "zero", "stack"])
def test_invalid_masks_publish_nothing(tmp_path, bad):
    src, _, _ = surface(tmp_path)
    mask = np.ones((7, 10), np.uint8)
    if bad == "shape":
        mask = mask[:-1]
    elif bad == "float":
        mask = mask.astype(np.float32)
    elif bad == "nonbinary":
        mask[1, 1] = 5
    elif bad == "zero":
        mask[:] = 0
    else:
        mask = np.stack([mask, mask])
    tifffile.imwrite(src / "mask.tif", mask, photometric="minisblack")
    with pytest.raises(ValueError):
        sampling.subsample(src, tmp_path / "coarse", 3)
    assert not (tmp_path / "coarse").exists()


@pytest.mark.parametrize("mask_dtype", [bool, np.uint8])
def test_binary_masks_are_canonicalized(tmp_path, mask_dtype):
    src, _, _ = surface(tmp_path)
    mask = np.ones((7, 10), dtype=mask_dtype)
    mask[0, 0] = 0
    tifffile.imwrite(src / "mask.tif", mask)
    dst = tmp_path / "coarse"
    sampling.subsample(src, dst, 3)
    np.testing.assert_array_equal(
        tifffile.imread(dst / "mask.tif"), mask[::3, ::3].astype(np.uint8) * 255
    )


@pytest.mark.parametrize(
    "scale",
    [
        None,
        [1],
        [1, 1, 1],
        [True, 1],
        ["1", 1],
        [-1, 1],
        [float("inf"), 1],
        [1e-100, 1],
        [1e100, 1],
    ],
)
def test_invalid_scale_is_refused(tmp_path, scale):
    src, _, meta = surface(tmp_path)
    meta["scale"] = scale
    (src / "meta.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        sampling.subsample(src, tmp_path / "coarse", 3)
    assert not (tmp_path / "coarse").exists()


@pytest.mark.parametrize(
    "metadata",
    [
        "[]",
        '{"scale":[1,1],"scale":[2,2]}',
        '{"scale":[1,1],"area":NaN}',
        '{"scale":[1,1],"format":"obj"}',
    ],
)
def test_malformed_metadata_is_refused(tmp_path, metadata):
    src, _, _ = surface(tmp_path)
    (src / "meta.json").write_text(metadata)
    with pytest.raises(ValueError):
        sampling.subsample(src, tmp_path / "coarse", 3)
    assert not (tmp_path / "coarse").exists()


@pytest.mark.parametrize(
    "budget",
    [
        {"max_points": 69},
        {"max_decoded_bytes": 839},
        {"max_points": True},
        {"max_decoded_bytes": 0},
    ],
)
def test_resource_limits_are_enforced_before_payload_reads(
    tmp_path, monkeypatch, budget
):
    src, _, _ = surface(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("invalid limits reached payload decoding")

    monkeypatch.setattr(sampling.tifffile, "imread", forbidden)
    with pytest.raises(ValueError):
        sampling.subsample(src, tmp_path / "coarse", 3, **budget)
    assert not (tmp_path / "coarse").exists()


@pytest.mark.parametrize(
    "where", ["existing", "file", "broken_link", "source_alias", "ancestor"]
)
def test_output_paths_preserve_existing_artifacts(tmp_path, where):
    src, _, _ = surface(tmp_path)
    dst = tmp_path / "coarse"
    if where == "existing":
        dst.mkdir()
        (dst / "old").write_text("prior result")
    elif where == "file":
        dst.write_text("prior result")
    elif where == "broken_link":
        dst.symlink_to(tmp_path / "missing")
    elif where == "source_alias":
        dst.symlink_to(src, target_is_directory=True)
    else:
        dst = tmp_path
    with pytest.raises(ValueError):
        sampling.subsample(src, dst, 3)
    if where == "existing":
        assert (dst / "old").read_text() == "prior result"
    elif where == "file":
        assert dst.read_text() == "prior result"
    elif where in {"broken_link", "source_alias"}:
        assert dst.is_symlink()
    assert (src / "meta.json").exists()


@pytest.mark.parametrize("failure", ["write", "serialize", "rename"])
def test_processing_failures_leave_no_partial_mesh(tmp_path, monkeypatch, failure):
    src, _, _ = surface(tmp_path)
    dst = tmp_path / "coarse"
    if failure == "write":
        original = tifffile.imwrite

        def bad_write(path, *args, **kwargs):
            original(path, *args, **kwargs)
            if Path(path).name == "y.tif":
                raise OSError("simulated disk failure")

        monkeypatch.setattr(tifffile, "imwrite", bad_write)
    elif failure == "serialize":
        original = json.dumps

        def bad_serialize(data, *args, **kwargs):
            if "subsampled_from" in data:
                raise ValueError("simulated serialization failure")
            return original(data, *args, **kwargs)

        monkeypatch.setattr(json, "dumps", bad_serialize)
    else:

        def bad_rename(*args, **kwargs):
            raise OSError("simulated rename failure")

        monkeypatch.setattr(Path, "rename", bad_rename)
    with pytest.raises((OSError, ValueError)):
        sampling.subsample(src, dst, 3)
    assert not dst.exists()
    assert not list(tmp_path.glob(".coarse-*"))


def test_access_time_change_is_not_a_source_mutation(tmp_path):
    src, _, _ = surface(tmp_path)
    for path in src.iterdir():
        os.utime(path, ns=(1, path.stat().st_mtime_ns))
    sampling.subsample(src, tmp_path / "coarse", 3)
    assert (tmp_path / "coarse/meta.json").is_file()


def test_source_mutation_is_refused(tmp_path, monkeypatch):
    src, _, _ = surface(tmp_path)
    original = sampling.source_fingerprint

    def changed(path):
        record = original(path)
        if path.name == "z.tif":
            with path.open("ab") as stream:
                stream.write(b"changed")
        return record

    monkeypatch.setattr(sampling, "source_fingerprint", changed)
    with pytest.raises(ValueError, match="changed"):
        sampling.subsample(src, tmp_path / "coarse", 3)
    assert not (tmp_path / "coarse").exists()


def test_copied_script_works_outside_the_checkout(tmp_path):
    src, planes, _ = surface(tmp_path)
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    script = frozen / "subsample_mesh.py"
    shutil.copyfile(REPO / "scripts/subsample_mesh.py", script)
    result = subprocess.run(
        [sys.executable, str(script), "../source", "../coarse", "3"],
        cwd=frozen,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    np.testing.assert_array_equal(
        tifffile.imread(tmp_path / "coarse/x.tif"), planes["x"][::3, ::3]
    )


@pytest.mark.parametrize("script", ["subsample_mesh.py", "automate_arap_flattening.py"])
def test_cli_failure_and_help_do_not_publish_artifacts(tmp_path, script):
    path = REPO / "scripts" / script
    if script == "subsample_mesh.py":
        args = [str(tmp_path / "missing"), str(tmp_path / "coarse"), "3"]
    else:
        args = [
            "--input",
            str(tmp_path / "missing"),
            "--output",
            str(tmp_path / "coarse"),
        ]
    result = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stderr and "published" not in result.stdout.lower()
    assert not (tmp_path / "coarse").exists()
    help_result = subprocess.run(
        [sys.executable, str(path), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0


def test_pinned_reader_consumes_sampled_coordinates_mask_and_xy_scale(tmp_path):
    from scripts.labeling.tifxyz_wrapper import (
        extract_patch_coords,
        load_tifxyz_surface,
    )

    src, planes, _ = surface(tmp_path, mask=True)
    dst = tmp_path / "coarse"
    record = sampling.subsample(src, dst, 3)
    loaded = load_tifxyz_surface(str(dst), resolution="stored")
    assert loaded.shape == (3, 4)
    np.testing.assert_allclose(loaded._scale, record["scale"][::-1])
    cx, cy, cz, valid = extract_patch_coords(loaded, y=0, x=0, h=3, w=4)
    assert not valid[0, 0] and valid.sum() == 11
    for actual, name in zip([cx, cy, cz], "xyz", strict=True):
        np.testing.assert_array_equal(actual[valid], planes[name][::3, ::3][valid])
        assert actual[0, 0] == -1


@pytest.mark.parametrize("component", ["meta.json", "x.tif", "mask.tif"])
def test_component_symlinks_are_refused_without_reading_the_target(tmp_path, component):
    src, _, _ = surface(tmp_path)
    original = src / component
    if original.exists():
        original.unlink()
    original.symlink_to(tmp_path / "absent-target")
    with pytest.raises(ValueError, match="nonsymlink"):
        sampling.subsample(src, tmp_path / "coarse", 3)
    assert original.is_symlink()
    assert not (tmp_path / "coarse").exists()


def test_metadata_budget_applies_before_parsing(tmp_path, monkeypatch):
    src, _, _ = surface(tmp_path)
    (src / "meta.json").write_bytes(b" " * (sampling.MAX_METADATA_BYTES + 1))

    def forbidden(*args, **kwargs):
        pytest.fail("oversized metadata reached JSON parsing")

    monkeypatch.setattr(sampling.json, "loads", forbidden)
    with pytest.raises(ValueError, match="limit"):
        sampling.subsample(src, tmp_path / "coarse", 3)
    assert not (tmp_path / "coarse").exists()


def test_late_output_is_preserved(tmp_path, monkeypatch):
    src, _, _ = surface(tmp_path)
    dst = tmp_path / "coarse"
    original = tifffile.imwrite

    def competing_writer(path, *args, **kwargs):
        original(path, *args, **kwargs)
        if Path(path).name == "mask.tif":
            dst.mkdir()
            (dst / "prior").write_text("another completed artifact")

    monkeypatch.setattr(tifffile, "imwrite", competing_writer)
    with pytest.raises(ValueError, match="appeared"):
        sampling.subsample(src, dst, 3)
    assert list(dst.iterdir()) == [dst / "prior"]
    assert (dst / "prior").read_text() == "another completed artifact"
    assert not list(tmp_path.glob(".coarse-*"))


def test_bad_tiff_is_an_explicit_cli_failure(tmp_path):
    src, _, _ = surface(tmp_path)
    (src / "z.tif").write_bytes(b"not a TIFF")
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/subsample_mesh.py"),
            str(src),
            str(tmp_path / "coarse"),
            "3",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Mesh subsampling failed" in result.stderr
    assert not (tmp_path / "coarse").exists()


def test_derivative_does_not_advertise_untransferred_channels(tmp_path):
    src, _, meta = surface(tmp_path)
    (src / "labels.png").write_bytes(b"auxiliary label content")
    meta["channels"] = {"ink": "labels.png"}
    (src / "meta.json").write_text(json.dumps(meta))
    dst = tmp_path / "coarse"
    record = sampling.subsample(src, dst, 3)
    assert "channels" not in record
    assert record["subsampled_from"]["source_metadata"]["channels"] == meta["channels"]
    assert {p.name for p in dst.iterdir()} == {
        "meta.json",
        "x.tif",
        "y.tif",
        "z.tif",
        "mask.tif",
    }
    assert (src / "labels.png").read_bytes() == b"auxiliary label content"
