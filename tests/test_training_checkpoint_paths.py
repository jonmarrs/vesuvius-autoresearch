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
