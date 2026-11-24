"""Memory refusal precedes models, CT reads and replacement of previous outputs."""

import json

import numpy as np
import pytest
import torch
import zarr
from test_volume_inference_contracts import setup_prediction

from scripts.inference import ensemble_predict as ensemble, predict as single


@pytest.mark.parametrize(
    ("axis", "value", "auto_z"), [("x", 23, False), ("x", 23, True), ("z", 5, False)]
)
def test_single_refuses_out_of_bounds_regions_before_building_model(
    tmp_path, monkeypatch, axis, value, auto_z
):
    run, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    argv[argv.index(f"--{axis}") + 1] = str(value)
    if auto_z:
        start = argv.index("--z")
        del argv[start : start + 2]

    with pytest.raises(ValueError, match="requested region exceeds volume shape"):
        run()

    assert not models
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("retarget", [False, True])
def test_auto_z_uses_one_reader_and_requires_a_stable_array(
    tmp_path, monkeypatch, retarget
):
    run, argv, models, volume, _ = setup_prediction(tmp_path, monkeypatch, "single")
    group = tmp_path / "linked.zarr"
    zarr.open_group(str(group), mode="w")
    level = group / "0"
    level.symlink_to(volume, target_is_directory=True)
    replacement = tmp_path / "replacement.zarr"
    zarr.open_array(str(replacement), mode="w", shape=(8, 24, 24), dtype="u1")[:] = 128
    argv[argv.index("--uri") + 1] = group.as_uri()
    start = argv.index("--z")
    del argv[start : start + 2]
    original = single.FastVesuviusVolume
    opened = []

    def track_open(*args, **kwargs):
        reader = original(*args, **kwargs)
        opened.append(reader.vol.path)
        if retarget and len(opened) == 1:
            level.unlink()
            level.symlink_to(replacement, target_is_directory=True)
        return reader

    monkeypatch.setattr(single, "FastVesuviusVolume", track_open)
    if retarget:
        with pytest.raises(RuntimeError, match="CT source selection changed"):
            run()
        assert not models
        assert not (tmp_path / "out").exists()
    else:
        run()
        assert models
    assert opened == [volume]


def test_auto_z_protects_the_original_group_when_two_groups_share_an_array(
    tmp_path, monkeypatch
):
    run, argv, models, volume, _ = setup_prediction(tmp_path, monkeypatch, "single")
    first, second = tmp_path / "first.zarr", tmp_path / "second.zarr"
    for group in (first, second):
        zarr.open_group(str(group), mode="w").attrs["group_name"] = group.name
        (group / "0").symlink_to(volume, target_is_directory=True)
    link = tmp_path / "current.zarr"
    link.symlink_to(first, target_is_directory=True)
    argv[argv.index("--uri") + 1] = link.as_uri()
    start = argv.index("--z")
    del argv[start : start + 2]
    metadata = first / ".zattrs"
    before = metadata.read_bytes()
    argv.extend(["--metadata_out", str(metadata)])
    original = single.FastVesuviusVolume

    def retarget_after_open(*args, **kwargs):
        reader = original(*args, **kwargs)
        link.unlink()
        link.symlink_to(second, target_is_directory=True)
        return reader

    monkeypatch.setattr(single, "FastVesuviusVolume", retarget_after_open)
    with pytest.raises(RuntimeError, match="CT source selection changed"):
        run()

    assert link.resolve() == second
    assert not models
    assert not (tmp_path / "out").exists()
    assert metadata.read_bytes() == before


