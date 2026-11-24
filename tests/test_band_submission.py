"""The submission inputs from a band read: Studio maps as the recipe's TIFFs, the flattening check, the control's
statistics and the reading orientation from the catalog flags, and the wrapper's refusals."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import tifffile

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "repro/first_letters/submission"
spec = importlib.util.spec_from_file_location(
    "submission_inputs", HERE / "submission_inputs.py"
)
sub = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sub
spec.loader.exec_module(sub)


def write_mesh(path: Path, xyz: np.ndarray, scale: float = 0.05) -> Path:
    path.mkdir(parents=True)
    for i, a in enumerate("xyz"):
        tifffile.imwrite(path / f"{a}.tif", xyz[..., i].astype(np.float32))
    (path / "meta.json").write_text(
        json.dumps({"scale": [scale, scale], "format": "tifxyz"})
    )
    return path


def flat_grid(rows=12, cols=15, step=20.0, sx=1.0, sy=1.0, shear=0.0):
    """Nodes on the plane z = 0: column j at x = j * step * sx (+ shear * i * step), row i at y = i * step * sy."""
    i, j = np.mgrid[0:rows, 0:cols].astype(np.float64)
    return np.stack(
        [j * step * sx + shear * i * step, i * step * sy, np.zeros_like(i)], axis=-1
    )


def test_ink_writes_both_maps_unchanged_under_the_recipes_names(tmp_path):
    rng = np.random.default_rng(0)
    reading, control = (rng.random((40, 60), dtype=np.float32) for _ in range(2))
    np.save(tmp_path / "r.npy", reading)
    np.save(tmp_path / "c.npy", control)
    out = sub.ink_tiffs(
        tmp_path / "r.npy", tmp_path / "c.npy", (40, 60), tmp_path / "maps", "w035"
    )
    assert out["reading"]["file"] == "w035__studio__L66zc33.50_reverse.tif"
    assert out["control"]["file"] == "w035__studio__L66zc33.50.tif"
    back = tifffile.imread(tmp_path / "maps" / out["reading"]["file"])
    assert back.dtype == np.float32 and np.array_equal(back, reading)
    assert np.array_equal(
        tifffile.imread(tmp_path / "maps" / out["control"]["file"]), control
    )
    # the recipe's script reads the window centre 33.5 as depth +1 and only _reverse as the reading side
    assert round(33.5 - 32.5, 2) == 1.0


@pytest.mark.parametrize(
    "values, message",
    [
        (np.zeros((40, 61), np.float32), "shape"),
        (np.zeros((40, 60), np.float64), "float32"),
        (np.full((40, 60), np.nan, np.float32), "not finite"),
    ],
)
def test_ink_refuses_a_map_that_is_not_the_renders(tmp_path, values, message):
    np.save(tmp_path / "r.npy", values)
    np.save(tmp_path / "c.npy", np.zeros((40, 60), np.float32))
    with pytest.raises(SystemExit, match=message):
        sub.ink_tiffs(
            tmp_path / "r.npy", tmp_path / "c.npy", (40, 60), tmp_path / "maps", "w"
        )


def test_ink_never_overwrites(tmp_path):
    np.save(tmp_path / "r.npy", np.zeros((4, 4), np.float32))
    np.save(tmp_path / "c.npy", np.zeros((4, 4), np.float32))
    sub.ink_tiffs(
        tmp_path / "r.npy", tmp_path / "c.npy", (4, 4), tmp_path / "maps", "w"
    )
    with pytest.raises(SystemExit, match="exists"):
        sub.ink_tiffs(
            tmp_path / "r.npy", tmp_path / "c.npy", (4, 4), tmp_path / "maps", "w"
        )


def test_an_isometric_grid_has_stretch_one_no_shear_and_area_one(tmp_path):
    mesh = write_mesh(tmp_path / "m.tifxyz", flat_grid())
    d = sub.isometry(mesh)
    for key in ("stretch_along_render_rows", "stretch_along_render_columns"):
        assert d[key]["median"] == 1.0 and d[key]["share_within_10pct"] == 1.0
    assert d["shear_deg"]["p95"] == 0.0 and d["area_ratio_3d_to_flat"] == 1.0


def test_a_stretch_and_a_shear_are_measured_in_their_directions(tmp_path):
    d = sub.isometry(write_mesh(tmp_path / "a.tifxyz", flat_grid(sx=1.2)))
    assert (
        d["stretch_along_render_rows"]["median"] == 1.2
    )  # columns step along a render row
    assert d["stretch_along_render_rows"]["share_within_10pct"] == 0.0
    assert d["stretch_along_render_columns"]["median"] == 1.0
    assert d["area_ratio_3d_to_flat"] == 1.2
    s = sub.isometry(
        write_mesh(tmp_path / "s.tifxyz", flat_grid(shear=np.tan(np.radians(10))))
    )
    assert s["shear_deg"]["median"] == pytest.approx(10.0, abs=1e-3)


def test_the_area_keeps_only_its_nodes_and_invalid_nodes_drop_out(tmp_path):
    xyz = flat_grid(rows=10, cols=10)
    xyz[0, 0] = -1  # an invalid node, as tifxyz writes it
    mesh = write_mesh(tmp_path / "m.tifxyz", xyz)
    assert sub.isometry(mesh)["nodes"] == 99
    # rows 40..100 px and columns 0..60 px hold nodes 2-4 x 0-2 (node (i, j) at pixel (20 i, 20 j))
    d = sub.isometry(mesh, (40, 100, 0, 60))
    assert d["nodes"] == 9 and d["quads"] == 4
    assert d["stretch_along_render_rows"]["n"] == 6


def test_control_stats_reuse_the_reading_images_numbers(tmp_path):
    sidecar = {
        "ink": {
            "maps": [{"side": "reading"}],
            "normalisation": {
                "mode": "single model",
                "models": ["studio"],
                "per_model": {
                    "studio": {
                        "p1": 0.14,
                        "p99_5": 0.93,
                        "mean": 0.28,
                        "sd": 0.21,
                        "n_px": 9,
                    }
                },
            },
        },
        "ct": {
            "shape": [66, 2380, 5480],
            "file": "w047_66.zarr",
            "stretch": {"lo": 28.0, "hi": 165.0},
        },
    }
    (tmp_path / "w.json").write_text(json.dumps(sidecar))
    s = sub.control_stats(tmp_path / "w.json")
    assert (s["H"], s["W"], s["surface"]) == (2380, 5480, "w047_66.zarr")
    assert s["models"]["studio"] == {
        "p1": 0.14,
        "p99_5": 0.93,
        "mean": 0.28,
        "sd": 0.21,
        "depths": [1],
    }
    assert s["ct"] == {"p1": 28.0, "p99_5": 165.0}
    sidecar["ink"]["normalisation"]["models"] = ["a", "b"]
    (tmp_path / "e.json").write_text(json.dumps(sidecar))
    with pytest.raises(SystemExit, match="one reading-side model"):
        sub.control_stats(tmp_path / "e.json")


def cylinder_patch(theta_step: float, z_step: float) -> np.ndarray:
    """Nodes on a cylinder of radius 500 around the z axis at (1000, 1000): theta changes by theta_step per column
    and z by z_step per row."""
    i, j = np.mgrid[0:8, 0:10].astype(np.float64)
    theta = np.radians(30 + theta_step * j)
    return np.stack(
        [1000 + 500 * np.cos(theta), 1000 + 500 * np.sin(theta), 5000 + z_step * i],
        axis=-1,
    )


@pytest.mark.parametrize(
    "ttb, lh, flip_lr, flip_ud",
    [
        (False, False, True, True),  # PHerc. 343's frame: the recipe's own rule
        (
            True,
            False,
            False,
            False,
        ),  # z top to bottom (PHerc. 211, 0358): both senses turn
        (False, True, False, True),  # left-handed: theta's sense turns
        (True, True, True, False),
    ],
)
def test_orientation_follows_the_catalog_flags(tmp_path, ttb, lh, flip_lr, flip_ud):
    mesh = write_mesh(
        tmp_path / "m.tifxyz", cylinder_patch(theta_step=1.0, z_step=20.0)
    )
    axis = {"control_points": [{"x": 1000, "y": 1000, "z": z} for z in (0, 10000)]}
    (tmp_path / "u.json").write_text(json.dumps(axis))
    d = sub.reading_orientation(mesh, tmp_path / "u.json", ttb, lh)
    assert (d["sign_dtheta_per_column"], d["sign_dz_per_row"]) == (1, 1)
    assert (d["flip_lr"], d["flip_ud"]) == (flip_lr, flip_ud)


def run_wrapper(tmp_path, *extra):
    args = [
        str(tmp_path / n) for n in ("m.tifxyz", "r.zarr", "r.npy", "c.npy", "u.json")
    ]
    args += ["0,10,0,10", "-", "-", str(tmp_path / "out")]
    return subprocess.run(
        ["bash", str(HERE / "make_band_submission.sh"), *args, *extra],
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "RECIPE": str(tmp_path / "no-recipe")},
    )


def test_the_wrapper_needs_the_catalog_flags_and_a_new_output(tmp_path):
    base = ["--scroll", "PHerc. 0826", "--volume-id", "1", "--voxel-um", "9.362"]
    r = run_wrapper(tmp_path, *base)
    assert (
        r.returncode == 2
        and "--top-to-bottom, --left-handed and --render-flipped" in r.stderr
    )
    flags = [
        "--top-to-bottom",
        "true",
        "--left-handed",
        "false",
        "--render-flipped",
        "true",
    ]
    (tmp_path / "out").mkdir()
    r = run_wrapper(tmp_path, *base, *flags)
    assert r.returncode == 2 and "exists" in r.stderr
    (tmp_path / "out").rmdir()
    r = run_wrapper(tmp_path, *base, *flags)
    assert r.returncode == 2 and "is not the recipe at" in r.stderr
    assert not (tmp_path / "out").exists()


# --- the maps' and the mesh's refusals, the edges of the flattening check, and the command line --------------------


def _maps(tmp_path, reading, control):
    np.save(tmp_path / "r.npy", np.asarray(reading, np.float32))
    np.save(tmp_path / "c.npy", np.asarray(control, np.float32))
    return tmp_path / "r.npy", tmp_path / "c.npy"


def test_ink_refuses_a_single_infinite_value_and_checks_the_control_too(tmp_path):
    one_inf = np.zeros((4, 4))
    one_inf[1, 2] = np.inf
    reading, control = _maps(tmp_path, np.zeros((4, 4)), one_inf)
    with pytest.raises(SystemExit, match="c.npy: has values that are not finite"):
        sub.ink_tiffs(reading, control, (4, 4), tmp_path / "maps", "w")


def test_ink_records_each_maps_own_source(tmp_path):
    reading, control = _maps(tmp_path, np.zeros((4, 4)), np.ones((4, 4)))
    out = sub.ink_tiffs(reading, control, (4, 4), tmp_path / "maps", "w")
    assert (out["reading"]["source"], out["control"]["source"]) == ("r.npy", "c.npy")


@pytest.mark.xfail(
    strict=True,
    reason="ink_tiffs writes the reading TIFF before it checks the control: a control that fails leaves the "
    "reading TIFF behind, and the next run refuses it as existing. Registered script, not changed.",
)
def test_a_control_that_fails_its_check_leaves_no_tiff_behind(tmp_path):
    reading, control = _maps(tmp_path, np.zeros((4, 4)), np.zeros((4, 5)))
    with pytest.raises(SystemExit, match="shape"):
        sub.ink_tiffs(reading, control, (4, 4), tmp_path / "maps", "w")
    assert list((tmp_path / "maps").iterdir()) == []


def _sidecar(tmp_path, **change):
    d = {"ink": {"maps": [{"side": change.get("side", "reading")}],
                 "normalisation": {"mode": change.get("mode", "single model"), "models": ["studio"],
                                   "per_model": {"studio": {"p1": 0.1, "p99_5": 0.9, "mean": 0.3, "sd": 0.2}}}},
         "ct": {"shape": [66, 20, 30], "file": "w_66.zarr", "stretch": {"lo": 20.0, "hi": 160.0}}}  # fmt: skip
    (tmp_path / "w.json").write_text(json.dumps(d))
    return tmp_path / "w.json"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"mode": "ensemble"}, "one reading-side model"),
        ({"side": "blind"}, "not made from the reading side"),
    ],
)
def test_control_stats_need_one_single_model_reading_image(tmp_path, change, message):
    with pytest.raises(SystemExit, match=message):
        sub.control_stats(_sidecar(tmp_path, **change))


@pytest.mark.parametrize("scale", [[0.05, 0.1], [0, 0]], ids=["unequal", "zero"])
def test_a_mesh_scale_must_be_two_equal_positive_numbers(tmp_path, scale):
    mesh = write_mesh(tmp_path / "m.tifxyz", flat_grid(rows=3, cols=3))
    (mesh / "meta.json").write_text(json.dumps({"scale": scale}))
    with pytest.raises(SystemExit, match="scale must be two equal positive numbers"):
        sub.isometry(mesh)


def test_a_node_with_any_coordinate_minus_1_or_not_finite_or_masked_out_is_invalid(
    tmp_path,
):
    xyz = flat_grid(rows=4, cols=4)
    xyz[0, 1, 0] = -1  # one coordinate only
    xyz[0, 2] = np.nan
    mesh = write_mesh(tmp_path / "m.tifxyz", xyz)
    mask = np.ones((4, 4), np.uint8)
    mask[3, 3] = 0
    tifffile.imwrite(mesh / "mask.tif", mask)
    assert sub.isometry(mesh)["nodes"] == 16 - 3


def test_an_area_with_nodes_but_no_edges_reports_none_rather_than_failing(tmp_path):
    mesh = write_mesh(tmp_path / "m.tifxyz", flat_grid(rows=4, cols=4))
    d = sub.isometry(mesh, (20, 21, 20, 21))  # the single node (1, 1)
    assert d["nodes"] == 1 and d["quads"] == 0 and d["area_ratio_3d_to_flat"] is None
    assert d["stretch_along_render_rows"] == {"n": 0} and d["shear_deg"] == {"n": 0}
    assert d["area_raw_render_px"] == {"row0": 20, "row1": 21, "col0": 20, "col1": 21}


def test_a_shear_either_way_is_its_size(tmp_path):
    d = sub.isometry(
        write_mesh(tmp_path / "s.tifxyz", flat_grid(shear=-np.tan(np.radians(10))))
    )
    assert d["shear_deg"]["median"] == pytest.approx(10.0, abs=1e-3)


def test_a_bent_quad_counts_both_of_its_triangles(tmp_path):
    xyz = flat_grid(rows=2, cols=2)
    xyz[1, 1, 2] = 20.0  # lift one corner: the quad's two triangles differ
    d = sub.isometry(write_mesh(tmp_path / "b.tifxyz", xyz))
    expected = (
        0.5
        * (20 * 20 + np.linalg.norm(np.cross([0, -20, -20], [-20, 0, -20])))
        / (20 * 20)
    )
    assert d["quads"] == 1 and d["area_ratio_3d_to_flat"] == round(expected, 4) == 1.366


def test_an_area_is_four_numbers_or_a_json_with_or_without_its_area_key(tmp_path):
    assert sub._area("1,2,3,4") == (1, 2, 3, 4)
    with pytest.raises(SystemExit, match="row0,row1,col0,col1"):
        sub._area("1,2,3,4,5")
    (tmp_path / "a.json").write_text(
        json.dumps(
            {"area": {"raw_render_px": {"row0": 1, "row1": 2, "col0": 3, "col1": 4}}}
        )
    )
    (tmp_path / "b.json").write_text(
        json.dumps({"raw_render_px": {"row0": 5, "row1": 6, "col0": 7, "col1": 8}})
    )
    assert sub._area(str(tmp_path / "a.json")) == (1, 2, 3, 4)
    assert sub._area(str(tmp_path / "b.json")) == (5, 6, 7, 8)


def test_the_command_passes_the_catalog_flags_in_their_places_and_writes_its_out_file(
    tmp_path, capsys
):
    mesh = write_mesh(
        tmp_path / "m.tifxyz", cylinder_patch(theta_step=1.0, z_step=20.0)
    )
    axis = {"control_points": [{"x": 1000, "y": 1000, "z": z} for z in (0, 10000)]}
    (tmp_path / "u.json").write_text(json.dumps(axis))
    argv = ["orient", str(mesh), "--umbilicus", str(tmp_path / "u.json"), "--top-to-bottom", "true",
            "--left-handed", "false", "--out", str(tmp_path / "o.json")]  # fmt: skip
    assert sub.main(argv) == 0
    written = json.loads((tmp_path / "o.json").read_text())
    assert written == json.loads(capsys.readouterr().out)
    assert (
        written["z_direction_is_top_to_bottom"],
        written["left_handed_coordinates"],
    ) == (True, False)
    assert (written["flip_lr"], written["flip_ud"]) == (
        False,
        False,
    )  # the table above: top to bottom, right-handed
