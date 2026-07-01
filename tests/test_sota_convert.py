import os
import sys

import cv2
import numpy as np
import pytest
import tifffile

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.convert import convert_surface_volume


def _make_src(root, seg, n_src=40, h=128, w=128, label_hw=None):
    layers = os.path.join(root, seg, "layers")
    os.makedirs(layers, exist_ok=True)
    for i in range(n_src):
        tifffile.imwrite(os.path.join(layers, f"{i:02d}.tif"),
                         (np.random.rand(h, w) * 60000).astype(np.uint16))
    lh, lw = label_hw or (h, w)
    lab = np.zeros((lh, lw), np.uint8)
    lab[lh // 4:lh // 2, lw // 4:lw // 2] = 255
    cv2.imwrite(os.path.join(root, seg, f"{seg}_inklabels.png"), lab)
    cv2.imwrite(os.path.join(root, seg, f"{seg}_mask.png"),
                np.full((lh, lw), 255, np.uint8))
    return os.path.join(root, seg)


def test_convert_writes_26_layers_and_labels(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segA")
    out = convert_surface_volume(src, "segA", str(tmp_path / "out"))
    layer_files = sorted(os.listdir(os.path.join(out, "layers")))
    assert layer_files == [f"{i:02d}.tif" for i in range(17, 43)]  # 26 layers, 17..42
    img = tifffile.imread(os.path.join(out, "layers", "17.tif"))
    assert img.shape == (128, 128) and img.dtype == np.uint8  # downcast to 8-bit
    assert os.path.exists(os.path.join(out, "segA_inklabels.png"))
    assert os.path.exists(os.path.join(out, "segA_mask.png"))


def test_convert_output_loads_via_detector(tmp_path):
    import sys
    sys.path.insert(0, os.path.abspath("."))
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask
    src = _make_src(str(tmp_path / "src"), "segB")
    convert_surface_volume(src, "segB", str(tmp_path / "out"))
    cfg = DetectorConfig(data_root=str(tmp_path / "out"))
    images, mask, frag_mask = read_image_mask(cfg, "segB")
    assert images.shape[2] == 26


def test_convert_too_few_layers_raises(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segC", n_src=10)
    with pytest.raises(ValueError, match="layers"):
        convert_surface_volume(src, "segC", str(tmp_path / "out"))


def test_convert_label_mismatch_raises(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segD", h=128, w=128, label_hw=(500, 30))
    with pytest.raises(ValueError, match="mismatch"):
        convert_surface_volume(src, "segD", str(tmp_path / "out"))
