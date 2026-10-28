"""Candidate reuse must reject changed data even when metadata is unchanged."""

import json
from pathlib import Path

import numpy as np
import pytest
import zarr

from scripts import (
    compute_structure_tensors as tensors,
    execute_lasagna_pipeline as pipeline,
)
from scripts.artifact_hashes import sha256_file
from scripts.candidate_artifacts import crop_matches, tensor_matches
from scripts.crop_candidate_zarr import crop_candidate_zarr


def make_crop(tmp_path):
    source, crop = tmp_path / "source.zarr", tmp_path / "crop.zarr"
    zarr.open(str(source), mode="w", shape=(6, 6, 6), chunks=(2, 2, 2), dtype="u1")[
        :
    ] = 7
    crop_candidate_zarr(source, crop, 0, 0, 0, 2, 2, 2)
    assert crop_matches(crop, source, (0, 0, 0), (2, 2, 2))
    return source, crop


def tensor_group(path, shape=(2, 2, 2)):
    root = zarr.open_group(str(path), mode="w")
    root.create_dataset(
        "structure_tensor", shape=(6, *shape), chunks=(6, *shape), dtype="f4"
    )[:] = 1
    for name in ("first_component", "second_component", "normal"):
        for axis in ("z", "y", "x"):
            root.create_dataset(
                f"{name}/{axis}/0", shape=shape, chunks=shape, dtype="u1"
            )[:] = 127
    root.create_dataset("confidence/0", shape=shape, chunks=shape, dtype="u1")[:] = 255
    return root


def make_tensors(tmp_path, monkeypatch, crop):
    script = tmp_path / "fake_upstream.py"
    script.touch()
    monkeypatch.setattr(tensors, "RUN_SCRIPT", script)

    def upstream(command, **kwargs):
        tensor_group(command[command.index("--output_dir") + 1])

    monkeypatch.setattr(tensors.subprocess, "run", upstream)
    output = tmp_path / "tensors.zarr"
    tensors.compute_structure_tensors(crop, output)
    assert tensor_matches(output, crop)
    return output


@pytest.mark.parametrize("change", ["source", "crop", "deleted_chunk"])
def test_crop_reuse_rejects_changed_voxels_or_lost_payload(tmp_path, change):
    source, crop = make_crop(tmp_path)
    target = zarr.open(str(source if change == "source" else crop), mode="r+")
    if change == "deleted_chunk":
        del target.chunk_store[target._chunk_key((0, 0, 0))]
    else:
        target[0, 0, 0] = 9
    assert not crop_matches(crop, source, (0, 0, 0), (2, 2, 2))


@pytest.mark.parametrize("change", ["source", "tensor", "deleted_chunk"])
def test_tensor_reuse_rejects_changed_source_or_output_payload(
    tmp_path, monkeypatch, change
):
    _, crop = make_crop(tmp_path)
    output = make_tensors(tmp_path, monkeypatch, crop)
    if change == "source":
        zarr.open(str(crop), mode="r+")[0, 0, 0] = 9
    else:
        target = zarr.open_group(str(output), mode="r+")["normal/z/0"]
        if change == "deleted_chunk":
            del target.chunk_store[target._chunk_key((0, 0, 0))]
        else:
            target[0, 0, 0] = 9
    assert not tensor_matches(output, crop)


def test_evidence_reuse_rejects_replaced_checkpoint_at_same_path(tmp_path, monkeypatch):
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"first weights")
    metadata = {
        "candidate": {"artifact_stem": "candidate"},
        "checkpoint_path": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
    }
    (tmp_path / "PRIZE_READINESS_REPORT.json").write_text(
        json.dumps({"status": "PASS"})
    )
    (tmp_path / "evidence_metadata.json").write_text(json.dumps(metadata))
    monkeypatch.setattr(pipeline, "validate", lambda path: {"status": "PASS"})
    assert pipeline._evidence_passed(tmp_path, "candidate", checkpoint=checkpoint)
    checkpoint.write_bytes(b"new weights at the same path")
    assert not pipeline._evidence_passed(tmp_path, "candidate", checkpoint=checkpoint)


def test_changes_outside_selected_region_do_not_invalidate_crop(tmp_path):
    source, crop = make_crop(tmp_path)
    zarr.open(str(source), mode="r+")[5, 5, 5] = 9
    assert crop_matches(crop, source, (0, 0, 0), (2, 2, 2))


