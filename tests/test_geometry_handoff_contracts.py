"""Geometry handoffs must preserve coordinates and produce real completed outputs."""

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import zarr

from scripts import register_volumes as registration, voxelize_predictions as mesher
from scripts.geometry_artifacts import validate_transform
from scripts.labeling import label_artifacts

REPO = Path(__file__).resolve().parents[1]


def tifxyz_wrapper():
    spec = importlib.util.spec_from_file_location(
        "_geometry_tifxyz", REPO / "scripts/labeling/tifxyz_wrapper.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tifxyz_helper_import_is_safe_without_optional_runtime():
    assert callable(tifxyz_wrapper().extract_patch_coords)


def test_prediction_mesh_cli_creates_an_actual_obj_outside_checkout(tmp_path):
    data = np.zeros((6, 7, 8), np.float32)
    data[1:5, 2:5, 2:6] = 1
    source, output = tmp_path / "prediction.zarr", tmp_path / "mesh.obj"
    zarr.array(data, store=str(source))
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/voxelize_predictions.py"),
            "--input",
            str(source),
            "--output_obj",
            str(output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output.is_file()
    assert any(line.startswith("f ") for line in output.read_text().splitlines())


def test_registration_rejects_missing_sources_before_starting_a_process(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "register_volumes.py",
            "--fixed",
            str(tmp_path / "missing-fixed"),
            "--moving",
            str(tmp_path / "missing-moving"),
            "--output-transform",
            str(tmp_path / "transform.json"),
        ],
    )

    def forbidden(*args, **kwargs):
        pytest.fail("missing sources reached the interactive process")

    monkeypatch.setattr(registration.subprocess, "run", forbidden)
    result = registration.main()
    assert isinstance(result, int) and result != 0


def test_registration_cannot_report_a_saved_transform_without_a_file(
    tmp_path, monkeypatch, capsys
):
    args = registration_args(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        registration.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0, "", ""),
    )
    assert registration.main([*args, "--execute"]) == 1
    assert "Success!" not in capsys.readouterr().out
    assert not (tmp_path / "transform.json").exists()
    assert not list(tmp_path.glob(".transform-*.json"))


def prediction(tmp_path, *, group=False):
    values = np.zeros((6, 7, 8), np.float32)
    values[1:5, 2:5, 2:6] = 1
    path = tmp_path / "prediction.zarr"
    if group:
        zarr.open_group(str(path), mode="w").create_dataset("0", data=values)
    else:
        zarr.array(values, store=str(path))
    return path, values


def read_obj(path):
    lines = Path(path).read_text().splitlines()
    header = json.loads(lines[0].removeprefix("# autoresearch_geometry "))
    vertices = np.array(
        [
            [float(value) for value in line.split()[1:]]
            for line in lines
            if line.startswith("v ")
        ]
    )
    faces = (
        np.array(
            [
                [int(value) for value in line.split()[1:]]
                for line in lines
                if line.startswith("f ")
            ]
        )
        - 1
    )
    return header, vertices, faces


@pytest.mark.parametrize("group", [False, True])
def test_real_isosurface_xyz_origin_spacing_and_winding(tmp_path, group):
    source, values = prediction(tmp_path, group=group)
    output = tmp_path / "mesh.obj"
    record = mesher.export_prediction_mesh(
        source,
        output,
        origin_zyx=(20, 30, 40),
        spacing_zyx=(2, 3, 4),
        units="micrometer",
    )
    header, actual, triangles = read_obj(output)
    vertices, faces, _, _ = mesher.marching_cubes(values, 0.5, allow_degenerate=False)
    expected = (vertices.astype(np.float64) * [2, 3, 4] + [20, 30, 40])[:, ::-1]
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(triangles, faces[:, [0, 2, 1]])
    np.testing.assert_array_equal(actual.min(axis=0), [46, 34.5, 21])
    np.testing.assert_array_equal(actual.max(axis=0), [62, 43.5, 29])
    assert record == header
    assert header["units"] == "micrometer" and header["submittable"] is None
    assert header["triangles"] == len(triangles) and header["vertices"] == len(actual)
    assert not (tmp_path / "prediction_pruned.zarr").exists()
    root = zarr.open(str(source), mode="r")
    np.testing.assert_array_equal((root["0"] if group else root)[:], values)


