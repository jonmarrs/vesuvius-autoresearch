# tests/test_ink_repro_dataset.py
import numpy as np
from PIL import Image

from repro.ink_segformer.dataset import InkTileDataset, compute_tile_origins


def _make_fragment(tmp_path, h=64, w=48, layers=20):
    d = tmp_path / "frag"
    (d / "surface_volume").mkdir(parents=True)
    for i in range(layers):
        Image.fromarray(np.full((h, w), i * 10, dtype=np.uint16)).save(
            d / "surface_volume" / f"{i:02d}.tif"
        )
    ink = np.zeros((h, w), dtype=np.uint8)
    ink[10:30, 5:25] = 255
    Image.fromarray(ink).save(d / "inklabels.png")
    mask = np.full((h, w), 255, dtype=np.uint8)
    Image.fromarray(mask).save(d / "mask.png")
    return str(d)


def test_compute_tile_origins_covers_masked_area_with_stride():
    mask = np.ones((64, 48), dtype=bool)
    origins = compute_tile_origins(mask, tile=32, stride=16, min_papyrus=0.05)
    # origins are clamped so a full 32-tile fits; (0,0) present, all in-bounds
    assert (0, 0) in origins
    assert all(0 <= y <= 64 - 32 and 0 <= x <= 48 - 32 for y, x in origins)


def test_dataset_returns_aligned_shapes(tmp_path):
    frag = _make_fragment(tmp_path)
    ds = InkTileDataset(
        [frag], tile=32, stride=16, z_start=4, z_count=8, min_papyrus=0.0
    )
    vol, ink, pmask = ds[0]
    assert vol.shape == (1, 8, 32, 32)
    assert ink.shape == (1, 32, 32) and pmask.shape == (1, 32, 32)
    assert vol.dtype.__str__() == "torch.float32"
    assert float(ink.max()) <= 1.0 and float(ink.min()) >= 0.0
