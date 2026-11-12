"""Experiment outputs must preserve active inputs and the loop's state."""

from types import SimpleNamespace

import pytest

from scripts.training.checkpoint_paths import (
    validate_checkpoint_writes,
    validate_training_checkpoint_writes,
)


def config(output, **changes):
    return SimpleNamespace(
        **{
            "checkpoint_out": output,
            "uris": ["train/volume.zarr"],
            "val_uri": "val/volume.zarr",
            "use_uamt": False,
            "unlabeled_uris": [],
            "pseudo_label_dir": "pseudo",
            "foundation_model_path": "foundation.pt",
            "eval_every_steps": 0,
            **changes,
        }
    )


@pytest.mark.parametrize(
    "name",
    [
        "best_model.pt",
        "last_model.pt",
        "config.json",
        "run_result.json",
        "autoresearch.lock",
    ],
)
def test_reserved_loop_paths_are_refused_before_any_directory_is_created(
    tmp_path, name
):
    with pytest.raises(ValueError, match="artifact collision"):
        validate_checkpoint_writes([name], base_dir=tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("alias", ["symlink", "hardlink"])
def test_loop_checkpoint_aliases_preserve_the_incumbent(tmp_path, alias):
    incumbent = tmp_path / "best_model.pt"
    incumbent.write_bytes(b"original checkpoint")
    output = tmp_path / "trial.pt"
    if alias == "symlink":
        output.symlink_to(incumbent)
    else:
        output.hardlink_to(incumbent)
    with pytest.raises(ValueError):
        validate_checkpoint_writes([output], base_dir=tmp_path)
    assert incumbent.read_bytes() == b"original checkpoint"


@pytest.mark.parametrize(
    "target",
    [
        "train/volume.zarr/0.0.0",
        "val/volume.zarr/.zarray",
        "train/inklabels.png",
        "val/inklabels_refined.png",
        "train/mask.png",
        "val/patches.json",
        "pseudo/train_pseudo.png",
        "foundation.pt",
        "experiment.json",
    ],
)
def test_named_inputs_are_protected_without_reading_their_contents(tmp_path, target):
    output = tmp_path / target
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"input must stay unchanged")
    with pytest.raises(ValueError, match="artifact collision"):
        validate_training_checkpoint_writes(
            config(target), config_path="experiment.json", base_dir=tmp_path
        )
    assert output.read_bytes() == b"input must stay unchanged"


def test_ordinary_checkpoint_replacement_and_default_loop_mode_are_allowed(tmp_path):
    (tmp_path / "trial.pt").write_bytes(b"old experiment")
    validate_training_checkpoint_writes(config("trial.pt"), base_dir=tmp_path)
    validate_training_checkpoint_writes(config(None), base_dir=tmp_path)
    assert (tmp_path / "trial.pt").read_bytes() == b"old experiment"


@pytest.mark.parametrize("role", ["training", "validation"])
@pytest.mark.parametrize("name", ["inklabels.png", "mask.png", "patches.json"])
def test_volume_symlink_keeps_annotation_paths_at_the_visible_parent(
    tmp_path, role, name
):
    real = tmp_path / "source/ct.zarr"
    real.mkdir(parents=True)
    visible = tmp_path / role
    visible.mkdir()
    alias = visible / "volume.zarr"
    alias.symlink_to(real, target_is_directory=True)
    target = visible / name
    target.write_bytes(b"visible training input")
    selected = config(
        str(target),
        **({"uris": [str(alias)]} if role == "training" else {"val_uri": str(alias)}),
    )
    with pytest.raises(ValueError, match="artifact collision"):
        validate_training_checkpoint_writes(selected, base_dir=tmp_path)
    assert target.read_bytes() == b"visible training input"


def test_uri_like_local_ct_tree_cannot_be_overwritten(tmp_path):
    volume = tmp_path / "scan:training.zarr"
    volume.mkdir()
    output = volume / "chunk"
    output.write_bytes(b"original CT chunk")
    with pytest.raises(ValueError, match="artifact collision"):
        validate_training_checkpoint_writes(
            config(str(output), uris=[volume.name]), base_dir=tmp_path
        )
    assert output.read_bytes() == b"original CT chunk"


def test_relative_checkout_base_protects_the_actual_annotation_path(
    tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    (root / "train/volume.zarr").mkdir(parents=True)
    label = root / "train/inklabels.png"
    label.write_bytes(b"original labels")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        validate_training_checkpoint_writes(
            config("train/inklabels.png"), base_dir="repo"
        )
    validate_training_checkpoint_writes(config("trials/candidate.pt"), base_dir="repo")
    assert label.read_bytes() == b"original labels"
    assert not (root / "trials").exists()


@pytest.mark.parametrize(
    "name",
    [
        "cycles.jsonl",
        "config_temp.json",
        ".current_day_shift_log",
        "autoresearch.out",
        "run.log",
        ".best_model.pt.held",
        "sprint_logs/shift.md",
    ],
)
def test_experiment_cannot_replace_loop_journals_logs_or_recovery_files(tmp_path, name):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"loop state")
    with pytest.raises(ValueError, match="artifact collision"):
        validate_checkpoint_writes([path], base_dir=tmp_path)
    assert path.read_bytes() == b"loop state"


@pytest.mark.parametrize("step", [None, 4])
def test_curve_and_step_artifacts_cannot_replace_foundation_inputs(tmp_path, step):
    source = "trial.pt.curve.csv" if step is None else "trial.pt.step4.pt"
    selected = config("trial.pt", eval_every_steps=4, foundation_model_path=source)
    with pytest.raises(ValueError, match="artifact collision"):
        validate_training_checkpoint_writes(selected, step=step, base_dir=tmp_path)
    assert not list(tmp_path.iterdir())


def test_remote_ct_is_not_opened_and_local_outputs_are_required(tmp_path):
    selected = config(
        "trials/model.pt", uris=["s3://bucket/train"], val_uri="s3://bucket/val"
    )
    validate_training_checkpoint_writes(selected, base_dir=tmp_path)
    with pytest.raises(ValueError, match="local filesystem"):
        validate_checkpoint_writes(["s3://bucket/output.pt"], base_dir=tmp_path)
    assert not list(tmp_path.iterdir())