@pytest.mark.parametrize(
    "settings",
    [
        {"threshold": 0},
        {"threshold": 1},
        {"threshold": float("nan")},
        {"threshold": True},
        {"origin_zyx": (0, float("inf"), 0)},
        {"origin_zyx": (0, 1j, 0)},
        {"spacing_zyx": (1, 0, 1)},
        {"spacing_zyx": (1, -1, 1)},
        {"origin_zyx": (0, 0)},
        {"units": "millimeter"},
        {"max_voxels": 1},
    ],
)
def test_invalid_mesh_settings_publish_nothing(tmp_path, settings):
    source, values = prediction(tmp_path)
    output = tmp_path / "mesh.obj"
    with pytest.raises(ValueError):
        mesher.export_prediction_mesh(source, output, **settings)
    assert not output.exists()
    np.testing.assert_array_equal(zarr.open(str(source))[:], values)


@pytest.mark.parametrize(
    "bad", ["nan", "negative", "above_one", "zero", "one", "4d", "thin", "complex"]
)
def test_invalid_probability_grids_publish_nothing(tmp_path, bad):
    source, values = prediction(tmp_path)
    if bad == "nan":
        values[0, 0, 0] = np.nan
    elif bad == "negative":
        values[0, 0, 0] = -0.1
    elif bad == "above_one":
        values[0, 0, 0] = 1.1
    elif bad == "zero":
        values[:] = 0
    elif bad == "one":
        values[:] = 1
    elif bad == "4d":
        values = values[np.newaxis]
    elif bad == "thin":
        values = values[:1]
    else:
        values = values.astype(np.complex64)
    zarr.array(values, store=str(source), overwrite=True)
    with pytest.raises(ValueError):
        mesher.export_prediction_mesh(source, tmp_path / "mesh.obj")
    assert not (tmp_path / "mesh.obj").exists()


@pytest.mark.parametrize(
    "where", ["inside_source", "existing", "symlink", "wrong_suffix"]
)
def test_mesh_outputs_preserve_existing_sources_and_files(tmp_path, where):
    source, values = prediction(tmp_path)
    output = tmp_path / "mesh.obj"
    if where == "inside_source":
        output = source / "mesh.obj"
    elif where == "existing":
        output.write_text("old mesh")
    elif where == "symlink":
        output.symlink_to(source, target_is_directory=True)
    else:
        output = tmp_path / "mesh.stl"
    with pytest.raises(ValueError):
        mesher.export_prediction_mesh(source, output)
    np.testing.assert_array_equal(zarr.open(str(source))[:], values)
    if where == "existing":
        assert output.read_text() == "old mesh"


@pytest.mark.parametrize("failure", ["read", "extract", "metadata", "write", "rename"])
def test_mesh_failure_leaves_no_partial_file(tmp_path, monkeypatch, failure):
    source, _ = prediction(tmp_path)
    output = tmp_path / "mesh.obj"

    def fail(*args, **kwargs):
        raise OSError("injected failure")

    if failure == "read":
        monkeypatch.setattr(zarr.Array, "__getitem__", fail)
    elif failure == "extract":
        monkeypatch.setattr(mesher, "marching_cubes", fail)
    elif failure == "metadata":
        monkeypatch.setattr(mesher.json, "dumps", fail)
    elif failure == "rename":
        monkeypatch.setattr(Path, "rename", fail)
    else:
        original_open = Path.open

        def interrupted(path, *args, **kwargs):
            if path.suffix == ".obj":
                with original_open(path, "w") as stream:
                    stream.write("partial mesh")
                raise OSError("interrupted OBJ write")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", interrupted)
    with pytest.raises(OSError):
        mesher.export_prediction_mesh(source, output)
    assert not output.exists()
    assert {path.name for path in tmp_path.iterdir()} == {"prediction.zarr"}


