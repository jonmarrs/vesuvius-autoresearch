"""Input receipts and actual pinned progress JSON, without importing GUI code."""

import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import tifffile
import zarr

from scripts import check_proofreader_session as check, launch_proofreader as launcher
from vesuvius_autoresearch.core import proofreader_session as sessions

PROOFREADER = launcher.ROOT / "villa/segmentation/vc_proofreader/main.py"


@pytest.fixture
def inputs(tmp_path):
    ct, labels = tmp_path / "ct.zarr", tmp_path / "labels.zarr"
    for path, dtype in ((ct, "u2"), (labels, "u1")):
        array = zarr.open(
            str(path), mode="w", shape=(8, 16, 16), chunks=(4, 8, 8), dtype=dtype
        )
        array[:] = 7 if path == ct else 1
    return ct, labels, tmp_path / "session"


def _launch(inputs, monkeypatch, child=None, extra=(), returncode=0):
    ct, labels, out = inputs
    configs = []

    def run(command, **kwargs):
        config = json.loads(Path(command[command.index("--config") + 1]).read_text())
        configs.append(config)
        if child:
            child(config)
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(launcher.subprocess, "run", run)
    result = launcher.main(
        [
            "--volume",
            str(ct),
            "--predictions",
            str(labels),
            "--patch-size",
            "8",
            "--out-dir",
            str(out),
            "--record-session",
            *extra,
        ]
    )
    return result, configs


def _pinned_function(name, namespace):
    node = next(
        n
        for n in ast.parse(PROOFREADER.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == name
    )
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(PROOFREADER), "exec"),
        namespace,
    )
    return namespace[name]


def _pinned_progress(
    config,
    *,
    save=False,
    save_edited_labels=False,
    label_value=42,
    approved_origin=(0, 0, 0),
):
    """Exercise the pinned writer/serializer without constructing a viewer."""
    root = Path(config["dataset_out_path"])
    root.mkdir(exist_ok=True)
    selected = config["volumes"]["Autoresearch_Prediction"]
    image = zarr.open(selected["volume_path"], mode="r")
    patch_size = config["patch_size"]
    grid = _pinned_function("generate_patch_coords", {})(
        image.shape, patch_size, "sequence"
    )
    state = {
        "save_progress": True,
        "progress_file": config["progress_file"],
        "patch_size": patch_size,
        "image_zarr": selected["volume_path"],
        "label_zarr": selected["label_path"],
        "image_volume": image,
        "dataset_out_path": str(root),
        "images_out_dir": str(root / "imagesTr"),
        "labels_out_dir": str(root / "labelsTr"),
        "progress_log": [
            {
                "index": grid.index(approved_origin),
                "coords": approved_origin,
                "percentage": 100.0,
                "status": "approved",
            },
            {"index": 1, "coords": (0, 0, 8), "percentage": 100.0, "status": "pending"},
        ],
    }
    namespace = {
        "state": state,
        "json": json,
        "datetime": datetime,
        "init_volume": SimpleNamespace(
            volume_selection=SimpleNamespace(value="Autoresearch_Prediction")
        ),
    }
    if save:
        if save_edited_labels:
            state["output_zarr_array"] = zarr.open_array(
                config["output_label_zarr"],
                mode="w",
                shape=state["image_volume"].shape,
                chunks=(128,) * 3,
                dtype="u1",
                compressor=zarr.Blosc(
                    cname="zstd", clevel=3, shuffle=zarr.Blosc.BITSHUFFLE
                ),
                write_empty_chunks=False,
            )
        Path(state["images_out_dir"]).mkdir()
        Path(state["labels_out_dir"]).mkdir()
        crop = tuple(slice(origin, origin + patch_size) for origin in approved_origin)
        state["current_patch"] = {"coords": approved_origin, "image": image[crop]}
        namespace.update(
            os=os,
            tifffile=tifffile,
            np=np,
            viewer=SimpleNamespace(
                layers={
                    "patch_label": SimpleNamespace(
                        data=np.full((8,) * 3, label_value, "u2")
                    )
                }
            ),
        )
        _pinned_function("save_current_patch", namespace)()
    _pinned_function("update_progress", namespace)()


def _all_bytes(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def test_pinned_progress_loader_accepts_wrong_source_but_checker_refuses(
    inputs, monkeypatch
):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    progress = json.loads(path.read_text())
    progress["metadata"]["image_zarr"] = "/different/ct.zarr"
    path.write_text(json.dumps(progress))
    state = {"save_progress": True, "progress_file": str(path)}
    namespace = {"state": state, "json": json, "os": os}
    _pinned_function("load_progress", namespace)()
    assert state["progress_log"] == progress["progress_log"]
    assert state["current_index"] == 2
    with pytest.raises(ValueError, match="context differs"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


def test_record_binds_actual_launch_and_verifies_actual_pinned_progress(
    inputs, monkeypatch
):
    before = [_all_bytes(path) for path in inputs[:2]]
    result, configs = _launch(inputs, monkeypatch, _pinned_progress)
    assert result == 0
    config = configs[0]
    record = json.loads((inputs[2] / sessions.RECORD_NAME).read_text())
    assert record["config"] == config
    assert config["progress_file"] == str(inputs[2] / "progress.json")
    assert config["output_label_zarr"] == str(inputs[2] / "edited_labels.zarr")
    all_before = _all_bytes(inputs[2].parent)
    report = sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)
    assert report["input_record_matches"]
    assert (
        report["input_record_sha256"]
        == hashlib.sha256((inputs[2] / sessions.RECORD_NAME).read_bytes()).hexdigest()
    )
    assert (
        report["progress"]["captured_sha256"]
        == hashlib.sha256((inputs[2] / "progress.json").read_bytes()).hexdigest()
    )
    assert report["progress"]["status_counts"] == {
        "approved": 1,
        "skipped": 0,
        "auto-skipped": 0,
        "pending": 1,
    }
    assert not report["resume_supported"]
    assert not report["approved_patch_files_verified"]
    assert not report["ink_training_ingestion_supported"]
    assert _all_bytes(inputs[2].parent) == all_before
    assert [_all_bytes(path) for path in inputs[:2]] == before


@pytest.mark.parametrize("returncode", [0, 23])
def test_receipt_is_an_initial_record_even_if_gui_has_no_progress(
    inputs, monkeypatch, returncode
):
    result, _ = _launch(inputs, monkeypatch, returncode=returncode)
    assert result == returncode
    report = sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)
    assert report["progress"] == {"present": False, "status_counts": None}
    assert "completion" not in json.loads(
        (inputs[2] / sessions.RECORD_NAME).read_text()
    )


