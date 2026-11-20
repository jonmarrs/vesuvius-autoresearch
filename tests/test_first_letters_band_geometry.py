"""The band read's geometry record: normals against the scroll axis, the final winding against its snapped sheet,
and the trust mask the inspection page shows."""

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


bg = _load("band_geometry_under_test", BAND / "band_geometry.py")
bi = _load("band_index_for_geometry", BAND / "band_index.py")

AXIS_XY = (500.0, 600.0)


def _ring(radius=1000.0, columns=80, rows=10, theta_up=True):
    """A quarter turn round the axis at AXIS_XY, nodes about 20 voxels apart, as a tifxyz at scale 0.05."""
    theta = np.linspace(0, np.pi / 2, columns)
    theta = theta if theta_up else theta[::-1]
    z = np.arange(rows) * 20.0 + 8000
    tt, zz = np.meshgrid(theta, z)
    xyz = np.stack(
        [AXIS_XY[0] + radius * np.cos(tt), AXIS_XY[1] + radius * np.sin(tt), zz], -1
    )
    return xyz, np.ones(xyz.shape[:2], bool)


def _centre(z):
    return np.broadcast_to(np.array(AXIS_XY), (len(z), 2))


def test_a_hole_in_the_snap_and_a_displaced_part_are_off_the_sheet_and_the_flip_swaps_the_side():
    final, fv = _ring()
    final = final.copy()
    final[:, 60:, :2] += (
        5.0 * (final[:, 60:, :2] - AXIS_XY) / 1000.0
    )  # 5 voxels outward: off the sheet
    snap, sv = _ring()
    sv = sv.copy()
    sv[:, 16:48] = (
        False  # a hole of 32 columns, about 640 voxels: its middle is uncovered
    )
    keep = bg.node_classes(final, fv, snap, sv, False, _centre)
    flip = bg.node_classes(final, fv, snap, sv, True, _centre)
    inner = keep[1:-1]  # the grid's edge rows have no normal: no surface
    on_sheet = (inner == bg.TRUSTED) | (inner == bg.OTHER_SIDE)
    assert (inner[:, 26:38] == bg.OFF_SHEET).all() and (
        inner[:, 62:-1] == bg.OFF_SHEET
    ).all()
    assert on_sheet[:, 1:12].all()
    swapped = np.where(
        keep == bg.TRUSTED,
        bg.OTHER_SIDE,
        np.where(keep == bg.OTHER_SIDE, bg.TRUSTED, keep),
    )
    assert (flip == swapped).all()
    inward = bg.inward_share(final, fv, _centre)
    assert inward in (0.0, 1.0)  # a ring's normals all point one way
    # layers run outward where the render offsets along an outward normal
    assert (inner[:, 1:12] == (bg.TRUSTED if inward == 0.0 else bg.OTHER_SIDE)).all()


def _band(tmp_path):
    import tifffile

    r = tmp_path / "band"
    work = r / "work"
    names = ["w010", "w011"]
    (r / "dataset").mkdir(parents=True)
    (r / "dataset" / "umbilicus.json").write_text(json.dumps({"control_points": [
        {"x": AXIS_XY[0], "y": AXIS_XY[1], "z": 0}, {"x": AXIS_XY[0], "y": AXIS_XY[1], "z": 20000}]}))  # fmt: skip
    work.mkdir()
    (work / "windings_a.txt").write_text("\n".join(names) + "\n")
    orient = {}
    for k, name in enumerate(names):
        xyz, _ = _ring(radius=1000.0 + 15 * k)
        for folder in (work / "final_a" / f"{name}.tifxyz", work / "snap_a" / name):
            folder.mkdir(parents=True)
            for i, axis in enumerate("xyz"):
                tifffile.imwrite(folder / f"{axis}.tif", xyz[..., i].astype(np.float32))
        inward = bg.inward_share(xyz, np.ones(xyz.shape[:2], bool), _centre)
        # w010 rendered as the axis rule says, w011 the other way
        right = "flip" if inward > 0.5 else "keep"
        orient[name] = {
            "render": right
            if name == "w010"
            else ("keep" if right == "flip" else "flip")
        }
    (work / "studio_a").mkdir()
    (work / "studio_a" / "orient.json").write_text(json.dumps({"windings": orient}))
    return r


def test_the_record_counts_trusted_area_and_names_windings_rendered_against_the_axis(
    tmp_path,
):
    r = _band(tmp_path)
    rec = bg.geometry(r, "a", tmp_path / "masks")
    w = rec["windings"]
    assert w["w010"]["trusted"] == 1.0 and w["w010"]["other_side"] == 0.0
    assert w["w011"]["trusted"] == 0.0 and w["w011"]["other_side"] == 1.0
    assert (
        w["w010"]["final_on_snap"]["covered"] == 1.0
    )  # nodes 20 voxels apart: the edges are covered too
    assert rec["summary"]["windings"] == 2
    import cv2

    mask = cv2.imread(str(tmp_path / "masks" / "w010.png"), cv2.IMREAD_GRAYSCALE)
    assert mask.shape == (10, 80) and (mask[1:-1, 1:-1] == bg.TRUSTED).all()


def test_the_page_shows_the_trusted_share_and_the_mask_turned_like_the_image(tmp_path):
    import cv2

    r = _band(tmp_path)
    rec = bg.geometry(r, "a", tmp_path / "masks")
    (tmp_path / "geom.json").write_text(json.dumps(rec))
    out = tmp_path / "summary"
    (out / "images").mkdir(parents=True)
    windings = {}
    for name in ("w010", "w011"):
        cv2.imwrite(
            str(out / "images" / f"{name}.png"), np.zeros((200, 1600), np.uint8)
        )
        windings[name] = {
            "ink_share": 0.1,
            "largest_tile_ink_share": 0.2,
            "tiles_scored": 1,
        }
    (out / "summary.json").write_text(json.dumps({"windings": windings}))
    page = bi.build(out, r / "work" / "final_a", r / "dataset" / "umbilicus.json", True, False, None, rec,
                    tmp_path / "masks").read_text()  # fmt: skip
    assert (
        "<th>trusted</th>" in page and "<td>1.0</td>" in page and "<td>0.0</td>" in page
    )
    assert "trust/w010.png" in page
    thumb = cv2.imread(str(out / "thumbs" / "w010.png"), cv2.IMREAD_GRAYSCALE)
    trust = cv2.imread(str(out / "trust" / "w010.png"), cv2.IMREAD_GRAYSCALE)
    assert trust.shape == thumb.shape
    assert bi.main([str(out), "--finals", str(r / "work" / "final_a"), "--umbilicus", str(r / "dataset" / "umbilicus.json"),
                    "--top-to-bottom", "true", "--left-handed", "false", "--geometry", str(tmp_path / "geom.json"),
                    str(tmp_path / "masks")]) == 0  # fmt: skip
