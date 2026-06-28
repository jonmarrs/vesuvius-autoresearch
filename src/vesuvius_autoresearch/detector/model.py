"""TimeSformer detector model. Behavior-for-behavior from repro/gp_winner/train_ours.py
RegressionPLModel: depth slices are video frames, output is a 4x4 ink grid per 64px tile."""
import numpy as np
import pytorch_lightning as pl
import segmentation_models_pytorch as smp
import torch
from timesformer_pytorch import TimeSformer
from torch.optim import AdamW


class DetectorModel(pl.LightningModule):
    def __init__(self, cfg, pred_shape):
        super().__init__()
        self.cfg = cfg
        self.pred_shape = pred_shape
        self.mask_pred = np.zeros(pred_shape)
        self.mask_count = np.zeros(pred_shape)
        self.loss_func1 = smp.losses.DiceLoss(mode="binary")
        self.loss_func2 = smp.losses.SoftBCEWithLogitsLoss(smooth_factor=cfg.bce_smooth)
        self.backbone = TimeSformer(
            dim=512, image_size=cfg.size, patch_size=16, num_frames=cfg.in_chans,
            num_classes=16, channels=1, depth=8, heads=6, dim_head=64,
            attn_dropout=0.1, ff_dropout=0.1,
        )

    def loss_func(self, logits, target):
        return self.cfg.dice_w * self.loss_func1(logits, target) + \
            self.cfg.bce_w * self.loss_func2(logits, target)

    def forward(self, x):
        if x.ndim == 4:
            x = x[:, None]
        x = self.backbone(torch.permute(x, (0, 2, 1, 3, 4)))
        return x.view(-1, 1, 4, 4)

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