def test_checker_verifies_pinned_writer_exports_read_only(inputs, monkeypatch, capsys):
    ct, _, root = inputs
    zarr.open(str(ct), mode="r+")[:, :, 8:] = 123  # distinguish the pending crop
    assert (
        _launch(inputs, monkeypatch, lambda c: _pinned_progress(c, save=True))[0] == 0
    )
    before = _all_bytes(root.parent)
    capsys.readouterr()
    assert check.main(["--session", str(root), "--verify-approved-patches"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["approved_patch_files_verified"] is True
    assert report["resume_supported"] is False
    assert report["ink_training_ingestion_supported"] is False
    verified = report["progress"]["approved_exports"]
    assert verified["pairs_verified"] == 1
    pair = verified["pairs"][0]
    assert pair["coords_zyx"] == [0, 0, 0]
    for role in ("image", "label"):
        item = pair[role]
        raw = (root / item["path"]).read_bytes()
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()
        assert item["bytes"] == len(raw)
    assert _all_bytes(root.parent) == before


@pytest.mark.parametrize(
    ("label_value", "failed_write"), [(42, False), (0, False), (42, True)]
)
def test_checker_compares_the_pinned_writers_label_tiff_and_zarr(
    inputs, monkeypatch, capsys, label_value, failed_write
):
    _, _, root = inputs

    def fail_zarr_write(array, selection, value):
        raise OSError("injected edited Zarr write failure")

    def child(config):
        with monkeypatch.context() as gui:
            if failed_write:
                gui.setattr(zarr.Array, "__setitem__", fail_zarr_write)
            _pinned_progress(
                config,
                save=True,
                save_edited_labels=True,
                label_value=label_value,
                approved_origin=(0, 8, 0),
            )

    assert _launch(inputs, monkeypatch, child)[0] == 0
    output = capsys.readouterr().out
    if failed_write:
        assert (
            "Error saving to output zarr: injected edited Zarr write failure" in output
        )
    before = _all_bytes(root.parent)
    tiff_check = sessions.verify_record(
        root, PROOFREADER, sessions.DEFAULT_LIMITS, verify_approved_patches=True
    )
    assert tiff_check["progress"]["approved_exports"]["pairs_verified"] == 1

    exit_code = check.main(["--session", str(root), "--verify-edited-labels"])
    captured = capsys.readouterr()
    if failed_write:
        assert exit_code == 1
        assert (
            "approved label TIFF differs from edited-label Zarr at [0, 8, 0]"
            in captured.err
        )
        assert not captured.out
    else:
        assert exit_code == 0
        report = json.loads(captured.out)
        assert report["approved_patch_files_verified"] is True
        assert report["progress"]["approved_exports"]["pairs"][0]["coords_zyx"] == [
            0,
            8,
            0,
        ]
        assert report["progress"]["approved_exports"]["edited_labels"] == {
            "path": "edited_labels.zarr",
            "shape_zyx": [8, 16, 16],
            "dtype": "uint8",
            "approved_crops_verified": 1,
        }
    assert _all_bytes(root.parent) == before


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing", "missing edited-label Zarr"),
        ("linked", "edited-label Zarr must be a nonsymlink directory"),
        ("shape", "must match the CT shape"),
        ("dtype", "with uint8 labels"),
        ("fill_value", "and zero fill"),
        ("chunks", "decoded edited-label Zarr chunk exceeds max_file_bytes"),
        ("zero_chunk", "invalid edited-label Zarr chunk geometry"),
        ("chunk_rank", "invalid edited-label Zarr chunk geometry"),
        ("missing_chunks", "invalid edited-label Zarr metadata"),
    ],
)
def test_edited_store_preflight_rejects_invalid_layout_and_size(
    inputs, monkeypatch, change, message
):
    root = inputs[2]
    assert (
        _launch(
            inputs,
            monkeypatch,
            lambda config: _pinned_progress(config, save=True, save_edited_labels=True),
        )[0]
        == 0
    )
    edited = root / "edited_labels.zarr"
    if change in {"missing", "linked"}:
        moved = edited.rename(root / "other.zarr")
        if change == "linked":
            edited.symlink_to(moved, target_is_directory=True)
    else:
        metadata = edited / ".zarray"
        header = json.loads(metadata.read_text())
        if change == "missing_chunks":
            del header["chunks"]
        elif change in {"zero_chunk", "chunk_rank"}:
            header["chunks"] = [0, 8, 8] if change == "zero_chunk" else [8, 8]
        else:
            header[change] = {
                "shape": [8, 16, 17],
                "dtype": "<u2",
                "fill_value": 1,
                "chunks": [512, 512, 512],
            }[change]
        metadata.write_text(json.dumps(header))

    def no_crop_reads(*args, **kwargs):
        pytest.fail("invalid edited Zarr reached TIFF decoding")

    monkeypatch.setattr(sessions, "_capture_tiff", no_crop_reads)
    with pytest.raises(ValueError, match=message):
        sessions.verify_record(
            root, PROOFREADER, sessions.DEFAULT_LIMITS, verify_edited_labels=True
        )


