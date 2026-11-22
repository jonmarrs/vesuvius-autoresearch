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


@pytest.mark.parametrize("name", ["scan:heldout.zarr", "s3://bucket/heldout.zarr"])
@pytest.mark.parametrize("role", ["training", "validation"])
def test_existing_local_names_take_precedence_over_uri_parsing(tmp_path, name, role):
    volume = tmp_path / name
    volume.mkdir(parents=True)
    local, alias = name, str(volume.resolve())
    selected = config(
        uris=[local if role == "training" else alias],
        val_uri=alias if role == "training" else local,
    )
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(selected, base_dir=tmp_path)


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


def test_a_file_uri_is_local_only_on_this_host(tmp_path):
    validation = tmp_path / "val.zarr"
    validation.mkdir()
    with pytest.raises(ValueError, match=r"training\[0\] overlaps val_uri"):
        validate_training_split(
            config(uris=[f"file://localhost{validation}"]), base_dir=tmp_path
        )
    # Another host's file is a remote address, which a local path cannot be compared with.
    validate_training_split(
        config(uris=[f"file://otherhost{validation}"]), base_dir=tmp_path
    )


@pytest.mark.parametrize("suffix", ["?version=2", "#part"])
def test_a_local_file_uri_with_a_query_or_fragment_is_refused(tmp_path, suffix):
    validation = tmp_path / "val.zarr"
    validation.mkdir()
    with pytest.raises(ValueError, match="query or fragment"):
        validate_training_split(
            config(uris=[validation.as_uri() + suffix]), base_dir=tmp_path
        )


def test_a_percent_encoded_file_uri_is_the_path_it_spells(tmp_path):
    validation = tmp_path / "val set.zarr"
    validation.mkdir()
    assert "%20" in validation.as_uri()
    with pytest.raises(ValueError, match=r"training\[0\] overlaps val_uri"):
        validate_training_split(
            config(uris=[validation.as_uri()], val_uri="val set.zarr"),
            base_dir=tmp_path,
        )


def test_a_different_host_stays_unverified_and_the_query_does_not(tmp_path):
    validation = "s3://bucket/val.zarr?versionId=1"
    for other in (
        validation,
        "s3://bucket/val.zarr?versionId=2",
        "s3://bucket/val.zarr",
    ):
        with pytest.raises(ValueError, match=r"training\[0\] overlaps val_uri"):
            validate_training_split(
                config(uris=[other], val_uri=validation), base_dir=tmp_path
            )
    validate_training_split(
        config(uris=["s3://other/val.zarr?versionId=1"], val_uri=validation),
        base_dir=tmp_path,
    )


@pytest.mark.parametrize(
    "training, validation",
    [
        ("s3://bucket/val.zarr/1", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/2/0", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/1", "s3://bucket/val.zarr/0"),
        ("s3://bucket/val.zarr", "s3://bucket/val.zarr/1"),
        ("s3://bucket/val.zarr/1?versionId=1", "s3://bucket/val.zarr?versionId=1"),
        ("s3://bucket/val.zarr/2", "s3://bucket/val.zarr/1"),
        ("s3://bucket/val.zarr/0", "s3://bucket/val.zarr/3"),
        ("s3n://bucket/val.zarr/2", "s3a://Bucket/val.zarr/1"),
    ],
)
def test_a_remote_path_inside_the_held_out_volume_is_refused(training, validation):
    """A pyramid level is the same volume. Local children are already refused."""
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(config(uris=[training], val_uri=validation))


def test_a_remote_name_that_only_shares_a_prefix_stays_unverified():
    validate_training_split(
        config(uris=["s3://bucket/val.zarr-other"], val_uri="s3://bucket/val.zarr")
    )
    validate_training_split(
        config(
            uris=["s3://other/val.zarr/1"],
            val_uri="s3://bucket/val.zarr",
        )
    )
    validate_training_split(
        config(uris=["s3://bucket/Val.zarr"], val_uri="s3://bucket/val.zarr")
    )
    validate_training_split(
        config(uris=["s3://bucket/other.zarr/2"], val_uri="s3://bucket/val.zarr/1")
    )


