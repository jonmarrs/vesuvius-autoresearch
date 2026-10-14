"""Regional CT inference must preserve geometry, features, and export provenance."""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest
import torch
import zarr

from scripts.inference import ensemble_predict as ensemble, predict as single
from scripts.validate_prize_artifact import validate
from vesuvius_autoresearch.core import (
    inference as inference_helpers,
    model_wrappers,
    vesuvius_loader,
)
from vesuvius_autoresearch.core.inference import (
    multitask_inference_recipe,
    multitask_probabilities,
)


class ConstantHeads(torch.nn.Module):
    def __init__(self, layers, ridges, bad=None):
        super().__init__()
        self.bias = torch.nn.Parameter(torch.zeros(1))
        self.layers = layers
        self.ridges = ridges
        self.bad = bad
        self.inputs = []

    def forward(self, x, **kwargs):
        assert tuple(x.shape[1:3]) == (2 if self.ridges else 1, self.layers)
        torch.testing.assert_close(x[:, :1], torch.full_like(x[:, :1], 128 / 255))
        self.inputs.append(x.detach().cpu().clone())
        ink = self.bias.expand(len(x), 1, x.shape[-2], x.shape[-1])
        fiber = self.bias.expand(len(x), 1, 1, x.shape[-2], x.shape[-1])
        qc = self.bias.expand(len(x), 1)
        if self.bad == "ink_nan":
            ink = ink * float("nan")
        elif self.bad == "fiber_nan":
            fiber = fiber * float("nan")
        elif self.bad == "qc_inf":
            qc = qc + float("inf")
        elif self.bad == "ink_channels":
            ink = ink.expand(-1, 2, -1, -1)
        return (ink, fiber, qc) if kwargs.get("return_qc") else (ink, fiber)


