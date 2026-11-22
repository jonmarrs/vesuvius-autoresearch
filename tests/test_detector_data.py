import importlib
import os
import tracemalloc

import cv2
import numpy as np
import pytest
import torch

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


def _legacy_volume_mask(cfg, fragment_id):
    """Independent reference for the former padding/stacking recipe."""
    layers = []
    for index in range(cfg.start_idx, cfg.end_idx):
        plane = cv2.imread(
            str(os.path.join(cfg.data_root, fragment_id, "layers", f"{index:02d}.tif")),
            0,
        )
        height, width = plane.shape
        pad = (
            (0, cfg.tile_size - height % cfg.tile_size),
            (0, cfg.tile_size - width % cfg.tile_size),
        )
        layers.append(np.clip(np.pad(plane, pad), 0, 200))
    mask = cv2.imread(
        str(os.path.join(cfg.data_root, fragment_id, f"{fragment_id}_mask.png")), 0
    )
    return np.stack(layers, axis=2), np.pad(mask, pad), (height, width)


@pytest.mark.parametrize("shape", [(256, 256), (256, 320), (320, 256), (320, 320)])
def test_detector_uses_minimum_padding_and_preserves_clipped_ct(tmp_path, shape):
    height, width = shape
    _make_fake_fragment(str(tmp_path), "frag", h=height, w=width)
    first = tmp_path / "frag/layers/17.tif"
    values = cv2.imread(str(first), 0)
    values[0, 0] = 255
    assert cv2.imwrite(str(first), values)
    cfg = DetectorConfig(data_root=str(tmp_path))
    images, mask, original = D.read_volume_mask(cfg, "frag")
    expected = tuple(
        (size + cfg.tile_size - 1) // cfg.tile_size * cfg.tile_size for size in shape
    )
    assert images.shape == (*expected, cfg.in_chans)
    assert mask.shape == expected
    assert original == shape
    assert images.dtype == np.uint8
    for channel, layer in ((0, cfg.start_idx), (cfg.in_chans - 1, cfg.end_idx - 1)):
        plane = cv2.imread(str(tmp_path / "frag/layers" / f"{layer:02d}.tif"), 0)
        np.testing.assert_array_equal(
            images[:height, :width, channel], np.clip(plane, 0, 200)
        )
    assert not images[height:].any() and not images[:, width:].any()
    assert not mask[height:].any() and not mask[:, width:].any()


def test_detector_loading_keeps_traced_buffer_peak_below_two_full_stacks(tmp_path):
    # Unaligned dimensions isolate stacking overhead from the padding correction.
    # This measures traced allocations, not OpenCV/native or whole-process RSS.
    _make_fake_fragment(str(tmp_path), "frag", h=264, w=264)
    cfg = DetectorConfig(data_root=str(tmp_path))
    tracemalloc.start()
    try:
        images, _, _ = D.read_volume_mask(cfg, "frag")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert images.shape == (512, 512, cfg.in_chans)
    assert peak < images.nbytes * 1.5 + 1024**2, (peak, images.nbytes)


@pytest.mark.parametrize("shape", [(256, 256), (256, 320), (320, 256), (320, 320)])
@pytest.mark.parametrize("is_valid", [False, True])
def test_detector_tiles_and_labels_match_legacy_padding(
    tmp_path, monkeypatch, shape, is_valid
):
    _make_fake_fragment(str(tmp_path), "frag", h=shape[0], w=shape[1])
    cfg = DetectorConfig(data_root=str(tmp_path))
    actual = D._tiles_for_fragment(cfg, "frag", is_valid)
    monkeypatch.setattr(D, "read_volume_mask", _legacy_volume_mask)
    previous = D._tiles_for_fragment(cfg, "frag", is_valid)
    assert actual[2:] == previous[2:]
    for current, old in zip(actual[:2], previous[:2], strict=True):
        assert len(current) == len(old) > 0
        for first, second in zip(current, old, strict=True):
            np.testing.assert_array_equal(first, second)


def test_detector_inference_maps_and_coverage_match_legacy_padding(
    tmp_path, monkeypatch
):
    inference = importlib.import_module("vesuvius_autoresearch.detector.infer")
    _make_fake_fragment(str(tmp_path), "frag", h=256, w=320)
    cfg = DetectorConfig(data_root=str(tmp_path))

    class PatchMean(torch.nn.Module):
        def forward(self, x):
            return x.mean((2, 3, 4))[:, :, None, None]

    model = PatchMean()
    actual = inference.infer(
        cfg, None, "frag", model=model, batch_size=7, return_details=True
    )
    monkeypatch.setattr(inference, "read_volume_mask", _legacy_volume_mask)
    previous = inference.infer(
        cfg, None, "frag", model=model, batch_size=7, return_details=True
    )
    for name in ("probability", "coverage", "fragment_mask"):
        np.testing.assert_array_equal(getattr(actual, name), getattr(previous, name))
    assert actual.summary == previous.summary


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


def test_missing_layer_reports_the_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="layers/17.tif"):
        D.read_image_mask(DetectorConfig(data_root=str(tmp_path)), "absent")


def test_ambiguous_labels_are_rejected(tmp_path):
    _make_fake_fragment(str(tmp_path), "frag", h=64, w=64)
    cv2.imwrite(
        str(tmp_path / "frag/other_inklabels.png"), np.zeros((64, 64), np.uint8)
    )
    with pytest.raises(ValueError, match="exactly one inklabels"):
        D.read_image_mask(DetectorConfig(data_root=str(tmp_path)), "frag")


def test_small_depth_augmentation_stays_in_bounds():
    cfg = DetectorConfig(in_chans=8, start_idx=0, end_idx=8)
    dataset = D.CustomDataset([], cfg)
    assert dataset._fourth_augment(np.ones((64, 64, 8), np.uint8)).shape == (64, 64, 8)


def test_training_validation_overlap_fails_before_reading_data():
    cfg = DetectorConfig(train_fragment_ids=["same"], valid_fragment_id="same")
    with pytest.raises(ValueError, match="must not occur"):
        D.build_datasets(cfg)
