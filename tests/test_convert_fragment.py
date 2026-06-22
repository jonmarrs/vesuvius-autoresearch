# tests/test_convert_fragment.py
import cv2
import numpy as np
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