def setup_prediction(tmp_path, monkeypatch, mode, configs=None, bad=None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    if configs is None:
        configs = [
            {
                "patch_size": 8,
                "num_layers": 2,
                "base_feat": 4,
                "use_ridges": False,
                "voxel_size_um": 2.0,
            }
        ]
    volume = tmp_path / "ct.zarr"
    zarr.open(str(volume), mode="w", shape=(6, 24, 24), chunks=(2, 8, 8), dtype="u1")[
        :
    ] = 128
    created = []

    def model_for(config):
        model = ConstantHeads(
            config.get("num_layers", 2), config.get("use_ridges", False), bad
        )
        created.append(model)
        return model

    monkeypatch.setattr(
        single, "build_prediction_model", lambda config, *args: model_for(config)
    )
    monkeypatch.setattr(
        ensemble, "build_inference_model", lambda **config: model_for(config)
    )
    monkeypatch.setattr(
        vesuvius_loader, "detect_ridges", lambda ct, **kwargs: np.zeros_like(ct)
    )
    checkpoints = []
    for index, config in enumerate(configs):
        checkpoint = tmp_path / f"model{index}.pt"
        torch.save(
            {"config": config, "model_state_dict": {"bias": torch.zeros(1)}}, checkpoint
        )
        checkpoints.append(str(checkpoint))
    argv = [
        mode,
        "--uri",
        str(volume),
        "--x",
        "3",
        "--y",
        "2",
        "--z",
        "1",
        "--width",
        "13",
        "--height",
        "11",
        "--stride",
        "4",
        "--output_img",
        str(tmp_path / "out/prediction.png"),
    ]
    if mode == "single":
        argv += ["--checkpoint", checkpoints[0], "--skip_active_learning"]
        runner = single.predict
    else:
        argv += ["--checkpoints", *checkpoints]
        runner = ensemble.ensemble_predict
    monkeypatch.setattr(sys, "argv", argv)
    return runner, argv, created, volume, checkpoints


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("tta", [False, True])
@pytest.mark.parametrize("gaussian", [False, True])
def test_complete_region_has_no_black_edges_and_consistent_exports(
    tmp_path, monkeypatch, mode, tta, gaussian
):
    runner, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    if not tta:
        argv.append("--disable_tta")
    if not gaussian:
        argv.append("--no-gaussian_blend")
    else:
        argv.append("--gaussian_blend")
    runner()
    output = tmp_path / "out"
    # Zero ink logits: sigmoid(0). (0.25 while a zero QC logit gated ink by 0.5.)
    np.testing.assert_allclose(np.load(next(output.glob("*_ink.npy"))), 0.5, atol=1e-6)
    np.testing.assert_allclose(
        np.load(next(output.glob("*_fiber.npy"))), 0.5, atol=1e-6
    )
    assert len(models[0].inputs) == (24 if tta else 6)
    metadata = json.loads(next(output.glob("*_meta.json")).read_text())
    assert metadata["width_px"] == 13 and metadata["height_px"] == 11
    assert metadata["prediction_complete"] is True
    assert metadata["coverage_fraction"] == 1.0
    assert metadata["position_xyz"] == [3, 2, 1]
    assert metadata["voxel_size_um"] == 2.0
    assert metadata["inference_recipe"]["tta_mirrors"] == (
        ["none", "x", "y", "xy"] if tta else ["none"]
    )
    assert metadata["inference_recipe"]["blend_window"] == (
        "gaussian" if gaussian else "positive_hann"
    )
    for key in ("vc3d_zarr_path", "fiber_vc3d_zarr_path"):
        export = Path(metadata[key])
        assert zarr.open_group(str(export), mode="r")["0"].shape == (1, 11, 13)
        transforms = json.loads((export / ".zattrs").read_text())["multiscales"][0][
            "datasets"
        ][0]["coordinateTransformations"]
        assert transforms == [
            {"type": "scale", "scale": [2.0, 2.0, 2.0]},
            {"type": "translation", "translation": [2.0, 4.0, 6.0]},
        ]


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize(
    "option,value",
    [
        ("--width", "0"),
        ("--width", "4"),
        ("--height", "-1"),
        ("--stride", "0"),
        ("--stride", "9"),
        ("--x", "-1"),
        ("--num_parts", "0"),
        ("--part_id", "-1"),
        ("--part_id", "1"),
    ],
)
def test_bad_geometry_fails_before_outputs(tmp_path, monkeypatch, mode, option, value):
    runner, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    if option in argv:
        argv[argv.index(option) + 1] = value
    else:
        argv += [option, value]
    with pytest.raises(ValueError):
        runner()
    assert not any(model.inputs for model in models)
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "predictions").exists()


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_out_of_bounds_region_fails_before_inference(tmp_path, monkeypatch, mode):
    runner, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv[argv.index("--x") + 1] = "20"
    with pytest.raises(ValueError, match="volume shape"):
        runner()
    assert not any(model.inputs for model in models)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("bad", ["ink_nan", "fiber_nan", "ink_channels"])
def test_bad_head_outputs_cannot_be_exported(tmp_path, monkeypatch, mode, bad):
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode, bad=bad)
    argv.append("--disable_tta")
    with pytest.raises(ValueError, match="model output"):
        runner()
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "predictions").exists()


def test_ensemble_handles_ct_and_ridge_models_with_different_depths(
    tmp_path, monkeypatch
):
    configs = [
        {
            "patch_size": 8,
            "num_layers": layers,
            "base_feat": 4,
            "use_ridges": ridges,
            "ridge_sigma": 3.0,
            "voxel_size_um": 2.0,
        }
        for layers, ridges in ((2, False), (4, True))
    ]
    runner, argv, models, _, checkpoints = setup_prediction(
        tmp_path, monkeypatch, "ensemble", configs
    )
    argv.append("--disable_tta")
    runner()
    assert [m.inputs[0].shape[1:3] for m in models] == [(1, 2), (2, 4)]
    metadata = json.loads(next((tmp_path / "out").glob("*_meta.json")).read_text())
    assert metadata["ensemble_checkpoints"] == checkpoints
    assert metadata["ensemble_model_configs"] == configs


