"""Data pipeline for the TimeSformer detector: read 8-bit converted layers, tile into
64px subtiles with depth-as-channels, and apply the proven augmentations. Lifted from
repro/gp_winner/train_ours.py with globals removed and cfg injected."""
import glob
import os
import random

import albumentations as A
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from albumentations.pytorch import ToTensorV2
from torch.utils.data import Dataset

_ROTATE = A.Compose([A.Rotate(5, p=1)])


def _train_aug(cfg):
    return A.Compose([
        A.Resize(cfg.size, cfg.size),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomBrightnessContrast(p=0.75),
        A.ShiftScaleRotate(rotate_limit=360, shift_limit=0.15, scale_limit=0.15, p=0.75),
        A.OneOf([A.GaussNoise(var_limit=[10, 50]), A.GaussianBlur(), A.MotionBlur()], p=0.4),
        A.CoarseDropout(max_holes=2, max_width=int(cfg.size * 0.2),
                        max_height=int(cfg.size * 0.2), mask_fill_value=0, p=0.5),
        A.Normalize(mean=[0] * cfg.in_chans, std=[1] * cfg.in_chans),
        ToTensorV2(transpose_mask=True),
    ])


def _valid_aug(cfg):
    return A.Compose([
        A.Resize(cfg.size, cfg.size),
        A.Normalize(mean=[0] * cfg.in_chans, std=[1] * cfg.in_chans),
        ToTensorV2(transpose_mask=True),
    ])


def read_image_mask(cfg, fragment_id):
    root = cfg.data_root
    images = []
    pad0 = pad1 = 0
    for i in range(cfg.start_idx, cfg.end_idx):
        p = os.path.join(root, fragment_id, "layers", f"{i:02d}.tif")
        image = cv2.imread(p, 0)
        pad0 = cfg.tile_size - image.shape[0] % cfg.tile_size
        pad1 = cfg.tile_size - image.shape[1] % cfg.tile_size
        image = np.pad(image, [(0, pad0), (0, pad1)], constant_values=0)
        image = np.clip(image, 0, 200)
        images.append(image)
    images = np.stack(images, axis=2)
    ink = glob.glob(os.path.join(root, fragment_id, "*inklabels.*"))
    mask = cv2.imread(ink[0], 0)
    frag_mask = cv2.imread(os.path.join(root, fragment_id, f"{fragment_id}_mask.png"), 0)
    frag_mask = np.pad(frag_mask, [(0, pad0), (0, pad1)], constant_values=0)
    mask = mask.astype("float32") / 255.0
    return images, mask, frag_mask


def _tiles_for_fragment(cfg, fragment_id, is_valid):
    image, mask, frag_mask = read_image_mask(cfg, fragment_id)
    imgs, labels, xyxys = [], [], []
    ts, sz = cfg.tile_size, cfg.size
    x1_list = range(0, image.shape[1] - ts + 1, cfg.stride)
    y1_list = range(0, image.shape[0] - ts + 1, cfg.stride)
    for a in y1_list:
        for b in x1_list:
            if np.any(frag_mask[a:a + ts, b:b + ts] == 0):
                continue
            if not is_valid and np.all(mask[a:a + ts, b:b + ts] < 0.05):
                continue
            for yi in range(0, ts, sz):
                for xi in range(0, ts, sz):
                    y1, x1 = a + yi, b + xi
                    y2, x2 = y1 + sz, x1 + sz
                    imgs.append(image[y1:y2, x1:x2])
                    labels.append(mask[y1:y2, x1:x2, None])
                    if is_valid:
                        xyxys.append([x1, y1, x2, y2])
    return imgs, labels, xyxys, mask.shape


def build_datasets(cfg):
    tr_imgs, tr_labels = [], []
    for fid in cfg.train_fragment_ids:
        i, l, _, _ = _tiles_for_fragment(cfg, fid, is_valid=False)
        tr_imgs += i
        tr_labels += l
    v_imgs, v_labels, v_xyxys, pred_shape = _tiles_for_fragment(
        cfg, cfg.valid_fragment_id, is_valid=True)
    train_ds = CustomDataset(tr_imgs, cfg, labels=tr_labels, transform=_train_aug(cfg))
    valid_ds = CustomDataset(v_imgs, cfg, xyxys=np.stack(v_xyxys), labels=v_labels,
                             transform=_valid_aug(cfg))
    return train_ds, valid_ds, np.stack(v_xyxys), pred_shape


class CustomDataset(Dataset):
    def __init__(self, images, cfg, xyxys=None, labels=None, transform=None):
        self.images = images
        self.cfg = cfg
        self.labels = labels
        self.transform = transform
        self.xyxys = xyxys

    def __len__(self):
        return len(self.images)

    def _fourth_augment(self, image):
        image_tmp = np.zeros_like(image)
        cropping_num = random.randint(18, 26)
        start_idx = random.randint(0, self.cfg.in_chans - cropping_num)
        crop_indices = np.arange(start_idx, start_idx + cropping_num)
        start_paste_idx = random.randint(0, self.cfg.in_chans - cropping_num)
        tmp = np.arange(start_paste_idx, cropping_num)
        np.random.shuffle(tmp)
        cutout_idx = random.randint(0, 2)
        temporal_random_cutout_idx = tmp[:cutout_idx]
        image_tmp[..., start_paste_idx:start_paste_idx + cropping_num] = image[..., crop_indices]
        if random.random() > 0.4:
            image_tmp[..., temporal_random_cutout_idx] = 0
        return image_tmp

    def __getitem__(self, idx):
        if self.xyxys is not None:
            image = self.images[idx]
            label = self.labels[idx]
            xy = self.xyxys[idx]
            data = self.transform(image=image, mask=label)
            image = data["image"].unsqueeze(0)
            if self.cfg.full_res:
                label = data["mask"]
            else:
                label = F.interpolate(data["mask"].unsqueeze(0),
                                      (self.cfg.size // 16, self.cfg.size // 16)).squeeze(0)
            return image, label, xy
        image = self.images[idx]
        label = self.labels[idx]
        image = image.transpose(2, 1, 0)
        image = _ROTATE(image=image)["image"].transpose(0, 2, 1)
        image = _ROTATE(image=image)["image"].transpose(0, 2, 1).transpose(2, 1, 0)
        image = self._fourth_augment(image)
        data = self.transform(image=image, mask=label)
        image = data["image"].unsqueeze(0)
        if self.cfg.full_res:
            label = data["mask"]
        else:
            label = F.interpolate(data["mask"].unsqueeze(0),
                                  (self.cfg.size // 16, self.cfg.size // 16)).squeeze(0)
        return image, label
