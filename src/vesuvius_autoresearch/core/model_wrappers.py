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
      - fiber: same 5D output as ink (dummy — re-uses ink tensor) when
               multi_task_heads=False, or a real Conv3d head's output
               when multi_task_heads=True.
      - qc:    torch.zeros((B, 1)) when dummy, real Linear head when not.
      - proj:  Linear projection of pooled scalar (real, used for DINO-Lite)
      - st:    torch.zeros((B, 6, Z, H, W)) when dummy, real Conv3d head
               (6 symmetric tensor components) when not.

    When multi_task_heads=True, the heads operate on
    `cat(input_x, backbone_output)` so they see both the raw CT/ridge
    inputs and the backbone's ink logits. Gradients from each task's
    loss flow back through the backbone via the ink-logits path,
    providing genuine multi-task supervision. Without this flag (the
    default), the heads are constants with zero gradient and the
    backbone gets only the ink supervision signal — see the long TODO
    we left in train.py before this commit.
    """

    def __init__(self, model, projector=None, multi_task_heads=False, input_channels=1):
        super().__init__()
        self.model = model
        self.multi_task_heads = multi_task_heads
        self.input_channels = input_channels
        if projector is not None:
            self.projector = projector
        else:
            self.projector = nn.Sequential(
                nn.AdaptiveAvgPool3d(1),
                nn.Flatten(),
                nn.Linear(1, 128),
                nn.LayerNorm(128),
            )
        if multi_task_heads:
            # Feature input to the heads: cat(input_x, backbone_output)
            # backbone outputs 1-channel ink logits (resenc_unet has num_classes=1)
            feat_ch = input_channels + 1
            self.fiber_head = nn.Sequential(
                nn.Conv3d(feat_ch, 16, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv3d(16, 1, kernel_size=1),
            )
            self.qc_head = nn.Sequential(
                nn.AdaptiveAvgPool3d(1),
                nn.Flatten(),
                nn.Linear(feat_ch, 32),
                nn.ReLU(inplace=True),
                nn.Linear(32, 1),
            )
            self.st_head = nn.Sequential(
                nn.Conv3d(feat_ch, 32, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv3d(32, 6, kernel_size=1),
            )

    def forward(
        self,
        x,
        return_fiber=False,
        return_qc=False,
        return_proj=False,
        return_st=False,
        **kwargs,
    ):
        out = self.model(x)
        if isinstance(out, (list, tuple)):
            out = out[0]
        if out.dim() == 5:
            ink_2d = torch.mean(out, dim=2)
        elif out.dim() == 2:
            ink_2d = out.view(out.shape[0], out.shape[1], 1, 1).expand(
                -1, -1, x.shape[3], x.shape[4]
            )
        else:
            ink_2d = out

        # Build feat = cat(x, out) for multi-task heads. Skip when not needed.
        # Shape: out is [B, 1, Z, H, W] for resenc; x is [B, C, Z, H, W].
        feat = None
        if self.multi_task_heads and out.dim() == 5 and x.dim() == 5:
            # Channel-wise cat: [B, input_channels + 1, Z, H, W]
            feat = torch.cat([x, out], dim=1)

        results = [ink_2d]
        if return_fiber:
            if self.multi_task_heads and feat is not None:
                results.append(self.fiber_head(feat))
            else:
                results.append(out if out.dim() == 5 else out.unsqueeze(2))
        if return_qc:
            if self.multi_task_heads and feat is not None:
                results.append(self.qc_head(feat))
            else:
                results.append(
                    torch.zeros((x.shape[0], 1), device=x.device, dtype=ink_2d.dtype)
                )
        if return_proj:
            proj_in = (
                out if out.dim() == 5 else out.unsqueeze(2).unsqueeze(-1).unsqueeze(-1)
            )
            projection = self.projector(proj_in)
            # Enforce finiteness to prevent NaN propagation
            results.append(torch.clamp(projection, min=-1e6, max=1e6))
        if return_st:
            if self.multi_task_heads and feat is not None:
                results.append(self.st_head(feat))
            else:
                results.append(
                    torch.zeros(
                        (x.shape[0], 6, *x.shape[2:]),
                        device=x.device,
                        dtype=ink_2d.dtype,
                    )
                )
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
    multi_task_heads: bool = False,
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
    from vesuvius_model import InkDetectorOptimized, VesuviusConfig

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
        features_per_stage = [base_feat * (2**i) for i in range(n_stages)]
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
        return GenericMultiTaskWrapper(
            backbone,
            multi_task_heads=multi_task_heads,
            input_channels=v_config.in_channels,
        )
    if architecture == "mednext":
        from vesuvius_model import MedNeXtInkDetector

        return MedNeXtInkDetector(v_config)

    return InkDetectorOptimized(v_config)
