"""Regional exports must keep model/data inputs and every artifact distinct."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from test_volume_inference_contracts import setup_prediction

from scripts.regional_prediction_artifacts import RegionalArtifactPlan


def _tree(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("collision", ["checkpoint", "ink_array"])
def test_custom_metadata_cannot_replace_an_input_or_prediction(
    tmp_path, monkeypatch, mode, collision
):
    run, argv, _, _, checkpoints = setup_prediction(tmp_path, monkeypatch, mode)
    stem = "region"
    argv.extend(["--artifact_stem", stem])
    target = (
        Path(checkpoints[0])
        if collision == "checkpoint"
        else tmp_path / "out" / f"{stem}_ink.npy"
    )
    argv.extend(["--metadata_out", str(target)])
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        run()
    assert _tree(tmp_path) == before


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("option", ["--metadata_out", "--output_img"])
def test_outputs_cannot_be_written_inside_the_source_volume(
    tmp_path, monkeypatch, mode, option
):
    run, argv, models, volume, _ = setup_prediction(tmp_path, monkeypatch, mode)
    target = volume / "custom.png"
    if option in argv:
        argv[argv.index(option) + 1] = str(target)
    else:
        argv.extend([option, str(target)])
    argv[argv.index("--uri") + 1] = volume.as_uri()
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        run()
    assert _tree(tmp_path) == before
    assert not any(model.inputs for model in models)


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "nested_link"])
def test_existing_unsafe_outputs_are_refused_before_inference(
    tmp_path, monkeypatch, mode, kind
):
    run, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv.extend(["--artifact_stem", "region"])
    external = tmp_path / "unrelated"
    external.write_bytes(b"preserve unrelated bytes")
    dest = tmp_path / "out/region_ink.npy"
    dest.parent.mkdir()
    if kind == "symlink":
        dest.symlink_to(external)
    elif kind == "hardlink":
        os.link(external, dest)
    elif kind == "fifo":
        os.mkfifo(dest)
    else:
        dest = tmp_path / "out/region_ink.zarr/0/chunk"
        dest.parent.mkdir(parents=True)
        dest.symlink_to(external)
    with pytest.raises(ValueError, match="nonsymlink"):
        run()
    assert external.read_bytes() == b"preserve unrelated bytes"
    assert not any(model.inputs for model in models)


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_custom_visualization_cannot_replace_the_ink_preview(
    tmp_path, monkeypatch, mode
):
    run, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv.extend(["--artifact_stem", "region"])
    argv[argv.index("--output_img") + 1] = str(tmp_path / "out/region_ink.png")
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        run()
    assert _tree(tmp_path) == before
    assert not any(model.inputs for model in models)


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_output_plan_is_rechecked_before_invalidating_old_metadata(
    tmp_path, monkeypatch, mode
):
    from test_volume_inference_contracts import ConstantHeads

    run, argv, _, _, checkpoints = setup_prediction(tmp_path, monkeypatch, mode)
    argv.extend(["--artifact_stem", "region"])
    output = tmp_path / "out"
    output.mkdir()
    metadata = output / "region_meta.json"
    metadata.write_text("previous completed metadata")
    checkpoint = Path(checkpoints[0])
    before = checkpoint.read_bytes()
    forward = ConstantHeads.forward

    def redirect_during_inference(self, *args, **kwargs):
        target = output / "region_ink.npy"
        if not target.is_symlink():
            target.symlink_to(checkpoint)
        return forward(self, *args, **kwargs)

    monkeypatch.setattr(ConstantHeads, "forward", redirect_during_inference)
    with pytest.raises(ValueError, match="artifact collision"):
        run()
    assert checkpoint.read_bytes() == before
    assert metadata.read_text() == "previous completed metadata"


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_custom_metadata_and_explicit_canonical_paths_remain_supported(
    tmp_path, monkeypatch, mode
):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv.extend(["--artifact_stem", "region"])
    argv[argv.index("--output_img") + 1] = str(tmp_path / "out/region.png")
    # The extension does not decide an artifact's role: this is a JSON file.
    metadata = tmp_path / "metadata.zarr"
    argv.extend(["--metadata_out", str(metadata)])
    run()
    assert json.loads(metadata.read_text())["prediction_complete"] is True
    run()  # A regular custom file with a .zarr suffix is still replaceable.
    argv[-1] = str(tmp_path / "out/region_meta.json")
    run()
    assert json.loads(Path(argv[-1]).read_text())["prediction_complete"] is True


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_selected_ome_array_outside_the_group_is_protected(tmp_path, monkeypatch, mode):
    run, argv, models, volume, _ = setup_prediction(tmp_path, monkeypatch, mode)
    output = tmp_path / "out"
    output.mkdir()
    array = output / "region_ink.zarr"
    volume.rename(array)
    volume.mkdir()
    (volume / "0").symlink_to(array, target_is_directory=True)
    argv.extend(["--artifact_stem", "region"])
    before = _tree(array)
    with pytest.raises(ValueError, match="artifact collision"):
        run()
    assert _tree(array) == before
    assert not any(model.inputs for model in models)


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("value", [float("nan"), {"non_json"}])
def test_unrecordable_checkpoint_metadata_fails_before_inference(
    tmp_path, monkeypatch, mode, value
):
    run, _, models, _, checkpoints = setup_prediction(tmp_path, monkeypatch, mode)
    checkpoint = torch.load(checkpoints[0], weights_only=False)
    checkpoint["config"]["extra_setting"] = value
    torch.save(checkpoint, checkpoints[0])
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="config cannot be recorded"):
        run()
    assert _tree(tmp_path) == before
    assert not any(model.inputs for model in models)


def _image_destination_writer(mode, plan):
    """Execute only the entry point's savefig statement on a synthetic figure."""
    import ast

    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from scripts.inference import ensemble_predict, predict

    module = predict if mode == "single" else ensemble_predict
    function = "predict" if mode == "single" else "ensemble_predict"
    tree = ast.parse(Path(module.__file__).read_text())
    entry = next(node for node in tree.body if getattr(node, "name", None) == function)
    (statement,) = [
        node
        for node in ast.walk(entry)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "savefig"
    ]
    figure = Figure(figsize=(1, 1))
    FigureCanvasAgg(figure)
    figure.subplots().plot([0, 1])
    scope = {
        "plt": SimpleNamespace(savefig=figure.savefig),
        "figure": figure,
        "out_path": str(plan.image),
        "output_img": str(plan.image),
        "artifacts": plan,
    }
    exec(
        compile(ast.Module(body=[statement], type_ignores=[]), module.__file__, "exec"),
        scope,
    )


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize("collision", ["checkpoint", "ct", "sibling", "symlink"])
def test_image_destination_cannot_hide_a_protected_appended_path(
    tmp_path, mode, collision
):
    from scripts.regional_prediction_artifacts import RegionalArtifactPlan

    source = tmp_path / "ct.zarr"
    source.mkdir()
    checkpoint = tmp_path / "model.png"
    checkpoint.write_bytes(b"disposable protected checkpoint sentinel")
    image = tmp_path / "model"
    if collision == "ct":
        source = tmp_path / "ct.png"
        source.mkdir()
        (source / "sentinel").write_bytes(b"CT sentinel")
        image = tmp_path / "ct"
    elif collision == "sibling":
        image = tmp_path / "region_ink"
        image.with_suffix(".png").write_bytes(b"existing sibling preview")
    elif collision == "symlink":
        image = tmp_path / "alias"
        image.with_suffix(".png").symlink_to(checkpoint)
    before = _tree(tmp_path)
    try:
        plan = RegionalArtifactPlan.create("region", image, None, source, [checkpoint])
        _image_destination_writer(mode, plan)
    except ValueError as exc:
        assert "artifact collision" in str(exc)
    else:
        assert _tree(tmp_path) == before, "savefig replaced a protected appended path"
        pytest.fail("protected image destination was accepted")
    assert _tree(tmp_path) == before


