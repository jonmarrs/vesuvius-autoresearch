"""Synthetic conversion regressions: one scale, consistent windows, stable inputs."""

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import tifffile
from PIL import Image

from repro.sota_data import conversion_artifacts as ca, fragment
from repro.sota_data.convert import convert_surface_volume, main
from repro.sota_data.depth_window import depth_window
from repro.sota_data.qualitative import region_to_layers, write_fragment


def _source(tmp_path, layers=None):
    if layers is None:
        layers = np.full((2, 4, 5), 0.5, np.float32)
        layers[1, 0, 0] = 2
    source = tmp_path / "source"
    (source / "layers").mkdir(parents=True)
    for index, plane in enumerate(layers):
        tifffile.imwrite(
            source / "layers" / f"{index}.tif", plane, photometric="minisblack"
        )
    Image.fromarray(np.full(layers.shape[1:], 255, np.uint8)).save(
        source / "s_inklabels.png"
    )
    return source


def _record(source):
    rows = []
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.name != "download.json":
            data = path.read_bytes()
            rows.append(
                {
                    "relative_path": path.relative_to(source).as_posix(),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    record = {"contract": 1, "status": "DOWNLOADED", "files": rows}
    (source / "download.json").write_text(json.dumps(record))
    return record


@pytest.mark.parametrize("writer", ["raw", "qualitative"])
@pytest.mark.parametrize(
    "mode,high,expected",
    [("auto", 2, 0), ("auto", 1, 127), ("byte", 1, 0), ("unit", 1, 127)],
)
def test_equal_float_values_use_one_scale_for_all_depths(
    tmp_path, writer, mode, high, expected
):
    layers = np.full((2, 4, 5), 0.5, np.float32)
    layers[1, 0, 0] = high
    if writer == "raw":
        source = _source(tmp_path, layers)
        out = convert_surface_volume(
            source, "s", tmp_path / "out", n_layers=2, float_encoding=mode
        )
    else:
        out = write_fragment(layers, tmp_path / "out", "s", float_encoding=mode)
    planes = [tifffile.imread(Path(out) / "layers" / f"{i}.tif") for i in (17, 18)]
    assert [int(plane[1, 1]) for plane in planes] == [expected, expected]
    manifest = json.loads((Path(out) / "fragment.json").read_text())
    assert manifest["float_encoding_requested"] == mode
    assert manifest["float_encoding_applied"] == ("unit" if expected == 127 else "byte")


@pytest.mark.parametrize(
    "dtype,values,expected",
    [
        (np.uint8, [0, 128, 255], [0, 128, 255]),
        (np.uint16, [255, 256, 65535], [0, 1, 255]),
    ],
)
def test_integer_mapping_is_preserved(tmp_path, dtype, values, expected):
    source = _source(tmp_path, np.array(values, dtype=dtype).reshape(1, 1, 3))
    out = convert_surface_volume(source, "s", tmp_path / "out", n_layers=1)
    np.testing.assert_array_equal(
        tifffile.imread(Path(out) / "layers/17.tif"), [expected]
    )


@pytest.mark.parametrize(
    "value,mode",
    [(2, "unit"), (256, "byte"), (-1, "auto"), (np.nan, "auto"), (np.inf, "auto")],
)
def test_bad_float_values_never_publish(tmp_path, value, mode):
    source = _source(tmp_path, np.full((1, 4, 5), value, np.float32))
    with pytest.raises(ValueError, match="finite"):
        convert_surface_volume(
            source, "s", tmp_path / "out", n_layers=1, float_encoding=mode
        )
    assert not (tmp_path / "out").exists()


def test_mixed_raw_encodings_are_not_silently_promoted(tmp_path):
    source = _source(tmp_path)
    tifffile.imwrite(source / "layers/1.tif", np.full((4, 5), 128, np.uint8))
    with pytest.raises(ValueError, match="dtype mismatch"):
        convert_surface_volume(source, "s", tmp_path / "out", n_layers=2)
    assert not (tmp_path / "out").exists()


def test_hidden_files_do_not_change_the_downloaders_selection(tmp_path):
    source = _source(tmp_path)
    (source / "layers/.unrelated.tif").write_bytes(b"ignored")
    (source / ".other_inklabels.png").write_bytes(b"ignored")
    (source / ".other_mask.png").write_bytes(b"ignored")
    plan = ca.build_plan(source, "s", tmp_path / "out", n_layers=2)
    assert [entry["relative_path"] for entry in plan["files"]] == [
        "layers/0.tif",
        "layers/1.tif",
        "s_inklabels.png",
    ]


def test_transparent_labels_are_rejected_before_decode(tmp_path):
    source = _source(tmp_path)
    image = Image.fromarray(np.zeros((4, 5), np.uint8))
    image.save(source / "s_inklabels.png", transparency=0)
    with pytest.raises(ValueError, match="grayscale"):
        ca.build_plan(source, "s", tmp_path / "out", n_layers=2)


def test_big_endian_uint16_retains_the_high_byte(tmp_path):
    source = _source(tmp_path, np.full((2, 4, 5), 32768, dtype=">u2"))
    out = convert_surface_volume(source, "s", tmp_path / "out", n_layers=2)
    assert np.all(tifffile.imread(Path(out) / "layers/17.tif") == 128)


def test_odd_centered_window_matches_raw_and_download_rule(tmp_path):
    volume = np.broadcast_to(np.arange(40, dtype=np.uint8)[:, None, None], (40, 4, 5))
    source = _source(tmp_path, volume)
    out = convert_surface_volume(source, "s", tmp_path / "out", n_layers=25)
    selected = region_to_layers(volume, 25)
    assert depth_window(40, 25) == (7, 32)
    np.testing.assert_array_equal(
        tifffile.imread(Path(out) / "layers/17.tif"), selected[0]
    )
    np.testing.assert_array_equal(selected[:, 0, 0], np.arange(7, 32))


def test_downloader_uses_the_same_odd_window():
    import fsspec

    from repro.sota_data.download_artifacts import BUCKET, build_plan, limits

    filesystem = fsspec.filesystem("memory")
    prefix = f"{BUCKET}/test_odd_conversion_window"
    try:
        for index in range(40):
            filesystem.pipe(f"{prefix}/layers/{index}.tif", b"x")
        filesystem.pipe(f"{prefix}/s_inklabels.png", b"x")
        plan = build_plan(filesystem, prefix, limits(1024, 1024, 512, 4096, 25))
        assert plan["selected_depth_indices"] == list(range(7, 32))
    finally:
        filesystem.rm(prefix, recursive=True)


@pytest.mark.parametrize(
    "count,center",
    [
        (0, None),
        (-1, None),
        (True, None),
        (2.0, None),
        (26, -1),
        (26, 1000),
        (26, 0),
        (26, 39),
        (26, True),
        (26, 20.5),
    ],
)
def test_invalid_depth_requests_are_refused_instead_of_clamped(count, center):
    with pytest.raises(ValueError):
        region_to_layers(np.zeros((40, 4, 5), np.uint8), count, center)


def test_explicit_center_is_preserved_when_it_fits():
    assert depth_window(40, 25, 20) == (8, 33)
    assert depth_window(40, 26, 20) == (7, 33)


def test_header_plan_does_not_decode_or_create_outputs(tmp_path, monkeypatch):
    source = _source(tmp_path)

    def fail(*args, **kwargs):
        pytest.fail("dry-run must not decode pixel arrays")

    monkeypatch.setattr(tifffile, "imread", fail)
    monkeypatch.setattr(cv2, "imdecode", fail)
    monkeypatch.setattr(Image.Image, "load", fail)
    plan = ca.build_plan(source, "s", tmp_path / "out", n_layers=2)
    assert plan["status"] == "HEADER_PLAN_ONLY"
    assert plan["shape_zyx"] == [2, 4, 5]
    assert plan["pixel_values_checked"] is False
    assert plan["float_encoding_applied"] is None
    assert not (tmp_path / "out").exists()


def test_voxel_limit_is_checked_before_decoding(tmp_path, monkeypatch):
    source = _source(tmp_path)
    monkeypatch.setattr(
        tifffile, "imread", lambda *a, **k: pytest.fail("must check header first")
    )
    with pytest.raises(ValueError, match="max_voxels"):
        convert_surface_volume(source, "s", tmp_path / "out", n_layers=2, max_voxels=39)
    assert not (tmp_path / "out").exists()


def test_encoded_limit_precedes_header_read(tmp_path, monkeypatch):
    source = _source(tmp_path)
    with (source / "layers/0.tif").open("wb") as stream:
        stream.truncate(ca.MAX_FILE_BYTES + 1)  # sparse: only stat may be read
    monkeypatch.setattr(
        ca, "_tiff_header", lambda *a: pytest.fail("must check size first")
    )
    with pytest.raises(ValueError, match="encoded byte limit"):
        ca.build_plan(source, "s", tmp_path / "out", n_layers=2)


@pytest.mark.parametrize("target", ["layers/0.tif", "s_inklabels.png", "layers"])
def test_symlink_sources_are_refused(tmp_path, target):
    source = _source(tmp_path)
    original = source / target
    saved = tmp_path / "saved"
    original.rename(saved)
    original.symlink_to(saved, target_is_directory=saved.is_dir())
    with pytest.raises(ValueError, match="symlink"):
        ca.build_plan(source, "s", tmp_path / "out", n_layers=2)


@pytest.mark.parametrize("kind", ["TIFF", "PNG"])
def test_successful_but_wrong_image_write_is_not_published(tmp_path, monkeypatch, kind):
    if kind == "TIFF":
        original = tifffile.imwrite
        monkeypatch.setattr(
            tifffile,
            "imwrite",
            lambda path, pixels, **kw: original(path, np.zeros_like(pixels), **kw),
        )
    else:
        original = cv2.imwrite
        monkeypatch.setattr(
            cv2, "imwrite", lambda path, pixels: original(path, np.zeros_like(pixels))
        )
    with pytest.raises(OSError, match=f"{kind} readback"):
        write_fragment(np.ones((2, 4, 5), np.uint8), tmp_path, "s")
    assert not list(tmp_path.iterdir())


def test_staged_output_mutation_after_readback_is_detected(tmp_path):
    def mutate():
        path = next(tmp_path.glob(".s-*/s/layers/17.tif"))
        tifffile.imwrite(path, np.zeros((4, 5), np.uint8))

    with pytest.raises(ValueError, match="output changed"):
        fragment.write_fragment_artifact(
            np.ones((2, 4, 5), np.uint8),
            np.ones((4, 5), bool),
            tmp_path,
            "s",
            verify_sources=mutate,
        )
    assert not list(tmp_path.iterdir())


def test_manifest_write_cannot_hide_an_earlier_output_rewrite(tmp_path, monkeypatch):
    original = Path.write_text

    def write(path, text, *args, **kwargs):
        result = original(path, text, *args, **kwargs)
        if path.name == "fragment.json":
            tifffile.imwrite(path.parent / "layers/17.tif", np.zeros((4, 5), np.uint8))
        return result

    monkeypatch.setattr(Path, "write_text", write)
    with pytest.raises(ValueError, match="output changed"):
        write_fragment(np.ones((2, 4, 5), np.uint8), tmp_path, "s")
    assert not list(tmp_path.iterdir())


def test_raw_source_rewrite_during_decoding_cannot_publish(tmp_path, monkeypatch):
    source = _source(tmp_path)
    original = tifffile.imread
    changed = False

    def read(data):
        nonlocal changed
        result = original(data)
        if not changed:
            changed = True
            tifffile.imwrite(source / "layers/0.tif", np.full((4, 5), 0.25, np.float32))
        return result

    monkeypatch.setattr(tifffile, "imread", read)
    with pytest.raises(ValueError, match="source changed"):
        convert_surface_volume(source, "s", tmp_path / "out", n_layers=2)
    assert not list((tmp_path / "out").iterdir())


def test_captured_bytes_are_the_decoded_bytes_and_recorded_hashes(
    tmp_path, monkeypatch
):
    source = _source(tmp_path)
    _record(source)
    original = tifffile.imread
    decoded = []

    def read(data):
        # Source is a captured buffer, not a pathname reopened after hashing.
        assert (
            isinstance(data, io.BytesIO)
            or isinstance(data, Path)
            and ".s-" in str(data)
        )
        if isinstance(data, io.BytesIO):
            decoded.append(hashlib.sha256(data.getvalue()).hexdigest())
        return original(data)

    monkeypatch.setattr(tifffile, "imread", read)
    out = Path(convert_surface_volume(source, "s", tmp_path / "out", n_layers=2))
    provenance = json.loads((out / "s_render_provenance.json").read_text())
    assert decoded == [
        provenance["inputs"][f"layers/{i}.tif"]["sha256"] for i in range(2)
    ]
    assert provenance["download_consumed_hashes_verified"] is True
    manifest = json.loads((out / "fragment.json").read_text())
    for name, identity in manifest["outputs"].items():
        data = (out / name).read_bytes()
        assert identity == {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    assert manifest["training_ready"] is False
    assert manifest["label_quality_verified"] is False


def test_edited_download_payload_is_refused(tmp_path):
    source = _source(tmp_path)
    _record(source)
    tifffile.imwrite(source / "layers/0.tif", np.full((4, 5), 0.25, np.float32))
    with pytest.raises(ValueError, match="download.json"):
        convert_surface_volume(source, "s", tmp_path / "out", n_layers=2)
    assert not (tmp_path / "out").exists()


def test_deleted_downloaded_mask_cannot_be_replaced_by_an_all_valid_mask(tmp_path):
    source = _source(tmp_path)
    mask = source / "s_mask.png"
    Image.fromarray(np.zeros((4, 5), np.uint8)).save(mask)
    _record(source)
    mask.unlink()
    with pytest.raises(ValueError, match="supervision.*download.json"):
        convert_surface_volume(source, "s", tmp_path / "out", n_layers=2)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "problem",
    ["invalid json", "duplicate", "unsafe", "status", "hash", "missing", "nonobject"],
)
def test_malformed_download_record_fails_closed(tmp_path, problem):
    source = _source(tmp_path)
    record = _record(source)
    if problem == "duplicate":
        record["files"].append(record["files"][0])
    elif problem == "unsafe":
        record["files"][0]["relative_path"] = "../0.tif"
    elif problem == "status":
        record["status"] = "HEADER_PLAN_ONLY"
    elif problem == "hash":
        record["files"][0]["sha256"] = "not a hash"
    elif problem == "missing":
        record["files"].pop()
    elif problem == "nonobject":
        record = []
    (source / "download.json").write_text(
        "{" if problem == "invalid json" else json.dumps(record)
    )
    with pytest.raises(ValueError, match="download"):
        convert_surface_volume(source, "s", tmp_path / "out", n_layers=2)
    assert not (tmp_path / "out").exists()


def test_cli_plan_and_conversion_report_honest_status(tmp_path, capsys):
    source = _source(tmp_path)
    arguments = [
        "--src",
        str(source),
        "--segment",
        "s",
        "--out-root",
        str(tmp_path / "out"),
        "--layers",
        "2",
    ]
    assert main([*arguments, "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["pixel_values_checked"] is False
    assert main(arguments) == 0
    assert Path(json.loads(capsys.readouterr().out)["output"]).is_dir()
    assert main(arguments) == 1
    assert "already exists" in capsys.readouterr().err


def test_help_from_another_cwd_has_no_image_s3_or_ml_imports(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    script = """
import runpy, sys
sys.argv = ['convert', '--help']
try:
    runpy.run_module('repro.sota_data.convert', run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
assert not {'numpy','cv2','tifffile','torch','s3fs'}.intersection(sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(repo)},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "--float-encoding" in result.stdout
