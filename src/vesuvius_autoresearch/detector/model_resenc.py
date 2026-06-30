"""Full-resolution 2.5D ResEncUNet ink detector. Depth slices are input channels (2D convs),
output is a per-pixel 64x64 ink mask (vs the TimeSformer's 4x4 grid). Wraps the installed
dynamic_network_architectures ResidualEncoderUNet in 2D mode.

Constraint: cfg.size must be divisible by 2**(resenc_n_stages-1) (64 = 2**4 * 4 for 5 stages)."""
import pytorch_lightning as pl
import segmentation_models_pytorch as smp
import torch.nn as nn
from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
from dynamic_network_architectures.building_blocks.helper import (
    convert_dim_to_conv_op,
    get_matching_instancenorm,
)
from torch.optim import AdamW


class ResEncDetectorModel(pl.LightningModule):
    def __init__(self, cfg, pred_shape):
        super().__init__()
        self.cfg = cfg
        self.pred_shape = pred_shape
        self.loss_func1 = smp.losses.DiceLoss(mode="binary")
        self.loss_func2 = smp.losses.SoftBCEWithLogitsLoss(smooth_factor=cfg.bce_smooth)
        n = cfg.resenc_n_stages
        conv2d = convert_dim_to_conv_op(2)
        features = [min(cfg.resenc_base_feat * (2 ** i), 320) for i in range(n)]
        self.backbone = ResidualEncoderUNet(
            input_channels=cfg.in_chans, n_stages=n, features_per_stage=features,
            conv_op=conv2d, kernel_sizes=[[3, 3]] * n,
            strides=[[1, 1]] + [[2, 2]] * (n - 1), n_blocks_per_stage=[2] * n,
            num_classes=1, n_conv_per_stage_decoder=[2] * (n - 1), conv_bias=True,
            norm_op=get_matching_instancenorm(conv2d),
            norm_op_kwargs={"eps": 1e-5, "affine": True}, dropout_op=None,
            nonlin=nn.LeakyReLU, nonlin_kwargs={"inplace": True}, deep_supervision=False,
        )

    def loss_func(self, logits, target):
        return self.cfg.dice_w * self.loss_func1(logits, target) + \
            self.cfg.bce_w * self.loss_func2(logits, target)

    def forward(self, x):
        if x.ndim == 5:
            x = x[:, 0]  # (B,1,C,H,W) -> (B,C,H,W)
        return self.backbone(x)  # (B,1,H,W)

    def training_step(self, batch, batch_idx):
        x, y = batch
        loss = self.loss_func(self(x), y)
        self.log("train/total_loss", loss.item(), on_step=True, on_epoch=True, prog_bar=True)
        return {"loss": loss}

    def validation_step(self, batch, batch_idx):
        x, y, _ = batch
        loss = self.loss_func(self(x), y)
        self.log("val/total_loss", loss.item(), on_step=True, on_epoch=True, prog_bar=True)
        return {"loss": loss}

    def configure_optimizers(self):
        from .train import build_scheduler
        optimizer = AdamW(self.parameters(), lr=self.cfg.lr)
        return [optimizer], [build_scheduler(self.cfg, optimizer)]