@pytest.mark.parametrize(
    ("mode", "stage"),
    [
        ("ensemble", "setup"),
        ("ensemble", "inference"),
        ("single", "opening"),
        ("single", "inference"),
    ],
)
def test_prediction_rechecks_the_planned_ct_before_reading_and_publication(
    tmp_path, monkeypatch, mode, stage
):
    from test_volume_inference_contracts import ConstantHeads

    run, argv, models, volume, _ = setup_prediction(tmp_path, monkeypatch, mode)
    group = tmp_path / "linked.zarr"
    zarr.open_group(str(group), mode="w")
    level = group / "0"
    level.symlink_to(volume, target_is_directory=True)
    argv[argv.index("--uri") + 1] = group.as_uri()
    argv.extend(["--artifact_stem", "region"])
    output = tmp_path / "out"
    output.mkdir()
    metadata = output / "region_meta.json"
    metadata.write_bytes(b"prior metadata")
    export = output / "region_ink.zarr"
    replacement = export / "0"
    zarr.open_group(str(export), mode="w").create_dataset(
        "0", shape=(6, 24, 24), dtype="u1"
    )[:] = 128
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}

    def retarget(original):
        def call(*args, **kwargs):
            if level.resolve() != replacement:
                level.unlink()
                level.symlink_to(replacement, target_is_directory=True)
            return original(*args, **kwargs)

        return call

    if stage == "setup":
        monkeypatch.setattr(
            ensemble, "build_inference_model", retarget(ensemble.build_inference_model)
        )
        monkeypatch.setattr(
            ensemble, "FastVesuviusVolume", lambda *a, **k: pytest.fail("volume opened")
        )
    elif stage == "opening":
        monkeypatch.setattr(
            single, "FastVesuviusVolume", retarget(single.FastVesuviusVolume)
        )
    else:
        monkeypatch.setattr(ConstantHeads, "forward", retarget(ConstantHeads.forward))

    with pytest.raises(RuntimeError, match="CT source selection changed"):
        run()

    assert len(models) == (0 if stage == "opening" else 1)
    assert any(model.inputs for model in models) == (stage == "inference")
    assert level.resolve() == replacement
    after = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    assert after == before


@pytest.mark.parametrize(
    "mode,skip_uncertainty", [("single", False), ("single", True), ("ensemble", True)]
)
@pytest.mark.parametrize("sharded", [False, True])
def test_large_region_is_refused_before_model_or_ct_work(
    tmp_path, monkeypatch, mode, sharded, skip_uncertainty
):
    run, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    if mode == "single" and not skip_uncertainty:
        argv.remove("--skip_active_learning")
    if mode == "single":
        start = argv.index("--z")
        del argv[start : start + 2]
    argv[argv.index("--width") + 1] = "100000"
    argv[argv.index("--height") + 1] = "100000"
    if sharded:
        argv.extend(["--num_parts", "2"])
    output = tmp_path / "out"
    output.mkdir()
    old = output / "region_meta.json"
    old.write_bytes(b"preserve previous record")
    argv.extend(["--artifact_stem", "region"])

    def unexpected_read(*args, **kwargs):
        pytest.fail("over-budget region reached CT metadata/payload reads")

    monkeypatch.setattr(
        single if mode == "single" else ensemble, "FastVesuviusVolume", unexpected_read
    )
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    loaded = []
    load = torch.load

    def cpu_checkpoint(*args, **kwargs):
        assert str(kwargs.get("map_location")) == "cpu"
        loaded.append(True)
        return load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", cpu_checkpoint)
    with pytest.raises(ValueError, match="max_accumulator_bytes"):
        run()
    assert loaded and not models
    assert old.read_bytes() == b"preserve previous record"
    assert list(output.iterdir()) == [old]


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_explicit_budget_is_recorded_and_allocations_are_float32(
    tmp_path, monkeypatch, mode
):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv.extend(["--max_accumulator_bytes", "1716", "--artifact_stem", "region"])
    previous = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float64)
        run()
    finally:
        torch.set_default_dtype(previous)
    metadata = json.loads((tmp_path / "out/region_meta.json").read_text())
    assert metadata["resource_plan"]["accumulator_bytes"] == 1716
    assert metadata["resource_plan"]["max_accumulator_bytes"] == 1716
    assert not metadata["resource_plan"]["whole_process_peak_estimated"]
    for name in ("ink", "fiber"):
        array = np.load(tmp_path / f"out/region_{name}.npy")
        assert array.dtype == np.float32
        np.testing.assert_allclose(array, 0.5)


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_default_region_budget_uses_the_checkpoint_patch(tmp_path, monkeypatch, mode):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    for option in ("--width", "--height"):
        start = argv.index(option)
        del argv[start : start + 2]
    argv.extend(["--max_accumulator_bytes", "768", "--artifact_stem", "region"])
    run()
    record = json.loads((tmp_path / "out/region_meta.json").read_text())
    assert record["resource_plan"]["width"] == 8
    assert record["resource_plan"]["height"] == 8
    assert record["resource_plan"]["accumulator_bytes"] == 768