def test_edited_store_changes_during_crop_verification_are_detected(
    inputs, monkeypatch
):
    root = inputs[2]
    assert (
        _launch(
            inputs,
            monkeypatch,
            lambda config: _pinned_progress(config, save=True, save_edited_labels=True),
        )[0]
        == 0
    )
    capture_tiff = sessions._capture_tiff

    def capture_then_edit_metadata(path, edge, limit, role):
        result = capture_tiff(path, edge, limit, role)
        if role == "label":
            (root / "edited_labels.zarr" / ".zattrs").write_text('{"edited":true}')
        return result

    monkeypatch.setattr(sessions, "_capture_tiff", capture_then_edit_metadata)
    with pytest.raises(
        ValueError, match="edited-label Zarr changed during export verification"
    ):
        sessions.verify_record(
            root, PROOFREADER, sessions.DEFAULT_LIMITS, verify_edited_labels=True
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing", "missing approved TIFF"),
        ("orphan", "unlisted proofreader export"),
        ("wrong_crop", "differs from recorded CT"),
        ("float_label", "invalid label TIFF shape or dtype"),
        ("wide_label", "outside 0..255"),
        ("truncated", "incomplete proofreader TIFF"),
        ("short_strip_count", "incomplete proofreader TIFF"),
        ("link", "nonsymlink regular file"),
        ("linked_directory", "directory must not be linked"),
        ("wrong_export", "patch list/count differs"),
        ("duplicate_approval", "duplicate approval"),
    ],
)
def test_export_check_refuses_inconsistent_approval_artifacts(
    inputs, monkeypatch, change, message
):
    ct, _, root = inputs
    volume = zarr.open(str(ct), mode="r+")
    volume[:, :, 8:] = 123
    assert (
        _launch(inputs, monkeypatch, lambda c: _pinned_progress(c, save=True))[0] == 0
    )
    image = root / "imagesTr/z0_y0_x0_0000.tif"
    label = root / "labelsTr/z0_y0_x0.tif"
    if change == "missing":
        label.unlink()
    elif change == "orphan":
        (root / "labelsTr/z0_y0_x8.tif").write_bytes(label.read_bytes())
    elif change == "wrong_crop":
        tifffile.imwrite(image, volume[:8, :8, 8:16])
    elif change == "float_label":
        tifffile.imwrite(label, np.full((8,) * 3, 1, "float32"))
    elif change == "wide_label":
        tifffile.imwrite(label, np.full((8,) * 3, 256, "uint16"))
    elif change == "truncated":
        with tifffile.TiffFile(label) as tiff:
            end = tiff.pages[-1].dataoffsets[-1] + tiff.pages[-1].databytecounts[-1]
        label.write_bytes(label.read_bytes()[: end - 1])
    elif change == "short_strip_count":
        # A contiguous TIFF decode can ignore an incorrect strip byte count.
        with tifffile.TiffFile(label, mode="r+") as tiff:
            tag = tiff.pages[0].tags["StripByteCounts"]
            tag.overwrite((tag.value[0] - 1,))
    elif change == "link":
        moved = label.rename(root / "moved.tif")
        label.symlink_to(moved)
    elif change == "linked_directory":
        moved = label.parent.rename(root / "moved")
        label.parent.symlink_to(moved, target_is_directory=True)
    else:
        path = root / "progress.json"
        progress = json.loads(path.read_bytes())
        if change == "wrong_export":
            progress["approved_patches"][0]["label_filename"] = "../moved.tif"
        else:
            progress["progress_log"].append(progress["progress_log"][0])
        path.write_text(json.dumps(progress))

    assert not sessions.verify_record(root, PROOFREADER, sessions.DEFAULT_LIMITS)[
        "approved_patch_files_verified"
    ]
    with pytest.raises(ValueError, match=message):
        sessions.verify_record(
            root, PROOFREADER, sessions.DEFAULT_LIMITS, verify_approved_patches=True
        )


def test_absent_progress_differs_from_zero_approved_exports(inputs, monkeypatch):
    assert _launch(inputs, monkeypatch)[0] == 0
    root = inputs[2]
    with pytest.raises(ValueError, match="requires progress.json"):
        sessions.verify_record(
            root, PROOFREADER, sessions.DEFAULT_LIMITS, verify_approved_patches=True
        )
    config = json.loads((root / sessions.RECORD_NAME).read_bytes())["config"]
    _pinned_progress(config)
    path = root / "progress.json"
    progress = json.loads(path.read_bytes())
    progress["metadata"]["total_approved"] = 0
    progress["approved_patches"] = []
    progress["progress_log"][0]["status"] = "skipped"
    path.write_text(json.dumps(progress))
    checked = sessions.verify_record(
        root, PROOFREADER, sessions.DEFAULT_LIMITS, verify_approved_patches=True
    )
    assert checked["progress"]["approved_exports"] == {"pairs_verified": 0, "pairs": []}


@pytest.mark.parametrize(
    ("source", "check_edited_labels", "diagnostic"),
    [(0, False, "recorded CT changed"), (1, True, "recorded labels changed")],
)
def test_input_mutation_during_export_read_refuses_verification(
    inputs, monkeypatch, source, check_edited_labels, diagnostic
):
    from volume_cartographer_wrapper.volume import FastLocalVolume

    assert (
        _launch(
            inputs,
            monkeypatch,
            lambda c: _pinned_progress(
                c, save=True, save_edited_labels=check_edited_labels
            ),
        )[0]
        == 0
    )
    original = FastLocalVolume.get_chunk

    def change_after_read(self, *args):
        values = original(self, *args)
        zarr.open(str(inputs[source]), mode="r+")[0, 0, 0] = 22
        return values

    monkeypatch.setattr(FastLocalVolume, "get_chunk", change_after_read)
    with pytest.raises(ValueError, match=diagnostic):
        sessions.verify_record(
            inputs[2],
            PROOFREADER,
            sessions.DEFAULT_LIMITS,
            verify_approved_patches=not check_edited_labels,
            verify_edited_labels=check_edited_labels,
        )


def test_export_check_bounds_decoded_ct_chunks_before_read(inputs, monkeypatch):
    from volume_cartographer_wrapper.volume import FastLocalVolume

    ct, _, root = inputs
    zarr.open(str(ct), mode="w", shape=(8, 16, 16), chunks=(16, 32, 32), dtype="u2")[
        :
    ] = 7
    assert (
        _launch(inputs, monkeypatch, lambda c: _pinned_progress(c, save=True))[0] == 0
    )
    monkeypatch.setattr(
        FastLocalVolume,
        "get_chunk",
        lambda *a: pytest.fail("decoded an over-budget chunk"),
    )
    with pytest.raises(ValueError, match="decoded CT patch or chunk exceeds"):
        sessions.verify_record(
            root,
            PROOFREADER,
            sessions.limits(max_file_bytes=8 * 1024),
            verify_approved_patches=True,
        )