@pytest.mark.parametrize("artifact", ["crop", "tensor"])
def test_corrupt_encoded_payload_refuses_reuse_without_crashing(
    tmp_path, monkeypatch, artifact
):
    source, crop = make_crop(tmp_path)
    if artifact == "crop":
        array = zarr.open(str(crop), mode="r+")
    else:
        output = make_tensors(tmp_path, monkeypatch, crop)
        array = zarr.open_group(str(output), mode="r+")["normal/z/0"]
    array.chunk_store[array._chunk_key((0, 0, 0))] = b"invalid compressed payload"
    assert not (
        crop_matches(crop, source, (0, 0, 0), (2, 2, 2))
        if artifact == "crop"
        else tensor_matches(output, crop)
    )


def test_hash_is_independent_of_storage_chunk_layout(tmp_path):
    from scripts.candidate_artifacts import array_content_sha256

    data = np.arange(65 * 3 * 3, dtype="u2").reshape(65, 3, 3)
    hashes = []
    for i, chunks in enumerate([(1, 1, 1), (64, 3, 3)]):
        array = zarr.open(
            str(tmp_path / str(i)),
            mode="w",
            shape=data.shape,
            chunks=chunks,
            dtype=data.dtype,
        )
        array[:] = data
        hashes.append(array_content_sha256(array))
    assert hashes[0] == hashes[1]


def test_source_drift_during_crop_preserves_previous_output(tmp_path, monkeypatch):
    source, crop = make_crop(tmp_path)
    original, reads = zarr.Array.__getitem__, []

    def changing(array, selection):
        result = original(array, selection)
        if str(getattr(array.store, "path", "")) == str(source):
            reads.append(selection)
            if len(reads) == 2:
                zarr.open(str(source), mode="r+")[0, 0, 0] = 9
        return result

    monkeypatch.setattr(zarr.Array, "__getitem__", changing)
    with pytest.raises(RuntimeError, match="source region changed"):
        crop_candidate_zarr(source, crop, 0, 0, 0, 2, 2, 2)
    np.testing.assert_array_equal(zarr.open(str(crop), mode="r")[:], 7)
    assert not list(tmp_path.glob(".crop.zarr-*"))


def test_source_voxel_drift_during_tensor_job_preserves_previous_output(
    tmp_path, monkeypatch
):
    _, crop = make_crop(tmp_path)
    output = make_tensors(tmp_path, monkeypatch, crop)
    before = dict(zarr.open_group(str(output), mode="r").attrs)

    def changed(command, **kwargs):
        tensor_group(command[command.index("--output_dir") + 1])
        zarr.open(str(crop), mode="r+")[0, 0, 0] = 9

    monkeypatch.setattr(tensors.subprocess, "run", changed)
    with pytest.raises(RuntimeError, match="source crop changed"):
        tensors.compute_structure_tensors(crop, output)
    assert dict(zarr.open_group(str(output), mode="r").attrs) == before


def verification_setup(tmp_path, monkeypatch):
    source, crop = make_crop(tmp_path)
    output = make_tensors(tmp_path, monkeypatch, crop)
    item = {
        "rank": 0,
        "candidate_index": 0,
        "artifact_stem": "candidate",
        "local_uri": str(source),
        "z": 0,
        "y": 0,
        "x": 0,
        "depth": 2,
        "height": 2,
        "width": 2,
        "cropped_volume_uri": str(crop),
        "structure_tensor_output": str(output),
        "evidence_output_dir": str(tmp_path / "evidence"),
    }
    table = tmp_path / "ranked.tsv"
    table.write_text(f"local_uri\n{source}\n")
    monkeypatch.setattr(pipeline, "build_worklist", lambda *a, **k: [item])
    monkeypatch.setattr(
        pipeline,
        "run_step",
        lambda *a, **k: pytest.fail("verification must not run commands"),
    )
    args = [
        "--verify-only",
        "--ranked",
        str(table),
        "--report",
        str(tmp_path / "report.json"),
    ]
    return source, crop, output, args


def test_verification_only_checks_bytes_without_running_or_modifying_artifacts(
    tmp_path, monkeypatch
):
    source, crop, output, args = verification_setup(tmp_path, monkeypatch)
    before = {
        str(p): (p.read_bytes(), p.stat().st_mtime_ns)
        for directory in (source, crop, output)
        for p in directory.rglob("*")
        if p.is_file()
    }
    report = pipeline.main(args)
    assert report["mode"] == "verify_only" and report["status"] == "PASS"
    assert report["candidates"][0]["stages"] == {
        "crop": "VERIFIED",
        "structure_tensor": "VERIFIED",
    }
    assert {
        str(p): (p.read_bytes(), p.stat().st_mtime_ns)
        for directory in (source, crop, output)
        for p in directory.rglob("*")
        if p.is_file()
    } == before


