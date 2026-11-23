"""Finding 126: PHerc. 0358 in the band scripts, the selection of windings before any ink, the stacked-winding
check, and the chain."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"


def _load():
    spec = importlib.util.spec_from_file_location(
        "studio_band_for_0358", BAND / "studio_band.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sb = _load()


def _env(tmp_path, **extra):
    env = {"PATH": "/usr/bin:/bin", "FL_ROOT": str(tmp_path), **extra}
    out = subprocess.run(
        ["bash", "-c", '. "$0"; printf "%s\\n" "$R" "$SENSE" "$VOLUME_ID" "$UMBILICUS_KEY" "$SURF_CHUNKS" "$CT_CHUNKS" "$LASAGNA_CHUNKS"', str(BAND / "env.sh")],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.splitlines()  # fmt: skip
    return dict(
        zip(
            ("R", "sense", "volume", "umbilicus", "surface", "ct", "lasagna"),
            out,
            strict=True,
        )
    )


def test_pherc0358_is_anticlockwise_with_its_published_axis_and_the_chunks_of_its_band(
    tmp_path,
):
    v = _env(tmp_path, FL_SCROLL="PHerc0358", FL_Z_BEGIN="8872", FL_Z_END="10372")
    assert v["R"] == f"{tmp_path}/pherc0358_band" and v["sense"] == "ACW"
    assert v["volume"] == "20250821151737"
    assert (
        v["umbilicus"]
        == "PHerc0358/representations/umbilicus/20250821151737-umbilicus-20260922235631.json"
    )
    lo, hi = 8872 - 64, 10372 + 64
    for key, voxels_per_chunk in (("surface", 384), ("ct", 256), ("lasagna", 128)):
        first, last = (int(x) for x in v[key].split())
        assert first * voxels_per_chunk <= lo and (last + 1) * voxels_per_chunk > hi


def test_the_band_is_the_middle_1500_slices_of_the_tracked_range():
    text = (
        ROOT / "docs/preregistration/2026-11-20_first_letters_0358_band_read.md"
    ).read_text()
    begin, end = 4500, 14744  # the tracks' effective_z_bounds
    middle = (begin + end) // 2
    assert (middle - 750, middle + 750) == (8872, 10372)
    assert "z 8872 to 10372" in text and "4500 to 14744" in text


def test_selection_keeps_windings_with_positive_excess_in_index_order():
    quality = {
        "windings": {
            "w101": {"excess": 0.2},
            "w010": {"excess": 0.01},
            "w011": {"excess": 0.0},
            "w012": {"excess": -0.1},
            "w013": None,
            "w099": {"excess": None},
        }
    }
    assert sb.select(quality) == ["w010", "w101"]


def _plane(path: Path, y: float) -> None:
    import tifffile

    r, c = np.mgrid[0:8, 0:10].astype(float)
    path.mkdir(parents=True)
    for axis, values in (
        ("x", c * 20 + 1000),
        ("y", np.full_like(r, y)),
        ("z", r * 20 + 9000),
    ):
        tifffile.imwrite(path / f"{axis}.tif", values.astype(np.float32))


def test_the_stacked_check_flags_consecutive_windings_on_one_surface(tmp_path):
    _plane(tmp_path / "w020", 500.0)
    _plane(tmp_path / "w021", 501.0)  # 1 voxel away: the same papyrus
    _plane(tmp_path / "w022", 515.0)  # a sheet spacing away
    _plane(tmp_path / "w024", 516.0)  # not consecutive with w022: not compared
    result = sb.stacked(tmp_path)
    assert set(result["pairs"]) == {"w020-w021", "w021-w022"}
    assert result["pairs"]["w020-w021"] == 1.0 and result["pairs"]["w021-w022"] == 0.0
    assert result["stacked"] == ["w020-w021"] and result["line"] == sb.STACKED == 0.30


def test_the_band_read_takes_a_winding_list_and_checks_for_stacking_after_the_snap():
    text = (BAND / "run_studio_band.sh").read_text()
    assert 'grep -Fxf "$STUDIO_WINDINGS"' in text
    assert (
        text.index("stage snap")
        < text.index("stage stacked")
        < text.index("for_each flatten")
    )


def test_the_chain_runs_the_registered_steps_in_order_and_uploads_nothing():
    path = BAND / "run_band_and_read.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
        assert word not in text
    order = ["step fetch_volumes", "step fetch_tracks", "step make_dataset", "step sdt", "step fit_smoke",
             "step fit_full", "step quality", "step select", "step read"]  # fmt: skip
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)
    assert 'run_fit.sh" full' in text and 'run_fit.sh" smoke 300' in text
    assert 'STUDIO_WINDINGS="$R/work/studio_windings_full.txt"' in text


def test_amendment_1_reads_against_the_axis_on_a_denser_grid():
    text = " ".join(
        (ROOT / "docs/preregistration/2026-11-20_first_letters_0358_band_read.md")
        .read_text()
        .split()
    )
    assert (
        "## Amendment 1, 2026-11-20, before anything of PHerc. 0358 was downloaded"
        in text
    )
    assert (
        "FL_SCROLL=PHerc0358 FL_Z_BEGIN=8872 FL_Z_END=10372 FL_DENSIFY=2 run_band_and_read.sh"
        in text
    )
    band = (BAND / "run_studio_band.sh").read_text()
    assert '--umbilicus "$R/dataset/umbilicus.json"' in band
    assert (
        "winner) TILING=(--stride 64 --blend hann) ;;" in band
    )  # the default the chain keeps


def test_the_snap_runs_in_batches_that_keep_every_winding_once_and_in_order(tmp_path):
    text = (BAND / "run_snap.sh").read_text()
    assert 'split -l "${SNAP_BATCH:-12}" -d -a 3 "$LIST" "$BATCHES/batch_"' in text
    assert '--windings "$batch"' in text and '--windings "$LIST"' not in text
    names = [f"w{i:03d}" for i in range(10, 35)]
    (tmp_path / "list.txt").write_text("\n".join(names) + "\n")
    subprocess.run(["split", "-l", "12", "-d", "-a", "3", str(tmp_path / "list.txt"), str(tmp_path / "batch_")],
                   check=True)  # fmt: skip
    batches = sorted(tmp_path.glob("batch_*"))
    assert [len(b.read_text().split()) for b in batches] == [12, 12, 1]
    assert [n for b in batches for n in b.read_text().split()] == names


# --- outer_sheets.py: predicted-sheet runs beyond a winding along rays from the axis ---------------------------------


def _outer_sheets():
    spec = importlib.util.spec_from_file_location(
        "outer_sheets_for_0358", BAND / "outer_sheets.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CENTRE = (
    100.0,
    120.0,
)  # the axis at the slice in grid cells, two working voxels each: (200, 240) working


def _field(tmp_path, rings=(30, 50)):
    """Grid slice 2 (working z 4) of a distance field: data (200) to 90 cells from the axis, none (0) beyond, and
    sheet (100) 2.5 cells either side of each full ring and of an arc at 70 over angles 0 to 60 degrees."""
    import zarr

    rows, cols = np.indices((260, 220))
    rho = np.hypot(cols - CENTRE[0], rows - CENTRE[1])
    angle = np.degrees(np.arctan2(rows - CENTRE[1], cols - CENTRE[0])) % 360
    plane = np.where(rho <= 90, 200, 0).astype(np.uint8)
    for ring in rings:
        plane[np.abs(rho - ring) <= 2.5] = 100
    plane[(np.abs(rho - 70) <= 2.5) & (angle < 60)] = 100
    volume = np.zeros((4, 260, 220), np.uint8)
    volume[2] = plane
    store = tmp_path / "sdt.zarr"
    zarr.open_group(str(store), mode="w").create_dataset("1", data=volume)
    axis = tmp_path / "umbilicus.json"
    # listed out of z order, and tilted: at z 4 the axis is at (200, 240) working
    axis.write_text(
        json.dumps(
            {
                "control_points": [
                    {"x": 210, "y": 250, "z": 104},
                    {"x": 190, "y": 230, "z": -96},
                ]
            }
        )
    )
    return store, axis, plane


def _winding(folder, grid_radius, z=4.0, degrees=360):
    """A winding at that radius from the axis on the slice, over the first `degrees` of angle, two nodes a degree;
    a second row 8 voxels off the slice at another radius, and a third missing (-1)."""
    import tifffile

    theta = np.radians((np.arange(720) + 0.5) / 720 * degrees)
    rows = [(grid_radius, z), (80.0, z + 8)]
    x = np.array([200 + 2 * g * np.cos(theta) for g, _ in rows] + [np.full(720, -1.0)])
    y = np.array([240 + 2 * g * np.sin(theta) for g, _ in rows] + [np.full(720, -1.0)])
    zz = np.array([np.full(720, zr) for _, zr in rows] + [np.full(720, -1.0)])
    folder.mkdir(parents=True)
    for name, values in (("x", x), ("y", y), ("z", zz)):
        tifffile.imwrite(folder / f"{name}.tif", values.astype(np.float32))
    return str(folder)


def _measure(monkeypatch, capsys, store, axis, windings):
    os_ = _outer_sheets()
    monkeypatch.setattr(
        sys, "argv", ["outer_sheets", str(store), str(axis), "4", *windings]
    )
    os_.main()
    return json.loads(capsys.readouterr().out)


def test_outer_sheets_counts_the_sheet_runs_beyond_each_winding(
    tmp_path, monkeypatch, capsys
):
    store, axis, plane = _field(tmp_path)
    w = {
        g: _winding(tmp_path / name, g)
        for name, g in (("w050", 50.0), ("w046", 46.0), ("w020", 20.0))
    }
    off = _winding(
        tmp_path / "w099", 60.0, z=40.0
    )  # no node within 3 voxels of the slice
    out = _measure(monkeypatch, capsys, store, axis, [*w.values(), off])
    assert out["axis_xy_working"] == [200.0, 240.0]
    assert out["sheet_share_of_data"] == round(
        float((plane == 100).sum() / (plane > 0).sum()), 4
    )
    assert out["outermost_sheet_radius_working_median"] == pytest.approx(
        105, abs=2
    )  # the ring at 50, on 300 rays
    assert out["outermost_data_radius_working_median"] == pytest.approx(180, abs=2)
    on_ring, inside_ring, inner = (
        out["windings"]["w050"],
        out["windings"]["w046"],
        out["windings"]["w020"],
    )
    assert on_ring["angles"] == 360 and on_ring["radius_working_median"] == 100.0
    # beyond 4 cells past it: the arc at 70 on a sixth of the rays; its own ring is not counted
    assert on_ring["sheet_runs_beyond_median"] == 0.0 and on_ring[
        "sheet_runs_beyond_p10_p90"
    ] == [0.0, 1.0]
    # 4 cells past it is inside the ring at 50, which counts as one run
    assert inside_ring["sheet_runs_beyond_median"] == 1.0 and inside_ring[
        "sheet_runs_beyond_p10_p90"
    ] == [1.0, 2.0]
    assert inner["sheet_runs_beyond_median"] == 2.0 and inner[
        "sheet_runs_beyond_p10_p90"
    ] == [2.0, 3.0]
    assert inner[
        "outermost_sheet_minus_winding_radius_working_median"
    ] == pytest.approx(65, abs=2)
    assert out["windings"]["w099"] is None


def test_outer_sheets_leaves_rays_that_cross_no_sheet_out_of_the_outermost(
    tmp_path, monkeypatch, capsys
):
    store, axis, _ = _field(tmp_path, rings=())  # only the arc at 70
    out = _measure(
        monkeypatch, capsys, store, axis, [_winding(tmp_path / "w050", 50.0)]
    )
    assert out["outermost_sheet_radius_working_median"] == pytest.approx(145, abs=2)
    assert out["windings"]["w050"][
        "outermost_sheet_minus_winding_radius_working_median"
    ] == pytest.approx(45, abs=2)


def test_outer_sheets_bins_each_node_by_its_own_angle_round_the_axis(
    tmp_path, monkeypatch, capsys
):
    # a winding over the first 60 degrees only, where the arc at 70 lies beyond it on every ray
    store, axis, _ = _field(tmp_path)
    out = _measure(
        monkeypatch,
        capsys,
        store,
        axis,
        [_winding(tmp_path / "w050", 50.0, degrees=60)],
    )
    assert out["windings"]["w050"]["angles"] == 60
    assert out["windings"]["w050"]["sheet_runs_beyond_p10_p90"] == [1.0, 1.0]


# --- run_band_and_read.sh, run with each step a stub beside it: order, gates, the stop, the densified arm -------------

_STEP_STUB = """#!/usr/bin/env bash
echo "$(basename "$0") $* windings=${STUDIO_WINDINGS:-}" >> "$CALLS"
if [ "$(basename "$0") ${1:-}" = "run_fit.sh full" ]; then mkdir -p "$FL_ROOT/pherc0358_band/work/fit_full/r/meshes/fitted"; fi
if [ "${FAIL_AT:-}" = "$(basename "$0")" ]; then exit 3; fi
exit 0
"""

_PYTHON_STUB = """#!/usr/bin/env bash
echo "python $(basename "$2") ${*:3}" >> "$CALLS"
case "$(basename "$2")" in
  studio_band.py) printf 'w010\\nw012\\n' > "$5" ;;
  densify_winding.py) if [ "${FAIL_DENSIFY:-}" = "$(basename "$3")" ]; then exit 4; fi; mkdir -p "$4" ;;
