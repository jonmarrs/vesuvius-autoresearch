import os
import sys

import cv2
import numpy as np
import pytest
import tifffile

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.distill_prep import prep_distill_fragment, teacher_region_for


def test_teacher_region_for_same_scale():
    teacher = np.arange(100 * 80).reshape(100, 80).astype(np.uint8)
    out = teacher_region_for(
        teacher, level_shape=(100, 80), region_box=(10, 20, 30, 40)
    )
    assert np.array_equal(out, teacher[10:30, 20:40])


def test_teacher_region_for_scales_box():
    # teacher at 2x the level scale: box coordinates double
    teacher = np.zeros((200, 160), np.uint8)
    teacher[20:60, 40:80] = 255
    out = teacher_region_for(
        teacher, level_shape=(100, 80), region_box=(10, 20, 30, 40)
    )
    assert out.shape == (40, 40)
    assert out.max() == 255 and out.min() == 255  # exactly the marked block


def test_prep_writes_fragment_with_teacher_label(tmp_path):
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((64, 64), np.uint8)
    teacher[16:48, 16:48] = 200  # above threshold 128
    out = prep_distill_fragment(layers, teacher, str(tmp_path), "segT_y0_x0")
    lab = cv2.imread(os.path.join(out, "segT_y0_x0_inklabels.png"), 0)
    assert lab.shape == (64, 64)
    assert lab[32, 32] == 255 and lab[0, 0] == 0  # binarized teacher
    assert sorted(os.listdir(os.path.join(out, "layers"))) == [
        f"{i:02d}.tif" for i in range(17, 43)
    ]
    assert os.path.exists(os.path.join(out, "segT_y0_x0_mask.png"))


def test_prep_loads_via_detector(tmp_path):
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask

    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.full((64, 64), 200, np.uint8)
    prep_distill_fragment(layers, teacher, str(tmp_path), "segT2_y0_x0")
    cfg = DetectorConfig(data_root=str(tmp_path))
    images, mask, frag_mask = read_image_mask(cfg, "segT2_y0_x0")
    assert images.shape[2] == 26
    assert mask.max() == 1.0  # teacher-positive label present


def test_prep_teacher_shape_mismatch_raises(tmp_path):
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((200, 20), np.uint8)  # >20% off in both axes
    with pytest.raises(ValueError, match="mismatch"):
        prep_distill_fragment(layers, teacher, str(tmp_path), "segT3_y0_x0")


def test_prep_accepts_uniform_scale_teacher(tmp_path):
    # teacher at 4x the region scale (level-0 teacher for a level-2 region)
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((256, 256), np.uint8)
    teacher[64:192, 64:192] = 200  # center block above threshold
    out = prep_distill_fragment(layers, teacher, str(tmp_path), "segS_y0_x0")
    lab = cv2.imread(os.path.join(out, "segS_y0_x0_inklabels.png"), 0)
    assert lab.shape == (64, 64)
    assert lab[32, 32] == 255 and lab[0, 0] == 0  # scaled + binarized correctly
