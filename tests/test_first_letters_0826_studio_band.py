"""Finding 125: the orientation rule on windings whose way is known, the per-winding summary, and the driver."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"


def _load():
    spec = importlib.util.spec_from_file_location(
        "studio_band_under_test", BAND / "studio_band.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sb = _load()


def _ring(path: Path, radius: float, reverse: bool = False) -> Path:
    """A cylinder of nodes round (500, 600), 20 voxels apart in z; `reverse` runs it the other way round."""
    import tifffile

    theta = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    if reverse:
        theta = theta[::-1]
    z = np.arange(6) * 20.0 + 8000
    tt, zz = np.meshgrid(theta, z)
    path.mkdir(parents=True)
    for axis, values in (
        ("x", 500 + radius * np.cos(tt)),
        ("y", 600 + radius * np.sin(tt)),
        ("z", zz),
    ):
        tifffile.imwrite(path / f"{axis}.tif", values.astype(np.float32))
    return path


def test_a_winding_run_the_other_way_round_gets_the_other_render(tmp_path):
    a = _ring(tmp_path / "w010.tifxyz", 100.0)
    b = _ring(tmp_path / "w011.tifxyz", 130.0, reverse=True)
    result = sb.orientation([a, b])
    assert result["centre_xyz"][:2] == [500.0, 600.0]
    shares = {
        n: e["share_of_normals_pointing_inward"] for n, e in result["windings"].items()
    }
    assert {round(v) for v in shares.values()} == {
        0,
        1,
    }  # one all inward, the other all outward
    renders = {n: e["render"] for n, e in result["windings"].items()}
    assert sorted(renders.values()) == ["flip", "keep"]
    assert (
        renders[min(shares, key=shares.get)] == "keep"
    )  # mostly outward: as the winner's PHerc. 211 surface


def test_the_summary_writes_an_image_a_contact_sheet_and_tile_numbers(tmp_path):
    import cv2
    import zarr

    maps = tmp_path / "maps"
    renders = tmp_path / "renders"
    maps.mkdir()
    prob = np.zeros((800, 1200), np.float32)
    prob[100:300, 100:500] = 0.9  # ink in the first tile row
    np.save(maps / "w020.npy", prob)
    layer = np.zeros((66, 800, 1200), np.uint8)
    layer[33, :, :1000] = 100  # rendered over the left 1,000 columns
    zarr.open(str(renders / "w020_66.zarr"), mode="w").create_dataset(
        "0", data=layer, chunks=(66, 800, 1200)
    )
    summary = sb.summarise(tmp_path / "out", maps, renders)["windings"]["w020"]
    assert summary["rendered_pixels"] == 800 * 1000
    assert summary["ink_share"] == round(200 * 400 / (800 * 1000), 4)
    # tiles of 380: two rows of two whole tiles inside the rendered 1,000 columns (the third column of tiles is cut)
    assert summary["tiles_scored"] == 4
    first = [t for t in summary["tiles"] if t["row"] == 0 and t["col"] == 0][0]
    assert first["ink_share"] == round(200 * 280 / 380**2, 4)
    image = cv2.imread(str(tmp_path / "out" / "images" / "w020.png"), 0)
    assert image.shape == prob.shape and image[200, 200] == 230
    assert (tmp_path / "out" / "contact_sheet.png").exists()
    assert json.loads((tmp_path / "out" / "summary.json").read_text())[
        "contact_sheet_order"
    ] == ["w020"]


def test_the_lines_are_the_registrations():
    assert (sb.TILE, sb.INK) == (380, 0.5)
    text = (
        ROOT / "docs/preregistration/2026-11-20_first_letters_0826_studio_band.md"
    ).read_text()
    assert (
        "flip a winding when more than half of its normals point toward the band's centre"
        in text
    )
    assert "our layers 41 down to 26" in text


def test_the_driver_reads_every_winding_and_keeps_going_past_a_failure():
    path = BAND / "run_studio_band.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
        assert word not in text
    order = [
        "stage snap",
        "for_each flatten",
        "stage orient",
        "for_each render",
        "for_each studio",
        "stage summarise",
    ]
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)
    assert (
        "W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90" in text
    )
    assert "--stride 64 --blend hann" in text and "--batch-size 32" in text
    assert (
        "grep -E '^w[0-9]+$'" in text
    )  # raw windings only: villa's _spliced twins are skipped
    assert 'LIVE=("${kept[@]}")' in text


# --- the scroll axis, the lines met exactly, the refusals, select and stacked -------------------------------------


def _umbilicus(path: Path, points: list[dict]) -> Path:
    path.write_text(json.dumps({"control_points": points}))
    return path


def test_the_scroll_axis_is_interpolated_in_z_from_points_in_any_order(tmp_path):
    umbilicus = _umbilicus(
        tmp_path / "u.json",
        [{"z": 9000, "x": 400, "y": 700}, {"z": 7000, "x": 600, "y": 500}],
    )
    assert sb.axis_xy(umbilicus, np.array([8000.0])).tolist() == [[500.0, 600.0]]


def _arc(path: Path, cx: float, cy: float) -> Path:
    import tifffile

    theta = np.linspace(0.1, np.pi - 0.1, 32)
    tt, zz = np.meshgrid(theta, np.arange(6) * 20.0 + 8000)
    path.mkdir()
    for axis, values in (
        ("x", cx + 100 * np.cos(tt)),
        ("y", cy + 100 * np.sin(tt)),
        ("z", zz),
    ):
        tifffile.imwrite(path / f"{axis}.tif", values.astype(np.float32))
    return path


def test_against_the_scroll_axis_a_winding_off_the_bands_centre_points_one_way(
    tmp_path,
):
    # a second winding 2,000 voxels away pulls the band's centre outside the first one's curve
    near = _arc(tmp_path / "w010.tifxyz", 500.0, 600.0)
    far = _arc(tmp_path / "w011.tifxyz", 2500.0, 600.0)
    umbilicus = _umbilicus(
        tmp_path / "u.json",
        [{"z": 7000, "x": 500, "y": 600}, {"z": 9000, "x": 500, "y": 600}],
    )
    centre = sb.orientation([near, far])["windings"]["w010"][
        "share_of_normals_pointing_inward"
    ]
    axis = sb.orientation([near, far], umbilicus)
    assert axis["reference"] == "scroll_axis"
    assert axis["windings"]["w010"]["share_of_normals_pointing_inward"] in (0.0, 1.0)
    assert 0.0 < centre < 1.0


def _stub_normals(monkeypatch, inward_columns, axis=(500.0, 600.0)):
    """Normals along the radius from the axis, pointing inward on the columns given and outward elsewhere."""

    def grid_normals(xyz, valid):
        radial = xyz[..., :2] - np.array(axis)
        length = np.linalg.norm(radial, axis=-1, keepdims=True)
        unit = np.divide(radial, length, out=np.zeros_like(radial), where=length > 0)
        sign = np.where(np.isin(np.arange(xyz.shape[1]), inward_columns), -1.0, 1.0)[
            None, :, None
        ]
        normals = np.concatenate([unit * sign, np.zeros(xyz.shape[:2] + (1,))], -1)
        return normals, np.ones(xyz.shape[:2], bool)

    monkeypatch.setattr(sb.analysis, "grid_normals", grid_normals)


def test_a_winding_exactly_half_inward_is_undecided_and_stops_the_step(
    tmp_path, monkeypatch, capsys
):
    ring = _ring(tmp_path / "w010.tifxyz", 100.0)
    _stub_normals(monkeypatch, inward_columns=range(32))  # 32 of 64 columns
    out = tmp_path / "orient.json"
    assert sb.main(["orient", str(out), str(ring)]) == 1
    record = json.loads(out.read_text())["windings"]["w010"]
    assert record == {"share_of_normals_pointing_inward": 0.5, "render": None}
    assert "w010 None" in capsys.readouterr().out
    assert sb.main(["orient", str(out), str(ring)]) == 2  # written once


def test_a_node_on_the_axis_has_no_direction_and_is_left_out(tmp_path, monkeypatch):
    import tifffile

    ring = _ring(tmp_path / "w010.tifxyz", 100.0)
    x = tifffile.imread(ring / "x.tif")
    y = tifffile.imread(ring / "y.tif")
    x[0, 0], y[0, 0] = 500.0, 600.0  # one node on the axis
    tifffile.imwrite(ring / "x.tif", x)
    tifffile.imwrite(ring / "y.tif", y)
    _stub_normals(
        monkeypatch, inward_columns=range(64)
    )  # every other node points inward
    umbilicus = _umbilicus(
        tmp_path / "u.json",
        [{"z": 7000, "x": 500, "y": 600}, {"z": 9000, "x": 500, "y": 600}],
    )
    share = sb.orientation([ring], umbilicus)["windings"]["w010"][
        "share_of_normals_pointing_inward"
    ]
    assert share == 1.0


def test_a_tile_rendered_exactly_at_the_cover_line_is_scored_and_half_is_ink():
    rendered = np.zeros((380, 380), bool)
    rendered[:342] = True  # 342 of 380 rows: exactly 0.9 of the tile
    prob = np.full((380, 380), 0.5, np.float32)
    assert sb.tile_shares(prob, rendered) == [{"row": 0, "col": 0, "ink_share": 1.0}]


def _summary_inputs(
    root: Path, renders_for: dict[str, int], shape=(800, 800), rendered=True
):
    import zarr

    maps, renders = root / "maps", root / "renders"
    maps.mkdir(parents=True)
    renders.mkdir()
    for name, count in renders_for.items():
        prob = np.zeros(shape, np.float32)
        prob[:380, :380] = 0.9  # the first tile all ink, the others none
        np.save(maps / f"{name}.npy", prob)
        for k in range(count):
            layer = np.zeros((66, 800, 800), np.uint8)
            layer[33] = 100 if rendered else 0
            zarr.open(str(renders / f"{name}_{k}.zarr"), mode="w").create_dataset(
                "0", data=layer, chunks=(66, 800, 800)
            )
    return maps, renders


@pytest.mark.parametrize(
    ("renders_for", "shape", "message"),
    [({"w020": 0}, (800, 800), "has 0 renders"), ({"w020": 2}, (800, 800), "has 2 renders"),
     ({"w020": 1}, (800, 760), r"is \(800, 760\), its render \(800, 800\)")],
    ids=["no_render", "two_renders", "another_size"],
)  # fmt: skip
def test_the_summary_refuses_a_map_without_exactly_one_render_of_its_size(
    tmp_path, renders_for, shape, message
):
    maps, renders = _summary_inputs(tmp_path, renders_for, shape)
    with pytest.raises(SystemExit, match=message):
        sb.summarise(tmp_path / "out", maps, renders)


def test_the_summary_takes_the_largest_tile_has_no_share_unrendered_and_is_written_once(
    tmp_path,
):
    maps, renders = _summary_inputs(tmp_path, {"w020": 1})
    summary = sb.summarise(tmp_path / "out", maps, renders)["windings"]["w020"]
    assert summary["tiles_scored"] == 4 and summary["largest_tile_ink_share"] == 1.0
    with pytest.raises(FileExistsError):
        sb.summarise(tmp_path / "out", maps, renders)
    dark_maps, dark_renders = _summary_inputs(
        tmp_path / "dark", {"w021": 1}, rendered=False
    )
    dark = sb.summarise(tmp_path / "dark" / "out", dark_maps, dark_renders)["windings"][
        "w021"
    ]
    assert (
        dark["rendered_pixels"] == 0
        and dark["ink_share"] is None
        and dark["largest_tile_ink_share"] is None
    )


def test_select_keeps_positive_excess_in_index_order_and_exits_1_on_none(tmp_path):
    quality = {"windings": {"w100": {"excess": 0.2}, "w99": {"excess": 0.1}, "w98": {"excess": 0.0},
                            "w97": None, "w96": {"excess": None}}}  # fmt: skip
    assert sb.select(quality) == ["w99", "w100"]
    path = tmp_path / "q.json"
    path.write_text(json.dumps({"windings": {"w010": {"excess": 0.0}}}))
    out = tmp_path / "kept.txt"
    assert sb.main(["select", str(path), str(out)]) == 1 and out.read_text() == ""


def test_stacked_pairs_are_consecutive_windings_and_the_line_is_inclusive(
    tmp_path, monkeypatch
):
    snap = tmp_path / "snap"
    for name in ("w010", "w011", "w013"):
        (snap / name).mkdir(parents=True)
        (snap / name / "x.tif").write_bytes(b"")
    shares = {("w010", "w011"): 0.30, ("w011", "w013"): 0.90}
    monkeypatch.setattr(
        sb.analysis, "load_tifxyz", lambda path: (Path(path).name, None)
    )
    monkeypatch.setattr(
        sb.analysis,
        "surface_distance",
        lambda a, av, b, bv: {"fraction_within": {"2": shares[(a, b)]}},
    )
    assert sb.stacked(snap) == {
        "line": 0.30,
        "pairs": {"w010-w011": 0.30},
        "stacked": ["w010-w011"],
    }
