"""Bound experimental adapters without changing valid scalar-field TTA/math."""

import subprocess
import sys
from pathlib import Path

import pytest
import torch
import torch.nn.functional as F

from scripts.labeling.prototype_volumetric_ink import VolumetricInkHead
from vesuvius_autoresearch.core import villa_inference as adapters
from vesuvius_autoresearch.core.inference_constants import validate_architecture
from vesuvius_autoresearch.core.model_wrappers import build_inference_model


@pytest.fixture
def tta(monkeypatch):
    backend = adapters.load_villa_leaf(adapters._VILLA_TTA)
    monkeypatch.setattr(backend, "_batched_tta_disabled", False)
    return backend


class SpatialHeads(torch.nn.Module):
    def __init__(self, multi=False, coarse=False):
        super().__init__()
        self.multi, self.coarse = multi, coarse

    def forward(self, x):
        y = x[:, :1] * 2 + 0.25
        if self.coarse:
            y = (F.avg_pool2d if x.ndim == 4 else F.avg_pool3d)(y, 2)
        return (y, y * 2, y - 1) if self.multi else y


@pytest.mark.parametrize("shape", [(2, 1, 4, 6), (2, 1, 2, 4, 6)])
@pytest.mark.parametrize("kind", ["mirroring", "rotation"])
@pytest.mark.parametrize("batched", [False, True])
@pytest.mark.parametrize("multi", [False, True])
def test_scalar_tta_matches_pinned_algorithm_exactly(tta, shape, kind, batched, multi):
    x = (
        torch.arange(torch.tensor(shape).prod().item(), dtype=torch.float32).reshape(
            shape
        )
        / 4
    )
    model = SpatialHeads(multi=multi).eval()
    with torch.inference_mode():
        expected = tta.infer_with_tta(
            model,
            x,
            kind,
            use_batched=batched,
            is_multi_task=multi,
            concat_multi_task_outputs=lambda out: torch.cat(out, dim=1),
        )
        actual = adapters.VillaTTAWrapper(
            model, kind, use_batched=batched, is_multi_task=multi
        )(x)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)


@pytest.mark.parametrize("shape", [(2, 1, 4, 6), (2, 1, 2, 4, 6)])
@pytest.mark.parametrize("kind", ["mirroring", "rotation"])
def test_sequential_tta_keeps_valid_coarser_output_grids(tta, shape, kind):
    x = torch.arange(torch.tensor(shape).prod().item(), dtype=torch.float32).reshape(
        shape
    )
    model = SpatialHeads(coarse=True)
    with torch.inference_mode():
        expected = tta.infer_with_tta(model, x, kind, use_batched=False)
        actual = adapters.VillaTTAWrapper(model, kind, use_batched=False)(x)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)


@pytest.mark.parametrize("bad", ["batch", "rank", "container"])
@pytest.mark.parametrize("batched", [True, False])
def test_incompatible_outputs_are_rejected_before_deaugmentation(tta, bad, batched):
    class BadModel(torch.nn.Module):
        def forward(self, x):
            if bad == "batch":
                return x.reshape(x.shape[0] // 2, 1, 2, 4)
            if bad == "rank":
                return x.mean(dim=(-2, -1))
            return {"ink": x}

    with pytest.raises((ValueError, TypeError), match="spatial|batch"):
        adapters.VillaTTAWrapper(BadModel(), use_batched=batched)(
            torch.zeros(2, 1, 2, 2)
        )


def test_batched_tta_cannot_reinterpret_an_equal_numel_grid(tta):
    class WrongGrid(torch.nn.Module):
        def forward(self, x):
            return x.reshape(x.shape[0], 1, 1, 4)

    with pytest.raises(ValueError, match="input spatial grid"):
        adapters.VillaTTAWrapper(WrongGrid())(torch.zeros(2, 1, 2, 2))


def test_mixed_project_ink_fiber_qc_shapes_fail_clearly(tta):
    class ProjectHeads(torch.nn.Module):
        def forward(self, x):
            return x.mean(dim=2), x, x.mean(dim=(2, 3, 4))

    with pytest.raises(ValueError, match="mixed ink/fiber/global-QC"):
        adapters.VillaTTAWrapper(ProjectHeads(), is_multi_task=True)(
            torch.zeros(2, 1, 3, 4, 5)
        )


def test_custom_concat_keeps_sequential_callback_order_and_unsplit_output(tta):
    events = []

    def model(x):
        events.append("model")
        return {"field": x}

    def concat(out):
        events.append("concat")
        return torch.cat([out["field"], out["field"] * 2], dim=1)

    with torch.inference_mode():
        output = adapters.VillaTTAWrapper(
            model,
            use_batched=False,
            is_multi_task=True,
            concat_multi_task_outputs=concat,
        )(torch.ones(2, 1, 3, 5))
    assert events == ["model"] * 4 + ["concat"] * 4
    assert output.shape == (2, 2, 3, 5)
    assert torch.equal(output[:, 0], torch.ones(2, 3, 5))
    assert torch.equal(output[:, 1], torch.full((2, 3, 5), 2.0))


def test_batched_oom_retains_pinned_sequential_fallback(tta, monkeypatch):
    calls, cleared = [], []

    def model(x):
        calls.append(x.shape[0])
        if x.shape[0] > 2:
            raise torch.cuda.OutOfMemoryError("synthetic batched OOM")
        return x + 1

    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: cleared.append(True))
    with torch.inference_mode():
        output = adapters.VillaTTAWrapper(model)(torch.zeros(2, 1, 3, 5))
    assert calls == [8, 2, 2, 2, 2] and cleared == [True]
    assert tta._batched_tta_disabled
    assert torch.equal(output, torch.ones_like(output))


