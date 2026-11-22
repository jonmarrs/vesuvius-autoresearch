"""The band read's geometry record: normals against the scroll axis, the final winding against the predicted sheet
and the snapped triangles, and the trust mask the inspection page shows."""

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


class _Sheets:
    """A predicted sheet one voxel thick at each of these radii from the axis: signed distance, <= 0 inside."""

    def __init__(self, *radii):
        self.radii = np.array(radii)

    def at(self, xyz):
        r = np.hypot(xyz[:, 0] - AXIS_XY[0], xyz[:, 1] - AXIS_XY[1])
        return np.min(np.abs(r[:, None] - self.radii[None, :]), axis=1) - 1.0


def test_a_part_off_the_predicted_sheet_is_off_and_the_flip_swaps_the_side():
    final, fv = _ring()
    final = final.copy()
    final[:, 60:, :2] += (
        5.0 * (final[:, 60:, :2] - AXIS_XY) / 1000.0
    )  # 5 voxels outward: off the sheet
    field = _Sheets(1000.0)
    keep = bg.node_classes(final, fv, field, False, _centre)
    flip = bg.node_classes(final, fv, field, True, _centre)
    inner = keep[1:-1]  # the grid's edge rows have no normal: no surface
    assert (inner[:, 62:-1] == bg.OFF_SHEET).all()
    assert np.isin(inner[:, 1:58], (bg.TRUSTED, bg.OTHER_SIDE)).all()
    swapped = np.where(
        keep == bg.TRUSTED,
        bg.OTHER_SIDE,
        np.where(keep == bg.OTHER_SIDE, bg.TRUSTED, keep),
    )
    assert (flip == swapped).all()
    inward = bg.inward_share(final, fv, _centre)
    assert inward in (0.0, 1.0)  # a ring's normals all point one way
    # layers run outward where the render offsets along an outward normal
    assert (inner[:, 1:58] == (bg.TRUSTED if inward == 0.0 else bg.OTHER_SIDE)).all()


def test_distance_to_triangles_is_zero_on_the_surface_and_the_offset_off_it():
    grid, valid = _ring(
        columns=20
    )  # nodes about 80 voxels apart: nearest-node distances would be tens of voxels
    rng = np.random.default_rng(0)
    i, j = rng.integers(1, 8, 200), rng.integers(1, 18, 200)
    s, t = rng.uniform(0, 1, 200), rng.uniform(0, 1, 200)
    # points inside cells: bilinear in the cell, which on this ring lies within a voxel of its triangles
    p = (1 - s)[:, None] * (
        (1 - t)[:, None] * grid[i, j] + t[:, None] * grid[i, j + 1]
    ) + s[:, None] * (
        (1 - t)[:, None] * grid[i + 1, j] + t[:, None] * grid[i + 1, j + 1]
    )
    assert np.percentile(bg.distance_to_triangles(p, grid, valid), 99) < 1.0
    radial = (p[:, :2] - AXIS_XY) / np.linalg.norm(p[:, :2] - AXIS_XY, axis=1)[:, None]
    off = p.copy()
    off[:, :2] += 6.0 * radial
    d = bg.distance_to_triangles(off, grid, valid)
    assert np.all((d > 5.0) & (d < 7.5))


def test_a_degenerate_triangle_gives_a_distance_not_nan():
    p = np.array([[5.0, 5.0, 5.0], [3.0, 0.0, 4.0]])
    corner = np.zeros((2, 3))
    # all three corners at one point: the distance to that point (0 / 0 on an edge used to overwrite it with NaN)
    assert np.allclose(
        bg._closest_on_triangles(p, corner, corner, corner), [np.sqrt(75.0), 5.0]
    )
    # a plane grid 10 voxels apart with three corners of its first cell on one point: every distance stays finite
    ii, jj = np.meshgrid(np.arange(4) * 10.0, np.arange(4) * 10.0, indexing="ij")
    grid = np.stack([ii, jj, np.zeros_like(ii)], -1)
    grid[1, 0] = grid[0, 1] = grid[0, 0]
    q = np.array(
        [[0.0, 0.0, 1.0], [1.0, 1.0, 1.0], [15.0, 15.0, 1.0], [25.0, 5.0, 2.0]]
    )
    d = bg.distance_to_triangles(q, grid, np.ones(grid.shape[:2], bool))
    assert np.allclose(d, [1.0, 1.0, 1.0, 2.0])


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
    rec = bg.geometry(r, "a", tmp_path / "masks", field=_Sheets(1000.0, 1015.0))
    w = rec["windings"]
    assert w["w010"]["trusted"] == 1.0 and w["w010"]["other_side"] == 0.0
    assert w["w011"]["trusted"] == 0.0 and w["w011"]["other_side"] == 1.0
    assert w["w010"]["on_snapped_triangles"] == 1.0
    sheet = w["w010"]["predicted_sheet"]
    assert sheet["snapped"]["on_sheet"] == sheet["final"]["on_sheet"] == 1.0
    assert {
        v for v in sheet["final"]["within_2_by_radius_tercile"] if v is not None
    } == {1.0}
    assert (
        rec["summary"]["windings"] == 2
        and rec["summary"]["on_snapped_triangles_median"] == 1.0
    )
    import cv2

    mask = cv2.imread(str(tmp_path / "masks" / "w010.png"), cv2.IMREAD_GRAYSCALE)
    assert mask.shape == (10, 80) and (mask[1:-1, 1:-1] == bg.TRUSTED).all()


def test_a_sheet_the_field_does_not_have_is_off_it(tmp_path):
    r = _band(tmp_path)
    rec = bg.geometry(r, "a", None, field=_Sheets(1000.0))  # no sheet at w011's radius
    assert (
        rec["windings"]["w011"]["trusted"] == 0.0
        and rec["windings"]["w011"]["other_side"] == 0.0
    )
    assert rec["windings"]["w011"]["predicted_sheet"]["final"]["within_2"] == 0.0


def test_a_winding_with_no_normal_is_left_out_of_the_orientation_summary(tmp_path):
    import tifffile

    r = _band(tmp_path)
    final = r / "work" / "final_a" / "w011.tifxyz"
    xyz = np.stack([tifffile.imread(final / f"{a}.tif") for a in "xyz"], -1)
    lone = np.full_like(xyz, -1.0)
    lone[5, 40] = xyz[5, 40]  # one node and no neighbour, so no normal
    for i, axis in enumerate("xyz"):
        tifffile.imwrite(final / f"{axis}.tif", lone[..., i])
    rec = bg.geometry(r, "a", None, field=_Sheets(1000.0, 1015.0))
    assert rec["windings"]["w011"]["inward_against_axis"] is None
    w010 = rec["windings"]["w010"]["inward_against_axis"]
    assert rec["summary"]["inward_against_axis"] == {
        "median": w010,
        "min": w010,
        "max": w010,
    }
    assert rec["summary"]["rendered_against_the_axis_rule"] == []


def test_the_page_shows_the_trusted_share_and_the_mask_turned_like_the_image(tmp_path):
    import cv2

    r = _band(tmp_path)
    rec = bg.geometry(r, "a", tmp_path / "masks", field=_Sheets(1000.0, 1015.0))
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
