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


def test_convert_float32_tiff_layers(tmp_path):
    """Regression test: float32 [0,1] TIFF layers should convert to non-zero uint8."""
    root = str(tmp_path / "src")
    seg = "segE"
    layers = os.path.join(root, seg, "layers")
    os.makedirs(layers, exist_ok=True)

    # Write 40 float32 layers in [0,1] range
    h, w = 128, 128
    for i in range(40):
        float_layer = (np.random.rand(h, w)).astype(np.float32)
        tifffile.imwrite(os.path.join(layers, f"{i:02d}.tif"), float_layer)

    # Add label and mask
    lab = np.zeros((h, w), np.uint8)
    lab[h // 4:h // 2, w // 4:w // 2] = 255
    cv2.imwrite(os.path.join(root, seg, f"{seg}_inklabels.png"), lab)
    cv2.imwrite(os.path.join(root, seg, f"{seg}_mask.png"),
                np.full((h, w), 255, np.uint8))

    # Convert
    out = convert_surface_volume(os.path.join(root, seg), seg, str(tmp_path / "out"))

    # Verify output layer 17.tif is uint8 and not all-zero
    layer_17 = tifffile.imread(os.path.join(out, "layers", "17.tif"))
    assert layer_17.dtype == np.uint8, f"Expected uint8, got {layer_17.dtype}"
    assert layer_17.max() > 0, "Output layer should not be all zeros"


def test_to_uint8_rejects_unexpected_int_dtype():
    from repro.sota_data.convert import to_uint8
    with pytest.raises(ValueError, match="dtype"):
        to_uint8(np.zeros((4, 4), np.int32))


def test_convert_unreadable_label_raises(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segE")
    # corrupt the label file so cv2.imread returns None
    with open(os.path.join(str(tmp_path / "src"), "segE", "segE_inklabels.png"), "wb") as f:
        f.write(b"not a png")
    with pytest.raises(ValueError, match="label"):
        convert_surface_volume(os.path.join(str(tmp_path / "src"), "segE"), "segE",
                               str(tmp_path / "out"))


def test_a_label_within_two_px_is_padded_onto_the_grid_not_stretched(tmp_path):
    """A label up to 20% off was resized onto the layers, moving every stroke."""
    src = _make_src(str(tmp_path / "src"), "segF", h=128, w=128, label_hw=(127, 128))
    out = convert_surface_volume(src, "segF", str(tmp_path / "out"))
    source = cv2.imread(os.path.join(src, "segF_inklabels.png"), 0)
    label = cv2.imread(os.path.join(out, "segF_inklabels.png"), 0)
    assert label.shape == (128, 128)
    assert np.array_equal(label[:127], source)  # registered at the origin
    assert not label[127].any()  # the missing row is padded, not invented
    mask = cv2.imread(os.path.join(out, "segF_mask.png"), 0)
    assert mask[:127].all() and not mask[127].any()


def test_rows_padded_onto_the_label_are_outside_the_mask(tmp_path):
    """Without a mask file the whole grid was valid, so padded rows read as negatives."""
    src = _make_src(str(tmp_path / "src"), "segI", h=128, w=128, label_hw=(128, 127))
    os.remove(os.path.join(src, "segI_mask.png"))
    out = convert_surface_volume(src, "segI", str(tmp_path / "out"))
    mask = cv2.imread(os.path.join(out, "segI_mask.png"), 0)
    assert mask[:, :127].all() and not mask[:, 127].any()


def test_the_tolerance_is_the_labeled_datasets():
    from repro.sota_data.convert import SHAPE_TOLERANCE_PX
    from vesuvius_autoresearch.core.vesuvius_loader import LABEL_SHAPE_TOLERANCE_PX

    assert SHAPE_TOLERANCE_PX == LABEL_SHAPE_TOLERANCE_PX


@pytest.mark.parametrize("name", ["inklabels", "mask"])
def test_a_label_or_mask_of_another_crop_or_scale_is_refused(tmp_path, name):
    """10% short: inside the old 20% bound, so it was stretched onto the layers."""
    src = _make_src(str(tmp_path / "src"), "segG", h=128, w=128)
    cv2.imwrite(os.path.join(src, f"segG_{name}.png"), np.full((115, 128), 255, np.uint8))
    with pytest.raises(ValueError, match="mismatch > 2 px"):
        convert_surface_volume(src, "segG", str(tmp_path / "out"))


@pytest.fixture
def fetch_module(monkeypatch):
    """repro.sota_data.fetch over an in-memory bucket (no network, no s3fs needed)."""
    import importlib
    import types

    import fsspec

    memory = fsspec.filesystem("memory")
    fake = types.ModuleType("s3fs")
    fake.S3FileSystem = lambda **kwargs: memory
    monkeypatch.setitem(sys.modules, "s3fs", fake)
    monkeypatch.delitem(sys.modules, "repro.sota_data.fetch", raising=False)
    module = importlib.import_module("repro.sota_data.fetch")
    yield module, memory
    sys.modules.pop("repro.sota_data.fetch", None)
    package = sys.modules["repro.sota_data"]
    if getattr(package, "fetch", None) is module:  # leave no module bound to the stand-in
        delattr(package, "fetch")


def test_fetch_puts_the_segment_where_convert_reads_it(tmp_path, fetch_module):
    """fsspec copied the segment directory into the existing out_dir, as
    out_dir/<segment>/, so convert found no layers at the returned path. And it copied
    everything, a SOTA segment's surface-volume zarrs included."""
    import io

    fetch, memory = fetch_module
    prefix = "PHercParis4/segments/segH_test_fetch"
    base = f"{fetch.BUCKET}/{prefix}"
    try:
        for i in range(30):
            buf = io.BytesIO()
            tifffile.imwrite(buf, np.full((64, 64), i * 2000, np.uint16))
            memory.pipe(f"{base}/layers/{i:02d}.tif", buf.getvalue())
        label = np.zeros((64, 64), np.uint8)
        label[16:32, 16:32] = 255
        png = cv2.imencode(".png", label)[1].tobytes()
        memory.pipe(f"{base}/segH_inklabels.png", png)
        memory.pipe(f"{base}/segH_mask.png", png)
        memory.pipe(f"{base}/surface-volumes/volume.zarr/0/0.0.0", b"not fetched")
        memory.pipe(f"{base}/segH_Mask_flat.PNG", b"not convert's *mask*")
        out = fetch.fetch_segment(prefix, str(tmp_path / "segH"))
    finally:
        memory.rm(base, recursive=True)
    assert out == str(tmp_path / "segH")
    assert not (tmp_path / "segH" / "segH_test_fetch").exists()
    assert sorted(os.listdir(out)) == ["layers", "segH_inklabels.png", "segH_mask.png"]
    converted = convert_surface_volume(out, "segH", str(tmp_path / "out"))
    assert len(os.listdir(os.path.join(converted, "layers"))) == 26


def test_fetch_refuses_a_mask_that_is_a_directory(tmp_path, fetch_module):
    """A non-recursive get skips a directory silently, and convert then used an
    all-valid mask."""
    fetch, memory = fetch_module
    base = f"{fetch.BUCKET}/PHercParis4/segments/segJ_test_fetch"
    try:
        memory.pipe(f"{base}/layers/00.tif", b"x")
        memory.pipe(f"{base}/masks/segJ_mask.png", b"y")
        with pytest.raises(ValueError, match="not a file"):
            fetch.fetch_segment("PHercParis4/segments/segJ_test_fetch", str(tmp_path / "j"))
    finally:
        memory.rm(base, recursive=True)