@pytest.mark.parametrize("mode", ["single", "ensemble"])
@pytest.mark.parametrize(
    ("name", "default_format", "expected"),
    [
        ("view", "png", "view.png"),
        ("view", "svg", "view.svg"),
        ("view...", "png", "view.png"),
        ("view.pdf", "png", "view.pdf"),
        ("view.PNG", "svg", "view.PNG"),
    ],
)
def test_image_destination_matches_actual_writer_and_allows_regular_replacement(
    tmp_path, mode, name, default_format, expected
):
    import matplotlib as mpl

    from scripts.regional_prediction_artifacts import RegionalArtifactPlan

    source = tmp_path / "ct.zarr"
    source.mkdir()
    checkpoint = tmp_path / "weights.sentinel"
    checkpoint.write_bytes(b"protected")
    output = tmp_path / expected
    output.write_bytes(b"ordinary replaceable image")
    with mpl.rc_context({"savefig.format": default_format}):
        plan = RegionalArtifactPlan.create(
            "region", tmp_path / name, None, source, [checkpoint]
        )
        assert plan.image == output
        # Changing defaults after planning cannot change the guarded destination.
        with mpl.rc_context({"savefig.format": "svg"}):
            _image_destination_writer(mode, plan)
    assert output.read_bytes() != b"ordinary replaceable image"
    assert checkpoint.read_bytes() == b"protected"
    assert {path.name for path in tmp_path.iterdir()} == {
        "ct.zarr",
        "weights.sentinel",
        expected,
    }


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_image_destination_preflight_in_both_entrypoints_without_loading_models(
    tmp_path, monkeypatch, mode
):
    import sys

    from scripts.inference import ensemble_predict, predict
    from scripts.regional_prediction_artifacts import RegionalArtifactPlan

    checkpoint = tmp_path / "model.png"
    checkpoint.write_bytes(b"plain sentinel, never deserialized")
    source = tmp_path / "ct.zarr"
    source.mkdir()
    config = {"patch_size": 8, "num_layers": 2, "base_feat": 4, "voxel_size_um": 2}
    # No serialized bytes or actual model are interpreted or executed.
    monkeypatch.setattr(
        torch, "load", lambda *a, **k: {"config": config, "model_state_dict": {}}
    )
    dummy = SimpleNamespace(task_heads=frozenset({"fiber"}))
    dummy.to = lambda *a, **k: dummy
    dummy.eval = lambda: dummy
    dummy.load_state_dict = lambda *a, **k: None
    monkeypatch.setattr(ensemble_predict, "build_inference_model", lambda **k: dummy)
    monkeypatch.setattr(
        predict, "build_prediction_model", lambda *a: pytest.fail("model constructed")
    )
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    original = RegionalArtifactPlan.create

    def capture(*args, **kwargs):
        plan = original(*args, **kwargs)
        pytest.fail(f"unsafe raw image path reached inference planning: {plan.image}")

    monkeypatch.setattr(RegionalArtifactPlan, "create", capture)
    argv = [
        mode,
        "--uri",
        str(source),
        "--x",
        "0",
        "--y",
        "0",
        "--z",
        "0",
        "--width",
        "8",
        "--height",
        "8",
        "--output_img",
        str(tmp_path / "model"),
        "--artifact_stem",
        "region",
    ]
    argv += (
        ["--checkpoint", str(checkpoint)]
        if mode == "single"
        else ["--checkpoints", str(checkpoint)]
    )
    monkeypatch.setattr(sys, "argv", argv)
    runner = predict.predict if mode == "single" else ensemble_predict.ensemble_predict
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match="artifact collision"):
        runner()
    assert _tree(tmp_path) == before