def test_verification_only_reports_stale_source_without_rebuilding(
    tmp_path, monkeypatch
):
    source, _, _, args = verification_setup(tmp_path, monkeypatch)
    zarr.open(str(source), mode="r+")[0, 0, 0] = 9
    with pytest.raises(SystemExit) as exc:
        pipeline.main(args)
    assert exc.value.code == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["candidates"][0]["stages"]["crop"] == "STALE_OR_MISSING"
    assert report["candidates"][0]["stages"]["structure_tensor"] == "BLOCKED_BY_CROP"


@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
@pytest.mark.parametrize("target", ["ranked", "checkpoint"])
def test_report_aliases_are_rejected_before_input_mutation(
    tmp_path, monkeypatch, alias, target
):
    import os

    _, _, _, args = verification_setup(tmp_path, monkeypatch)
    path = tmp_path / ("ranked.tsv" if target == "ranked" else "model.pt")
    if target == "checkpoint":
        path.write_bytes(b"weights")
    original = path.read_bytes()
    args += ["--checkpoint", str(tmp_path / "model.pt")]
    output = path if alias == "direct" else tmp_path / "alias.json"
    if alias == "symlink":
        output.symlink_to(path)
    elif alias == "hardlink":
        os.link(path, output)
    args[args.index("--report") + 1] = str(output)
    with pytest.raises(SystemExit):
        pipeline.main(args)
    assert path.read_bytes() == original


@pytest.mark.parametrize("kind", ["crop", "tensor"])
def test_legacy_completion_without_fingerprints_requires_recomputation(
    tmp_path, monkeypatch, kind
):
    source, crop = make_crop(tmp_path)
    if kind == "crop":
        array = zarr.open(str(crop), mode="r+")
        array.attrs["candidate_crop_contract"] = 1
        assert not crop_matches(crop, source, (0, 0, 0), (2, 2, 2))
    else:
        output = make_tensors(tmp_path, monkeypatch, crop)
        root = zarr.open_group(str(output), mode="r+")
        record = dict(root.attrs["candidate_tensor_completion"])
        record["contract"] = 1
        root.attrs["candidate_tensor_completion"] = record
        assert not tensor_matches(output, crop)


@pytest.mark.parametrize("kind", ["source", "crop", "tensor"])
def test_report_cannot_replace_artifact_metadata(tmp_path, monkeypatch, kind):
    source, crop, tensor, args = verification_setup(tmp_path, monkeypatch)
    path = {
        "source": source / ".zarray",
        "crop": crop / ".zarray",
        "tensor": tensor / ".zattrs",
    }[kind]
    before = path.read_bytes()
    args[args.index("--report") + 1] = str(path)
    with pytest.raises(SystemExit):
        pipeline.main(args)
    assert path.read_bytes() == before


def test_rebuilt_crop_forces_requested_ct_evidence_to_refresh(tmp_path, monkeypatch):
    source, crop, tensor, _ = verification_setup(tmp_path, monkeypatch)
    item = {
        "rank": 0,
        "candidate_index": 0,
        "artifact_stem": "candidate",
        "local_uri": str(source),
        "z": 0,
        "y": 0,
        "x": 0,
        "depth": 2,
        "height": 2,
        "width": 2,
        "cropped_volume_uri": str(crop),
        "structure_tensor_output": str(tensor),
        "evidence_output_dir": str(tmp_path / "evidence"),
        "crop_command": "python crop.py",
        "structure_tensor_command": "python tensors.py",
        "evidence_command": "python evidence.py --checkpoint old",
    }
    checks = iter([False, True])
    monkeypatch.setattr(pipeline, "crop_matches", lambda *a: next(checks))
    monkeypatch.setattr(pipeline, "_structure_tensor_complete", lambda *a: True)
    monkeypatch.setattr(pipeline, "_evidence_passed", lambda *a: True)
    calls = []

    def successful(name, *args):
        calls.append(name)
        return True

    monkeypatch.setattr(pipeline, "run_step", successful)
    report = pipeline.process_candidate(item, with_evidence=True)
    assert report["status"] == "PASS"
    assert calls == ["Crop", "CT evidence"]
