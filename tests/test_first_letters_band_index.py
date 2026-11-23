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


# --- the order's ties, the axis, the senses' edges, and the page's turns, thumbnails, masks and command line ---------


def _arc(theta, z, centre=(500.0, 600.0), radius=100.0):
    """Nodes at the given angles round the axis (one per column) and heights (one per row)."""
    tt, zz = np.meshgrid(np.asarray(theta, float), np.asarray(z, float))
    xyz = np.stack(
        [centre[0] + radius * np.cos(tt), centre[1] + radius * np.sin(tt), zz], -1
    )
    return xyz, np.ones(xyz.shape[:2], bool)


QUARTER = np.linspace(np.pi / 4, 3 * np.pi / 4, 12)  # theta rising with column
ROWS = 8000 + 20.0 * np.arange(6)  # z rising with row


def _senses(turn):
    return (
        turn["sign_dtheta_per_column"],
        turn["sign_dz_per_row"],
        turn["flip_lr"],
        turn["flip_ud"],
    )


def test_windings_with_the_same_largest_tile_go_by_name():
    s = {
        "w013": {"largest_tile_ink_share": 0.4},
        "w011": {"largest_tile_ink_share": 0.4},
        "w012": {"largest_tile_ink_share": None},
        "w010": {"largest_tile_ink_share": None},
    }
    assert bi.order(s) == ["w011", "w013", "w010", "w012"]


def test_the_axis_is_read_in_z_order_whatever_the_files_order(tmp_path):
    path = tmp_path / "umbilicus.json"
    path.write_text(json.dumps({"control_points": [
        {"x": 700, "y": 900, "z": 20000}, {"x": 500, "y": 600, "z": 0}, {"x": 600, "y": 800, "z": 10000}]}))  # fmt: skip
    assert bi.axis(path).tolist() == [
        [0, 10000, 20000],
        [500, 600, 700],
        [600, 800, 900],
    ]


def test_theta_is_measured_round_the_axis_own_x_and_y():
    # round (1000, 0) the arc's theta rises; round (1000, 1000), beyond the arc, it would fall
    xyz, valid = _arc(QUARTER, ROWS, centre=(1000.0, 0.0))
    axis = np.array([[0.0, 20000.0], [1000.0, 1000.0], [0.0, 0.0]])
    assert _senses(bi.orientation(xyz, valid, axis, False, False)) == (1, 1, True, True)


def test_nodes_that_do_not_exist_are_left_out_of_both_senses():
    # the first eight of each row's twelve nodes are missing (-1), as a tifxyz marks them
    xyz, valid = _arc(QUARTER, ROWS)
    valid[:, :8] = False
    xyz[~valid] = -1.0
    assert _senses(bi.orientation(xyz, valid, AXIS, False, False)) == (1, 1, True, True)


def test_a_winding_across_the_negative_x_direction_is_unwrapped():
    # theta runs pi - 0.2, pi - 0.05, then pi + 0.1, which atan2 gives as -pi + 0.1
    xyz, valid = _arc(np.pi + np.array([-0.2, -0.05, 0.1]), ROWS)
    assert _senses(bi.orientation(xyz, valid, AXIS, False, False)) == (1, 1, True, True)


@pytest.mark.parametrize(
    ("theta", "z", "senses"),
    [
        (QUARTER, [8000.0], (1, 0, True, False)),
        ([np.pi / 2], ROWS, (0, 1, False, True)),
    ],
    ids=["one-row", "one-column"],
)
def test_a_single_row_or_column_has_no_sense_along_it(theta, z, senses):
    xyz, valid = _arc(theta, z)
    assert _senses(bi.orientation(xyz, valid, AXIS, False, False)) == senses


def test_a_rows_height_is_its_median_node():
    # one node of the lower row sits 1000 above it: its mean would put that row above the next
    xyz, valid = _arc(QUARTER, [8000.0, 8020.0])
    xyz[0, -1, 2] = 9000.0
    assert _senses(bi.orientation(xyz, valid, AXIS, False, False)) == (1, 1, True, True)


def test_the_sense_along_a_row_is_the_median_step():
    # ten steps of +0.01 and one fold back of -2.0: the steps' sum is negative, their median positive
    theta = np.append(0.5 + 0.01 * np.arange(11), 0.6 - 2.0)
    xyz, valid = _arc(theta, ROWS)
    assert _senses(bi.orientation(xyz, valid, AXIS, False, False))[0] == 1


def _summary(tmp_path, windings, image=None):
    """A summary folder with each winding's image and numbers, the final meshes, and the axis at (500, 600)."""
    import cv2
    import tifffile

    if image is None:
        image = np.zeros((40, 64), np.uint8)
        image[:8, :8] = 255  # top left as rendered
    out, finals = tmp_path / "summary", tmp_path / "finals"
    (out / "images").mkdir(parents=True)
    rows = {}
    for rank, (name, (xyz, valid)) in enumerate(windings.items()):
        mesh = finals / f"{name}.tifxyz"
        mesh.mkdir(parents=True)
        for i, c in enumerate("xyz"):
            tifffile.imwrite(
                mesh / f"{c}.tif", np.where(valid, xyz[..., i], -1.0).astype(np.float32)
            )
        cv2.imwrite(str(out / "images" / f"{name}.png"), image)
        rows[name] = {
            "ink_share": 0.1,
            "largest_tile_ink_share": 0.5 - 0.1 * rank,
            "tiles_scored": 3,
        }
    (out / "summary.json").write_text(json.dumps({"windings": rows}))
    umbilicus = tmp_path / "umbilicus.json"
    umbilicus.write_text(json.dumps({"control_points": [{"x": 500, "y": 600, "z": 0}, {"x": 500, "y": 600, "z": 20000}]}))  # fmt: skip
    return out, finals, umbilicus


