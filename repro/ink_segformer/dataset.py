# repro/ink_segformer/dataset.py
import os

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

Image.MAX_IMAGE_PIXELS = None


def read_middle_layers(frag_dir, z_start, z_count):
    """Read z_count depth layers starting at z_start from <frag>/surface_volume/*.tif
    into a normalized float32 array [D, H, W] (uint16 -> /65535, uint8 -> /255)."""
    files = sorted(
        f
        for f in os.listdir(os.path.join(frag_dir, "surface_volume"))
        if f.endswith(".tif")
    )
    files = files[z_start : z_start + z_count]
    layers = []
    for f in files:
        a = np.array(Image.open(os.path.join(frag_dir, "surface_volume", f)))
        denom = 65535.0 if a.dtype == np.uint16 else 255.0
        layers.append(a.astype(np.float32) / denom)
    return np.stack(layers, axis=0)


def read_layers_raw(frag_dir, z_start, z_count):
    """Like read_middle_layers but keeps the native dtype (uint16/uint8) to halve
    resident memory for large fragments; returns (vol[D,H,W], denom). Normalize
    per-tile at access time."""
    files = sorted(
        f
        for f in os.listdir(os.path.join(frag_dir, "surface_volume"))
        if f.endswith(".tif")
    )
    files = files[z_start : z_start + z_count]
    layers, denom = [], 255.0
    for f in files:
        a = np.array(Image.open(os.path.join(frag_dir, "surface_volume", f)))
        denom = 65535.0 if a.dtype == np.uint16 else 255.0
        layers.append(a)
    return np.stack(layers, axis=0), denom


def compute_tile_origins(mask, tile, stride, min_papyrus=0.05):
    """List of (y, x) top-left origins on a grid (stride), clamped so a full tile
    fits, keeping only tiles whose papyrus-mask coverage >= min_papyrus."""
    h, w = mask.shape
    ys = list(range(0, max(1, h - tile + 1), stride))
    xs = list(range(0, max(1, w - tile + 1), stride))
    if ys[-1] != h - tile:
        ys.append(max(0, h - tile))
    if xs[-1] != w - tile:
        xs.append(max(0, w - tile))
    origins = []
    for y in ys:
        for x in xs:
            if mask[y : y + tile, x : x + tile].mean() >= min_papyrus:
                origins.append((y, x))
    return origins


class InkTileDataset(Dataset):
    """Tiles of one or more fragments. __getitem__ -> (vol[1,D,H,W], ink[1,H,W],
    pmask[1,H,W]) as float32 torch tensors. Volumes are loaded once per fragment
    and held in memory (Kaggle fragments fit)."""

    def __init__(
        self, frag_dirs, tile, stride, z_start, z_count, min_papyrus=0.05, augment=False
    ):
        self.tile, self.augment = tile, augment
        self.items = []  # (frag_index, y, x)
        self.vols, self.denoms, self.inks, self.masks = [], [], [], []
        for fi, d in enumerate(frag_dirs):
            vol, denom = read_layers_raw(d, z_start, z_count)  # [D,H,W] native dtype
            self.denoms.append(denom)
            ink = (
                np.array(Image.open(os.path.join(d, "inklabels.png")).convert("L"))
                > 127
            ).astype(np.float32)
            mask = (
                np.array(Image.open(os.path.join(d, "mask.png")).convert("L")) > 127
            ).astype(np.float32)
            self.vols.append(vol)
            self.inks.append(ink)
            self.masks.append(mask)
            for y, x in compute_tile_origins(mask > 0.5, tile, stride, min_papyrus):
                self.items.append((fi, y, x))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        fi, y, x = self.items[idx]
        t = self.tile
        vol = (
            self.vols[fi][:, y : y + t, x : x + t].astype(np.float32) / self.denoms[fi]
        )  # [D,t,t]
        ink = self.inks[fi][y : y + t, x : x + t]  # [t,t]
        pmask = self.masks[fi][y : y + t, x : x + t]  # [t,t]
        if self.augment:
            k = np.random.randint(0, 4)
            vol = np.rot90(vol, k, axes=(1, 2)).copy()
            ink = np.rot90(ink, k).copy()
            pmask = np.rot90(pmask, k).copy()
            if np.random.rand() < 0.5:
                vol, ink, pmask = (
                    vol[:, ::-1].copy(),
                    ink[::-1].copy(),
                    pmask[::-1].copy(),
                )
        vol = torch.from_numpy(vol).unsqueeze(0).float()  # [1,D,t,t]
        ink = torch.from_numpy(ink).unsqueeze(0).float()  # [1,t,t]
        pmask = torch.from_numpy(pmask).unsqueeze(0).float()
        return vol, ink, pmask