def test_progress_hash_and_counts_use_the_same_captured_bytes(inputs, monkeypatch):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    before = path.read_bytes()
    original = sessions.capture_bytes

    def capture(source, limit):
        result = original(source, limit)
        if Path(source) == path:
            changed = json.loads(before)
            changed["progress_log"][0]["status"] = "skipped"
            path.write_text(json.dumps(changed))
        return result

    monkeypatch.setattr(sessions, "capture_bytes", capture)
    report = sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)
    assert report["progress"]["captured_sha256"] == hashlib.sha256(before).hexdigest()
    assert (
        report["progress"]["captured_sha256"]
        != hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert report["progress"]["status_counts"]["approved"] == 1


@pytest.mark.parametrize(("role", "name"), [(0, "CT"), (1, "labels")])
def test_default_check_rejects_a_source_changed_after_hashing(
    inputs, monkeypatch, capsys, role, name
):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    root = inputs[2]
    original = sessions.capture_bytes

    def capture(source, limit):
        result = original(source, limit)
        if Path(source) == root / sessions.PROGRESS_NAME:
            zarr.open(str(inputs[role]), mode="r+")[0, 0, 0] = 22
        return result

    monkeypatch.setattr(sessions, "capture_bytes", capture)
    capsys.readouterr()
    assert check.main(["--session", str(root)]) == 1
    stdout, stderr = capsys.readouterr()
    assert not stdout
    assert f"recorded {name} changed during session verification" in stderr


@pytest.mark.parametrize("role", [0, 1])
@pytest.mark.parametrize("change", ["chunk", "metadata", "add", "remove"])
def test_changed_source_bytes_or_inventory_refuse_verification(
    inputs, monkeypatch, role, change
):
    assert _launch(inputs, monkeypatch)[0] == 0
    root = inputs[role]
    if change == "chunk":
        zarr.open(str(root), mode="r+")[0, 0, 0] = 19
    elif change == "metadata":
        zarr.open(str(root), mode="r+").attrs["origin"] = [1, 2, 3]
    elif change == "add":
        (root / "new_metadata").write_text("new")
    else:
        (root / "0.0.0").unlink()
    with pytest.raises(ValueError, match="source differs"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("patch_size", 4),
        ("image_zarr", "/other.zarr"),
        ("volume_shape", [8, 16, 15]),
        ("coordinate_system", "other"),
        ("dataset_out_path", "/other"),
    ],
)
def test_wrong_progress_context_is_not_accepted(inputs, monkeypatch, field, value):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    progress = json.loads(path.read_text())
    progress["metadata"][field] = value
    path.write_text(json.dumps(progress))
    with pytest.raises(ValueError, match="context differs"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("coords", [-1, 0, 0]),
        ("coords", [0, 0, 16]),
        ("index", True),
        ("index", 4),
        ("percentage", 101),
        ("status", "unknown"),
    ],
)
def test_invalid_progress_entries_fail_closed(inputs, monkeypatch, field, value):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    progress = json.loads(path.read_text())
    progress["progress_log"][0][field] = value
    path.write_text(json.dumps(progress))
    with pytest.raises(ValueError, match="invalid proofreader progress"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "extra",
    [
        ("--max-source-bytes", "1"),
        ("--max-file-bytes", "1"),
        ("--max-entries", "1"),
        ("--max-entries", "0"),
    ],
)
def test_source_budgets_fail_before_receipt_or_gui(inputs, monkeypatch, extra):
    result, configs = _launch(inputs, monkeypatch, extra=extra)
    assert result == 1 and not configs and not inputs[2].exists()


@pytest.mark.parametrize("kind", ["symlink", "directory_link", "hardlink", "fifo"])
def test_links_and_special_sources_are_not_followed(inputs, monkeypatch, kind):
    ct, _, out = inputs
    target = ct / "extra"
    if kind == "symlink":
        target.symlink_to(ct / "0.0.0")
    elif kind == "directory_link":
        target.symlink_to(inputs[1], target_is_directory=True)
    elif kind == "hardlink":
        os.link(ct / "0.0.0", target)
    elif not hasattr(os, "mkfifo"):
        pytest.skip("FIFO unavailable")
    else:
        os.mkfifo(target)
    result, configs = _launch(inputs, monkeypatch)
    assert result == 1 and not configs and not out.exists()


def test_source_change_during_capture_refuses_publication(inputs, monkeypatch):
    original = sessions.capture_bytes

    def capture(path, limit):
        result = original(path, limit)
        if Path(path) == inputs[0] / ".zarray":
            (inputs[0] / "new").write_text("mutation")
        return result

    monkeypatch.setattr(sessions, "capture_bytes", capture)
    result, configs = _launch(inputs, monkeypatch)
    assert result == 1 and not configs and not inputs[2].exists()


def test_record_cannot_raise_checker_limits_or_change_pinned_code(
    inputs, monkeypatch, tmp_path
):
    assert _launch(inputs, monkeypatch)[0] == 0
    with pytest.raises(ValueError, match="max_source_bytes"):
        sessions.verify_record(
            inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS | {"max_source_bytes": 1}
        )
    other = tmp_path / "other.py"
    other.write_text("# changed source")
    with pytest.raises(ValueError, match="pinned proofreader source differs"):
        sessions.verify_record(inputs[2], other, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "replacement",
    ['{"schema_version":1,"schema_version":1}', '{"schema_version":NaN}', "[]"],
)
def test_malformed_receipt_is_rejected(inputs, monkeypatch, replacement):
    assert _launch(inputs, monkeypatch)[0] == 0
    (inputs[2] / sessions.RECORD_NAME).write_text(replacement)
    with pytest.raises(ValueError):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


def test_checker_cli_reports_missing_and_matching_records(inputs, monkeypatch, capsys):
    assert check.main(["--session", str(inputs[2])]) == 1
    assert "check failed" in capsys.readouterr().err
    assert _launch(inputs, monkeypatch)[0] == 0
    capsys.readouterr()
    assert check.main(["--session", str(inputs[2])]) == 0
    assert json.loads(capsys.readouterr().out)["input_record_matches"]


def test_recorded_session_still_cannot_resume_or_overwrite(inputs, monkeypatch):
    assert _launch(inputs, monkeypatch)[0] == 0
    before = _all_bytes(inputs[2])
    result, configs = _launch(inputs, monkeypatch)
    assert result == 1 and not configs and _all_bytes(inputs[2]) == before