@pytest.mark.parametrize("mismatch", ["patch_size", "voxel_size_um", "ridge_sigma"])
def test_ensemble_rejects_incompatible_context_before_opening_volume(
    tmp_path, monkeypatch, mismatch
):
    config = {
        "patch_size": 8,
        "num_layers": 4,
        "base_feat": 4,
        "voxel_size_um": 2.0,
        "use_ridges": True,
        "ridge_sigma": 2.0,
    }
    other = dict(
        config,
        **{
            mismatch: {"patch_size": 4, "voxel_size_um": 3.0, "ridge_sigma": 3.0}[
                mismatch
            ]
        },
    )
    runner, _, _, _, _ = setup_prediction(
        tmp_path, monkeypatch, "ensemble", [config, other]
    )
    monkeypatch.setattr(
        ensemble,
        "FastVesuviusVolume",
        lambda *args, **kwargs: pytest.fail("volume opened"),
    )
    with pytest.raises(ValueError, match=mismatch):
        runner()


def test_missing_requested_ensemble_member_fails(tmp_path, monkeypatch):
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "ensemble")
    argv += [str(tmp_path / "missing.pt")]
    with pytest.raises(FileNotFoundError):
        runner()
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_checkpoint_ridge_sigma_reaches_the_loader(tmp_path, monkeypatch, mode):
    config = {
        "patch_size": 8,
        "num_layers": 4,
        "base_feat": 4,
        "voxel_size_um": 2.0,
        "use_ridges": True,
        "ridge_sigma": 3.0,
    }
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode, [config])
    argv.append("--disable_tta")
    seen = []

    def ridges(ct, *, sigma):
        seen.append((sigma, ct.shape[0]))
        return np.zeros_like(ct)

    monkeypatch.setattr(vesuvius_loader, "detect_ridges", ridges)
    monkeypatch.setattr(vesuvius_loader, "_WARNING_COUNTS", defaultdict(int))
    runner()
    # Every tile's ridges see the depth context: all 6 slices of this volume, not
    # the model's 4. The overlay's one-slice CT read no longer reaches the filter.
    assert seen and set(seen) == {(3.0, 6)}
    assert "ridge_fallback" not in vesuvius_loader.warning_counts()
    metadata = json.loads(next((tmp_path / "out").glob("*_meta.json")).read_text())
    context = metadata["inference_recipe"]["ridge_depth_context"]
    assert context.startswith("up to num_layers + 8 slices")


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_a_non_finite_qc_head_does_not_stop_a_region(tmp_path, monkeypatch, mode):
    """QC is not served or requested, so a broken QC head cannot abort a region."""
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode, bad="qc_inf")
    argv.append("--disable_tta")
    runner()
    ink = np.load(next((tmp_path / "out").glob("*_ink.npy")))
    np.testing.assert_allclose(ink, 0.5, atol=1e-6)


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_partial_shard_is_explicit_and_saves_blend_weights(tmp_path, monkeypatch, mode):
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv += ["--disable_tta", "--num_parts", "2", "--part_id", "0"]
    runner()
    metadata = json.loads(next((tmp_path / "out").glob("*_meta.json")).read_text())
    assert metadata["prediction_complete"] is False
    assert metadata["num_parts"] == 2 and metadata["part_id"] == 0
    weights = np.load(metadata["blend_weight_path"])
    assert weights.shape == (11, 13)
    assert metadata["coverage_fraction"] == np.count_nonzero(weights) / weights.size
    assert np.isfinite(np.load(next((tmp_path / "out").glob("*_ink.npy")))).all()


def test_readiness_rejects_partial_shards(evidence):
    path, metadata = evidence
    metadata.update(
        prediction_complete=False, num_parts=2, part_id=0, coverage_fraction=0.7
    )
    path.write_text(json.dumps(metadata))
    report = validate(path)
    assert report["status"] == "FAIL"
    assert any(
        "partial" in failure or "shard" in failure for failure in report["failures"]
    )


