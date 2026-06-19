# repro/ink_segformer/train.py
import argparse
import os
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader, RandomSampler

_R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _R)

from repro.ink_segformer.config import ReproConfig
from repro.ink_segformer.dataset import InkTileDataset
from repro.ink_segformer.losses import bce_dice_loss
from repro.ink_segformer.model import InkSegformer
from scripts.pixel_auc import pooled_pixel_auc


def _frag_dirs(cfg, ids):
    return [os.path.join(cfg.data_root, str(i)) for i in ids]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val", type=int, default=1, help="held-out fragment id")
    ap.add_argument("--epochs", type=int, default=ReproConfig.epochs)
    ap.add_argument("--out", default="repro/ink_segformer/runs/model_val{val}.pt")
    ap.add_argument(
        "--data-root", default=ReproConfig.data_root, help="dir containing frag subdirs"
    )
    ap.add_argument(
        "--frags", type=int, nargs="+", default=[1, 2, 3], help="available fragment ids"
    )
    ap.add_argument("--z-start", type=int, default=ReproConfig.z_start)
    ap.add_argument("--z-count", type=int, default=ReproConfig.z_count)
    ap.add_argument("--batch-size", type=int, default=ReproConfig.batch_size)
    ap.add_argument("--num-workers", type=int, default=4)
    ap.add_argument(
        "--max-train-tiles",
        type=int,
        default=0,
        help="if >0, randomly sample this many train tiles per epoch (redrawn each epoch)",
    )
    args = ap.parse_args()
    cfg = ReproConfig(epochs=args.epochs)
    cfg.data_root = args.data_root
    cfg.z_start = args.z_start
    cfg.z_count = args.z_count
    cfg.batch_size = args.batch_size
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    dev = torch.device("cuda")

    train_ids = [i for i in args.frags if i != args.val]
    tr = InkTileDataset(
        _frag_dirs(cfg, train_ids),
        cfg.tile,
        cfg.stride,
        cfg.z_start,
        cfg.z_count,
        cfg.min_papyrus,
        augment=True,
    )
    va = InkTileDataset(
        _frag_dirs(cfg, [args.val]),
        cfg.tile,
        cfg.stride,
        cfg.z_start,
        cfg.z_count,
        cfg.min_papyrus,
        augment=False,
    )
    if args.max_train_tiles and args.max_train_tiles < len(tr):
        # redraws a fresh random subset each epoch (overlapping tiles still cover the frag)
        sampler = RandomSampler(tr, replacement=False, num_samples=args.max_train_tiles)
        tl = DataLoader(
            tr,
            batch_size=cfg.batch_size,
            sampler=sampler,
            num_workers=args.num_workers,
            drop_last=True,
            pin_memory=True,
        )
    else:
        tl = DataLoader(
            tr,
            batch_size=cfg.batch_size,
            shuffle=True,
            num_workers=args.num_workers,
            drop_last=True,
            pin_memory=True,
        )
    vl = DataLoader(
        va, batch_size=cfg.batch_size, shuffle=False, num_workers=args.num_workers
    )
    print(
        f"train tiles={len(tr)} (frags {train_ids})  val tiles={len(va)} (frag {args.val})"
    )

    model = InkSegformer(cfg.stem_channels, cfg.encoder, encoder_weights="imagenet").to(
        dev
    )
    opt = torch.optim.AdamW(
        model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
    )
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg.epochs * len(tl))
    scaler = torch.cuda.amp.GradScaler()

    best = 0.0
    out_path = args.out.format(val=args.val)
    for ep in range(cfg.epochs):
        model.train()
        for vol, ink, pmask in tl:
            vol, ink, pmask = vol.to(dev), ink.to(dev), pmask.to(dev)
            opt.zero_grad()
            with torch.cuda.amp.autocast():
                loss = bce_dice_loss(model(vol), ink, mask=pmask)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
        # validation: pooled pixel AUC over masked pixels
        model.eval()
        probs, labels = [], []
        with torch.no_grad():
            for vol, ink, pmask in vl:
                p = torch.sigmoid(model(vol.to(dev))).cpu().numpy()
                m = pmask.numpy() > 0.5
                for b in range(p.shape[0]):
                    sel = m[b, 0]
                    if sel.sum() > 0:
                        probs.append(p[b, 0][sel].ravel())
                        labels.append(ink[b, 0].numpy()[sel].ravel())
        auc = pooled_pixel_auc(probs, labels) if probs else 0.5
        print(
            f"epoch {ep + 1}/{cfg.epochs}  loss={loss.item():.4f}  val_pixel_auc={auc:.4f}"
        )
        if auc > best:
            best = auc
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            torch.save(
                {
                    "model": model.state_dict(),
                    "cfg": vars(cfg),
                    "val_auc": auc,
                    "val_frag": args.val,
                },
                out_path,
            )
    print(f"BEST val_pixel_auc={best:.4f}  saved {out_path}")


if __name__ == "__main__":
    main()
