"""Shared model wrappers and the canonical inference-side model factory.

Previously `GenericMultiTaskWrapper` was duplicated in train.py and
predict.py with slight signature drift (the train.py version accepted an
optional `projector` arg). This module is the single canonical source so
train.py and predict.py can never get out of sync.

`build_inference_model` is the single canonical architecture dispatch
used by predict.py, ensemble_predict.py, and scripts/reevaluate_best_model.py.
train.py keeps its own dispatch — it has training-specific concerns
(foundation_model_path loading, villa-imported resnet3d/i3d backbones,
multi-task head wiring) that don't apply at inference time.

TODO(multi-task-heads): fiber/qc/st outputs from this wrapper are dummies
(re-use of the ink output or torch.zeros). With dummy outputs the
corresponding losses become zero-gradient constants — they inflate
reported total_loss without contributing supervision. resenc_unet's
good topology (May-5 skel_dist=1.0) came from ink BCE+Dice alone, so
the dummies are not actively harmful, but real heads would unlock
multi-task gains.
"""
import torch
import torch.nn as nn


class GenericMultiTaskWrapper(nn.Module):
    """Adapter that gives a single-headed backbone (e.g. ResEnc UNet)
    the multi-head forward signature train.py expects.

    Returns an ink_2d output for every call, plus optionally:
      - fiber: same 5D output as ink (dummy — re-uses ink tensor)
      - qc:    torch.zeros((B, 1))
      - proj:  Linear projection of pooled scalar (real, used for DINO-Lite)
      - st:    torch.zeros((B, 6, Z, H, W))
    """

    def __init__(self, model, projector=None):
        super().__init__()
        self.model = model
        if projector is not None:
            self.projector = projector
        else:
            self.projector = nn.Sequential(
                nn.AdaptiveAvgPool3d(1),
                nn.Flatten(),
                nn.Linear(1, 128),
            )

    def forward(self, x, return_fiber=False, return_qc=False, return_proj=False, return_st=False, **kwargs):
        out = self.model(x)
        if isinstance(out, (list, tuple)):
            out = out[0]
        if out.dim() == 5:
            ink_2d = torch.mean(out, dim=2)
        elif out.dim() == 2:
            ink_2d = out.view(out.shape[0], out.shape[1], 1, 1).expand(-1, -1, x.shape[3], x.shape[4])
        else:
            ink_2d = out

        results = [ink_2d]
        if return_fiber:
            results.append(out if out.dim() == 5 else out.unsqueeze(2))
        if return_qc:
            results.append(torch.zeros((x.shape[0], 1), device=x.device, dtype=ink_2d.dtype))
        if return_proj:
            proj_in = out if out.dim() == 5 else out.unsqueeze(2).unsqueeze(-1).unsqueeze(-1)
            results.append(self.projector(proj_in))
        if return_st:
            results.append(torch.zeros((x.shape[0], 6, *x.shape[2:]), device=x.device, dtype=ink_2d.dtype))
        return tuple(results) if len(results) > 1 else results[0]


def build_inference_model(
    architecture: str = "gated_unet",
    patch_size: int = 64,
    num_layers: int = 16,
    base_feat: int = 64,
    num_blocks: int = 16,
    num_heads: int = 8,
    dropout: float = 0.0,
    use_ridges: bool = False,
) -> nn.Module:
    """Canonical architecture dispatcher for the inference path.

    Used by predict.py, ensemble_predict.py, and
    scripts/reevaluate_best_model.py so they cannot diverge in which
    architectures they support. train.py uses its own dispatcher
    (it has training-only branches for villa-imported resnet3d / i3d
    and for foundation_model_path loading).

    Unknown architectures fall back to InkDetectorOptimized (gated_unet).
    Callers should run load_compatible_state_dict afterward and check
    the skip count to catch architecture mismatches.
    """
    from vesuvius_model import VesuviusConfig, InkDetectorOptimized

    v_config = VesuviusConfig(
        patch_size=patch_size,
        num_layers=num_layers,
        base_feat=base_feat,
        num_blocks=num_blocks,
        num_heads=num_heads,
        dropout=dropout,
        in_channels=2 if use_ridges else 1,
        architecture=architecture,
    )

    if architecture == "timesformer":
        from vesuvius_model import VesuviusTimeSformer
        return VesuviusTimeSformer(v_config)
    if architecture == "resnet3d_decoder":
        from vesuvius_model import VesuviusResNet3DDecoder
        return VesuviusResNet3DDecoder(v_config)
    if architecture == "lejepa_unet":
        from vesuvius_model import LeJEPAUNet
        return LeJEPAUNet(v_config)
    if architecture == "resenc_unet":
        from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
        from dynamic_network_architectures.building_blocks.helper import (
            convert_dim_to_conv_op,
            get_matching_instancenorm,
        )
        n_stages = 3
        features_per_stage = [base_feat * (2 ** i) for i in range(n_stages)]
        strides = [[1, 1, 1]] + [[2, 2, 2]] * (n_stages - 1)
        backbone = ResidualEncoderUNet(
            input_channels=v_config.in_channels,
            n_stages=n_stages,
            features_per_stage=features_per_stage,
            conv_op=convert_dim_to_conv_op(3),
            kernel_sizes=[[3, 3, 3]] * n_stages,
            strides=strides,
            n_blocks_per_stage=[2] * n_stages,
            num_classes=1,
            n_conv_per_stage_decoder=[2] * (n_stages - 1),
            conv_bias=True,
            norm_op=get_matching_instancenorm(convert_dim_to_conv_op(3)),
            norm_op_kwargs={"eps": 1e-5, "affine": True},
            dropout_op=None,
            nonlin=nn.LeakyReLU,
            nonlin_kwargs={"inplace": True},
            deep_supervision=False,
        )
        return GenericMultiTaskWrapper(backbone)

    return InkDetectorOptimized(v_config)