@pytest.mark.parametrize(
    "option",
    [
        {"tta_type": "other"},
        {"use_batched": 1},
        {"is_multi_task": "yes"},
        {"concat_multi_task_outputs": 4},
    ],
)
def test_invalid_tta_options_fail_before_loading_upstream(monkeypatch, option):
    monkeypatch.setattr(
        adapters, "_load_villa_tta", lambda: pytest.fail("upstream loaded")
    )
    with pytest.raises((TypeError, ValueError)):
        adapters.VillaTTAWrapper(torch.nn.Identity(), **option)


@pytest.mark.parametrize("shape", [(1, 2, 3), (1, 1, 1, 1, 1, 1), (0, 1, 3, 4)])
def test_invalid_tta_inputs_fail_before_loading_upstream(monkeypatch, shape):
    monkeypatch.setattr(
        adapters, "_load_villa_tta", lambda: pytest.fail("upstream loaded")
    )
    with pytest.raises(ValueError, match="nonempty"):
        adapters.VillaTTAWrapper(torch.nn.Identity())(torch.zeros(shape))


def test_wrapper_keeps_model_state_dict_names():
    wrapper = adapters.VillaTTAWrapper(torch.nn.Conv2d(1, 1, 1))
    assert set(wrapper.state_dict()) == {"model.weight", "model.bias"}


@pytest.mark.parametrize("patch", [0, -1, True, 1.5])
def test_gaussian_rejects_invalid_patch_sizes(patch):
    with pytest.raises(ValueError, match="patch_size"):
        adapters.GaussianBlender(patch)


@pytest.mark.parametrize("sigma", [0, -0.125, True, float("nan"), float("inf")])
def test_gaussian_rejects_invalid_sigma(sigma):
    with pytest.raises(ValueError, match="sigma"):
        adapters.GaussianBlender(8, sigma)


@pytest.mark.parametrize("patch,sigma", [(2, 1e-5), (4, 0.02)])
def test_unrepresentable_gaussian_window_is_not_cached(patch, sigma):
    blender = adapters.GaussianBlender(patch, sigma)
    with pytest.raises(ValueError, match="sigma"):
        blender.get_weight_window(torch.device("cpu"))
    assert not blender._cache


@pytest.mark.parametrize("patch", [1, 2, 8, 64])
def test_default_gaussian_is_finite_positive_symmetric_and_cached(patch):
    blender = adapters.GaussianBlender(patch)
    window = blender.get_weight_window(torch.device("cpu"))
    assert window.dtype == torch.float32 and window.shape == (patch, patch)
    assert torch.isfinite(window).all() and (window > 0).all() and window.max() == 1
    assert torch.equal(window, window.flip((0,))) and torch.equal(window, window.T)
    assert blender.get_weight_window("cpu") is window


def test_gaussian_cache_resolves_implicit_cuda_device(monkeypatch):
    current, built = [0], []
    monkeypatch.setattr(torch.cuda, "current_device", lambda: current[0])
    blender = adapters.GaussianBlender(2)

    def build(device):
        built.append(str(device))
        return torch.tensor([device.index])

    monkeypatch.setattr(blender, "_build_window", build)
    first = blender.get_weight_window(torch.device("cuda"))
    current[0] = 1
    second = blender.get_weight_window(torch.device("cuda"))
    assert built == ["cuda:0", "cuda:1"]
    assert first.item() == 0 and second.item() == 1
    assert blender.get_weight_window(torch.device("cuda:0")) is first


@pytest.mark.parametrize(
    "name,value",
    [
        ("in_channels", 0),
        ("in_channels", True),
        ("num_layers", -1),
        ("num_layers", 1.5),
    ],
)
def test_volumetric_head_requires_positive_integer_sizes(name, value):
    with pytest.raises(ValueError, match=name):
        VolumetricInkHead(**{"in_channels": 2, "num_layers": 3, name: value})


@pytest.mark.parametrize(
    "shape", [(1, 2, 4, 5, 6), (1, 1, 3, 5, 6), (2, 3, 5, 6), (0, 2, 3, 5, 6)]
)
def test_volumetric_head_rejects_wrong_channels_depth_or_rank(shape):
    with pytest.raises(ValueError, match="features|channels/depth"):
        VolumetricInkHead(2, 3)(torch.zeros(shape))


def test_volumetric_head_returns_logits_with_gradients():
    head = VolumetricInkHead(2, 3)
    torch.nn.init.zeros_(head.conv3d.weight)
    torch.nn.init.constant_(head.conv3d.bias, -2)
    output = head(torch.ones(2, 2, 3, 4, 5))
    assert output.shape == (2, 3, 4, 5) and torch.equal(
        output, torch.full_like(output, -2)
    )
    output.sum().backward()
    assert torch.isfinite(head.conv3d.weight.grad).all()


@pytest.mark.parametrize("architecture", ["resnet3d", "i3d"])
def test_legacy_training_names_stay_accepted_but_inference_is_rejected(architecture):
    assert validate_architecture(architecture, training=True) == architecture
    with pytest.raises(ValueError, match="inference architecture"):
        build_inference_model(architecture=architecture)


def test_prototype_cli_describes_an_untrained_shape_demo(tmp_path):
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts/labeling/prototype_volumetric_ink.py"
    )
    help_run = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert help_run.returncode == 0 and "Untrained" in help_run.stdout
    run = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stderr
    assert (
        "random" in run.stdout
        and "no checkpoint" in run.stdout
        and "logits" in run.stdout
    )
    assert "Probability Distribution" not in run.stdout and not list(tmp_path.iterdir())
