"""Memory refusal precedes models, CT reads and replacement of previous outputs."""

import json

import numpy as np
import pytest
import torch
from test_volume_inference_contracts import setup_prediction

from scripts.inference import ensemble_predict as ensemble, predict as single


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
