"""Finding 130: the densified grid, the comparison of the two arms, the verdict table and the run script."""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"
REGISTRATION = ROOT / "docs/preregistration/2026-11-20_first_letters_dense_snap.md"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dw = _load("densify_under_test", BAND / "densify_winding.py")
ds = _load("dense_snap_under_test", BAND / "dense_snap.py")


def test_densify_keeps_the_nodes_and_adds_midpoints():
    xyz = np.zeros((3, 4, 3))
    xyz[..., 0] = np.arange(4)[None, :] * 20.0 + 100
    xyz[..., 1] = np.arange(3)[:, None] * 20.0 + 200
    xyz[..., 2] = 9000.0
    valid = np.ones((3, 4), bool)
    dense, ok = dw.densify(xyz, valid, 2)
    assert dense.shape == (5, 7, 3) and ok.all()
    assert np.allclose(dense[::2, ::2], xyz)
    assert np.allclose(dense[1, 1], (xyz[0, 0] + xyz[0, 1] + xyz[1, 0] + xyz[1, 1]) / 4)
    assert np.allclose(dense[0, 1], (xyz[0, 0] + xyz[0, 1]) / 2)


def test_a_missing_node_removes_only_the_new_nodes_that_lean_on_it():
    xyz = np.ones((3, 3, 3)) * 500.0
    valid = np.ones((3, 3), bool)
    valid[0, 0] = False
    _, ok = dw.densify(xyz, valid, 2)
    assert not ok[0, 0] and not ok[0, 1] and not ok[1, 0] and not ok[1, 1]
    assert ok[2, 2] and ok[0, 2] and ok[2, 0] and ok[1, 2] and ok[2, 1]


def test_the_cli_doubles_the_scale_and_marks_missing_nodes(tmp_path):
    import tifffile

    src = tmp_path / "w020"
    src.mkdir()
    for i, c in enumerate("xyz"):
        a = np.full((3, 3), 100.0 + i, np.float32)
        a[0, 0] = -1.0
        tifffile.imwrite(src / f"{c}.tif", a)
    (src / "meta.json").write_text(
        json.dumps({"scale": [0.05, 0.05], "source": "fit_spiral fitted"})
    )
    assert dw.main([str(src), str(tmp_path / "out"), "--factor", "2"]) == 0
    meta = json.loads((tmp_path / "out" / "meta.json").read_text())
    assert meta["scale"] == [0.1, 0.1] and "densify_winding x2" in meta["source"]
    x = tifffile.imread(tmp_path / "out" / "x.tif")
    assert x.shape == (5, 5) and x[0, 0] == -1.0 and x[4, 4] == 100.0
    with pytest.raises(SystemExit, match="exists"):
        dw.main([str(src), str(tmp_path / "out")])


@pytest.mark.parametrize(
    ("gains", "on_tri", "ok", "expected"),
    [
        ([0.05, 0.06, 0.04], [0.97, 0.96, 0.95], True, "DENSE_SNAP_HELPS"),
        ([0.05, 0.04, 0.04], [0.97, 0.96, 0.95], True, "DENSE_SNAP_NO_GAIN"),
        ([0.2, 0.2, 0.2], [0.94, 0.94, 0.97], True, "DENSE_SNAP_NO_GAIN"),
        ([0.2, 0.2, 0.2], [0.97, 0.97, 0.97], False, "DOES_NOT_RUN"),
    ],
)
def test_the_verdict_table(gains, on_tri, ok, expected):
    assert ds.verdict(gains, on_tri, ok) == expected


AXIS = (5000.0, 5000.0)


class _Sheet:
    def __init__(self, radius):
        self.radius = radius

    def at(self, xyz):
        return (
            np.abs(np.hypot(xyz[:, 0] - AXIS[0], xyz[:, 1] - AXIS[1]) - self.radius)
            - 1.0
        )


def _write(folder, xyz):
    import tifffile

    folder.mkdir(parents=True)
    for i, c in enumerate("xyz"):
        tifffile.imwrite(folder / f"{c}.tif", xyz[..., i].astype(np.float32))


def _ring(radius, columns, rows=6):
    theta = np.linspace(0, np.pi / 2, columns)
    z = np.linspace(9000, 9100, rows)
    tt, zz = np.meshgrid(theta, z)
    return np.stack(
        [AXIS[0] + radius * np.cos(tt), AXIS[1] + radius * np.sin(tt), zz], -1
    )