def test_mesh_bound_is_checked_before_reading_sparse_payload(tmp_path, monkeypatch):
    source = tmp_path / "huge.zarr"
    zarr.open(str(source), mode="w", shape=(1024,) * 3, chunks=(64,) * 3, dtype="f4")

    def forbidden(*args, **kwargs):
        pytest.fail("oversized payload was read")

    monkeypatch.setattr(zarr.Array, "__getitem__", forbidden)
    with pytest.raises(ValueError, match="max_voxels"):
        mesher.export_prediction_mesh(source, tmp_path / "mesh.obj")


def registration_args(tmp_path):
    for name in ("fixed", "moving"):
        zarr.open_group(str(tmp_path / f"{name}.zarr"), mode="w").create_dataset(
            "0", data=np.ones((6, 7, 8), np.uint16)
        )
    return [
        "--fixed",
        str(tmp_path / "fixed.zarr"),
        "--moving",
        str(tmp_path / "moving.zarr"),
        "--fixed-voxel-size",
        "7.91",
        "--moving-voxel-size",
        "3.955",
        "--output-transform",
        str(tmp_path / "transform.json"),
    ]


def transform_data():
    return {
        "schema_version": "1.0.0",
        "fixed_volume": "fixed",
        "transformation_matrix": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]],
        "fixed_landmarks": [[7, 6, 5]],
        "moving_landmarks": [[7, 6, 5]],
    }


def fake_viewer(monkeypatch, callback, *, probe_code=0, exit_code=0):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    def run(command, **kwargs):
        assert command[0] == sys.executable
        assert str(registration.REGISTRATION_DIR) in kwargs["env"]["PYTHONPATH"]
        if command[1] == "-c":
            return subprocess.CompletedProcess(
                command,
                probe_code,
                "",
                "optional dependency absent" if probe_code else "",
            )
        assert (
            command[1] == "-i"
            and Path(command[2]) == registration.REGISTRATION_DIR / "find_transform.py"
        )
        if callback is not None:
            callback(Path(command[-1]))
        return subprocess.CompletedProcess(command, exit_code)

    monkeypatch.setattr(registration.subprocess, "run", run)


