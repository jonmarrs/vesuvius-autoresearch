"""Regional exports must keep model/data inputs and every artifact distinct."""

import json
import os
from pathlib import Path

import pytest
import torch
from test_volume_inference_contracts import setup_prediction


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
