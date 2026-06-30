"""Training entry point for the TimeSformer detector. Proven recipe: warmup+cosine,
16-mixed precision, grad-clip 1.0, checkpoint on train loss."""
import os

import pytorch_lightning as pl
import torch
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import CSVLogger
from torch.utils.data import DataLoader
from warmup_scheduler import GradualWarmupScheduler

from .data import build_datasets
from .model import DetectorModel


class GradualWarmupSchedulerV2(GradualWarmupScheduler):
    def get_lr(self):
        if self.last_epoch > self.total_epoch:
            if self.after_scheduler:
                if not self.finished:
                    self.after_scheduler.base_lrs = [
                        b * self.multiplier for b in self.base_lrs]
                    self.finished = True
                return self.after_scheduler.get_lr()
            return [b * self.multiplier for b in self.base_lrs]
        if self.multiplier == 1.0:
            return [b * (float(self.last_epoch) / self.total_epoch) for b in self.base_lrs]
        return [b * ((self.multiplier - 1.0) * self.last_epoch / self.total_epoch + 1.0)
                for b in self.base_lrs]


def build_scheduler(cfg, optimizer):
    cosine = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, 10, eta_min=cfg.min_lr)
    return GradualWarmupSchedulerV2(optimizer, multiplier=1.0, total_epoch=1,
                                    after_scheduler=cosine)


def build_model(cfg, pred_shape):
    if cfg.architecture == "resenc":
        from .model_resenc import ResEncDetectorModel
        return ResEncDetectorModel(cfg, pred_shape=pred_shape)
    return DetectorModel(cfg, pred_shape=pred_shape)


def train(cfg, max_epochs=None, limit_batches=None):
    cfg.validate_window()
    pl.seed_everything(cfg.seed, workers=True)
    torch.set_float32_matmul_precision("medium")
    os.makedirs(cfg.model_dir, exist_ok=True)
    train_ds, valid_ds, _, pred_shape = build_datasets(cfg)
    train_loader = DataLoader(train_ds, batch_size=cfg.train_batch_size, shuffle=True,
                              num_workers=cfg.num_workers, pin_memory=True, drop_last=True)
    valid_loader = DataLoader(valid_ds, batch_size=cfg.train_batch_size, shuffle=False,
                              num_workers=cfg.num_workers, pin_memory=True, drop_last=True)
    model = build_model(cfg, pred_shape=pred_shape)
    # Save every epoch (proven recipe used save_top_k=epochs) so the best epoch can be
    # selected by held-out AUC afterwards, not just by train loss.
    ckpt_cb = ModelCheckpoint(filename="detector_{epoch}", dirpath=cfg.model_dir,
                              monitor="train/total_loss", mode="min", save_top_k=-1)
    trainer = pl.Trainer(
        max_epochs=max_epochs or cfg.epochs, accelerator="auto", devices=1,
        logger=CSVLogger(save_dir=cfg.model_dir, name="logs"),
        precision="16-mixed" if torch.cuda.is_available() else "32-true",
        gradient_clip_val=1.0, gradient_clip_algorithm="norm",
        limit_train_batches=limit_batches, limit_val_batches=limit_batches,
        callbacks=[ckpt_cb], enable_progress_bar=False,
    )
    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=valid_loader)
    return ckpt_cb.best_model_path or os.path.join(cfg.model_dir, "last.ckpt")
