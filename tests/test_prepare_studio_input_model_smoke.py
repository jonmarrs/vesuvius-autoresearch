"""Bounded CPU tensor-consumer smoke, not inference with a trained Studio model."""

import numpy as np
import pytest
import torch

from scripts.prepare_studio_input import export_input


@pytest.mark.parametrize("first,step", [(23, -1), (0, 1)])
def test_exported_depth_order_reaches_dummy_cpu_model(
    tmp_path, monkeypatch, first, step
):
    def forbidden(*args, **kwargs):
        raise AssertionError(
            "CPU synthetic smoke must not load/save checkpoints or initialize CUDA"
        )

    monkeypatch.setattr(torch, "load", forbidden)
    monkeypatch.setattr(torch, "save", forbidden)
    monkeypatch.setattr(torch.cuda, "_lazy_init", forbidden)
    source = tmp_path / "render.npy"
    original = np.arange(31 * 6 * 7, dtype=np.uint16).reshape(31, 6, 7).astype(np.uint8)
    np.save(source, original)
    output = tmp_path / "input"
    export_input(
        source,
        output,
        first_plane=first,
        depth_step=step,
        crop=(1, 5, 2, 7),
        depth_order_note="Synthetic CPU consumer only; not real render orientation",
    )
    prepared = np.load(output / "planes.npy", mmap_mode="r", allow_pickle=False)
    # This tiny 17-parameter consumer weights every depth differently, so a
    # reversed/scrambled export does not accidentally pass a depth-mean check.
    model = torch.nn.Conv3d(1, 1, kernel_size=(16, 1, 1), bias=True, device="cpu")
    weights = np.arange(1, 17, dtype=np.float32) / 136
    with torch.no_grad():
        model.weight.copy_(torch.from_numpy(2 * weights).reshape(1, 1, 16, 1, 1))
        model.bias.fill_(-1)
        tensor = torch.from_numpy(np.array(prepared, copy=True))[None, None].float()
        # Match only the documented intensity boundary. This is not the
        # released reader's architecture, tiling, checkpoint or validation.
        tensor.clamp_(0, 200).div_(255)
        actual = model(tensor).sigmoid()[0, 0, 0].numpy()
    planes = [first + step * i for i in range(16)]
    selected = original[planes, 1:5, 2:7].astype(np.float32)
    logits = 2 * ((np.clip(selected, 0, 200) / 255) * weights[:, None, None]).sum(0) - 1
    expected = 1 / (1 + np.exp(-logits))
    assert actual.shape == (4, 5)
    assert np.isfinite(actual).all()
    assert all(p.device.type == "cpu" for p in model.parameters())
    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-7)
    np.testing.assert_array_equal(np.load(source), original)
