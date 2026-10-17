# tests/test_convert_fragment.py
import os

import cv2
import numpy as np
import pytest
from PIL import Image

from repro.gp_winner.convert_fragment import convert_fragment, convert_layer_u16_to_u8


def test_convert_layer_scales_u16_to_u8_by_256():
    arr = np.array([[0, 256, 65535]], dtype=np.uint16)
    out = convert_layer_u16_to_u8(arr)
    assert out.dtype == np.uint8
    assert out.tolist() == [[0, 1, 255]]


def test_convert_fragment_writes_cv2_readable_8bit_layers(tmp_path):
    src = tmp_path / "src" / "FragX"
    (src / "surface_volume").mkdir(parents=True)
    # 50 uint16 layers 00..49; only 17..42 should be converted
    for i in range(50):
        Image.fromarray(np.full((40, 32), i * 1000, dtype=np.uint16)).save(
            src / "surface_volume" / f"{i:02d}.tif"
        )
    Image.fromarray((np.eye(40, 32) * 255).astype(np.uint8)).save(src / "inklabels.png")
    Image.fromarray(np.full((40, 32), 255, dtype=np.uint8)).save(src / "mask.png")

    dst = tmp_path / "dst"
    stats = convert_fragment("FragX", str(tmp_path / "src"), str(dst), z_start=17, z_end=43)

    layers = sorted((dst / "FragX" / "layers").glob("*.tif"))
    assert len(layers) == 26  # 17..42
    back = cv2.imread(str(dst / "FragX" / "layers" / "17.tif"), 0)
    assert back is not None and back.dtype == np.uint8
    assert (dst / "FragX" / "FragX_inklabels.png").exists()
    assert (dst / "FragX" / "FragX_mask.png").exists()
    assert "17" in stats and "u8_max" in stats["17"]


def _source_fragment(root, frag_id, n_layers=50, shape=(40, 32)):
    src = root / frag_id
    (src / "surface_volume").mkdir(parents=True)
    for i in range(n_layers):
        Image.fromarray(np.full(shape, i * 1000, dtype=np.uint16)).save(
            src / "surface_volume" / f"{i:02d}.tif"
        )
    Image.fromarray(np.zeros(shape, dtype=np.uint8)).save(src / "inklabels.png")
    Image.fromarray(np.full(shape, 255, dtype=np.uint8)).save(src / "mask.png")


def _detector_cfg(dst, **overrides):
    from vesuvius_autoresearch.detector.config import DetectorConfig

    return DetectorConfig(
        data_root=str(dst),
        train_fragment_ids=["FragA"],
        valid_fragment_id="FragB",
        **overrides,
    )


def test_reproduce_redoes_a_conversion_that_lacks_a_file(tmp_path):
    """The reproduce path used to skip conversion whenever layers/ existed, so an
    interrupted conversion was trained on until a layer read failed."""
    from vesuvius_autoresearch.detector.cli import _ensure_converted

    for fid in ("FragA", "FragB"):
        _source_fragment(tmp_path / "src", fid)
    cfg = _detector_cfg(tmp_path / "dst")
    assert _ensure_converted(cfg, str(tmp_path / "src")) == ["FragA", "FragB"]
    assert _ensure_converted(cfg, str(tmp_path / "src")) == []

    (tmp_path / "dst" / "FragA" / "layers" / "30.tif").unlink()
    assert _ensure_converted(cfg, str(tmp_path / "src")) == ["FragA"]
    assert (tmp_path / "dst" / "FragA" / "layers" / "30.tif").exists()


def test_reproduce_converts_the_configured_layer_range(tmp_path):
    from vesuvius_autoresearch.detector.cli import _ensure_converted
    from vesuvius_autoresearch.detector.data import read_volume_mask

    for fid in ("FragA", "FragB"):
        _source_fragment(tmp_path / "src", fid)
    cfg = _detector_cfg(tmp_path / "dst", start_idx=11, end_idx=37)
    _ensure_converted(cfg, str(tmp_path / "src"))
    layers = sorted(p.name for p in (tmp_path / "dst" / "FragA" / "layers").iterdir())
    assert layers == [f"{i:02d}.tif" for i in range(11, 37)]
    images, _, shape = read_volume_mask(cfg, "FragA")
    assert images.shape[2] == 26 and shape == (40, 32)


def test_a_layer_is_never_left_partial_under_its_own_name(tmp_path, monkeypatch):
    """Each layer is written to a .part and renamed. Stopped before the fourth
    rename, the conversion leaves three layers and no file under a final name that
    it had not finished; reproduce's per-file check then redoes it."""
    _source_fragment(tmp_path / "src", "FragX")
    real = os.replace
    renamed = []

    def replace(src, dst):
        renamed.append(dst)
        if len(renamed) == 4:
            raise OSError("interrupted")
        return real(src, dst)

    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(OSError, match="interrupted"):
        convert_fragment("FragX", str(tmp_path / "src"), str(tmp_path / "dst"))
    out = tmp_path / "dst" / "FragX"
    assert sorted(p.name for p in (out / "layers").glob("*.tif")) == [
        "17.tif",
        "18.tif",
        "19.tif",
    ]
    assert not (out / "FragX_inklabels.png").exists()
