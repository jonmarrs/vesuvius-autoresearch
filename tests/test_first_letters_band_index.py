"""The band read's inspection page: its order, the reading-orientation rule and its links."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "repro/first_letters/eligible_band/band_index.py"
    spec = importlib.util.spec_from_file_location("band_index_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bi = _load()


def _ring(theta_increasing: bool, z_increasing: bool):
    """A quarter turn of a sheet round the axis at (500, 600): 6 rows by 12 columns of nodes."""
    theta = np.linspace(0, np.pi / 2, 12)
    theta = theta if theta_increasing else theta[::-1]
    z = np.arange(6) * 20.0 + 8000
    z = z if z_increasing else z[::-1]
    tt, zz = np.meshgrid(theta, z)
    xyz = np.stack([500 + 100 * np.cos(tt), 600 + 100 * np.sin(tt), zz], -1)
    return xyz, np.ones(xyz.shape[:2], bool)


AXIS = np.array([[0.0, 20000.0], [500.0, 500.0], [600.0, 600.0]])  # z, x, y


@pytest.mark.parametrize(
    ("theta_up", "z_up", "ttb", "lh", "flip_lr", "flip_ud"),
    [
        (True, True, False, False, True, True),  # PHerc. 343's frame: the recipe's rule
        (False, False, False, False, False, False),
        (
            True,
            True,
            True,
            False,
            False,
            False,
        ),  # PHerc. 211's frame, as the winner's surface: unturned
        (
            False,
            True,
            True,
            False,
            True,
            False,
        ),  # PHerc. 211's frame, as our w035: mirrored only
        (True, True, False, True, False, True),  # left-handed: theta's sense reversed
    ],
)
def test_the_reading_orientation_rule(theta_up, z_up, ttb, lh, flip_lr, flip_ud):
    turn = bi.orientation(*_ring(theta_up, z_up), AXIS, ttb, lh)
    assert (turn["flip_lr"], turn["flip_ud"]) == (flip_lr, flip_ud)


def test_the_order_puts_the_largest_tile_first_and_unscored_windings_last():
    s = {
        "w010": {"largest_tile_ink_share": 0.1},
        "w011": {"largest_tile_ink_share": 0.4},
        "w012": {"largest_tile_ink_share": None},
        "w013": {"largest_tile_ink_share": 0.4},
        "w014": {"largest_tile_ink_share": 0.0},  # scored, no ink: before the unscored
    }
    assert bi.order(s) == ["w011", "w013", "w010", "w014", "w012"]


def test_the_page_turns_each_image_and_links_the_original(tmp_path):
    import cv2
    import tifffile

    out = tmp_path / "summary"
    finals = tmp_path / "finals"
    (out / "images").mkdir(parents=True)
    windings = {}
    for name, theta_up, largest in (("w010", True, 0.1), ("w011", False, 0.4)):
        xyz, _ = _ring(theta_up, True)
        mesh = finals / f"{name}.tifxyz"
        mesh.mkdir(parents=True)
        for i, axis_name in enumerate("xyz"):
            tifffile.imwrite(mesh / f"{axis_name}.tif", xyz[..., i].astype(np.float32))
        image = np.zeros((40, 64), np.uint8)
        image[:8, :8] = 255  # top left as rendered
        cv2.imwrite(str(out / "images" / f"{name}.png"), image)
        windings[name] = {
            "ink_share": 0.1,
            "largest_tile_ink_share": largest,
            "tiles_scored": 3,
        }
    (out / "summary.json").write_text(json.dumps({"windings": windings}))
    umbilicus = tmp_path / "umbilicus.json"
    umbilicus.write_text(
        json.dumps(
            {
                "control_points": [
                    {"x": 500, "y": 600, "z": 0},
                    {"x": 500, "y": 600, "z": 20000},
                ]
            }
        )
    )
    page = bi.build(
        out, finals, umbilicus, True, False, {"w011": {"excess": 0.12345}}
    ).read_text()
    # PHerc. 211's frame: w010 (theta up, z up) unturned, w011 (theta down) mirrored
    assert cv2.imread(str(out / "images_reading" / "w010.png"), 0)[:8, :8].min() == 255
    assert cv2.imread(str(out / "images_reading" / "w011.png"), 0)[:8, -8:].min() == 255
    turns = json.loads((out / "orientation.json").read_text())
    assert turns["w011"]["flip_lr"] and not turns["w010"]["flip_lr"]
    assert page.index("w011") < page.index("w010")
    assert "images_reading/w011.png" in page and "images/w011.png'>as rendered" in page
    assert "mirrored" in page and "<td>0.123</td>" in page
