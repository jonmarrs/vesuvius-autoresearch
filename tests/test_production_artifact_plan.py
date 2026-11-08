"""Production artifact paths must not replace model or source-volume inputs."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import torch
import zarr
from test_production_predict import production_fixture

from scripts import production_artifacts, production_predict as production

BASE = "prod_pred_1_2_3_13x11"


def _tree(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("source", ["volume", "checkpoint"])
def test_production_refuses_output_paths_that_replace_inputs(
    tmp_path, monkeypatch, source
):
    out, argv, model = production_fixture(tmp_path, monkeypatch)
    out.mkdir()
    if source == "volume":
        volume = out / f"{BASE}.zarr"
        group = zarr.open_group(str(volume), mode="w")
        group.create_dataset("0", shape=(5, 20, 24), dtype="u1")[:] = 128
        argv[argv.index("--uri") + 1] = str(volume)
    else:
        checkpoint = out / f"{BASE}_meta.json"
        Path(argv[argv.index("--checkpoint") + 1]).rename(checkpoint)
        argv[argv.index("--checkpoint") + 1] = str(checkpoint)
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        production.production_predict()
    assert _tree(tmp_path) == before
    assert model.batches == []


def test_production_metadata_identifies_the_loaded_checkpoint_bytes(
    tmp_path, monkeypatch
):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    checkpoint = Path(argv[argv.index("--checkpoint") + 1])
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    production.production_predict()
    metadata = json.loads(next(out.glob("*_meta.json")).read_text())
    assert metadata["checkpoint_sha256"] == digest
    assert metadata["checkpoint_size_bytes"] == checkpoint.stat().st_size


def _set(argv, option, value):
    argv[argv.index(option) + 1] = str(value)


def _ome_volume(path):
    group = zarr.open_group(str(path), mode="w")
    group.create_dataset("0", shape=(5, 20, 24), dtype="u1")[:] = 128


@pytest.mark.parametrize("ome", [False, True])
def test_dry_run_is_json_without_model_voxel_reads_or_writes(
    tmp_path, monkeypatch, capsys, ome
):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    if ome:
        source = tmp_path / "ome.zarr"
        _ome_volume(source)
        _set(argv, "--uri", source.as_uri())
    argv.extend(["--dry-run", "--artifact-stem", "comparison"])

    def forbidden(*args, **kwargs):
        pytest.fail("dry run must not construct a model, probe CUDA or read voxels")

    monkeypatch.setattr(production, "build_prediction_model", forbidden)
    monkeypatch.setattr(torch.cuda, "is_available", forbidden)
    monkeypatch.setattr(production.FastVesuviusVolume, "read_ct", forbidden)
    monkeypatch.setattr(production.FastVesuviusVolume, "get_raw_patch", forbidden)
    monkeypatch.setattr(production, "tile_starts", forbidden)
    before = _tree(tmp_path)
    result = production.production_predict()
    assert json.loads(capsys.readouterr().out) == result
    assert result["tiles_total"] == 6
    assert result["artifact_stem"] == "comparison"
    assert result["outputs"] == {
        "ink_zarr": str(out / "comparison.zarr"),
        "metadata": str(out / "comparison_meta.json"),
    }
    assert result["source_shape_zyx"] == [5, 20, 24]
    assert result["voxel_size_um"] == 2.0
    assert result["model_config"]["patch_size"] == 8
    assert result["model_weights_verified"] is False
    assert result["voxel_data_verified"] is False
    assert result["inference_performed"] is False
    assert _tree(tmp_path) == before
    assert not out.exists()


def test_dry_run_large_geometry_does_not_allocate_tile_lists(tmp_path, monkeypatch):
    _, argv, _ = production_fixture(tmp_path, monkeypatch)
    _set(argv, "--width", 10**10)
    _set(argv, "--height", 10**10)
    argv.append("--dry-run")

    class MetadataOnly:
        shape = (5, 10**11, 10**11)

        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(production, "FastVesuviusVolume", MetadataOnly)
    monkeypatch.setattr(production, "tile_starts", lambda *a: pytest.fail("tile list"))
    result = production.production_predict()
    assert result["tiles_total"] == (2_499_999_999) ** 2


def test_artifact_stems_keep_comparisons_separate(tmp_path, monkeypatch):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    production.production_predict()
    before = _tree(out)
    argv.extend(["--artifact-stem", "candidate"])
    production.production_predict()
    assert (out / "candidate.zarr" / "0").is_dir()
    metadata = json.loads((out / "candidate_meta.json").read_text())
    assert metadata["artifact_stem"] == "candidate"
    for path, data in before.items():
        assert (out / path).read_bytes() == data


@pytest.mark.parametrize("stem", ["../ct", "nested/name", "", "bad\nname"])
def test_bad_stem_fails_before_checkpoint_load(tmp_path, monkeypatch, stem):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    argv.extend(["--artifact-stem", stem])
    monkeypatch.setattr(torch, "load", lambda *a, **k: pytest.fail("checkpoint load"))
    with pytest.raises(ValueError, match="artifact_stem"):
        production.production_predict()
    assert not out.exists()


@pytest.mark.parametrize("alias", ["file_uri", "source_symlink", "output_symlink"])
def test_volume_aliases_cannot_hide_an_output_collision(tmp_path, monkeypatch, alias):
    out, argv, model = production_fixture(tmp_path, monkeypatch)
    out.mkdir()
    source = out / f"{BASE}.zarr"
    _ome_volume(source)
    if alias == "file_uri":
        _set(argv, "--uri", source.as_uri())
    elif alias == "source_symlink":
        link = tmp_path / "ct_alias.zarr"
        link.symlink_to(source, target_is_directory=True)
        _set(argv, "--uri", link)
    else:
        actual_source = Path(argv[argv.index("--uri") + 1])
        # The output root itself aliases an input volume; no traversal is needed.
        _set(argv, "--uri", source)
        _set(argv, "--out-dir", actual_source)
        (actual_source / f"{BASE}.zarr").symlink_to(source, target_is_directory=True)
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        production.production_predict()
    assert _tree(tmp_path) == before
    assert not model.batches


def test_external_ome_level_cannot_alias_an_output_array(tmp_path, monkeypatch):
    out, argv, model = production_fixture(tmp_path, monkeypatch)
    source = Path(argv[argv.index("--uri") + 1])
    dest = out / f"{BASE}.zarr"
    dest.mkdir(parents=True)
    source.rename(dest / "0")
    source.mkdir()
    (source / "0").symlink_to(dest / "0", target_is_directory=True)
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        production.production_predict()
    assert _tree(tmp_path) == before
    assert not model.batches


@pytest.mark.parametrize(
    "target,kind",
    [
        ("metadata", "symlink"),
        ("metadata", "hardlink"),
        ("zarr", "symlink"),
        ("nested", "symlink"),
        ("nested", "hardlink"),
        ("nested", "fifo"),
    ],
)
def test_existing_output_links_and_special_entries_fail_before_inference(
    tmp_path, monkeypatch, target, kind
):
    out, _, model = production_fixture(tmp_path, monkeypatch)
    out.mkdir()
    unrelated = tmp_path / "unrelated"
    unrelated.write_bytes(b"preserve this file")
    dest = out / f"{BASE}_meta.json"
    if target in {"zarr", "nested"}:
        dest = out / f"{BASE}.zarr"
        if target == "nested":
            dest = dest / "0" / "chunk"
            dest.parent.mkdir(parents=True)
    if kind == "symlink":
        dest.symlink_to(unrelated)
    elif kind == "hardlink":
        os.link(unrelated, dest)
    else:
        os.mkfifo(dest)
    with pytest.raises(ValueError, match="nonsymlink"):
        production.production_predict()
    assert unrelated.read_bytes() == b"preserve this file"
    assert not model.batches


def test_existing_output_inspection_has_an_entry_limit(tmp_path, monkeypatch):
    out, _, model = production_fixture(tmp_path, monkeypatch)
    dest = out / f"{BASE}.zarr"
    dest.mkdir(parents=True)
    for name in ("one", "two"):
        (dest / name).write_bytes(b"original")
    monkeypatch.setattr(production_artifacts, "MAX_OUTPUT_ENTRIES", 1)
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="exceeds 1 entries"):
        production.production_predict()
    assert _tree(tmp_path) == before
    assert not model.batches


def test_output_plan_is_rechecked_after_inference(tmp_path, monkeypatch):
    out, argv, model = production_fixture(tmp_path, monkeypatch)
    source = Path(argv[argv.index("--uri") + 1])
    original_forward = model.forward

    def changed(x):
        out.mkdir(exist_ok=True)
        dest = out / f"{BASE}.zarr"
        if not dest.is_symlink():
            dest.symlink_to(source, target_is_directory=True)
        return original_forward(x)

    monkeypatch.setattr(model, "forward", changed)
    before = _tree(source)
    with pytest.raises(ValueError, match="artifact collision"):
        production.production_predict()
    assert _tree(source) == before
    assert model.batches
    assert not (out / f"{BASE}_meta.json").exists()


def test_metadata_hash_describes_captured_checkpoint_despite_later_replacement(
    tmp_path, monkeypatch
):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    checkpoint = Path(argv[argv.index("--checkpoint") + 1])
    original = checkpoint.read_bytes()
    load = torch.load

    def replace_after_capture(*args, **kwargs):
        checkpoint.write_bytes(b"later checkpoint bytes")
        return load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", replace_after_capture)
    production.production_predict()
    metadata = json.loads((out / f"{BASE}_meta.json").read_text())
    assert metadata["checkpoint_sha256"] == hashlib.sha256(original).hexdigest()
    assert metadata["checkpoint_size_bytes"] == len(original)


@pytest.mark.parametrize("kind", ["oversize", "fifo"])
def test_checkpoint_capture_fails_before_torch_load(tmp_path, monkeypatch, kind):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    if kind == "oversize":
        argv.extend(["--max-checkpoint-bytes", "1"])
    else:
        fifo = tmp_path / "checkpoint.fifo"
        os.mkfifo(fifo)
        _set(argv, "--checkpoint", fifo)
    monkeypatch.setattr(torch, "load", lambda *a, **k: pytest.fail("checkpoint load"))
    with pytest.raises(ValueError, match="exceeds|regular file"):
        production.production_predict()
    assert not out.exists()


@pytest.mark.parametrize("value", ["0", "-1", str(sys.maxsize)])
def test_invalid_capture_limits_fail_as_usage_errors(tmp_path, monkeypatch, value):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    argv.extend(["--max-checkpoint-bytes", value])
    with pytest.raises(SystemExit) as exc:
        production.production_predict()
    assert exc.value.code == 2
    assert not out.exists()


@pytest.mark.parametrize("value", [float("nan"), {"not", "json"}])
def test_config_metadata_must_be_serializable_before_model_work(
    tmp_path, monkeypatch, value
):
    out, argv, model = production_fixture(tmp_path, monkeypatch)
    checkpoint = argv[argv.index("--checkpoint") + 1]
    saved = torch.load(checkpoint, weights_only=False)
    saved["config"]["unrelated_setting"] = value
    torch.save(saved, checkpoint)
    with pytest.raises(ValueError, match="config cannot be recorded as JSON"):
        production.production_predict()
    assert not model.batches
    assert not out.exists()


def test_direct_cli_dry_run_from_external_directory(tmp_path, monkeypatch):
    out, argv, _ = production_fixture(tmp_path, monkeypatch)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(production.__file__).resolve()),
            *argv[1:],
            "--dry-run",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=45,
    )
    plan = json.loads(result.stdout)
    assert plan["status"] == "PLANNED"
    assert plan["tiles_total"] == 6
    assert not out.exists()
