"""The band read's inspection page: its order, its mirrored images and its links."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "repro/first_letters/eligible_band/band_index.py"
    spec = importlib.util.spec_from_file_location("band_index_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bi = _load()


def _summary(tmp_path: Path) -> Path:
    import cv2

    out = tmp_path / "summary"
    (out / "images").mkdir(parents=True)
    windings = {}
    for name, largest in (("w010", 0.1), ("w011", 0.4), ("w012", None)):
        image = np.zeros((40, 64), np.uint8)
        image[:, :8] = 255  # a bright stripe on the left of the image as rendered
        cv2.imwrite(str(out / "images" / f"{name}.png"), image)
        windings[name] = {
            "ink_share": 0.1,
            "largest_tile_ink_share": largest,
            "tiles_scored": 0 if largest is None else 3,
        }
    (out / "summary.json").write_text(json.dumps({"windings": windings}))
    return out


def test_the_order_puts_the_largest_tile_first_and_unscored_windings_last():
    s = {
        "w010": {"largest_tile_ink_share": 0.1},
        "w011": {"largest_tile_ink_share": 0.4},
        "w012": {"largest_tile_ink_share": None},
        "w013": {"largest_tile_ink_share": 0.4},
        "w014": {"largest_tile_ink_share": 0.0},  # scored, no ink: before the unscored
    }
    assert bi.order(s) == ["w011", "w013", "w010", "w014", "w012"]


def test_the_page_shows_mirrored_images_and_links_the_originals(tmp_path):
    import cv2

    out = _summary(tmp_path)
    page = bi.build(out, {"w011": {"excess": 0.12345}}).read_text()
    mirrored = cv2.imread(str(out / "images_mirrored" / "w010.png"), 0)
    assert (
        mirrored[:, -8:].min() == 255 and mirrored[:, :8].max() == 0
    )  # the stripe is now on the right
    assert (out / "thumbs" / "w010.png").exists()
    assert page.index("w011") < page.index("w010") < page.index("w012")
    assert "images_mirrored/w011.png" in page and "images/w011.png'>as rendered" in page
    assert "<td>0.123</td>" in page  # the fit's excess, rounded
    assert bi.main([]) == 2
