"""sheet_coverage.py on a synthetic scroll: rings of predicted sheet, and cylinders standing on chosen rings."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import tifffile
import zarr

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "sheet_coverage", ROOT / "repro/first_letters/eligible_band/sheet_coverage.py"
)
assert _spec and _spec.loader
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

AX = AY = 400.0  # working voxels; the grid (SDT level 1) centre is 200, 200
RINGS = list(
    range(40, 160, 10)
)  # grid radii of the 12 rings; each is 2 grid voxels thick
Z0 = 20.0


def _slice() -> np.ndarray:
    yy, xx = np.mgrid[0:400, 0:400]
    r = np.hypot(xx - AX / 2, yy - AY / 2)
    sl = np.full((400, 400), 140, np.uint8)  # data, outside every sheet
    for ring in RINGS:
        sl[(r >= ring) & (r < ring + 2)] = 120  # inside a sheet
    return sl


def _cylinder(tmp: Path, name: str, grid_radius: float, tilt: float = 0.0) -> str:
    """A tifxyz winding standing on a ring: 3 rows (z 0, 20, 40) by 720 columns round the axis."""
    d = tmp / name
    d.mkdir()
    th = np.deg2rad(np.arange(720) / 2)
    rw = 2 * (grid_radius + 1) + tilt  # working voxels, the ring's middle
    zs = np.array([0.0, 20.0, 40.0])[:, None] * np.ones((1, 720))
    x = AX + rw * np.cos(th)[None, :] * np.ones((3, 1))
    y = AY + rw * np.sin(th)[None, :] * np.ones((3, 1))
    for c, a in (("x", x), ("y", y), ("z", zs)):
        tifffile.imwrite(d / f"{c}.tif", a.astype(np.float32))
    return str(d)


def test_the_cut_is_the_curve_at_z(tmp_path):
    p = sc.cut(_cylinder(tmp_path, "w", 50), Z0)
    r = np.hypot(p[:, 0] - AX, p[:, 1] - AY)
    assert len(p) >= 720 and np.allclose(r, 2 * 51, atol=1e-3)


def test_coverage_counts_the_rings_each_set_stands_on(tmp_path):
    every = [_cylinder(tmp_path, f"a{r}", r) for r in RINGS]
    half = [_cylinder(tmp_path, f"b{r}", r) for r in RINGS[::2]]
    twice = half + [_cylinder(tmp_path, "c40", RINGS[0], tilt=1.0)]
    out = sc.coverage(
        _slice(), AX, AY, Z0, [("every", every), ("half", half), ("twice", twice)]
    )
    assert out["range_from"] == "every" and out["degrees_with_range"] == 360
    s = out["sets"]
    assert s["every"]["runs_counted"] == 360 * len(RINGS)
    assert s["every"]["covered_share"] == 1.0
    assert s["every"]["covered_by_two_or_more_share"] == 0.0
    assert s["half"]["covered_share"] == 0.5
    # one ring carries two windings: 1 of the 12 rings at every degree
    assert s["twice"]["covered_by_two_or_more_share"] == pytest.approx(1 / 12, abs=1e-4)
    assert s["twice"]["covered_share"] == 0.5


def test_runs_outside_the_first_sets_range_are_not_counted(tmp_path):
    inner = [_cylinder(tmp_path, f"i{r}", r) for r in RINGS[2:6]]  # rings 60 to 90 only
    out = sc.coverage(_slice(), AX, AY, Z0, [("inner", inner)])
    assert out["sets"]["inner"]["runs_counted"] == 360 * 4
    assert out["sets"]["inner"]["covered_share"] == 1.0
    assert out["sets"]["inner"]["covered_share_by_third_of_range"] == [1.0, 1.0, 1.0]


def test_the_command_reads_level_1_of_the_sdt_and_writes_numbers_only(tmp_path):
    g = zarr.open_group(str(tmp_path / "sdt.zarr"), mode="w")
    level1 = g.create_dataset(
        "1", shape=(30, 400, 400), dtype=np.uint8, chunks=(8, 128, 128)
    )
    level1[int(Z0 / 2)] = _slice()
    umb = {
        "control_points": [{"x": AX, "y": AY, "z": 0.0}, {"x": AX, "y": AY, "z": 100.0}]
    }
    (tmp_path / "umb.json").write_text(json.dumps(umb))
    lst = tmp_path / "every.txt"
    lst.write_text("\n".join(_cylinder(tmp_path, f"a{r}", r) for r in RINGS) + "\n")
    out = tmp_path / "out.json"
    res = sc.main(
        [
            str(tmp_path / "sdt.zarr"),
            str(tmp_path / "umb.json"),
            str(Z0),
            str(out),
            f"every={lst}",
        ]
    )
    assert json.loads(out.read_text()) == res
    assert (
        res["axis_xy_working"] == [AX, AY]
        and res["sets"]["every"]["covered_share"] == 1.0
    )
