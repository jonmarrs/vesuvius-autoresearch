"""look_first.py: windows in the glyph order finding 138 tested, cropped from the reading images at the right columns."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "repro/first_letters/triage"
sys.path.insert(0, str(TRIAGE))
_spec = importlib.util.spec_from_file_location("look_first", TRIAGE / "look_first.py")
assert _spec and _spec.loader
lf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lf)


def _summary(tmp_path: Path) -> Path:
    s = tmp_path / "summary"
    (s / "images_reading").mkdir(parents=True)
    for name, width in (("w010", 6000), ("w011", 4000)):
        # each column's value is its map column modulo 256, so a crop shows which map columns it holds
        cols = np.arange(width) % 256
        img = np.tile(cols, (40, 1)).astype(np.uint8)
        flip = name == "w011"
        Image.fromarray(img[:, ::-1] if flip else img).save(
            s / "images_reading" / f"{name}.png"
        )
    (s / "orientation.json").write_text(
        json.dumps(
            {
                "w010": {"flip_lr": False, "flip_ud": True},
                "w011": {"flip_lr": True, "flip_ud": False},
            }
        )
    )
    return s


RECORD = {
    "windings": {
        "w010": [
            {"x0": 0, "glyph": 10.0},
            {"x0": 1300, "glyph": 12.0},
            {"x0": 3400, "glyph": 11.0},
        ],
        "w011": [
            {"x0": 0, "glyph": 12.0},
            {"x0": 1300, "glyph": None},
            {"x0": 1400, "glyph": 13.0},
        ],
    }
}


def test_the_order_is_glyph_rank_and_unscored_windows_are_left_out(tmp_path):
    out = lf.build(_summary(tmp_path), RECORD, first=2)
    got = [(r["rank"], r["winding"], r["x0"]) for r in out["order"]]
    # 13.0 first; the two 12.0 tie, broken by winding then x0; w011's unscored window is not ranked
    assert got == [
        (1, "w011", 1400),
        (2, "w010", 1300),
        (3, "w011", 0),
        (4, "w010", 3400),
        (5, "w010", 0),
    ]
    assert out["windows"] == 5


def test_crops_hold_the_scored_map_columns_in_reading_orientation(tmp_path):
    s = _summary(tmp_path)
    out = lf.build(s, RECORD, first=2)
    first, second = out["order"][:2]
    # w011 is mirrored: map columns 1400..4000 sit at reading columns 0..2600, in reverse
    assert first["columns_in_reading_image"] == [0, 2600]
    crop = np.asarray(Image.open(s / first["crop"]))
    assert crop.shape == (40, 2600)
    assert crop[0, 0] == (4000 - 1) % 256 and crop[0, -1] == 1400 % 256
    # w010 is not mirrored: map columns 1300..3900
    assert second["columns_in_reading_image"] == [1300, 3900]
    crop = np.asarray(Image.open(s / second["crop"]))
    assert crop[0, 0] == 1300 % 256 and crop[0, -1] == 3899 % 256
    assert out["order"][2]["crop"] is None  # only the first windows are cropped


def test_the_page_and_record_stay_in_the_summary_folder(tmp_path):
    s = _summary(tmp_path)
    lf.build(s, RECORD, first=2)
    made = sorted(
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()
    )
    assert made == [
        "summary/images_reading/w010.png",
        "summary/images_reading/w011.png",
        "summary/look_first.html",
        "summary/look_first.json",
        "summary/look_first/001_w011_x1400.png",
        "summary/look_first/002_w010_x1300.png",
        "summary/orientation.json",
    ]
    page = (s / "look_first.html").read_text()
    assert "says nothing about where text is" in page and "href='index.html'" in page
    assert page.count("<figure>") == 2 and page.count("<tr><td>") == 5
    assert "13.0" not in page  # the page orders; scores stay in the record


def test_a_window_at_the_end_is_cut_to_the_image():
    assert lf.reading_columns(3400, 6000, False) == (3400, 6000)
    assert lf.reading_columns(3400, 6000, True) == (0, 2600)
    assert lf.reading_columns(5000, 6000, False) == (5000, 6000)