def _masks(tmp_path, names):
    """A trust mask per winding: its top left 8 x 8 trusted, the rest grey and dark grey pixel by pixel."""
    import cv2

    masks = tmp_path / "masks"
    masks.mkdir()
    mask = np.where(np.indices((40, 64)).sum(0) % 2 == 0, 64, 128).astype(np.uint8)
    mask[:8, :8] = 255
    for name in names:
        cv2.imwrite(str(masks / f"{name}.png"), mask)
    return masks


def test_the_page_turns_each_image_thumbnail_and_mask_and_says_how(tmp_path):
    import cv2

    # the recipe's frame: w010 (theta and z rising) is turned both ways, w011 (theta falling) upside down only
    windings = {"w010": _arc(QUARTER, ROWS), "w011": _arc(QUARTER[::-1], ROWS)}
    out, finals, umbilicus = _summary(tmp_path, windings)
    masks = _masks(tmp_path, windings)
    geometry = {"windings": {"w010": {"trusted": 0.812}, "w011": {}}}
    page = bi.build(
        out, finals, umbilicus, False, False, None, geometry, masks
    ).read_text()
    reading = cv2.imread(str(out / "images_reading" / "w010.png"), 0)
    assert reading[-8:, -8:].min() == 255 and reading[:8, :8].max() == 0
    assert cv2.imread(str(out / "images_reading" / "w011.png"), 0)[-8:, :8].min() == 255
    thumb = cv2.imread(str(out / "thumbs" / "w010.png"), 0)
    assert thumb.shape == (5, 8) and thumb[-1, -1] == 255 and thumb[0, 0] == 0
    trust = cv2.imread(str(out / "trust" / "w010.png"), 0)
    assert trust.shape == (5, 8) and trust[-1, -1] == 255
    assert set(np.unique(trust)) <= {64, 128, 255} and trust[0, 0] != 255
    assert "as rendered</a>; mirrored, upside down)" in page
    assert "as rendered</a>; upside down)" in page
    assert "<tr><td>1</td><td><a href='images_reading/w010.png'>" in page
    assert (
        "<tr><td>2</td><td><a href='images_reading/w011.png'>" in page
        and "<td>0.812</td>" in page
    )
    assert "<img src='trust/w010.png'>" in page and "None" not in page


def test_an_unturned_page_without_geometry_makes_no_masks(tmp_path):
    # PHerc. 211's frame: theta and z rising read as rendered
    out, finals, umbilicus = _summary(tmp_path, {"w010": _arc(QUARTER, ROWS)})
    page = bi.build(out, finals, umbilicus, True, False).read_text()
    assert "as rendered</a>; unturned)" in page
    assert not (out / "trust").exists() and "trust/" not in page


def test_a_missing_image_or_mask_stops_the_page(tmp_path):
    out, finals, umbilicus = _summary(tmp_path, {"w010": _arc(QUARTER, ROWS)})
    masks = tmp_path / "masks"
    masks.mkdir()
    with pytest.raises(SystemExit, match="no mask for w010"):
        bi.build(out, finals, umbilicus, False, False, None, {}, masks)
    (out / "images" / "w010.png").unlink()
    with pytest.raises(SystemExit, match="no image for w010"):
        bi.build(out, finals, umbilicus, False, False)


def test_a_map_smaller_than_a_thumbnail_step_still_gets_one_pixel(tmp_path):
    import cv2

    image = np.full((4, 4), 200, np.uint8)
    out, finals, umbilicus = _summary(tmp_path, {"w010": _arc(QUARTER, ROWS)}, image)
    bi.build(out, finals, umbilicus, False, False)
    assert cv2.imread(str(out / "thumbs" / "w010.png"), 0).shape == (1, 1)


def test_the_command_line_reads_the_fit_excess_and_the_geometry(tmp_path, capsys):
    out, finals, umbilicus = _summary(tmp_path, {"w010": _arc(QUARTER, ROWS)})
    masks = _masks(tmp_path, ["w010"])
    quality = tmp_path / "quality.json"
    quality.write_text(json.dumps({"windings": {"w010": {"excess": 0.25}}}))
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps({"windings": {"w010": {"trusted": 0.75}}}))
    common = [str(out), "--finals", str(finals), "--umbilicus", str(umbilicus)]
    with pytest.raises(SystemExit) as stop:
        bi.main(common + ["--top-to-bottom", "True", "--left-handed", "false"])
    assert stop.value.code == 2
    assert bi.main(common + ["--top-to-bottom", "false", "--left-handed", "false", "--quality", str(quality),
                             "--geometry", str(geometry), str(masks)]) == 0  # fmt: skip
    page = (out / "index.html").read_text()
    assert (
        "<td>0.25</td><td>0.75</td>" in page and (out / "trust" / "w010.png").exists()
    )