def test_the_comparison_finds_the_denser_arm_closer_to_the_sheet(tmp_path):
    r = tmp_path / "band"
    work = r / "work"
    (r / "dataset").mkdir(parents=True)
    (r / "dataset" / "umbilicus.json").write_text(json.dumps({"control_points": [
        {"x": AXIS[0], "y": AXIS[1], "z": 0}, {"x": AXIS[0], "y": AXIS[1], "z": 20000}]}))  # fmt: skip
    coarse, fine = (
        _ring(1000.0, 8),
        _ring(1000.0, 64),
    )  # 8 columns: chords up to ~13 voxels inside the circle
    for arm, snap in (("base", coarse), ("dense", fine)):
        _write(work / f"snap_{arm}" / "w020", snap)
        # the final samples the snapped triangles evenly: midpoints of its cells
        final = (snap[:-1, :-1] + snap[1:, :-1] + snap[:-1, 1:] + snap[1:, 1:]) / 4
        _write(work / f"final_{arm}" / "w020.tifxyz", final)
    (work / "gate_dense").mkdir()
    (work / "gate_dense" / "snap.json").write_text(
        json.dumps({"exit": 0, "seconds": 1})
    )
    out = ds.compare(r, ["w020"], "base", "dense", field=_Sheet(1000.0))
    row = out["windings"]["w020"]
    assert row["base"]["snapped_within_2"] == row["dense"]["snapped_within_2"] == 1.0
    assert row["dense"]["final_within_2"] == 1.0 and row["base"]["final_within_2"] < 0.5
    assert row["gain"] > 0.5 and row["dense"]["on_snapped_triangles"] >= 0.95
    assert out["verdict"] == "DENSE_SNAP_HELPS"
    (work / "gate_dense" / "flatten_w020.json").write_text(
        json.dumps({"exit": 1, "seconds": 1})
    )
    assert (
        ds.compare(r, ["w020"], "base", "dense", field=_Sheet(1000.0))["verdict"]
        == "DOES_NOT_RUN"
    )


def test_the_run_script_follows_the_registration_and_uploads_nothing():
    path = BAND / "run_dense_snap.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    assert re.findall(r"^step (\w+)", text, flags=re.M) == [
        "densify",
        "snap",
        "flatten",
        "compare",
    ]
    windings = re.search(r"^WINDINGS=\(([^)]*)\)", text, flags=re.M).group(1).split()
    assert windings == ["w020", "w030", "w040", "w050", "w060", "w070"]
    reg = " ".join(REGISTRATION.read_text().split())
    assert "w020, w030, w040, w050, w060 and w070" in reg
    assert "at least +0.05" in reg and "at least 0.95" in reg
    assert (ds.GAIN, ds.ON_TRIANGLES) == (0.05, 0.95)
    assert "render" not in re.sub(r"#.*", "", text)  # no render step


# --- each corner rule, the edges of the verdict, the arms and the radius terciles ----------------------------------


@pytest.mark.parametrize("missing", [-1.0, np.nan], ids=["sentinel", "nan"])
def test_a_missing_centre_removes_its_eight_neighbours_and_keeps_every_original_node(
    missing,
):
    # the centre is each corner (r0c0, r0c1, r1c0, r1c1) of one of the new nodes round it
    cols, rows = np.meshgrid(np.arange(3) * 20.0, np.arange(3) * 20.0)
    xyz = np.stack([cols, rows, np.full((3, 3), 9e3)], -1)
    xyz[1, 1] = missing
    valid = np.isfinite(xyz).all(-1) & (xyz > -0.5).all(-1)
    dense, ok = dw.densify(xyz, valid, 2)
    expected = np.ones((5, 5), bool)
    expected[1:4, 1:4] = False
    assert (ok == expected).all()
    assert np.isfinite(dense[ok]).all() and np.allclose(
        dense[::2, ::2][valid], xyz[valid]
    )


def test_a_factor_below_one_is_refused():
    with pytest.raises(ValueError, match="at least 1"):
        dw.densify(np.zeros((2, 2, 3)), np.ones((2, 2), bool), 0)


def test_a_winding_without_a_recorded_scale_takes_the_fits_default(tmp_path):
    import tifffile

    src = tmp_path / "w020"
    src.mkdir()
    for c in "xyz":
        tifffile.imwrite(src / f"{c}.tif", np.full((2, 2), 100.0, np.float32))
    (src / "meta.json").write_text(json.dumps({}))
    assert dw.main([str(src), str(tmp_path / "out"), "--factor", "2"]) == 0
    assert json.loads((tmp_path / "out" / "meta.json").read_text())["scale"] == [
        0.1,
        0.1,
    ]


def test_the_verdict_at_its_other_edges():
    assert ds.verdict([], [], True) == "DOES_NOT_RUN"
    assert (
        ds.verdict([0.05, 0.05, 0.05], [0.95, 0.95, 0.99], True) == "DENSE_SNAP_HELPS"
    )


