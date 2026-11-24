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


# --- the wrapper run end to end: git reports the recipe's commit, a stand-in for the recipe's image script records its
# arguments and writes the reading image's sidecar, and our own submission_inputs.py runs as written ----------------

RECIPE_COMMIT = "e8370f1f88a211166056df62ea6fcfffe4a1063e"
SIDECAR = {"ink": {"maps": [{"side": "reading"}],
                   "normalisation": {"mode": "single model", "models": ["studio"],
                                     "per_model": {"studio": {"p1": 0.1, "p99_5": 0.9, "mean": 0.3, "sd": 0.2}}}},
           "ct": {"shape": [66, 160, 200], "file": "w035_66.zarr", "stretch": {"lo": 20.0, "hi": 160.0}}}  # fmt: skip


def _stub(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


def _wrapper(
    tmp_path,
    ttb,
    lh,
    flipped,
    *,
    area="20,100,0,120",
    rows=True,
    letters=True,
    extra=(),
    env=None,
    remove=None,
):
    """Inputs for winding w035 (an 8 x 10-node mesh, a 160 x 200 render), the stand-ins, and the wrapper's run."""
    inp = tmp_path / "in"
    mesh = write_mesh(inp / "w035.tifxyz", cylinder_patch(theta_step=1.0, z_step=20.0))
    tifffile.imwrite(mesh / "mask.tif", np.ones((8, 10), np.uint8))
    (inp / "w035_66.zarr").mkdir()
    rng = np.random.default_rng(3)
    for name in ("r", "c"):
        np.save(inp / f"{name}.npy", rng.random((160, 200), dtype=np.float32))
    axis = {"control_points": [{"x": 1000, "y": 1000, "z": z} for z in (0, 10000)]}
    (inp / "u.json").write_text(json.dumps(axis))
    for name in ("rows", "letters"):
        (inp / f"{name}.json").write_text("{}")
    recipe = tmp_path / "recipe"
    (recipe / "ink/scripts").mkdir(parents=True)
    (recipe / "ink/scripts/make_submission_image.py").write_text(
        "# the recipe's script, stood in for\n"
    )
    _stub(
        tmp_path / "bin/git",
        f'case "$*" in *rev-parse*) echo {RECIPE_COMMIT} ;; *diff*) exit "${{DIFF_RC:-0}}" ;; esac\n',
    )
    (tmp_path / "sidecar.json").write_text(json.dumps(SIDECAR))
    _stub(
        tmp_path / "py343",
        f"""[ "$2" = -c ] && {{ echo "160 200"; exit 0; }}
out=; prev=; for a in "$@"; do [ "$prev" = --out-dir ] && out=$a; prev=$a; done
printf '%s\\n' "$@" > {tmp_path}/$(basename "$out").args
[ "$(basename "$out")" = "${{FAIL:-none}}" ] && exit 1
cp {tmp_path}/sidecar.json "$out/w035.json"
""",
    )
    if isinstance(area, dict):
        (inp / "area.json").write_text(json.dumps(area))
        area = str(inp / "area.json")
    if remove:
        (tmp_path / remove).unlink()
    args = [str(mesh), str(inp / "w035_66.zarr"), str(inp / "r.npy"), str(inp / "c.npy"), str(inp / "u.json"), area,
            str(inp / "rows.json") if rows else "-", str(inp / "letters.json") if letters else "-", str(tmp_path / "out"),
            "--scroll", "PHerc. 0826", "--volume-id", "1", "--voxel-um", "9.362", "--top-to-bottom", ttb,
            "--left-handed", lh, "--render-flipped", flipped, *extra]  # fmt: skip
    run = subprocess.run(
        ["bash", str(HERE / "make_band_submission.sh"), *args],
        capture_output=True, text=True, timeout=120,
        env={"PATH": f"{tmp_path}/bin:/usr/bin:/bin", "RECIPE": str(recipe), "PY343": str(tmp_path / "py343"),
             "PYW": sys.executable, **(env or {})},
    )  # fmt: skip
    calls = {
        name: (tmp_path / f"{name}.args").read_text().splitlines()
        for name in ("image", "control")
        if (tmp_path / f"{name}.args").exists()
    }
    return run, tmp_path / "out", calls


def _value(argv, flag):
    return argv[argv.index(flag) + 1]


def test_the_wrapper_draws_the_image_and_its_control_with_the_orientation_area_and_annotations(
    tmp_path,
):
    area = {
        "raw_render_px": {"row0": 20, "row1": 100, "col0": 0, "col1": 120}
    }  # a JSON without its "area" key
    (tmp_path / "forbid.txt").write_text("word\n")
    run, out, calls = _wrapper(tmp_path, "true", "true", "true", area=area,
                               extra=("--max-cm2", "6", "--forbid-words", str(tmp_path / "forbid.txt")))  # fmt: skip
    assert run.returncode == 0, run.stderr
    image, control = calls["image"], calls["control"]
    orientation = json.loads((out / "orientation.json").read_text())
    assert (orientation["flip_lr"], orientation["flip_ud"]) == (
        True,
        False,
    )  # top to bottom, left-handed
    for argv in (image, control):
        assert (_value(argv, "--flip-lr"), _value(argv, "--flip-ud")) == ("1", "0")
        assert (
            _value(argv, "--area") == "0,20,120,100"
        )  # col0,row0,col1,row1, as the recipe's script takes it
        assert (_value(argv, "--max-cm2"), _value(argv, "--forbid-words")) == (
            "6",
            str(tmp_path / "forbid.txt"),
        )
        assert "--umbilicus" not in argv  # not the script's own frame
        assert _value(argv, "--note").startswith("Rendered with flipped normals")
    assert _value(image, "--ink") == f"{out}/maps/w035__studio__L66zc33.50_reverse.tif"
    assert (_value(image, "--rows"), _value(image, "--letters")) == (f"{tmp_path}/in/rows.json",
                                                                    f"{tmp_path}/in/letters.json")  # fmt: skip
    assert _value(image, "--sizes-csv") == f"{out}/image/w035_letter_sizes.csv"
    assert _value(control, "--ink") == f"{out}/maps/w035__studio__L66zc33.50.tif"
    assert (
        _value(control, "--ink-stats") == f"{out}/control_ink_stats.json"
        and "--allow-blind" in control
    )
    assert "--rows" not in control and "--letters" not in control
    sums = (out / "mesh_geometry.sha256").read_text().split()[1::2]
    assert sums == [
        "w035.tifxyz/x.tif",
        "w035.tifxyz/y.tif",
        "w035.tifxyz/z.tif",
        "w035.tifxyz/mask.tif",
    ]
    assert (
        json.loads((out / "isometry.json").read_text())["area_raw_render_px"]
        == area["raw_render_px"]
    )
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["recipe_commit"] == RECIPE_COMMIT
    assert {n: v["sha256"] is None for n, v in manifest["inputs"].items()} == {
        "mesh": True, "render": True, "reading_map": False, "control_map": False, "umbilicus": False, "rows": False,
        "letters": False,
    }  # fmt: skip
    assert (
        "manifest.json" not in manifest["outputs"]
        and "isometry.json" in manifest["outputs"]
    )
    assert set(manifest["commands"]) == {
        "ink",
        "orient",
        "image",
        "stats",
        "control",
        "isometry",
        "manifest",
    }


@pytest.mark.parametrize(
    ("ttb", "lh", "flipped", "umbilicus", "note"),
    [("false", "true", "true", False, True), ("false", "false", "false", True, False)],
    ids=["left-handed-only", "the-scripts-own-frame"],
)
def test_the_umbilicus_goes_to_the_script_only_in_its_own_frame_and_the_note_only_for_a_flipped_render(
    tmp_path, ttb, lh, flipped, umbilicus, note
):
    run, out, calls = _wrapper(tmp_path, ttb, lh, flipped, rows=False, letters=False)
    assert run.returncode == 0, run.stderr
    image = calls["image"]
    assert ("--umbilicus" in image) is umbilicus and ("--note" in image) is note
    assert (
        "--rows" not in image
        and "--letters" not in image
        and "--sizes-csv" not in image
    )
    assert _value(image, "--max-cm2") == "4"
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["inputs"]["rows"] == {"path": "-", "sha256": None}


def test_a_failed_step_stops_the_wrapper(tmp_path):
    run, out, calls = _wrapper(
        tmp_path, "true", "false", "false", env={"FAIL": "image"}
    )
    assert (
        run.returncode == 1 and f"step image failed: {out}/logs/image.log" in run.stderr
    )
    assert "control" not in calls and not (out / "manifest.json").exists()


@pytest.mark.parametrize(
    ("arrange", "message"),
    [
        ("diff", "differs from the recipe's commit"),
        ("in/u.json", "missing"),
        ("in/rows.json", "missing"),
    ],
)
def test_the_wrapper_refuses_a_changed_recipe_script_or_a_missing_input_before_it_writes_anything(
    tmp_path, arrange, message
):
    if arrange == "diff":
        run, out, calls = _wrapper(
            tmp_path, "true", "false", "false", env={"DIFF_RC": "1"}
        )
    else:
        run, out, calls = _wrapper(tmp_path, "true", "false", "false", remove=arrange)
    assert run.returncode == 2 and message in run.stderr
    assert not out.exists() and calls == {}


@pytest.mark.parametrize(
    ("argv", "message"),
    [(["a"] * 8, "A First Letters submission image"),
     (["a"] * 9 + ["--scroll", "S", "--volume-id", "1"], "--scroll, --volume-id and --voxel-um are required")],
    ids=["eight-paths", "no-voxel-size"],
)  # fmt: skip
def test_the_wrapper_needs_nine_paths_and_the_scrolls_three_names(argv, message):
    run = subprocess.run(["bash", str(HERE / "make_band_submission.sh"), *argv], capture_output=True, text=True,
                         env={"PATH": "/usr/bin:/bin"})  # fmt: skip
    assert run.returncode == 2 and message in run.stderr
