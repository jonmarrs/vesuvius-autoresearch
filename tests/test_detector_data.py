import os

import cv2
import numpy as np

from vesuvius_autoresearch.detector import data as D
from vesuvius_autoresearch.detector.config import DetectorConfig


def _make_fake_fragment(root, frag, h=320, w=320, ink_box=(40, 40, 200, 200)):
    layers = os.path.join(root, frag, "layers")
    os.makedirs(layers, exist_ok=True)
    for i in range(17, 43):
        cv2.imwrite(
            os.path.join(layers, f"{i:02d}.tif"),
            (np.random.rand(h, w) * 200).astype(np.uint8),
        )
    label = np.zeros((h, w), np.uint8)
    y0, x0, y1, x1 = ink_box
    label[y0:y1, x0:x1] = 255
    cv2.imwrite(os.path.join(root, frag, f"{frag}_inklabels.png"), label)
    cv2.imwrite(
        os.path.join(root, frag, f"{frag}_mask.png"), np.full((h, w), 255, np.uint8)
    )


def test_read_image_mask_stacks_26_depth(tmp_path):
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr47")
    cfg = DetectorConfig(data_root=root)
    images, mask, frag_mask = D.read_image_mask(cfg, "PHercParis2Fr47")
    assert images.shape[2] == cfg.in_chans
    assert mask.max() <= 1.0


def test_build_datasets_subtile_and_label_shapes(tmp_path):
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143")
    cfg = DetectorConfig(data_root=root)
    train_ds, valid_ds, valid_xyxys, pred_shape = D.build_datasets(cfg)
    assert len(train_ds) > 0 and len(valid_ds) > 0
    img, label = train_ds[0]
    assert img.shape[-2:] == (cfg.size, cfg.size)
    assert tuple(label.shape) == (1, cfg.size // 16, cfg.size // 16)  # (1,4,4)
    vimg, vlabel, vxy = valid_ds[0]
    assert tuple(vlabel.shape) == (1, 4, 4)
    assert len(vxy) == 4


def test_full_res_label_shape(tmp_path):
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143")
    cfg = DetectorConfig(data_root=root, architecture="resenc")  # full_res True
    train_ds, valid_ds, _, _ = D.build_datasets(cfg)
    _, label = train_ds[0]
    assert tuple(label.shape) == (1, cfg.size, cfg.size)  # (1,64,64) full-res
    _, vlabel, _ = valid_ds[0]
    assert tuple(vlabel.shape) == (1, cfg.size, cfg.size)
    # default TimeSformer path is still 4x4
    tr2, _, _, _ = D.build_datasets(DetectorConfig(data_root=root))
    _, lab2 = tr2[0]
    assert tuple(lab2.shape) == (1, 4, 4)