def _band(tmp_path, arms: dict, gates=({"exit": 0, "seconds": 1},)):
    """A run directory: the axis, each arm's snapped and final winding, and the dense arm's gates."""
    r = tmp_path / "band"
    work = r / "work"
    (r / "dataset").mkdir(parents=True)
    (r / "dataset" / "umbilicus.json").write_text(json.dumps({"control_points": [
        {"x": AXIS[0], "y": AXIS[1], "z": 0}, {"x": AXIS[0], "y": AXIS[1], "z": 20000}]}))  # fmt: skip
    for arm, (snap, final) in arms.items():
        _write(work / f"snap_{arm}" / "w020", snap)
        _write(work / f"final_{arm}" / "w020.tifxyz", final)
    (work / "gate_dense").mkdir()
    for k, gate in enumerate(gates):
        (work / "gate_dense" / f"step{k}.json").write_text(json.dumps(gate))
    return r


def _midpoints(snap):
    return (snap[:-1, :-1] + snap[1:, :-1] + snap[:-1, 1:] + snap[1:, 1:]) / 4


def test_without_any_gate_the_comparison_does_not_run(tmp_path):
    snap = _ring(1000.0, 64)
    r = _band(
        tmp_path,
        {"base": (snap, _midpoints(snap)), "dense": (snap, _midpoints(snap))},
        gates=(),
    )
    assert (
        ds.compare(r, ["w020"], "base", "dense", field=_Sheet(1000.0))["verdict"]
        == "DOES_NOT_RUN"
    )


def test_the_verdict_reads_the_dense_arms_triangles(tmp_path):
    # the dense arm's final lies on the predicted sheet but 5 voxels off its own snapped triangles
    coarse, fine = _ring(1000.0, 8), _ring(1000.0, 64)
    off = _midpoints(_ring(1005.0, 64))
    r = _band(tmp_path, {"base": (coarse, _midpoints(coarse)), "dense": (fine, off)})
    out = ds.compare(r, ["w020"], "base", "dense", field=_Sheet(1005.0))
    row = out["windings"]["w020"]
    assert row["gain"] >= 0.05 and row["base"]["on_snapped_triangles"] >= 0.95
    assert row["dense"]["on_snapped_triangles"] < 0.95
    assert out["verdict"] == "DENSE_SNAP_NO_GAIN"


class _InnerThird:
    """On the sheet within the inner third of the radii, 5 voxels off it beyond."""

    def at(self, xyz):
        radius = np.hypot(xyz[:, 0] - AXIS[0], xyz[:, 1] - AXIS[1])
        return np.where(radius < 966.0, 0.0, 5.0)


def test_the_radius_terciles_split_the_nodes_in_thirds(tmp_path):
    radii = np.linspace(900.0, 1100.0, 30)  # ten columns to a tercile
    zz, rr = np.meshgrid(np.linspace(9000, 9100, 6), radii, indexing="ij")
    strip = np.stack([AXIS[0] + rr, np.full_like(rr, AXIS[1]), zz], -1)
    r = _band(tmp_path, {"base": (strip, strip), "dense": (strip, strip)})
    out = ds.compare(r, ["w020"], "base", "dense", field=_InnerThird())
    assert out["windings"]["w020"]["dense"]["final_within_2_by_radius_tercile"] == [
        1.0,
        0.0,
        0.0,
    ]


def test_the_comparison_is_measured_once(tmp_path):
    out = tmp_path / "dense_snap.json"
    out.write_text("{}")
    assert ds.main(["compare", str(tmp_path), str(out), "--windings", "w020"]) == 2


class _OuterThirdOutside:
    """On the sheet inside, and outside the distance field (no value) for the outer third of the radii."""

    def at(self, xyz):
        radius = np.hypot(xyz[:, 0] - AXIS[0], xyz[:, 1] - AXIS[1])
        return np.where(radius < 1033.0, 0.0, np.nan)


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="a tercile with no finite distance is None in its winding's row, and the summary's median of the "
    "windings' values raises on it",
)
def test_a_tercile_outside_the_field_does_not_stop_the_comparison(tmp_path):
    radii = np.linspace(900.0, 1100.0, 30)
    zz, rr = np.meshgrid(np.linspace(9000, 9100, 6), radii, indexing="ij")
    strip = np.stack([AXIS[0] + rr, np.full_like(rr, AXIS[1]), zz], -1)
    r = _band(tmp_path, {"base": (strip, strip), "dense": (strip, strip)})
    out = ds.compare(r, ["w020"], "base", "dense", field=_OuterThirdOutside())
    assert (
        out["windings"]["w020"]["dense"]["final_within_2_by_radius_tercile"][2] is None
    )