@pytest.mark.parametrize("architecture", ["gated_unet_typo", None, []])
def test_unknown_architecture_cannot_fall_back_to_another_model(architecture):
    with pytest.raises(ValueError, match="architecture"):
        model_wrappers.build_inference_model(
            architecture=architecture, patch_size=8, num_layers=4, base_feat=4
        )


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_bare_image_and_nested_metadata_paths(tmp_path, monkeypatch, mode):
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv[argv.index("--output_img") + 1] = "preview.png"
    argv += [
        "--disable_tta",
        "--metadata_out",
        str(tmp_path / "evidence/nested/meta.json"),
    ]
    runner()
    metadata = json.loads((tmp_path / "evidence/nested/meta.json").read_text())
    assert Path(metadata["output_image_path"]) == tmp_path / "preview.png"
    assert Path(metadata["vc3d_zarr_path"]).parent == tmp_path
    assert not (tmp_path / "predictions").exists()


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_empty_shard_is_rejected(tmp_path, monkeypatch, mode):
    runner, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv += ["--num_parts", "7", "--part_id", "6"]
    with pytest.raises(ValueError, match="no tiles"):
        runner()
    assert not any(model.inputs for model in models)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("patch_size", 8.5),
        ("num_layers", True),
        ("base_feat", 0),
        ("use_ridges", "false"),
        ("ridge_sigma", float("nan")),
        ("voxel_size_um", float("inf")),
    ],
)
def test_invalid_checkpoint_settings_fail_before_reading_volume(
    tmp_path, monkeypatch, mode, field, value
):
    config = {
        "patch_size": 8,
        "num_layers": 2,
        "base_feat": 4,
        "use_ridges": False,
        "voxel_size_um": 2.0,
        field: value,
    }
    runner, _, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode, [config])
    target = single if mode == "single" else ensemble
    monkeypatch.setattr(
        target,
        "FastVesuviusVolume",
        lambda *args, **kwargs: pytest.fail("volume opened"),
    )
    with pytest.raises(ValueError):
        runner()


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("bad_checkpoint", [[], {"config": []}])
def test_malformed_checkpoint_is_rejected(tmp_path, monkeypatch, mode, bad_checkpoint):
    runner, _, _, _, paths = setup_prediction(tmp_path, monkeypatch, mode)
    torch.save(bad_checkpoint, paths[0])
    with pytest.raises(ValueError, match="object"):
        runner()
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_nonfinite_ct_cannot_be_exported(tmp_path, monkeypatch, mode):
    runner, _, models, volume, _ = setup_prediction(tmp_path, monkeypatch, mode)
    array = zarr.open(str(volume), mode="w", shape=(6, 24, 24), dtype="f4")
    array[:] = float("nan")
    with pytest.raises(ValueError, match="volume patch must be finite"):
        runner()
    assert not any(model.inputs for model in models)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("second_ridges", [False, True])
def test_ensemble_rejects_different_ridge_depth_context(
    tmp_path, monkeypatch, second_ridges
):
    configs = [
        {
            "patch_size": 8,
            "num_layers": depth,
            "base_feat": 4,
            "use_ridges": ridges,
            "voxel_size_um": 2.0,
        }
        for depth, ridges in ((3, True), (4, second_ridges))
    ]
    runner, _, _, _, _ = setup_prediction(tmp_path, monkeypatch, "ensemble", configs)
    monkeypatch.setattr(
        ensemble,
        "FastVesuviusVolume",
        lambda *args, **kwargs: pytest.fail("volume opened"),
    )
    with pytest.raises(ValueError, match="num_layers"):
        runner()


def test_spatial_mirrors_are_undone_before_probability_average():
    batch = torch.arange(24, dtype=torch.float32).reshape(1, 1, 2, 3, 4) / 12

    class SpatialHeads(torch.nn.Module):
        def forward(self, x, **kwargs):
            ink = x.mean(2)
            # An asymmetric position prior makes the model non-equivariant,
            # so reversing all output mirrors is observable in the average.
            ink = ink + torch.arange(4, dtype=x.dtype).view(1, 1, 1, 4)
            fiber = (2 * ink).unsqueeze(2)
            qc = torch.zeros((len(x), 1))
            return (ink, fiber, qc) if kwargs.get("return_qc") else (ink, fiber)

    expected_ink, expected_fiber = [], []
    model = SpatialHeads()
    for dims in ((), (-1,), (-2,), (-2, -1)):
        ink, fiber = model(torch.flip(batch, dims) if dims else batch)
        ink, fiber = torch.sigmoid(ink)[:, 0], torch.sigmoid(fiber[:, 0, 0])
        expected_ink.append(torch.flip(ink, dims) if dims else ink)
        expected_fiber.append(torch.flip(fiber, dims) if dims else fiber)
    actual_ink, actual_fiber = multitask_probabilities(model, batch)
    torch.testing.assert_close(actual_ink, torch.stack(expected_ink).mean(0))
    torch.testing.assert_close(actual_fiber, torch.stack(expected_fiber).mean(0))