esac
"""


def _chain(tmp_path, **env):
    """Run a copy of the chain, beside a copy of env.sh, with every step and the Python a logging stub."""
    import shutil

    band = tmp_path / "eligible_band"
    (band / "setup").mkdir(parents=True)
    (tmp_path / "pherc343" / "mesh_step").mkdir(parents=True)
    for name in ("run_band_and_read.sh", "env.sh"):
        shutil.copy(BAND / name, band / name)
    for name in ("setup/fetch_volumes.sh", "setup/fetch_tracks.sh", "setup/make_dataset.sh", "run_sdt.sh",
                 "run_fit.sh", "run_quality.sh", "run_studio_band.sh"):  # fmt: skip
        (band / name).write_text(_STEP_STUB)
    python = tmp_path / "python_stub"
    python.write_text(_PYTHON_STUB)
    python.chmod(0o755)
    calls = tmp_path / "calls.log"
    calls.touch()
    root = tmp_path / "fl"
    full_env = {"PATH": "/usr/bin:/bin", "FL_ROOT": str(root), "FL_SCROLL": "PHerc0358", "PYW": str(python),
                "CALLS": str(calls), **env}  # fmt: skip
    rc = subprocess.run(
        ["bash", str(band / "run_band_and_read.sh")], env=full_env, capture_output=True
    ).returncode
    r = root / "pherc0358_band"
    gates = {
        p.stem: json.loads(p.read_text())["exit"]
        for p in sorted((r / "work" / "gate_chain").glob("*.json"))
    }
    return rc, calls.read_text().splitlines(), gates, r


def test_the_chain_runs_each_step_once_in_order_and_reads_the_selected_windings(
    tmp_path,
):
    rc, calls, gates, r = _chain(tmp_path)
    assert rc == 0
    windings = f"windings={r}/work/studio_windings_full.txt"
    assert calls == [
        "fetch_volumes.sh  windings=", "fetch_tracks.sh  windings=", "make_dataset.sh  windings=",
        "run_sdt.sh  windings=", "run_fit.sh smoke 300 windings=", "run_fit.sh full windings=",
        "run_quality.sh full windings=",
        f"python studio_band.py select {r}/work/quality_full.json {r}/work/studio_windings_full.txt",
        f"run_studio_band.sh full {windings}",
    ]  # fmt: skip
    assert gates == dict.fromkeys(
        ["fetch_volumes", "fetch_tracks", "make_dataset", "sdt", "fit_smoke", "fit_full", "quality", "select",
         "read"], 0)  # fmt: skip


def test_the_chain_stops_at_the_first_failing_step_with_its_exit(tmp_path):
    rc, calls, gates, _ = _chain(tmp_path, FAIL_AT="run_sdt.sh")
    assert rc == 3 and calls[-1] == "run_sdt.sh  windings="
    assert gates == {"fetch_volumes": 0, "fetch_tracks": 0, "make_dataset": 0, "sdt": 3}


def test_a_densified_chain_subdivides_each_selected_winding_and_reads_that_arm(
    tmp_path,
):
    rc, calls, gates, r = _chain(tmp_path, FL_DENSIFY="3")
    base, dest = (
        r / "work" / "fit_full" / "r" / "meshes" / "fitted",
        r / "work" / "fit_fulldense" / "densified",
    )
    assert rc == 0 and gates["densify"] == 0
    assert calls[-3:] == [
        f"python densify_winding.py {base}/w010 {dest}/meshes/fitted/w010 --factor 3",
        f"python densify_winding.py {base}/w012 {dest}/meshes/fitted/w012 --factor 3",
        f"run_studio_band.sh fulldense windings={r}/work/studio_windings_full.txt",
    ]


def test_a_densify_that_fails_or_finds_its_arm_stops_the_chain(tmp_path):
    rc, calls, gates, _ = _chain(
        tmp_path / "fails", FL_DENSIFY="2", FAIL_DENSIFY="w010"
    )
    assert rc == 1 and gates["densify"] == 1 and "read" not in gates
    assert not any("w012" in c for c in calls)
    (tmp_path / "found" / "fl" / "pherc0358_band" / "work" / "fit_fulldense").mkdir(
        parents=True
    )
    rc, calls, gates, _ = _chain(tmp_path / "found", FL_DENSIFY="2")
    assert (
        rc == 1
        and gates["densify"] == 1
        and not any("densify_winding" in c for c in calls)
    )


def test_the_chain_refuses_a_band_that_is_already_fitted(tmp_path):
    (tmp_path / "fl" / "pherc0358_band" / "work" / "fit_full").mkdir(parents=True)
    rc, calls, gates, _ = _chain(tmp_path)
    assert rc == 2 and calls == [] and gates == {}