def _plan(tmp_path, **changes):
    """The plan alone, without a model: an OME group whose array is level 0, and one checkpoint."""
    volume = tmp_path / "ct.zarr"
    (volume / "0").mkdir(parents=True, exist_ok=True)
    (volume / "0" / ".zarray").write_text("{}")
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"weights")
    options = {
        "image": tmp_path / "out" / "region.png",
        "metadata": None,
        "uri": str(volume),
        "checkpoints": [checkpoint],
        **changes,
    }
    return RegionalArtifactPlan.create("region", **options)


def test_the_plan_alone_accepts_a_new_output_directory(tmp_path):
    plan = _plan(tmp_path)
    assert plan.image == tmp_path / "out" / "region.png" and plan.image_format == "png"
    assert plan.metadata == tmp_path / "out" / "region_meta.json"
    assert plan.source == tmp_path / "ct.zarr"
    assert plan.source_array == tmp_path / "ct.zarr" / "0"
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "option, value",
    [
        ("image", ""),
        ("image", " "),
        ("image", "s3://bucket/region.png"),
        # an empty metadata path selects the default name, so it is not a case here
        ("metadata", " "),
        ("metadata", "s3://bucket/region_meta.json"),
    ],
)
def test_an_output_must_be_a_nonempty_local_path(tmp_path, option, value):
    with pytest.raises(ValueError, match="nonempty local path"):
        _plan(tmp_path, **{option: value})


