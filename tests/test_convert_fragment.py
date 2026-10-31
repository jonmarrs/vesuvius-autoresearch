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
    stats = convert_fragment(
        "FragX", str(tmp_path / "src"), str(dst), z_start=17, z_end=43
    )

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
    interrupted conversion failed at its first missing layer on every later run."""
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


def test_interrupted_staging_publishes_no_fragment(tmp_path, monkeypatch):
    """A failed fourth write no longer exposes a partial generation."""
    from vesuvius_autoresearch.core import fragment_conversion as conversion

    _source_fragment(tmp_path / "src", "FragX")
    real = conversion._write
    written = []

    def write(path, data):
        written.append(path)
        if len(written) == 4:
            raise OSError("interrupted")
        return real(path, data)

    monkeypatch.setattr(conversion, "_write", write)
    with pytest.raises(OSError, match="interrupted"):
        convert_fragment("FragX", str(tmp_path / "src"), str(tmp_path / "dst"))
    out = tmp_path / "dst" / "FragX"
    assert not out.exists()
    assert list((tmp_path / "dst").iterdir()) == []


def test_a_conversion_for_another_layer_range_is_redone(tmp_path):
    from vesuvius_autoresearch.detector.cli import _ensure_converted

    for fid in ("FragA", "FragB"):
        _source_fragment(tmp_path / "src", fid)
    _ensure_converted(_detector_cfg(tmp_path / "dst"), str(tmp_path / "src"))
    shifted = _detector_cfg(tmp_path / "dst", start_idx=11, end_idx=37)
    assert _ensure_converted(shifted, str(tmp_path / "src")) == ["FragA", "FragB"]


def test_a_conversion_missing_its_mask_is_redone(tmp_path):
    from vesuvius_autoresearch.detector.cli import _ensure_converted

    for fid in ("FragA", "FragB"):
        _source_fragment(tmp_path / "src", fid)
    cfg = _detector_cfg(tmp_path / "dst")
    _ensure_converted(cfg, str(tmp_path / "src"))
    (tmp_path / "dst" / "FragB" / "FragB_mask.png").unlink()
    assert _ensure_converted(cfg, str(tmp_path / "src")) == ["FragB"]


def test_an_interrupted_label_write_preserves_the_entire_prior_fragment(
    tmp_path, monkeypatch
):
    from vesuvius_autoresearch.core import fragment_conversion as conversion
    from vesuvius_autoresearch.detector.cli import _ensure_converted, _is_converted

    for fid in ("FragA", "FragB"):
        _source_fragment(tmp_path / "src", fid)
    cfg = _detector_cfg(tmp_path / "dst")
    _ensure_converted(cfg, str(tmp_path / "src"))
    (tmp_path / "dst" / "FragA" / "layers" / "20.tif").unlink()
    out = tmp_path / "dst" / "FragA"
    before = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    real = conversion._write

    def write(path, data):
        if path.name.endswith("_inklabels.png"):
            raise OSError("interrupted")
        return real(path, data)

    monkeypatch.setattr(conversion, "_write", write)
    with pytest.raises(OSError, match="interrupted"):
        _ensure_converted(cfg, str(tmp_path / "src"))
    monkeypatch.undo()
    assert not _is_converted(
        cfg, "FragA"
    )  # the pre-existing missing layer stays missing
    assert before == {
        p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()
    }
    assert _ensure_converted(cfg, str(tmp_path / "src")) == ["FragA"]
    assert _is_converted(cfg, "FragA")


def test_a_label_under_another_name_counts_as_converted(tmp_path):
    """read_image_mask takes any single *inklabels.*, such as villa's own
    <id>_inklabels.tiff, so such a fragment is not re-converted."""
    from vesuvius_autoresearch.detector.cli import _ensure_converted

    for fid in ("FragA", "FragB"):
        _source_fragment(tmp_path / "src", fid)
    cfg = _detector_cfg(tmp_path / "dst")
    _ensure_converted(cfg, str(tmp_path / "src"))
    label = tmp_path / "dst" / "FragA" / "FragA_inklabels.png"
    label.rename(label.with_suffix(".tiff"))
    # Native/legacy fragments do not carry the new converter's output manifest.
    (label.parent / "conversion.json").unlink()
    assert _ensure_converted(cfg, str(tmp_path / "src")) == []


@pytest.mark.parametrize("valid_id", ["../escape", "FragA"])
def test_reproduce_rejects_invalid_or_overlapping_ids_before_conversion(
    tmp_path, valid_id
):
    from vesuvius_autoresearch.detector.cli import _ensure_converted

    cfg = _detector_cfg(tmp_path / "dst")
    cfg.valid_fragment_id = valid_id
    with pytest.raises(ValueError, match="single directory|distinct"):
        _ensure_converted(cfg, str(tmp_path / "src"))
    assert not (tmp_path / "dst").exists()


def test_reproduce_cannot_import_an_ambient_converter(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace

    from vesuvius_autoresearch.detector.cli import _ensure_converted

    def wrong_converter(*args, **kwargs):
        raise AssertionError("ambient converter was called")

    monkeypatch.setitem(
        sys.modules,
        "convert_fragment",
        SimpleNamespace(convert_fragment=wrong_converter),
    )
    for fid in ("FragA", "FragB"):
        _source_fragment(tmp_path / "src", fid)
    assert _ensure_converted(
        _detector_cfg(tmp_path / "dst"), str(tmp_path / "src")
    ) == ["FragA", "FragB"]