def test_registration_plan_uses_pinned_options_and_has_no_launch_side_effect(
    tmp_path, monkeypatch
):
    args = registration_args(tmp_path)
    monkeypatch.chdir(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("dry run started a process")

    monkeypatch.setattr(registration.subprocess, "run", forbidden)
    assert registration.main(args) == 0
    assert not (tmp_path / "transform.json").exists()
    plan = registration.registration_plan(
        tmp_path / "fixed.zarr", tmp_path / "moving.zarr", "transform.json", 7.91, 3.955
    )
    command = plan["command"]
    tree = ast.parse((registration.REGISTRATION_DIR / "find_transform.py").read_text())
    supported = {
        value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        for value in node.args
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    }
    assert {arg for arg in command if arg.startswith("--")} <= supported
    assert command[command.index("--moving-voxel-size") + 1] == "3.955"
    assert plan["output"] == tmp_path / "transform.json"


@pytest.mark.parametrize("size", [None, 0, -1, float("nan"), float("inf"), True])
def test_registration_requires_explicit_finite_positive_voxel_sizes(tmp_path, size):
    registration_args(tmp_path)
    with pytest.raises(ValueError):
        registration.registration_plan(
            tmp_path / "fixed.zarr",
            tmp_path / "moving.zarr",
            tmp_path / "transform.json",
            size,
            7.91,
        )
    assert not (tmp_path / "transform.json").exists()


@pytest.mark.parametrize(
    "bad", ["bare", "4d", "same_source", "ome", "metadata", "alias", "existing"]
)
def test_registration_rejects_unsupported_frames_and_aliases(tmp_path, bad):
    registration_args(tmp_path)
    fixed, moving, output = (
        tmp_path / "fixed.zarr",
        tmp_path / "moving.zarr",
        tmp_path / "transform.json",
    )
    if bad == "bare":
        zarr.array(np.ones((6, 7, 8)), store=str(fixed), overwrite=True)
    elif bad == "4d":
        zarr.open_group(str(fixed), mode="w").create_dataset(
            "0", data=np.ones((2, 6, 7, 8))
        )
    elif bad == "same_source":
        moving = fixed
    elif bad == "ome":
        zarr.open_group(str(fixed), mode="r+").attrs["multiscales"] = []
    elif bad == "metadata":
        (fixed / "metadata.json").write_text(
            json.dumps(
                {
                    "scan": {
                        "tomo": {"acquisition": {"detector": {"samplePixelSize": 0.02}}}
                    }
                }
            )
        )
    elif bad == "alias":
        output = moving / "transform.json"
    else:
        output.write_text("old transform")
    with pytest.raises(ValueError):
        registration.registration_plan(fixed, moving, output, 7.91, 3.955)
    if bad == "existing":
        assert output.read_text() == "old transform"


def test_actual_upstream_writer_output_is_validated_and_published(
    tmp_path, monkeypatch, capsys
):
    args = registration_args(tmp_path)
    source = registration.REGISTRATION_DIR / "transform_utils.py"
    tree = ast.parse(source.read_text())
    node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "write_transform_json"
    )
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {"np": np, "json": json}
    exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)

    def save(path):
        assert path.suffix == ".json" and path != tmp_path / "transform.json"
        namespace["write_transform_json"](
            str(path), "fixed", np.eye(4), [[7, 6, 5]], [[7, 6, 5]]
        )

    fake_viewer(monkeypatch, save)
    assert registration.main([*args, "--execute"]) == 0
    output = tmp_path / "transform.json"
    assert json.loads(output.read_text()) == transform_data()
    printed = capsys.readouterr().out
    assert "press W" in printed and "Ctrl+D does not save" in printed
    assert "Alignment accuracy remains unverified" in printed
    assert not list(tmp_path.glob(".transform-*.json"))


@pytest.mark.parametrize(
    "bad",
    [
        "missing",
        "truncated",
        "singular",
        "wrong_fixed",
        "nan",
        "extra_field",
        "mismatched_pairs",
        "out_of_bounds",
        "invalid_schema",
        "process_error",
        "interrupt",
    ],
)
def test_failed_or_invalid_registration_publishes_nothing(tmp_path, monkeypatch, bad):
    args = registration_args(tmp_path)
    data = transform_data()
    if bad == "singular":
        data["transformation_matrix"][0] = [0, 0, 0, 0]
    elif bad == "wrong_fixed":
        data["fixed_volume"] = "other"
    elif bad == "nan":
        data["transformation_matrix"][0][0] = float("nan")
    elif bad == "extra_field":
        data["unexpected"] = 1
    elif bad == "mismatched_pairs":
        data["moving_landmarks"] = []
    elif bad == "out_of_bounds":
        data["moving_landmarks"][0] = [8, 1, 1]
    elif bad == "invalid_schema":
        data["schema_version"] = "wrong"

    def save(path):
        if bad == "interrupt":
            raise KeyboardInterrupt
        if bad == "missing":
            return
        path.write_text("{broken" if bad == "truncated" else json.dumps(data))

    fake_viewer(monkeypatch, save, exit_code=7 if bad == "process_error" else 0)
    assert registration.main([*args, "--execute"]) != 0
    assert not (tmp_path / "transform.json").exists()
    assert not list(tmp_path.glob(".transform-*.json"))


def test_missing_registration_runtime_never_enters_repl(tmp_path, monkeypatch):
    args = registration_args(tmp_path)

    def forbidden(*args):
        pytest.fail("failed runtime entered the REPL")

    fake_viewer(monkeypatch, forbidden, probe_code=1)
    assert registration.main([*args, "--execute"]) == 1
    assert not (tmp_path / "transform.json").exists()