def test_an_output_inside_an_ome_group_but_outside_its_array_is_refused(tmp_path):
    """The whole source is protected, not only the level the reader selects."""
    with pytest.raises(ValueError, match="artifact collision"):
        _plan(tmp_path, image=tmp_path / "ct.zarr" / "preview.png")


def test_an_output_directory_that_links_into_the_source_is_refused(tmp_path):
    _plan(tmp_path)
    (tmp_path / "alias").symlink_to(tmp_path / "ct.zarr", target_is_directory=True)
    with pytest.raises(ValueError, match="artifact collision"):
        _plan(tmp_path, image=tmp_path / "alias" / "preview.png")


def test_a_source_named_through_a_link_protects_the_real_volume(tmp_path):
    _plan(tmp_path)
    (tmp_path / "alias.zarr").symlink_to(tmp_path / "ct.zarr", target_is_directory=True)
    linked = _plan(tmp_path, uri=str(tmp_path / "alias.zarr"))
    assert linked.source == tmp_path / "ct.zarr"
    assert linked.source_array == tmp_path / "ct.zarr" / "0"
    with pytest.raises(ValueError, match="artifact collision"):
        _plan(
            tmp_path,
            uri=str(tmp_path / "alias.zarr"),
            image=tmp_path / "ct.zarr" / "preview.png",
        )


def test_a_checkpoint_named_through_a_link_protects_the_real_file(tmp_path):
    _plan(tmp_path)
    (tmp_path / "linked.pt").symlink_to(tmp_path / "model.pt")
    linked = _plan(tmp_path, checkpoints=[tmp_path / "linked.pt"])
    assert linked.checkpoints == (tmp_path / "model.pt",)
    with pytest.raises(ValueError, match="artifact collision"):
        _plan(
            tmp_path,
            checkpoints=[tmp_path / "linked.pt"],
            metadata=tmp_path / "model.pt",
        )


def test_an_output_directory_that_is_a_file_is_refused(tmp_path):
    (tmp_path / "out").write_bytes(b"not a directory")
    with pytest.raises(ValueError, match="nonsymlink directory"):
        _plan(tmp_path)
    assert (tmp_path / "out").read_bytes() == b"not a directory"


def test_existing_outputs_keep_their_kinds(tmp_path):
    """The two arrays and the uncertainty mask are trees; every other artifact is a file."""
    out = tmp_path / "out"
    for name in ("region_ink.zarr", "region_fiber.zarr", "region_uncertain"):
        (out / name).mkdir(parents=True)
    (out / "region_ink.npy").write_bytes(b"old")
    _plan(tmp_path)
    (out / "region_ink.npy").unlink()
    (out / "region_ink.npy").mkdir()
    with pytest.raises(ValueError):
        _plan(tmp_path)