def test_checker_help_without_scientific_or_gui_dependencies(tmp_path):
    result = subprocess.run(
        [sys.executable, "-S", str(Path(check.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0 and "Read-only" in result.stdout


# --- the approved-export check on its own, without the pinned proofreader -------------------------------------------
# The tests above reach the export check through villa's pinned proofreader; these call it directly, on TIFF pairs
# written as the pinned writer writes them (uncompressed, one page per slice), against an in-memory CT.

EDGE = 8


class _CT:
    """The two members of the recorded CT volume the check reads: its geometry and get_chunk."""

    def __init__(self, data, chunks=(8, 8, 8)):
        self.data, self.shape, self.dtype, self.chunks = (
            data,
            data.shape,
            data.dtype,
            chunks,
        )

    def get_chunk(self, z, y, x, dz, dy, dx):
        return self.data[z : z + dz, y : y + dy, x : x + dx]


def _ct():
    return _CT(np.random.default_rng(5).integers(0, 255, (16, 16, 16), dtype=np.uint8))


def _exports(root: Path, ct, coords=((0, 0, 0), (8, 8, 0)), statuses=None, label=None):
    """Approved TIFF pairs for `coords` and the progress log that lists them."""
    (root / "imagesTr").mkdir(parents=True, exist_ok=True)
    (root / "labelsTr").mkdir(exist_ok=True)
    log, approved = [], []
    for index, (z, y, x) in enumerate(coords):
        status = statuses[index] if statuses else "approved"
        entry = {"status": status, "coords": [z, y, x], "percentage": 50.0, "index": index,
                 "date_processed": "2026-11-17"}  # fmt: skip
        log.append(entry)
        if status != "approved":
            continue
        stem = f"z{z}_y{y}_x{x}"
        tifffile.imwrite(
            root / "imagesTr" / f"{stem}_0000.tif",
            ct.get_chunk(z, y, x, EDGE, EDGE, EDGE),
        )
        values = np.ones((EDGE,) * 3, np.uint8) if label is None else label
        tifffile.imwrite(root / "labelsTr" / f"{stem}.tif", values)
        approved.append({"volume_index": 0, "coords": [z, y, x], "percentage": 50.0, "index": index,
                         "date_processed": "2026-11-17", "image_filename": f"{stem}_0000.tif",
                         "label_filename": f"{stem}.tif", "patch_size": EDGE})  # fmt: skip
    return {
        "progress_log": log,
        "metadata": {"total_approved": len(approved)},
        "approved_patches": approved,
    }


def _verify(root, progress, ct, **budget):
    return sessions._verify_exports(
        root, progress, ct, {"patch_size": EDGE}, sessions.limits(**budget)
    )


def test_approved_pairs_equal_to_the_recorded_ct_are_verified_and_hashed(tmp_path):
    ct = _ct()
    progress = _exports(tmp_path, ct, coords=((0, 0, 0), (8, 8, 0), (8, 0, 8)),
                        statuses=["approved", "skipped", "approved"])  # fmt: skip
    report = _verify(tmp_path, progress, ct)
    assert report["pairs_verified"] == 2
    first = report["pairs"][0]
    assert (
        first["coords_zyx"] == [0, 0, 0]
        and first["image"]["path"] == "imagesTr/z0_y0_x0_0000.tif"
    )
    raw = (tmp_path / "labelsTr" / "z0_y0_x0.tif").read_bytes()
    assert first["label"] == {"path": "labelsTr/z0_y0_x0.tif", "bytes": len(raw),
                              "sha256": hashlib.sha256(raw).hexdigest()}  # fmt: skip


def test_no_approvals_and_no_export_folders_verify_nothing(tmp_path):
    progress = {
        "progress_log": [],
        "metadata": {"total_approved": 0},
        "approved_patches": [],
    }
    assert _verify(tmp_path, progress, _ct()) == {"pairs_verified": 0, "pairs": []}


@pytest.mark.parametrize(
    "change",
    ["one_voxel", "another_dtype"],
)
def test_an_image_that_is_not_the_recorded_ct_is_refused(tmp_path, change):
    ct = _ct()
    progress = _exports(tmp_path, ct, coords=((0, 0, 0),))
    image = ct.get_chunk(0, 0, 0, EDGE, EDGE, EDGE)
    image = image.astype(np.uint16) if change == "another_dtype" else image.copy()
    if change == "one_voxel":
        image[3, 3, 3] ^= 1
    tifffile.imwrite(tmp_path / "imagesTr" / "z0_y0_x0_0000.tif", image)
    with pytest.raises(ValueError, match="differs from recorded CT"):
        _verify(tmp_path, progress, ct)


@pytest.mark.parametrize("value", [-1, 256])
def test_a_label_outside_0_to_255_is_refused(tmp_path, value):
    label = np.zeros((EDGE,) * 3, np.int16)
    label[0, 0, 0] = value
    with pytest.raises(ValueError, match="outside 0..255"):
        _verify(
            tmp_path, _exports(tmp_path, _ct(), coords=((0, 0, 0),), label=label), _ct()
        )


def test_labels_at_0_and_255_are_in_range(tmp_path):
    label = np.zeros((EDGE,) * 3, np.int16)
    label[0, 0, 0] = 255
    assert (
        _verify(
            tmp_path, _exports(tmp_path, _ct(), coords=((0, 0, 0),), label=label), _ct()
        )["pairs_verified"]
        == 1
    )


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (
            lambda p: p["progress_log"].append(dict(p["progress_log"][0], index=9)),
            "duplicate approval",
        ),
        (lambda p: p["metadata"].update(total_approved=3), "differs from progress log"),
        (
            lambda p: p["metadata"].update(total_approved=True),
            "differs from progress log",
        ),
        (
            lambda p: p["approved_patches"][0].update(date_processed="2026-11-18"),
            "differs from progress log",
        ),
        (lambda p: p["approved_patches"].pop(), "differs from progress log"),
    ],
    ids=["duplicate", "count", "count_not_int", "listed_field", "listed_missing"],
)
def test_the_approved_list_must_be_the_one_the_log_implies(tmp_path, edit, message):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    edit(progress)
    with pytest.raises(ValueError, match=message):
        _verify(tmp_path, progress, ct)


def test_an_approval_logged_without_a_date_is_listed_with_an_empty_one(tmp_path):
    ct = _ct()
    progress = _exports(tmp_path, ct, coords=((0, 0, 0),))
    del progress["progress_log"][0]["date_processed"]
    progress["approved_patches"][0]["date_processed"] = ""
    assert _verify(tmp_path, progress, ct)["pairs_verified"] == 1


@pytest.mark.parametrize(
    ("arrange", "message"),
    [
        (
            lambda r: (r / "imagesTr" / "stray.tif").write_bytes(b"x"),
            "unlisted proofreader export",
        ),
        (
            lambda r: (r / "labelsTr" / "z8_y8_x0.tif").unlink(),
            "missing approved TIFF in",
        ),
        (
            lambda r: __import__("shutil").rmtree(r / "labelsTr"),
            "missing approved TIFF directory",
        ),
        (
            lambda r: os.link(r / "imagesTr" / "z0_y0_x0_0000.tif", r / "hardlink"),
            "without hard links",
        ),
    ],
    ids=["unlisted", "missing_file", "missing_folder", "hard_link"],
)
def test_the_export_folders_hold_exactly_the_approved_files(tmp_path, arrange, message):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    arrange(tmp_path)
    with pytest.raises(ValueError, match=message):
        _verify(tmp_path, progress, ct)


def test_a_linked_export_folder_or_file_is_refused(tmp_path):
    ct = _ct()
    progress = _exports(tmp_path / "real", ct)
    (tmp_path / "linked").mkdir()
    (tmp_path / "linked" / "imagesTr").symlink_to(tmp_path / "real" / "imagesTr")
    (tmp_path / "linked" / "labelsTr").mkdir()
    with pytest.raises(ValueError, match="must not be linked"):
        _verify(tmp_path / "linked", progress, ct)
    label = tmp_path / "real" / "labelsTr" / "z0_y0_x0.tif"
    moved = tmp_path / "elsewhere.tif"
    label.rename(moved)
    label.symlink_to(moved)
    with pytest.raises(ValueError, match="nonsymlink regular file"):
        _verify(tmp_path / "real", progress, ct)


def test_the_budgets_bound_files_bytes_entries_and_decoded_chunks(tmp_path):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    size = (tmp_path / "imagesTr" / "z0_y0_x0_0000.tif").stat().st_size
    with pytest.raises(ValueError, match="exceeds max_file_bytes"):
        _verify(tmp_path, progress, ct, max_file_bytes=size - 1)
    total = sum(p.stat().st_size for p in tmp_path.rglob("*.tif"))
    with pytest.raises(ValueError, match="exceed max_source_bytes"):
        _verify(tmp_path, progress, ct, max_source_bytes=total - 1)
    with pytest.raises(ValueError, match="exceed max_entries"):
        _verify(
            tmp_path, progress, ct, max_entries=5
        )  # two pairs need 2 * 2 + 2 entries
    assert _verify(tmp_path, progress, ct, max_entries=6)["pairs_verified"] == 2
    with pytest.raises(ValueError, match="decoded CT patch or chunk"):
        _verify(
            tmp_path,
            progress,
            _CT(ct.data, chunks=(16, 16, 16)),
            max_file_bytes=16**3 - 1,
        )


@pytest.mark.parametrize(
    ("write", "message"),
    [
        (
            lambda p, a: tifffile.imwrite(p, a, compression="zlib"),
            "invalid or incomplete",
        ),
        (lambda p, a: tifffile.imwrite(p, a, tile=(16, 16)), "invalid or incomplete"),
        (lambda p, a: tifffile.imwrite(p, a[:-1]), "invalid image TIFF shape"),
        (
            lambda p, a: tifffile.imwrite(p, a.astype(np.complex64)),
            "invalid image TIFF shape or dtype",
        ),
    ],
    ids=["compressed", "tiled", "short", "complex"],
)
def test_an_image_tiff_the_pinned_writer_would_not_write_is_refused(
    tmp_path, write, message
):
    ct = _ct()
    progress = _exports(tmp_path, ct, coords=((0, 0, 0),))
    path = tmp_path / "imagesTr" / "z0_y0_x0_0000.tif"
    write(path, ct.get_chunk(0, 0, 0, EDGE, EDGE, EDGE))
    with pytest.raises(ValueError, match=message):
        _verify(tmp_path, progress, ct)


def test_a_float_label_is_refused_where_a_float_image_may_pass_the_type_check(tmp_path):
    ct = _ct()
    progress = _exports(
        tmp_path, ct, coords=((0, 0, 0),), label=np.ones((EDGE,) * 3, np.float32)
    )
    with pytest.raises(ValueError, match="invalid label TIFF shape or dtype"):
        _verify(tmp_path, progress, ct)


@pytest.mark.parametrize(
    ("cut", "message"),
    [
        ("structure", "unreadable proofreader TIFF"),
        ("strip", "incomplete proofreader TIFF"),
    ],
)
def test_a_cut_short_tiff_is_refused_with_its_reason(tmp_path, cut, message):
    # cut through the last page's structure, tifffile cannot parse the file at all; cut through the last strip, the
    # last page is lost and the patch is short
    ct = _ct()
    progress = _exports(tmp_path, ct, coords=((0, 0, 0),))
    path = tmp_path / "labelsTr" / "z0_y0_x0.tif"
    raw = path.read_bytes()
    if cut == "structure":
        path.write_bytes(raw[: len(raw) - 40])
    else:
        with tifffile.TiffFile(path) as tiff:
            end = tiff.pages[-1].dataoffsets[-1] + tiff.pages[-1].databytecounts[-1]
        path.write_bytes(raw[: end - 1])
    with pytest.raises(ValueError, match=message):
        _verify(tmp_path, progress, ct)


def test_an_export_changed_while_it_is_read_is_refused(tmp_path, monkeypatch):
    ct = _ct()
    progress = _exports(tmp_path, ct, coords=((0, 0, 0),))
    capture = sessions._capture_tiff

    def capture_then_touch(path, *args):
        result = capture(path, *args)
        os.utime(path, ns=(1, 1))  # same bytes, a new modification time
        return result

    monkeypatch.setattr(sessions, "_capture_tiff", capture_then_touch)
    with pytest.raises(ValueError, match="changed during verification"):
        _verify(tmp_path, progress, ct)


def test_an_approved_count_of_true_is_not_the_number_one(tmp_path):
    ct = _ct()
    progress = _exports(tmp_path, ct, coords=((0, 0, 0),))
    progress["metadata"]["total_approved"] = (
        True  # equal to 1, but not an integer count
    )
    with pytest.raises(ValueError, match="differs from progress log"):
        _verify(tmp_path, progress, ct)


def test_a_tiled_page_is_refused_even_when_one_tile_is_the_whole_page(tmp_path):
    # 16-pixel tiles on a 16-pixel patch: the tile's bytes match an untiled page's, so only the tiling tells
    edge = 16
    ct = _CT(
        np.random.default_rng(6).integers(0, 255, (16, 16, 16), dtype=np.uint8),
        chunks=(16, 16, 16),
    )
    (tmp_path / "imagesTr").mkdir()
    (tmp_path / "labelsTr").mkdir()
    tifffile.imwrite(
        tmp_path / "imagesTr" / "z0_y0_x0_0000.tif", ct.data, tile=(16, 16)
    )
    tifffile.imwrite(
        tmp_path / "labelsTr" / "z0_y0_x0.tif", np.ones((edge,) * 3, np.uint8)
    )
    entry = {
        "status": "approved",
        "coords": [0, 0, 0],
        "percentage": 50.0,
        "index": 0,
        "date_processed": "d",
    }
    listed = {"volume_index": 0, "coords": [0, 0, 0], "percentage": 50.0, "index": 0, "date_processed": "d",
              "image_filename": "z0_y0_x0_0000.tif", "label_filename": "z0_y0_x0.tif", "patch_size": edge}  # fmt: skip
    progress = {
        "progress_log": [entry],
        "metadata": {"total_approved": 1},
        "approved_patches": [listed],
    }
    with pytest.raises(ValueError, match="invalid or incomplete proofreader TIFF data"):
        sessions._verify_exports(
            tmp_path, progress, ct, {"patch_size": edge}, sessions.limits()
        )


# --- the edited-label Zarr check without Villa: _verify_exports directly, and verify_record on a session written here
# with a stand-in proofreader file. The tests above that run the pinned writer need Villa's source.


def _edited_store(
    root, ct, crops=((0, 0, 0), (8, 8, 0)), value=1, chunk_shape=(8, 8, 8), **header
):
    """An edited-label Zarr holding `value` in each approved crop, then `header` written into its .zarray."""
    path = root / "edited_labels.zarr"
    array = zarr.open_array(
        str(path),
        mode="w",
        shape=ct.shape,
        chunks=chunk_shape,
        dtype="u1",
        fill_value=0,
    )
    for z, y, x in crops:
        array[z : z + EDGE, y : y + EDGE, x : x + EDGE] = value
    if header:
        meta = json.loads((path / ".zarray").read_text())
        for key, new in header.items():
            if new is None:
                del meta[key]
            else:
                meta[key] = new
        (path / ".zarray").write_text(json.dumps(meta))
    return path


def _verify_edited(root, progress, ct, path, **budget):
    return sessions._verify_exports(
        root,
        progress,
        ct,
        {"patch_size": EDGE},
        sessions.limits(**budget),
        edited_label_path=path,
    )


def test_approved_labels_equal_to_the_edited_zarr_crops_are_reported(tmp_path):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    report = _verify_edited(tmp_path, progress, ct, _edited_store(tmp_path, ct))
    assert report["pairs_verified"] == 2
    assert report["edited_labels"] == {
        "path": "edited_labels.zarr", "shape_zyx": [16, 16, 16], "dtype": "uint8", "approved_crops_verified": 2,
    }  # fmt: skip


@pytest.mark.parametrize(
    ("crops", "flip", "where"),
    [
        (
            ((0, 0, 0), (8, 8, 0)),
            (15, 15, 7),
            "[8, 8, 0]",
        ),  # one voxel of the second crop differs
        (
            ((0, 0, 0), (0, 8, 8)),
            None,
            "[8, 8, 0]",
        ),  # the store holds the crop at Z and X swapped
    ],
)
def test_an_approved_label_that_differs_from_the_edited_zarr_at_its_logged_coordinates_is_refused(
    tmp_path, crops, flip, where
):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    path = _edited_store(tmp_path, ct, crops=crops)
    if flip:
        zarr.open_array(str(path), mode="r+")[flip] = 2
    with pytest.raises(ValueError) as refused:
        _verify_edited(tmp_path, progress, ct, path)
    assert (
        str(refused.value)
        == f"approved label TIFF differs from edited-label Zarr at {where}"
    )


@pytest.mark.parametrize(
    ("arrange", "budget", "message"),
    [
        ("missing", {}, "missing edited-label Zarr"),
        ("linked", {}, "edited-label Zarr must be a nonsymlink directory"),
        ("group", {}, "edited-label Zarr must be a bare Zarr v2 array"),
        ("no_chunks", {}, "invalid edited-label Zarr metadata"),
        ("shape", {}, "must match the CT shape"),
        ("dtype", {}, "with uint8 labels"),
        ("fill_value", {}, "and zero fill"),
        ("chunk_rank", {}, "invalid edited-label Zarr chunk geometry"),
        ("zero_chunk", {}, "invalid edited-label Zarr chunk geometry"),
        (
            "big_chunks",
            {"max_file_bytes": 16**3 - 1},
            "decoded edited-label Zarr chunk exceeds max_file_bytes",
        ),
        (
            "many_files",
            {"max_entries": 6},
            "proofreader source exceeds max_entries",
        ),  # the exports need just 6
    ],
)
def test_an_edited_zarr_that_is_not_a_bounded_bare_uint8_array_of_the_ct_shape_is_refused_before_any_crop(
    tmp_path, monkeypatch, arrange, budget, message
):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    path = tmp_path / "edited_labels.zarr"
    if arrange == "linked":
        _edited_store(tmp_path / "elsewhere", ct)
        path.symlink_to(
            tmp_path / "elsewhere" / "edited_labels.zarr", target_is_directory=True
        )
    elif arrange == "group":
        zarr.open_group(str(path), mode="w").create_dataset(
            "0", shape=ct.shape, chunks=(8, 8, 8), dtype="u1"
        )
    elif arrange != "missing":
        header = {"no_chunks": {"chunks": None}, "shape": {"shape": [16, 16, 17]}, "dtype": {"dtype": "<u2"},
                  "fill_value": {"fill_value": 1}, "chunk_rank": {"chunks": [8, 8]},
                  "zero_chunk": {"chunks": [0, 8, 8]}}.get(arrange, {})  # fmt: skip
        every = [
            (z, y, x) for z in (0, 8) for y in (0, 8) for x in (0, 8)
        ]  # a chunk file for each crop
        _edited_store(tmp_path, ct, crops=every if arrange == "many_files" else ((0, 0, 0), (8, 8, 0)),
                      chunk_shape=(16, 16, 16) if arrange == "big_chunks" else (8, 8, 8), **header)  # fmt: skip
    monkeypatch.setattr(
        sessions, "_capture_tiff", lambda *a: pytest.fail("a crop was read")
    )
    with pytest.raises(ValueError, match=message):
        _verify_edited(tmp_path, progress, ct, path, **budget)


def test_an_edited_chunk_exactly_at_the_file_limit_is_read(tmp_path):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    path = _edited_store(tmp_path, ct, chunk_shape=(16, 16, 16))
    assert (
        _verify_edited(tmp_path, progress, ct, path, max_file_bytes=16**3)[
            "pairs_verified"
        ]
        == 2
    )


def test_a_log_with_no_approvals_still_needs_a_compatible_edited_zarr(tmp_path):
    ct = _ct()
    progress = {
        "progress_log": [],
        "metadata": {"total_approved": 0},
        "approved_patches": [],
    }
    with pytest.raises(ValueError, match="missing edited-label Zarr"):
        _verify_edited(tmp_path, progress, ct, tmp_path / "edited_labels.zarr")
    path = _edited_store(tmp_path, ct, crops=())
    assert (
        _verify_edited(tmp_path, progress, ct, path)["edited_labels"][
            "approved_crops_verified"
        ]
        == 0
    )


def test_an_edited_zarr_that_changes_while_its_crops_are_read_is_refused(
    tmp_path, monkeypatch
):
    ct = _ct()
    progress = _exports(tmp_path, ct)
    path = _edited_store(tmp_path, ct)
    capture = sessions._capture_tiff

    def capture_then_edit(file, edge, limit, role):
        result = capture(file, edge, limit, role)
        if role == "label":
            (path / ".zattrs").write_text('{"edited": true}')
        return result

    monkeypatch.setattr(sessions, "_capture_tiff", capture_then_edit)
    with pytest.raises(
        ValueError, match="edited-label Zarr changed during export verification"
    ):
        _verify_edited(tmp_path, progress, ct, path)


def _session_without_villa(tmp_path):
    """A receipt bound to a stand-in proofreader file, one approved pair at (0, 8, 0) and the edited store."""
    ct, labels = tmp_path / "ct.zarr", tmp_path / "labels.zarr"
    for path, dtype, value in ((ct, "u2", 7), (labels, "u1", 1)):
        zarr.open(
            str(path), mode="w", shape=(8, 16, 16), chunks=(4, 8, 8), dtype=dtype
        )[:] = value
    proofreader = tmp_path / "pinned_proofreader.txt"
    proofreader.write_text("a stand-in for the pinned source")
    root = (tmp_path / "session").resolve()
    root.mkdir()
    config = sessions.recorded_config(ct, labels, root, EDGE)
    sessions.create_record(config, proofreader, sessions.DEFAULT_LIMITS)
    (root / "imagesTr").mkdir()
    (root / "labelsTr").mkdir()
    tifffile.imwrite(
        root / "imagesTr" / "z0_y8_x0_0000.tif", np.full((EDGE,) * 3, 7, np.uint16)
    )
    tifffile.imwrite(
        root / "labelsTr" / "z0_y8_x0.tif", np.full((EDGE,) * 3, 42, np.uint8)
    )
    edited = zarr.open_array(
        config["output_label_zarr"],
        mode="w",
        shape=(8, 16, 16),
        chunks=(8, 8, 8),
        dtype="u1",
    )
    edited[0:8, 8:16, 0:8] = 42
    entry = {
        "index": 2,
        "coords": [0, 8, 0],
        "percentage": 100.0,
        "status": "approved",
        "date_processed": "d",
    }
    selected = config["volumes"]["Autoresearch_Prediction"]
    progress = {
        "metadata": {"patch_size": EDGE, "volume_selection": "Autoresearch_Prediction",
                     "image_zarr": selected["volume_path"], "label_zarr": selected["label_path"],
                     "volume_shape": [8, 16, 16], "coordinate_system": "highest_resolution",
                     "dataset_out_path": str(root), "images_out_dir": str(root / "imagesTr"),
                     "labels_out_dir": str(root / "labelsTr"), "total_approved": 1},
        "progress_log": [entry],
        "approved_patches": [{"volume_index": 0, "coords": [0, 8, 0], "percentage": 100.0, "index": 2,
                              "date_processed": "d", "image_filename": "z0_y8_x0_0000.tif",
                              "label_filename": "z0_y8_x0.tif", "patch_size": EDGE}],
    }  # fmt: skip
    (root / "progress.json").write_text(json.dumps(progress))
    return root, proofreader, labels


@pytest.mark.parametrize("verify_exports", [False, True])
@pytest.mark.parametrize("file", ["receipt", "proofreader"])
def test_late_receipt_or_proofreader_change_refuses_verification(
    tmp_path, monkeypatch, verify_exports, file
):
    root, proofreader, _ = _session_without_villa(tmp_path)
    changed = root / sessions.RECORD_NAME if file == "receipt" else proofreader
    original = sessions.capture_bytes

    def capture(path, limit):
        result = original(path, limit)
        if Path(path) == root / sessions.PROGRESS_NAME:
            changed.write_bytes(changed.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(sessions, "capture_bytes", capture)
    diagnostic = (
        "proofreader input record" if file == "receipt" else "pinned proofreader source"
    )
    with pytest.raises(ValueError, match=f"{diagnostic} changed during"):
        sessions.verify_record(
            root,
            proofreader,
            sessions.DEFAULT_LIMITS,
            verify_approved_patches=verify_exports,
        )


@pytest.mark.parametrize(("patches", "edited"), [(False, True), (True, False)])
def test_the_edited_label_check_alone_also_checks_the_pairs_and_says_so_in_its_scope(
    tmp_path, patches, edited
):
    root, proofreader, _ = _session_without_villa(tmp_path)
    report = sessions.verify_record(root, proofreader, sessions.DEFAULT_LIMITS, verify_approved_patches=patches,
                                    verify_edited_labels=edited)  # fmt: skip
    exports = report["progress"]["approved_exports"]
    assert (
        report["approved_patch_files_verified"] is True
        and exports["pairs_verified"] == 1
    )
    assert ("edited_labels" in exports) is edited
    assert (
        report["scope"].endswith(
            " Edited-label Zarr values match within approved crops."
        )
        is edited
    )
    if edited:
        assert exports["edited_labels"]["approved_crops_verified"] == 1


@pytest.mark.parametrize("role", ["ct", "labels"])
def test_a_source_that_changes_while_the_edited_crops_are_read_is_named(
    tmp_path, monkeypatch, role
):
    root, proofreader, labels = _session_without_villa(tmp_path)
    source = tmp_path / ("ct.zarr" if role == "ct" else "labels.zarr")
    capture = sessions._capture_tiff

    def capture_then_touch(file, edge, limit, kind):
        result = capture(file, edge, limit, kind)
        if kind == "label":
            (source / ".zattrs").write_text('{"touched": true}')
        return result

    monkeypatch.setattr(sessions, "_capture_tiff", capture_then_touch)
    name = "CT" if role == "ct" else "labels"
    with pytest.raises(
        ValueError, match=f"recorded {name} changed during export verification"
    ):
        sessions.verify_record(
            root, proofreader, sessions.DEFAULT_LIMITS, verify_edited_labels=True
        )


@pytest.mark.parametrize(
    "text", ["{not json", "[]", "null", '{"zarr_format": 2, "shape": "x"}']
)
def test_unreadable_edited_zarr_metadata_is_refused_with_the_checkers_own_error(
    tmp_path, monkeypatch, text
):
    """A .zarray that is not JSON, or not a JSON object, is refused as invalid metadata with its path: never an
    AttributeError, which the checker's command line does not catch, nor a parser message without the path."""
    ct = _ct()
    progress = _exports(tmp_path, ct)
    path = _edited_store(tmp_path, ct)
    (path / ".zarray").write_text(text)
    monkeypatch.setattr(
        sessions, "_capture_tiff", lambda *a: pytest.fail("a crop was read")
    )
    with pytest.raises(ValueError) as refused:
        _verify_edited(tmp_path, progress, ct, path)
    assert str(refused.value) == f"invalid edited-label Zarr metadata: {path}"
