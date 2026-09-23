"""measure_layout_rescoring: area vs density, and block-level rescoring, for two scored arms."""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from measure_layout_rescoring import compare  # noqa: E402

W, H = 8192, 40


def _arm(root: Path, strip: np.ndarray, mask: np.ndarray) -> Path:
    ink = root / "meshes" / "ink"
    pred = root / "ink_metric" / "predictions"
    ink.mkdir(parents=True)
    pred.mkdir(parents=True)
    half = strip.shape[1] // 2
    for k, sl in enumerate((slice(0, half), slice(half, None))):
        Image.fromarray(strip[:, sl]).save(ink / f"w120-129_flat.{k:03d}.png")
        Image.fromarray(mask[:, sl]).save(pred / f"w120-129_flat_mask.{k:03d}.png")
    return root


def _base(seed=0):
    rng = np.random.default_rng(seed)
    strip = np.full((H, W), 100, np.uint8)
    mask = ((rng.random((H, W)) > 0.95) * 255).astype(np.uint8)
    return strip, mask


def test_identical_arms_read_no_change(tmp_path):
    s, m = _base()
    r = compare(_arm(tmp_path / "a", s, m), _arm(tmp_path / "b", s, m), blocks=(1024,))
    assert r["covered_ratio"] == 1.0 and r["fg_ratio"] == 1.0
    assert r["block"][1024]["sd"] == 0.0


def test_more_ink_on_the_same_area_is_density_not_area(tmp_path):
    s, m = _base()
    m2 = m.copy()
    m2[:, :1024] = 255  # one block gains a lot of ink
    r = compare(_arm(tmp_path / "a", s, m), _arm(tmp_path / "b", s, m2), blocks=(1024,))
    assert r["covered_ratio"] == 1.0
    assert r["density_ratio"] > 1.5
    assert r["block"][1024]["sd"] > 0.5


def test_more_area_at_the_same_density_is_area(tmp_path):
    s, m = _base()
    s2 = s.copy()
    s[:, :1024] = 0  # A lacks one block of sheet, and its ink there
    m_a = m.copy()
    m_a[:, :1024] = 0
    r = compare(
        _arm(tmp_path / "a", s, m_a), _arm(tmp_path / "b", s2, m), blocks=(1024,)
    )
    assert r["covered_ratio"] > 1.1
    assert abs(r["density_ratio"] - 1.0) < 0.05
