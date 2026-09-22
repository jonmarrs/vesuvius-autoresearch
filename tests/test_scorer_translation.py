"""The scorer-translation study's builder and rule, tested before any arm existed.

The builder's one job is to change NOTHING but position: the shifted strip must
hold every decoded source pixel unchanged, offset by exactly (dy, dx), with only
black added. A lossy re-encode would confound the shift with compression.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_scorer_translation import verdict  # noqa: E402
from build_shifted_strip_arm import build, load_strip  # noqa: E402


def _tiles(d: Path, rng) -> np.ndarray:
    d.mkdir(parents=True)
    a = rng.integers(0, 256, (40, 90), dtype=np.uint8)
    b = rng.integers(
        0, 256, (37, 60), dtype=np.uint8
    )  # a shorter tile, like render_ink's last
    Image.fromarray(a).save(d / "w120-129_flat.000.jpg", quality=95)
    Image.fromarray(b).save(d / "w120-129_flat.001.jpg", quality=95)
    return load_strip(d)


def test_load_strip_matches_the_scorers_concatenation(tmp_path):
    """Same rule as get_ink_metrics.load_concat_strip: L, pad short tiles at the bottom."""
    s = _tiles(tmp_path / "ink", np.random.default_rng(0))
    assert s.shape == (40, 150)
    assert (s[37:, 90:] == 0).all()


def test_shift_preserves_every_pixel_and_adds_only_black(tmp_path):
    src = tmp_path / "ink"
    s = _tiles(src, np.random.default_rng(1))
    out = tmp_path / "arm" / "meshes" / "ink"
    build(src, out, dx=5, dy=3)
    files = sorted(out.iterdir())
    assert [f.name for f in files] == ["w120-129_flat.png"]
    got = np.asarray(Image.open(files[0]))
    assert got.shape == (s.shape[0] + 3, s.shape[1] + 5)
    assert np.array_equal(got[3:, 5:], s)
    assert (got[:3] == 0).all() and (got[:, :5] == 0).all()


def test_zero_shift_is_the_source_exactly(tmp_path):
    src = tmp_path / "ink"
    s = _tiles(src, np.random.default_rng(2))
    out = tmp_path / "arm" / "meshes" / "ink"
    build(src, out, dx=0, dy=0)
    assert np.array_equal(np.asarray(Image.open(out / "w120-129_flat.png")), s)


def test_verdict_bands():
    F = 24 / 1_698_831
    assert verdict(spread=0.02, floor=F)[0] == "LAYOUT-SENSITIVE"
    assert verdict(spread=0.004, floor=F)[0] == "SENSITIVE, SMALL"
    assert verdict(spread=2 * F, floor=F)[0] == "INSENSITIVE"


def test_block_sd_aligns_a_shifted_mask_back_to_source_coordinates(tmp_path):
    """A shifted arm's mask is offset by (dy, dx). After undoing the offset an
    identical prediction must read a per-block change of exactly 0."""
    from analyse_scorer_translation import block_sd

    rng = np.random.default_rng(3)
    m = (rng.random((50, 6000)) > 0.9).astype(np.uint8) * 255
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    Image.fromarray(m).save(a / "w120-129_flat_mask.png")
    Image.fromarray(np.pad(m, ((4, 0), (7, 0)))).save(b / "w120-129_flat_mask.png")
    assert block_sd(a, b, dx=7, dy=4, block=1000) == 0.0
    m2 = m.copy()
    m2[:, :1000] = 0  # wipe one block of the second prediction
    Image.fromarray(np.pad(m2, ((4, 0), (7, 0)))).save(b / "w120-129_flat_mask.png")
    assert block_sd(a, b, dx=7, dy=4, block=1000) > 0.1
