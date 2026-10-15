"""What a model's auxiliary outputs train, and one ResEnc construction.

Before 2026-10-14, GenericMultiTaskWrapper without multi_task_heads, LeJEPAUNet
and VesuviusNeuralTracingViT returned the ink logits as "fiber" and zeros as
QC/ST (the TimeSformer zeros as ST), and train.py put losses on them: the fiber
BCE trained the ink logits toward the fiber target, and the hallucination
penalty on a zero QC pushed every ink probability down. The docs called them
zero-gradient constants. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-14_MODEL_HEADS.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train  # noqa: E402

import run_autoresearch_loop as loop  # noqa: E402
import vesuvius_model  # noqa: E402
from scripts.training.config import ExperimentConfig  # noqa: E402
from vesuvius_autoresearch.core.model_wrappers import (  # noqa: E402
    TASK_OUTPUTS,
    GenericMultiTaskWrapper,
    build_inference_model,
    build_resenc_unet,
    task_heads,
)


def _headless():
    torch.manual_seed(0)
    return GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 3, padding=1))


def test_a_headless_wrapper_returns_the_ink_logits_as_fiber():
    model = _headless()
    x = torch.rand(2, 1, 4, 8, 8)
    ink, fiber, qc, st = model(x, return_fiber=True, return_qc=True, return_st=True)
    assert torch.allclose(fiber.mean(dim=2), ink)
    assert not qc.any() and not st.any()
    # Not a constant: the fiber BCE trains the backbone, i.e. the ink logits.
    target = torch.rand(2, 1, 8, 8)
    F.binary_cross_entropy_with_logits(fiber.mean(dim=2), target).backward()
    assert model.model.weight.grad.abs().sum() > 0


def test_each_model_declares_its_real_heads():
    assert task_heads(_headless()) == frozenset()
    headed = GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1), multi_task_heads=True)
    assert task_heads(headed) == TASK_OUTPUTS
    assert task_heads(vesuvius_model.LeJEPAUNet) == frozenset()
    assert task_heads(vesuvius_model.VesuviusNeuralTracingViT) == frozenset()
    assert task_heads(vesuvius_model.VesuviusTimeSformer) == {"fiber", "qc"}
    for name in (
        "InkDetectorOptimized",
        "MedNeXtInkDetector",
        "VesuviusResNet3DDecoder",
    ):
        assert task_heads(getattr(vesuvius_model, name)) == TASK_OUTPUTS


def test_a_model_must_declare_its_heads():
    """Assuming real heads for an undeclared model is how placeholders were
    trained before; a malformed declaration would drop real heads."""
    with pytest.raises(TypeError, match="does not declare"):
        task_heads(torch.nn.Conv3d(1, 1, 1))

    class Misdeclared(torch.nn.Module):
        task_heads = "fiber"

    with pytest.raises(ValueError, match="must be a set"):
        task_heads(Misdeclared())
    Misdeclared.task_heads = frozenset({"qc", "structure"})
    with pytest.raises(ValueError, match="must be a set"):
        task_heads(Misdeclared())


def test_the_training_step_drops_outputs_that_are_not_heads():
    x = torch.rand(2, 1, 4, 8, 8)
    flags = {
        "return_fiber": True,
        "return_qc": True,
        "return_proj": True,
        "return_st": True,
    }
    model = _headless()
    ink, fiber, qc, proj, st = train.trained_outputs(
        model(x, **flags), task_heads(model)
    )
    assert ink is not None and proj is not None
    assert fiber is None and qc is None and st is None
    headed = GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1), multi_task_heads=True)
    outputs = train.trained_outputs(headed(x, **flags), task_heads(headed))
    assert all(output is not None for output in outputs)
    assert train.trained_outputs(torch.zeros(1), TASK_OUTPUTS)[1:] == (None,) * 4


class _Stop(Exception):
    pass


@pytest.mark.parametrize("multi_task_heads", [True, False])
def test_the_training_loader_never_computes_the_frangi_target(
    tmp_path, monkeypatch, multi_task_heads
):
    """~150 ms/patch on the CPU in the loader; the training step computes it on
    the batch's device instead (train.fiber_target), for a head that uses it
    (train.fiber_source, tests/test_frangi_torch.py)."""
    monkeypatch.chdir(tmp_path)
    for fragment in ("train", "val"):
        (tmp_path / fragment).mkdir()
        (tmp_path / fragment / "inklabels.png").write_bytes(b"")
    config = ExperimentConfig(
        architecture="resenc_unet",
        base_feat=4,
        patch_size=16,
        num_layers=8,
        multi_task_heads=multi_task_heads,
        target_fiber_source="frangi",
        use_wandb=False,
        uris=[str(tmp_path / "train" / "surface_volume.zarr")],
        val_uri=str(tmp_path / "val" / "surface_volume.zarr"),
    )
    seen = {}

    class Catalogue:
        def __len__(self):
            return 10

        def __getitem__(self, index):
            return index

    def dataset(uri, *args, **kwargs):
        if "train" in uri:
            seen["source"] = kwargs.get("target_fiber_source")
            raise _Stop
        return Catalogue()

    monkeypatch.setattr(train, "VesuviusLabeledDataset", dataset)
    # The real construction, on the CPU (train() builds on CUDA).
    monkeypatch.setattr(
        train,
        "build_model",
        lambda config, v_config, device: build_resenc_unet(1, 4, multi_task_heads),
    )
    with pytest.raises(_Stop):
        train.train(config)
    assert seen["source"] == "sobel_z"  # the zero placeholder


def test_heads_on_a_backbone_without_a_volume_output_are_refused():
    """resnet3d/i3d backbones return no 5D logits; their heads silently fell back
    to placeholders that train.py then trained as heads."""
    flat = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.LazyLinear(1))
    model = GenericMultiTaskWrapper(flat, multi_task_heads=True)
    with pytest.raises(ValueError, match="5D backbone output"):
        model(torch.rand(2, 1, 4, 8, 8), return_fiber=True)


@pytest.mark.parametrize("multi_task_heads", [True, False])
@pytest.mark.parametrize("use_ridges", [True, False])
def test_training_and_inference_build_the_same_resenc_unet(
    multi_task_heads, use_ridges
):
    """Weights load by name and shape only, so two constructions that differed
    in a shape-free setting would load cleanly and compute something else."""
    config = ExperimentConfig(
        architecture="resenc_unet",
        base_feat=4,
        patch_size=16,
        num_layers=8,
        use_ridges=use_ridges,
        multi_task_heads=multi_task_heads,
    )
    trained = train.build_model(config, train.build_vconfig(config), "cpu")
    served = build_inference_model(
        architecture="resenc_unet",
        patch_size=16,
        num_layers=8,
        base_feat=4,
        use_ridges=use_ridges,
        multi_task_heads=multi_task_heads,
    )
    assert repr(trained) == repr(served)
    assert {k: v.shape for k, v in trained.state_dict().items()} == {
        k: v.shape for k, v in served.state_dict().items()
    }
    assert task_heads(trained) == (TASK_OUTPUTS if multi_task_heads else frozenset())
    assert all(
        loop.trains_head(config, head) == (head in task_heads(trained))
        for head in TASK_OUTPUTS
    )


def _proposed(config):
    active, _ = loop.tweak_proposals(config, cap=float("inf"))
    return {template["attr"] for template in active}


def test_dropout_is_only_proposed_where_it_reaches_the_model():
    """resenc_unet has no dropout layers: 162 logged cycles tweaked it to no
    effect, and one was promoted on noise."""
    assert "dropout" not in _proposed(ExperimentConfig(architecture="resenc_unet"))
    assert "dropout" in _proposed(ExperimentConfig(architecture="gated_unet"))


@pytest.mark.parametrize(
    "architecture,model_class",
    [
        ("lejepa_unet", "LeJEPAUNet"),
        ("neural_tracing_vit", "VesuviusNeuralTracingViT"),
        ("timesformer", "VesuviusTimeSformer"),
        ("gated_unet", "InkDetectorOptimized"),
        ("mednext", "MedNeXtInkDetector"),
        ("resnet3d_decoder", "VesuviusResNet3DDecoder"),
    ],
)
def test_the_loop_mirrors_each_architecture_s_declared_heads(architecture, model_class):
    """The loop decides without building a model; it must agree with the
    declarations train.py uses."""
    config = ExperimentConfig(architecture=architecture)
    declared = task_heads(getattr(vesuvius_model, model_class))
    assert {h for h in TASK_OUTPUTS if loop.trains_head(config, h)} == declared


def test_multi_task_heads_is_only_proposed_where_it_builds_heads():
    assert "multi_task_heads" in _proposed(ExperimentConfig(architecture="resenc_unet"))
    for architecture in ("gated_unet", "lejepa_unet", "resnet3d", "i3d"):
        assert "multi_task_heads" not in _proposed(
            ExperimentConfig(architecture=architecture)
        )
    # resnet3d/i3d backbones give no volume output: no heads either way.
    for architecture in ("resnet3d", "i3d"):
        config = ExperimentConfig(architecture=architecture, multi_task_heads=True)
        assert not any(loop.trains_head(config, h) for h in TASK_OUTPUTS)


def test_head_weights_are_only_proposed_for_heads_that_are_trained():
    headless = _proposed(
        ExperimentConfig(architecture="resenc_unet", multi_task_heads=False)
    )
    assert not {"loss_fiber_bce", "loss_st", "target_fiber_source"} & headless
    headed = _proposed(
        ExperimentConfig(architecture="resenc_unet", multi_task_heads=True)
    )
    assert {"loss_fiber_bce", "loss_st", "target_fiber_source"} <= headed
