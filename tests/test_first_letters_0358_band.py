"""Finding 126: PHerc. 0358 in the band scripts, the selection of windings before any ink, the stacked-winding
check, and the chain."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

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