def test_registration_requires_a_terminal_for_execute(tmp_path, monkeypatch):
    args = registration_args(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    def forbidden(*args, **kwargs):
        pytest.fail("noninteractive execution started a viewer")

    monkeypatch.setattr(registration.subprocess, "run", forbidden)
    assert registration.main([*args, "--execute"]) == 1


def test_coarse_transform_with_zero_landmark_pairs_is_valid_but_not_accuracy_evidence(
    tmp_path,
):
    data = transform_data()
    data["fixed_landmarks"] = data["moving_landmarks"] = []
    output = tmp_path / "transform.json"
    output.write_text(json.dumps(data))
    assert validate_transform(output, "fixed.zarr", (6, 7, 8), (6, 7, 8)) == data


def real_surface():
    wrapper = tifxyz_wrapper()
    api = wrapper.tifxyz_api()
    y, x = np.mgrid[:6, :7].astype(np.float32)
    return wrapper, api.Tifxyz(
        x + 10,
        y + 20,
        np.full_like(x, 30),
        _mask=np.ones_like(x, bool),
        _scale=(0.5, 0.5),
    )


@pytest.mark.parametrize(
    "region",
    [
        (-1, 0, 2, 2),
        (0, -1, 2, 2),
        (5, 0, 2, 2),
        (0, 6, 2, 2),
        (0, 0, 0, 2),
        (0, 0, 2, -1),
        (0.5, 0, 2, 2),
        (True, 0, 2, 2),
    ],
)
def test_tifxyz_tiles_cannot_clip_or_wrap_coordinates(region):
    wrapper, surface = real_surface()
    with pytest.raises(ValueError):
        wrapper.extract_patch_coords(surface, *region)


def test_tifxyz_tile_keeps_xyz_order_and_masks_nonfinite_or_missing_points():
    wrapper, surface = real_surface()
    surface._x[2, 2] = np.nan
    surface._y[2, 3] = -1
    surface._mask[3, 2] = False
    x, y, z, valid = wrapper.extract_patch_coords(surface, 1, 1, 3, 3)
    assert (x[0, 0], y[0, 0], z[0, 0]) == (11, 21, 30)
    assert not valid[1, 1] and not valid[1, 2] and not valid[2, 1]
    assert valid[0, 0] and surface._mask[2, 2]


@pytest.mark.parametrize("resolution", ["stored", "full"])
def test_tifxyz_real_reader_respects_explicit_resolution(tmp_path, resolution):
    wrapper, surface = real_surface()
    api = wrapper.tifxyz_api()
    source = tmp_path / "surface"
    api.write_tifxyz(source, surface)
    loaded = wrapper.load_tifxyz_surface(str(source), resolution=resolution)
    assert loaded.resolution == resolution
    assert loaded.shape == ((6, 7) if resolution == "stored" else (12, 14))
    actual = wrapper.extract_patch_coords(loaded, 2, 2, 3, 3)
    expected = loaded[2:5, 2:5]
    for actual_plane, expected_plane in zip(actual, expected, strict=True):
        np.testing.assert_array_equal(actual_plane, expected_plane)


def test_tifxyz_missing_runtime_or_surface_raises_instead_of_returning_none(
    tmp_path, monkeypatch
):
    wrapper = tifxyz_wrapper()
    monkeypatch.setattr(wrapper, "TIFXYZ_DIR", tmp_path / "absent")
    with pytest.raises(ImportError):
        wrapper.load_tifxyz_surface(str(tmp_path))
    with pytest.raises(ValueError):
        wrapper.extract_patch_coords(None, 0, 0, 1, 1)


def test_new_file_publication_refuses_destination_that_appears_during_work(tmp_path):
    output = tmp_path / "result.json"
    with pytest.raises(ValueError, match="appeared"):
        with label_artifacts.publish_new_file(output) as staging:
            staging.write_text("new result")
            output.write_text("other writer")
    assert output.read_text() == "other writer"
    assert not list(tmp_path.glob(".result-*.json"))
