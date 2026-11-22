"""The Studio reference page draws known-letter maps as the band pages draw theirs: same encoding, turned into reading
orientation, thumbnails at one eighth with a 1 cm bar, and studio_band's numbers over the rendered area."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rp = _load("reference_page_under_test", BAND / "reference_page.py")


def _render(path: Path, rendered: np.ndarray) -> Path:
    import zarr

    data = np.zeros((66, *rendered.shape), np.uint8)
    data[33] = np.where(rendered, 100, 0)
    zarr.open(str(path), mode="w").create_dataset(
        "0", data=data, chunks=(66, *rendered.shape)
    )
    return path


def _panel(tmp_path, key="0211_w035", flip_ud=False, flip_lr=True):
    h, w = 760, 1140  # two by three tiles of 380
    rendered = np.zeros((h, w), bool)
    rendered[:, :760] = True  # the right third was not rendered: its tile is not scored
    prob = np.zeros((h, w), np.float32)
    prob[:380, :380] = 0.8  # the top-left tile is all ink
    np.save(tmp_path / f"{key}.npy", prob)
    render = _render(tmp_path / f"{key}_66.zarr", rendered)
    return rp.Panel(
        key,
        "PHerc. 211",
        "Studio",
        tmp_path / f"{key}.npy",
        render,
        flip_ud,
        flip_lr,
        9.362,
    )


def test_a_panel_is_turned_into_reading_orientation_and_scored_on_its_rendered_area(
    tmp_path,
):
    import cv2

    out = tmp_path / "page"
    path = rp.build(out, [_panel(tmp_path)])
    n = json.loads((out / "reference.json").read_text())["panels"]["0211_w035"]
    assert n["tiles_scored"] == 4 and n["largest_tile_ink_share"] == 1.0
    assert n["ink_share"] == 0.25  # one tile of ink over four rendered tiles
    image = cv2.imread(str(out / "images" / "0211_w035.png"), cv2.IMREAD_GRAYSCALE)
    assert image.shape == (760, 1140)
    assert (
        image[0, -1] == 204 and image[0, 0] == 0
    )  # mirrored: the ink is now top right (0.8 x 255)
    thumb = cv2.imread(str(out / "thumbs" / "0211_w035.png"), cv2.IMREAD_GRAYSCALE)
    assert thumb.shape == (95, 142)
    assert n["bar_px_on_thumbnail"] == 134  # 1 cm at 9.362 um, at one eighth
    assert (thumb[84:87, 6:140] == 255).all()  # the bar, bottom left
    assert (
        "0211_w035" in path.read_text()
        and "planes in reverse order" in path.read_text()
    )


def test_upside_down_flips_rows(tmp_path):
    import cv2

    out = tmp_path / "page"
    rp.build(out, [_panel(tmp_path, flip_ud=True, flip_lr=False)])
    image = cv2.imread(str(out / "images" / "0211_w035.png"), cv2.IMREAD_GRAYSCALE)
    assert image[-1, 0] == 204 and image[0, 0] == 0


def test_a_map_that_does_not_fit_its_render_is_refused(tmp_path):
    p = _panel(tmp_path)
    np.save(p.studio_map, np.zeros((10, 10), np.float32))
    try:
        rp.build(tmp_path / "page", [p])
    except SystemExit as e:
        assert "its render" in str(e)
    else:
        raise AssertionError("a map of the wrong shape was drawn")


def test_the_letter_sizes_and_band_links_are_on_the_page(tmp_path):
    sizes = tmp_path / "sizes.csv"
    sizes.write_text("id,height_mm\n1,2.0\n2,3.0\n3,5.0\n")
    letters = rp.letter_heights(sizes)
    assert letters == {"letters": 3, "median_mm": 3.0, "min_mm": 2.0, "max_mm": 5.0}
    page = rp.build(
        tmp_path / "page",
        [_panel(tmp_path)],
        letters,
        [("PHerc. 0826", "a/index.html")],
    ).read_text()
    assert "2.0 to 5.0 mm tall (median 3.0 mm)" in page
    assert "about 320 pixels at full resolution and 40 on a thumbnail" in page
    assert "<a href='../a/index.html'>PHerc. 0826</a>" in page
