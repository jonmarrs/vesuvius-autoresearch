"""Held-out volume guards work without arrays, ML imports, or source mutation."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from scripts.training.data_split import validate_training_split


def config(**changes):
    return SimpleNamespace(
        **{
            "uris": ["train.zarr"],
            "val_uri": "val.zarr",
            "use_uamt": False,
            "unlabeled_uris": [],
            **changes,
        }
    )


@pytest.mark.parametrize(
    "spelling", ["exact", "dots", "absolute", "child", "parent", "symlink", "file_uri"]
)
def test_labeled_validation_aliases_are_refused_before_reading_data(tmp_path, spelling):
    validation = tmp_path / "val.zarr"
    (validation / "0").mkdir(parents=True)
    (tmp_path / "alias.zarr").symlink_to(validation, target_is_directory=True)
    selected = {
        "exact": "val.zarr",
        "dots": "./missing/../val.zarr/",
        "absolute": str(validation),
        "child": "val.zarr/0",
        "parent": str(tmp_path),
        "symlink": "alias.zarr",
        "file_uri": validation.as_uri(),
    }[spelling]
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    with pytest.raises(ValueError, match=r"training\[0\] overlaps val_uri"):
        validate_training_split(config(uris=[selected]), base_dir=tmp_path)
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before


def test_active_uamt_alias_is_refused_without_mutating_the_configuration(tmp_path):
    selected = config(use_uamt=True, unlabeled_uris=["train.zarr", "./val.zarr/"])
    before = deepcopy(vars(selected))
    with pytest.raises(ValueError, match=r"unlabeled\[1\] overlaps val_uri"):
        validate_training_split(selected, base_dir=tmp_path)
    assert vars(selected) == before


def test_uamt_can_share_training_inputs_and_inactive_inputs_are_ignored(tmp_path):
    for selected in [
        config(use_uamt=True, unlabeled_uris=["train.zarr"]),
        config(use_uamt=False, unlabeled_uris=["val.zarr"]),
    ]:
        validate_training_split(selected, base_dir=tmp_path)


def test_hard_linked_file_identifiers_are_observable_aliases(tmp_path):
    # No array decoding: only inode identity. Does not certify chunk-tree copies.
    validation = tmp_path / "val.zarr"
    validation.write_bytes(b"stat only")
    (tmp_path / "train.zarr").hardlink_to(validation)
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(config(), base_dir=tmp_path)


@pytest.mark.parametrize(
    "training", ["s3://bucket/val", "s3://bucket/val/", "s3://bucket/val/0/"]
)
def test_identical_remote_resources_are_refused_without_network(training):
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(config(uris=[training], val_uri="s3://bucket/val"))


def test_distinct_remote_addresses_remain_unverified_without_network():
    validate_training_split(
        config(uris=["s3://bucket/train"], val_uri="s3://bucket/val")
    )


def test_relative_paths_use_the_explicit_checkout_not_the_callers_cwd(
    tmp_path, monkeypatch
):
    inspected, caller = tmp_path / "inspected", tmp_path / "caller"
    inspected.mkdir()
    caller.mkdir()
    (inspected / "alias").symlink_to(inspected / "val.zarr")
    monkeypatch.chdir(caller)
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(config(uris=["alias"]), base_dir=inspected)
    validate_training_split(config(uris=["alias"]), base_dir=caller)


@pytest.mark.parametrize(
    "changes",
    [
        {"uris": []},
        {"uris": "train.zarr"},
        {"uris": [None]},
        {"val_uri": ""},
        {"use_uamt": True, "unlabeled_uris": "val.zarr"},
    ],
)
def test_malformed_active_inputs_fail_before_readers(changes):
    with pytest.raises(ValueError):
        validate_training_split(config(**changes))