@pytest.mark.parametrize("qc_logit", [-5.0, 0.0, 5.0, float("inf")])
def test_the_qc_head_does_not_scale_served_ink(qc_logit):
    """The QC head is fit to the patch's mean fiber target, not to quality. As a
    gate, sigmoid(qc / 0.1) took the production checkpoint's ink to ~1e-5."""
    batch = torch.rand((2, 1, 2, 4, 4), generator=torch.Generator().manual_seed(3))

    class FiberDensityQC(torch.nn.Module):
        def forward(self, x, **kwargs):
            ink = 4 * x.mean(2) - 2
            qc = torch.full((len(x), 1), qc_logit)
            return (
                (ink, ink.unsqueeze(2), qc)
                if kwargs.get("return_qc")
                else (
                    ink,
                    ink.unsqueeze(2),
                )
            )

    ink, _ = multitask_probabilities(FiberDensityQC(), batch, disable_tta=True)
    torch.testing.assert_close(ink, torch.sigmoid(4 * batch.mean(2) - 2)[:, 0])
    recipe = multitask_inference_recipe(True, False)
    assert recipe["ink_probability"] == "sigmoid(ink)"
    assert recipe["ridge_depth_context"] == "none (no ridge channel)"
    ridges = multitask_inference_recipe(True, False, use_ridges=True)
    assert ridges["ridge_depth_context"].startswith("up to num_layers + 8 slices")


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("real_heads", [False, True])
def test_real_resenc_weights_match_direct_model_probabilities(
    tmp_path, monkeypatch, mode, real_heads
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    config = {
        "architecture": "resenc_unet",
        "patch_size": 8,
        "num_layers": 8,
        "base_feat": 4,
        "multi_task_heads": real_heads,
        "voxel_size_um": 2.0,
    }
    data = np.random.default_rng(2).integers(0, 256, (8, 8, 8), dtype=np.uint8)
    volume = tmp_path / "ct.zarr"
    zarr.open(str(volume), mode="w", shape=data.shape, dtype="u1")[:] = data
    batch = torch.from_numpy(data.astype(np.float32) / 255)[None, None]
    expected_ink, expected_fiber, checkpoints = [], [], []
    for index in range(1 if mode == "single" else 2):
        torch.manual_seed(100 + index)
        model = model_wrappers.build_inference_model(
            **{key: value for key, value in config.items() if key != "voxel_size_um"}
        ).eval()
        checkpoint = tmp_path / f"resenc{index}.pt"
        torch.save(
            {"config": config, "model_state_dict": model.state_dict()}, checkpoint
        )
        checkpoints.append(str(checkpoint))
        with torch.no_grad():
            ink, fiber, qc = model(batch, return_fiber=True, return_qc=True)
            expected_ink.append(torch.sigmoid(ink)[0, 0].numpy())
            expected_fiber.append(torch.sigmoid(fiber.mean(2))[0, 0].numpy())
    argv = [
        mode,
        "--uri",
        str(volume),
        "--x",
        "0",
        "--y",
        "0",
        "--z",
        "0",
        "--disable_tta",
    ]
    if mode == "single":
        argv += ["--checkpoint", checkpoints[0], "--skip_active_learning"]
    else:
        argv += ["--checkpoints", *checkpoints]
    monkeypatch.setattr(sys, "argv", argv)
    (single.predict if mode == "single" else ensemble.ensemble_predict)()
    np.testing.assert_allclose(
        np.load(next((tmp_path / "predictions").glob("*_ink.npy"))),
        np.mean(expected_ink, axis=0),
        atol=1e-6,
    )
    np.testing.assert_allclose(
        np.load(next((tmp_path / "predictions").glob("*_fiber.npy"))),
        np.mean(expected_fiber, axis=0),
        atol=1e-6,
    )


@pytest.mark.parametrize(
    "facts",
    [
        {"prediction_complete": "true"},
        {"prediction_complete": False},
        {"num_parts": 2, "prediction_complete": True, "coverage_fraction": 1.0},
        {"num_parts": True},
        {"coverage_fraction": float("nan")},
        {"coverage_fraction": 0.99},
        {"coverage_fraction": True},
    ],
)
def test_readiness_rejects_inconsistent_completeness_facts(evidence, facts):
    path, metadata = evidence
    metadata.update(facts)
    path.write_text(json.dumps(metadata))
    assert validate(path)["status"] == "FAIL"


@pytest.mark.parametrize(
    ("z", "depth", "expected"),
    [
        (10, 40, (6, 24, 4)),  # interior: validation's centred context
        (2, 40, (0, 24, 2)),  # near the top: context shifted inside the volume
        (24, 40, (16, 24, 8)),  # the last window
        (0, 16, (0, 16, 0)),  # a volume with no room for context
    ],
)
def test_depth_window_matches_validation_context(z, depth, expected):
    assert inference_helpers.depth_window(z, 16, depth) == expected


def test_inference_ridges_match_the_validation_input(tmp_path, monkeypatch):
    """The ridge filter min-max normalizes its block, so ridges computed over the
    window alone differ from validation's, computed over window + context."""
    from PIL import Image

    layers, size = 4, 16
    margin = inference_helpers.DEPTH_MARGIN
    monkeypatch.setattr(vesuvius_loader, "_CUPY", None)  # CPU ridges
    rng = np.random.default_rng(5)
    data = rng.integers(0, 256, (layers + 2 * margin, size, size), dtype=np.uint8)
    data[margin + layers :] //= 4  # context darker than the window
    uri = str(tmp_path / "surface_volume.zarr")
    zarr.open(uri, mode="w", shape=data.shape, dtype="u1")[:] = data
    Image.fromarray(np.full((size, size), 255, np.uint8)).save(tmp_path / "ink.png")
    (tmp_path / "patches.json").write_text(json.dumps({"patches": [{"y": 0, "x": 0}]}))
    dataset = vesuvius_loader.VesuviusLabeledDataset(
        uri,
        str(tmp_path / "ink.png"),
        patch_size=size,
        num_layers=layers + 2 * margin,
        use_ridges=True,
        ridge_sigma=1.0,
        jitter=False,
        patches_json=str(tmp_path / "patches.json"),
        cache_dir=str(tmp_path / "cache"),
    )
    validation_input = dataset[0][0][:, margin : margin + layers]
    volume = vesuvius_loader.FastVesuviusVolume(uri, use_ridges=True, ridge_sigma=1.0)

    served = inference_helpers.read_model_block(volume, margin, 0, 0, layers, size)

    torch.testing.assert_close(served, validation_input)
    window_only = volume[margin : margin + layers, 0:size, 0:size]
    assert not torch.allclose(window_only[1], validation_input[1])


@pytest.mark.parametrize(("depth", "offset"), [(24, 4), (20, 2), (18, 1), (16, 0)])
def test_centre_window_uses_validation_offset_or_centres_a_shallow_read(depth, offset):
    batch = torch.arange(depth, dtype=torch.float32).view(1, 1, depth, 1, 1)
    window = inference_helpers.centre_window(batch, 16)
    assert window[0, 0, :, 0, 0].tolist() == list(range(offset, offset + 16))


def test_centre_window_refuses_a_read_shallower_than_the_model():
    with pytest.raises(ValueError, match="below num_layers"):
        inference_helpers.centre_window(torch.zeros(1, 1, 15, 2, 2), 16)


def test_without_z_the_window_is_centred_in_the_volume_depth(tmp_path, monkeypatch):
    """Surface volumes put the segment surface at their middle layer."""
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    index = argv.index("--z")
    del argv[index : index + 2]
    argv.append("--disable_tta")
    runner()
    metadata = json.loads(next((tmp_path / "out").glob("*_meta.json")).read_text())
    assert metadata["position_xyz"] == [3, 2, (6 - 2) // 2]


def test_without_z_the_window_is_centred_in_the_checkpoint_depth_band(
    tmp_path, monkeypatch
):
    config = {
        "patch_size": 8,
        "num_layers": 2,
        "base_feat": 4,
        "use_ridges": False,
        "voxel_size_um": 2.0,
        "depth_band": [0, 4],
        # Relative, as config.json records it; the test runs in tmp_path.
        "val_uri": "ct.zarr",
    }
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single", [config])
    index = argv.index("--z")
    del argv[index : index + 2]
    argv.append("--disable_tta")
    runner()
    metadata = json.loads(next((tmp_path / "out").glob("*_meta.json")).read_text())
    assert metadata["position_xyz"] == [3, 2, (0 + 4 - 2) // 2]


def test_a_band_is_not_applied_to_a_volume_the_checkpoint_did_not_record(
    tmp_path, monkeypatch, capsys
):
    """The band names slices of the checkpoint's own volumes (finding 87: their
    slice 0 is layer 16). On another volume the same numbers name other layers,
    so the window is centred in the volume."""
    config = {
        "patch_size": 8,
        "num_layers": 2,
        "base_feat": 4,
        "use_ridges": False,
        "voxel_size_um": 2.0,
        "depth_band": [0, 4],
        "uris": ["other/fragment.zarr"],
        "val_uri": "held_out.zarr",
    }
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single", [config])
    index = argv.index("--z")
    del argv[index : index + 2]
    argv.append("--disable_tta")
    runner()
    metadata = json.loads(next((tmp_path / "out").glob("*_meta.json")).read_text())
    assert metadata["position_xyz"] == [3, 2, (6 - 2) // 2]
    assert "the band is not applied" in capsys.readouterr().err


def test_a_band_outside_the_volume_falls_back_to_the_volume_centre(
    tmp_path, monkeypatch
):
    """A recorded volume that has become shallower than the band (a 6-slice
    volume, a 17-43 band) gets its centre rather than a refused read."""
    config = {
        "patch_size": 8,
        "num_layers": 2,
        "base_feat": 4,
        "use_ridges": False,
        "voxel_size_um": 2.0,
        "depth_band": [17, 43],
        "val_uri": "ct.zarr",
    }
    runner, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single", [config])
    index = argv.index("--z")
    del argv[index : index + 2]
    argv.append("--disable_tta")
    runner()
    metadata = json.loads(next((tmp_path / "out").glob("*_meta.json")).read_text())
    assert metadata["position_xyz"] == [3, 2, (6 - 2) // 2]


def test_depth_band_for_matches_recorded_volumes_by_path(tmp_path, monkeypatch):
    from vesuvius_autoresearch.core.inference import depth_band_for

    monkeypatch.chdir(tmp_path)
    saved = {
        "depth_band": [1, 27],
        "uris": ["local_data/Fr47/surface_volume.zarr"],
        "val_uri": "local_data/Fr143/surface_volume.zarr",
        "unlabeled_uris": ["s3://bucket/scroll.zarr"],
    }
    own = tmp_path / "local_data/Fr143/surface_volume.zarr"
    assert depth_band_for(saved, str(own)) == [1, 27]
    assert depth_band_for(saved, "local_data/Fr47/surface_volume.zarr/") == [1, 27]
    assert depth_band_for(saved, "s3://bucket/scroll.zarr/") == [1, 27]
    assert depth_band_for(saved, "local_data/Fr3/surface_volume.zarr") is None
    assert depth_band_for(saved, "s3://bucket/other.zarr") is None
    assert depth_band_for({**saved, "depth_band": None}, str(own)) is None
    assert depth_band_for({"depth_band": [1, 27]}, str(own)) is None
