"""Failure and integrity checks for the CPU-only detector preparation boundary."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from vesuvius_autoresearch.core import fragment_conversion as conversion

REPO = Path(__file__).resolve().parents[1]


def source(tmp_path, *, dtype=np.uint16, shape=(5, 7)):
    root = tmp_path / "src" / "fragment"
    (root / "surface_volume").mkdir(parents=True)
    for index in range(2):
        Image.fromarray(np.full(shape, 200, dtype)).save(
            root / "surface_volume" / f"{index:02d}.tif"
        )
    for name in ("inklabels.png", "mask.png"):
        Image.fromarray(np.full(shape, 255, np.uint8)).save(root / name)
    return root


def run_conversion(tmp_path, **kwargs):
    return conversion.convert_fragment(
        "fragment", tmp_path / "src", tmp_path / "dst", 0, 2, **kwargs
    )


def tree(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def status(tmp_path):
    return conversion.conversion_status(tmp_path / "dst", "fragment", 0, 2)


def test_completion_binds_exact_input_and_output_bytes(tmp_path):
    source(tmp_path)
    stats = run_conversion(tmp_path)
    root = tmp_path / "dst" / "fragment"
    manifest = json.loads((root / conversion.MANIFEST).read_text())
    assert manifest["z_range"] == [0, 2] and manifest["shape_yx"] == [5, 7]
    assert stats["0"]["u8_max"] == 0  # preserve the declared global high-byte scale
    for record in manifest["sources"]:
        data = Path(record["path"]).read_bytes()
        assert record["sha256"] == hashlib.sha256(data).hexdigest()
        assert record["bytes"] == len(data)
    for path, record in manifest["outputs"].items():
        data = (root / path).read_bytes()
        assert record == {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    assert status(tmp_path) == (True, "verified output hashes")


@pytest.mark.parametrize("dtype", [np.uint8, np.int16, np.float32])
def test_wrong_source_dtype_never_publishes_black_or_wrapped_layers(tmp_path, dtype):
    source(tmp_path, dtype=dtype)
    with pytest.raises(ValueError, match="uint16"):
        run_conversion(tmp_path)
    assert not (tmp_path / "dst" / "fragment").exists()


@pytest.mark.parametrize(
    "array",
    [
        np.ones((2, 3), np.uint8),
        np.ones((2, 3), np.float32),
        np.ones((2, 3, 1), np.uint16),
    ],
)
def test_array_conversion_rejects_ambiguous_input(array):
    with pytest.raises(ValueError, match="2D uint16"):
        conversion.convert_layer_u16_to_u8(array)


def test_big_endian_uint16_uses_same_high_byte_scale():
    array = np.array([[0, 255, 256, 65535]], dtype=">u2")
    assert conversion.convert_layer_u16_to_u8(array).tolist() == [[0, 0, 1, 255]]


@pytest.mark.parametrize("file", ["surface_volume/01.tif", "inklabels.png", "mask.png"])
def test_late_source_failure_keeps_previous_generation_byte_identical(tmp_path, file):
    src = source(tmp_path)
    run_conversion(tmp_path)
    output = tmp_path / "dst" / "fragment"
    before = tree(output)
    Image.fromarray(np.full((5, 7), 65535, np.uint16)).save(
        src / "surface_volume/00.tif"
    )
    (src / file).unlink()
    with pytest.raises(FileNotFoundError):
        run_conversion(tmp_path)
    assert tree(output) == before
    assert status(tmp_path)[0]
    assert list((tmp_path / "dst").iterdir()) == [output]


@pytest.mark.parametrize("file", ["surface_volume/01.tif", "inklabels.png", "mask.png"])
def test_every_image_must_have_same_geometry(tmp_path, file):
    src = source(tmp_path)
    dtype = np.uint16 if file.endswith(".tif") else np.uint8
    Image.fromarray(np.zeros((6, 7), dtype)).save(src / file)
    with pytest.raises(ValueError, match="shape mismatch"):
        run_conversion(tmp_path)
    assert not (tmp_path / "dst" / "fragment").exists()


@pytest.mark.parametrize("kind", ["rgb", "stack", "oversize"])
def test_non_scalar_or_over_budget_sources_fail_before_decode(tmp_path, kind):
    src = source(tmp_path)
    path = src / "surface_volume/00.tif"
    if kind == "rgb":
        Image.fromarray(np.zeros((5, 7, 3), np.uint8)).save(path)
    elif kind == "stack":
        image = Image.fromarray(np.zeros((5, 7), np.uint16))
        image.save(path, save_all=True, append_images=[image])
    with pytest.raises(ValueError, match="pixel budget"):
        run_conversion(tmp_path, **({"max_pixels": 34} if kind == "oversize" else {}))


@pytest.mark.parametrize("start,end", [(2, 2), (-1, 2), (0, 513), (True, 2), (0.5, 2)])
def test_invalid_ranges_do_not_create_directories(tmp_path, start, end):
    with pytest.raises(ValueError, match="z_start"):
        conversion.convert_fragment(
            "fragment", tmp_path / "src", tmp_path / "dst", start, end
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "name", ["..", ".", "", "../escape", "/absolute", "nested/name", "nested\\name"]
)
def test_fragment_ids_cannot_escape_roots(tmp_path, name):
    with pytest.raises(ValueError, match="single directory"):
        conversion.convert_fragment(name, tmp_path / "src", tmp_path / "dst", 0, 2)
    assert list(tmp_path.iterdir()) == []


def test_source_destination_alias_is_rejected_before_writes(tmp_path):
    src = source(tmp_path)
    before = tree(src)
    with pytest.raises(ValueError, match="overlap"):
        conversion.convert_fragment(
            "fragment", tmp_path / "src", tmp_path / "src", 0, 2
        )
    assert tree(src) == before


def test_output_symlink_is_rejected(tmp_path):
    src = source(tmp_path)
    (tmp_path / "dst").mkdir()
    (tmp_path / "dst/fragment").symlink_to(src, target_is_directory=True)
    with pytest.raises(ValueError, match="overlap|nonsymlink"):
        run_conversion(tmp_path)


@pytest.mark.parametrize("replace_succeeds", [False, True])
def test_publication_rollback_or_success_is_one_complete_generation(
    tmp_path, monkeypatch, replace_succeeds
):
    src = source(tmp_path)
    run_conversion(tmp_path)
    output = tmp_path / "dst/fragment"
    before = tree(output)
    Image.fromarray(np.full((5, 7), 65535, np.uint16)).save(
        src / "surface_volume/00.tif"
    )
    real = Path.rename

    def rename(path, target):
        if path.name == "new" and not replace_succeeds:
            raise OSError("injected publish error")
        return real(path, target)

    monkeypatch.setattr(Path, "rename", rename)
    if replace_succeeds:
        run_conversion(tmp_path)
        assert tree(output) != before
    else:
        with pytest.raises(OSError, match="injected publish"):
            run_conversion(tmp_path)
        assert tree(output) == before
    assert status(tmp_path)[0]
    assert list((tmp_path / "dst").iterdir()) == [output]


def test_rollback_failure_retains_recoverable_previous_generation(
    tmp_path, monkeypatch
):
    source(tmp_path)
    run_conversion(tmp_path)
    before = tree(tmp_path / "dst/fragment")
    real = Path.rename

    def rename(path, target):
        if path.name in {"new", "previous"}:
            raise OSError("injected rename error")
        return real(path, target)

    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(RuntimeError, match="recover previous"):
        run_conversion(tmp_path)
    retained = list((tmp_path / "dst").glob(".fragment-*/previous"))
    assert len(retained) == 1 and tree(retained[0]) == before


@pytest.mark.parametrize("target", ["source", "staged", "manifest"])
def test_changed_input_or_staged_output_blocks_publication(
    tmp_path, monkeypatch, target
):
    src = source(tmp_path)
    run_conversion(tmp_path)
    output = tmp_path / "dst/fragment"
    before = tree(output)
    real = conversion._verify_sources

    def verify(records, limit):
        if target == "source":
            (src / "mask.png").write_bytes(b"changed")
        else:
            workspace = next((tmp_path / "dst").glob(".fragment-*"))
            path = "layers/00.tif" if target == "staged" else conversion.MANIFEST
            (workspace / "new" / path).write_bytes(b"changed")
        return real(records, limit)

    monkeypatch.setattr(conversion, "_verify_sources", verify)
    with pytest.raises(ValueError, match="changed"):
        run_conversion(tmp_path)
    assert tree(output) == before


@pytest.mark.parametrize("target", ["layer", "label", "mask", "manifest"])
def test_existing_but_corrupt_outputs_are_not_reusable(tmp_path, target):
    source(tmp_path)
    run_conversion(tmp_path)
    path = {
        "layer": "layers/00.tif",
        "label": "fragment_inklabels.png",
        "mask": "fragment_mask.png",
        "manifest": conversion.MANIFEST,
    }[target]
    (tmp_path / "dst/fragment" / path).write_bytes(b"corrupt")
    assert not status(tmp_path)[0]


def test_changed_valid_image_is_detected_by_manifest_and_legacy_is_explicit(tmp_path):
    source(tmp_path)
    run_conversion(tmp_path)
    output = tmp_path / "dst/fragment"
    Image.fromarray(np.full((5, 7), 7, np.uint8)).save(output / "layers/00.tif")
    assert not status(tmp_path)[0]
    (output / conversion.MANIFEST).unlink()
    assert status(tmp_path) == (True, "legacy image checks; no source provenance")


def test_existing_fragment_permissions_are_preserved(tmp_path):
    source(tmp_path)
    run_conversion(tmp_path)
    output = tmp_path / "dst/fragment"
    output.chmod(0o700)
    (output / "layers").chmod(0o700)
    (output / "layers/00.tif").chmod(0o600)
    (output / conversion.MANIFEST).chmod(0o640)
    run_conversion(tmp_path)
    assert output.stat().st_mode & 0o777 == 0o700
    assert (output / "layers").stat().st_mode & 0o777 == 0o700
    assert (output / "layers/00.tif").stat().st_mode & 0o777 == 0o600
    assert (output / conversion.MANIFEST).stat().st_mode & 0o777 == 0o640


@pytest.mark.parametrize(
    "extra", ["annotations.nml", "layers/notes.txt", "custom_inklabels.tiff"]
)
def test_repairs_do_not_delete_unmanaged_user_files(tmp_path, extra):
    source(tmp_path)
    run_conversion(tmp_path)
    output = tmp_path / "dst/fragment"
    (output / extra).write_bytes(b"user work")
    before = tree(output)
    with pytest.raises(ValueError, match="unmanaged"):
        run_conversion(tmp_path)
    assert tree(output) == before


def test_cli_check_is_no_write_no_source_read_and_no_training_import(tmp_path):
    # Import guard is in a fresh interpreter, not a fake replacement for Torch.
    code = """
import builtins, runpy, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'pytorch_lightning', 'wandb'} or '.detector' in name:
        raise RuntimeError('training import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
sys.argv = [sys.argv[1], '--frag', 'fragment', '--z-start', '0', '--z-end', '2', '--src-root', '/no-such-source', '--dst-root', sys.argv[2], '--check']
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    command = [
        sys.executable,
        "-c",
        code,
        str(REPO / "repro/gp_winner/convert_fragment.py"),
        str(tmp_path / "dst"),
    ]
    result = subprocess.run(
        command, cwd=tmp_path, text=True, capture_output=True, timeout=30
    )
    assert result.returncode == 2, result.stderr
    assert "NEEDS_CONVERSION" in result.stdout
    assert list(tmp_path.iterdir()) == []
    source(tmp_path)
    run_conversion(tmp_path)
    before = tree(tmp_path)
    result = subprocess.run(
        command, cwd=tmp_path, text=True, capture_output=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert "verified output hashes" in result.stdout
    assert tree(tmp_path) == before