@pytest.mark.parametrize(
    "training, validation",
    [
        ("s3://bucket/val.zarr#part", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr?x=", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr?sig=abc", "s3://bucket/val.zarr"),
        ("s3://Bucket/val.zarr", "s3://bucket/val.zarr"),
        ("S3://bucket/val.zarr", "s3://bucket/val.zarr"),
        ("s3a://bucket/val.zarr", "s3://bucket/val.zarr"),
        ("s3n://bucket/val.zarr", "s3a://bucket/val.zarr"),
        ("s3://bucket/val.zarr%2F1", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/%2E%2E/val.zarr", "s3://bucket/val.zarr"),
        ("s3://bucket/a/../val.zarr", "s3://bucket/val.zarr"),
        ("https://host:443/val.zarr", "https://host/val.zarr"),
        ("https://HOST/val.zarr?sig=one#part", "https://host/val.zarr"),
    ],
)
def test_normalized_remote_spellings_of_one_volume_are_refused(training, validation):
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(config(uris=[training], val_uri=validation))


def test_a_non_default_port_stays_a_different_endpoint():
    """An explicit non-default port is not the scheme default, including s3."""
    validate_training_split(
        config(uris=["https://host:8443/val.zarr"], val_uri="https://host/val.zarr")
    )
    validate_training_split(
        config(uris=["s3://bucket:443/val.zarr"], val_uri="s3://bucket/val.zarr")
    )


def test_integer_levels_of_the_bucket_root_are_the_same_volume():
    """An all-integer path is a level of the root. A non-integer key is not."""
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(config(uris=["s3://bucket/2"], val_uri="s3://bucket/1"))
    validate_training_split(
        config(uris=["s3://bucket/val.zarr"], val_uri="s3://bucket/1")
    )


@pytest.mark.parametrize(
    "training, validation",
    [
        ("https://host./val.zarr", "https://host/val.zarr"),
        ("http://host/val.zarr", "https://host/val.zarr"),
        ("http://host:80/val.zarr", "https://host:443/val.zarr"),
        ("https://%68ost/val.zarr", "https://host/val.zarr"),
        ("https://host:abc/val.zarr", "https://host/val.zarr"),
        ("s3://bucket/val%252Ezarr", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr%252F1", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr%25252F1", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr%252525252525252F1", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr\\1", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr;params", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/01", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/00", "s3://bucket/val.zarr/0"),
        ("s3://bucket/val.zarr/01", "s3://bucket/val.zarr/1"),
        ("s3://bucket/val.zarr/labels", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/volume", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/volume/0", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/0/c", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/.zarray", "s3://bucket/val.zarr"),
        ("s3://bucket/data", "s3://bucket/data/val.zarr"),
        ("s3://bucket/val.zarr", "s3://bucket/val.zarr/volume"),
        ("s3://bucket/val.zarr/１", "s3://bucket/val.zarr/1"),
        ("s3://bucket/val.zarr/ 1", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/../other", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/%2E%2E/other", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/%252E%252E/other", "s3://bucket/val.zarr"),
        ("s3://bucket/vol/1", "s3://bucket/vol/2"),
        ("s3://bucket/surface_volume/1", "s3://bucket/surface_volume/2"),
        ("s3://bucket/val.zarr.zip/1", "s3://bucket/val.zarr.zip/2"),
        ("s3://bucket/100", "s3://bucket/1"),
        ("s3://bucket/val.zarr/2/0", "s3://bucket/val.zarr/2/1"),
        ("s3://bucket/val.zarr/2/0", "s3://bucket/val.zarr/1"),
        ("s3://bucket/scroll/2", "s3://bucket/scroll/1"),
        ("s3://bucket/scroll/99", "s3://bucket/scroll/1"),
        ("s3://bucket/val.zarr/99", "s3://bucket/val.zarr/0"),
        ("s3://bucket", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr/1", "s3://bucket"),
        ("s3://bucket/a/../val.zarr/labels", "s3://bucket/val.zarr"),
        ("s3://bucket/./val.zarr", "s3://bucket/val.zarr"),
        ("s3://bucket/val.zarr ", "s3://bucket/val.zarr"),
    ],
)
def test_residual_remote_spellings_and_nested_paths_are_refused(training, validation):
    with pytest.raises(ValueError, match="overlaps val_uri"):
        validate_training_split(config(uris=[training], val_uri=validation))


def test_a_year_under_a_non_zarr_name_is_not_a_pyramid_level():
    """``scroll/2024`` is not a resolution of ``scroll/2023``.

    ``100`` under a name is past the pyramid bound. A stored ``..`` segment at
    the bucket root is that key, not every object in the bucket.
    """
    validate_training_split(
        config(uris=["s3://bucket/scroll/2024"], val_uri="s3://bucket/scroll/2023")
    )
    validate_training_split(
        config(uris=["s3://bucket/scroll/100"], val_uri="s3://bucket/scroll/1")
    )
    validate_training_split(
        config(uris=["s3://bucket/.."], val_uri="s3://bucket/val.zarr")
    )
    # Once-decoded this is the key ``val%2Ezarr/../other``, which is not inside
    # ``val.zarr``. Fully decoding it also leaves the volume.
    validate_training_split(
        config(
            uris=["s3://bucket/val%252Ezarr/%2E%2E/other"],
            val_uri="s3://bucket/val.zarr",
        )
    )


def test_an_unlabeled_remote_pyramid_level_is_refused():
    with pytest.raises(ValueError, match=r"unlabeled\[0\] overlaps val_uri"):
        validate_training_split(
            config(
                use_uamt=True,
                unlabeled_uris=["s3://bucket/val.zarr/1"],
                val_uri="s3://bucket/val.zarr",
            )
        )


def test_a_symlink_to_the_validation_volume_s_parent_is_refused(tmp_path):
    (tmp_path / "data" / "val.zarr").mkdir(parents=True)
    (tmp_path / "link").symlink_to(tmp_path / "data", target_is_directory=True)
    with pytest.raises(ValueError, match=r"training\[0\] overlaps val_uri"):
        validate_training_split(
            config(uris=["link"], val_uri="data/val.zarr"), base_dir=tmp_path
        )


@pytest.mark.parametrize("uris", [("train.zarr",), "train.zarr", [], None])
def test_training_volumes_are_a_nonempty_list(tmp_path, uris):
    with pytest.raises(ValueError, match="uris must be a nonempty list"):
        validate_training_split(config(uris=uris), base_dir=tmp_path)


@pytest.mark.parametrize("uri", [" ", "", None, 3])
def test_a_volume_identifier_is_a_nonempty_string(tmp_path, uri):
    with pytest.raises(ValueError, match="nonempty strings"):
        validate_training_split(config(uris=[uri]), base_dir=tmp_path)


def test_active_unlabeled_volumes_are_a_list(tmp_path):
    with pytest.raises(ValueError, match="unlabeled_uris must be a list"):
        validate_training_split(
            config(use_uamt=True, unlabeled_uris="other.zarr"), base_dir=tmp_path
        )
