"""PHerc. 0813 in the band scripts (clockwise, as PHerc. 343), its band, and the band read's tiling option."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"


def _env(tmp_path, **extra):
    env = {"PATH": "/usr/bin:/bin", "FL_ROOT": str(tmp_path), **extra}
    out = subprocess.run(
        ["bash", "-c", '. "$0"; printf "%s\\n" "$R" "$SENSE" "$VOLUME_ID" "$UMBILICUS_KEY" "$SURF_CHUNKS" "$CT_CHUNKS" "$LASAGNA_CHUNKS" "$CT_NAME"', str(BAND / "env.sh")],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.splitlines()  # fmt: skip
    keys = ("R", "sense", "volume", "umbilicus", "surface", "ct", "lasagna", "ct_name")
    return dict(zip(keys, out, strict=True))


def test_pherc0813_is_clockwise_with_its_published_axis_and_the_chunks_of_its_band(
    tmp_path,
):
    v = _env(tmp_path, FL_SCROLL="PHerc0813", FL_Z_BEGIN="9996", FL_Z_END="11496")
    assert v["R"] == f"{tmp_path}/pherc0813_band" and v["sense"] == "CW"
    assert v["volume"] == "20250821151723"
    assert (
        v["umbilicus"]
        == "PHerc0813/representations/umbilicus/20250821151723-umbilicus-20260924033203.json"
    )
    assert (
        v["ct_name"] == "20250821151723-9.362um-1.2m-113keV-masked.zarr"
    )  # its scan is 9.362 um
    lo, hi = 9996 - 64, 11496 + 64
    for key, voxels_per_chunk in (("surface", 384), ("ct", 256), ("lasagna", 128)):
        first, last = (int(x) for x in v[key].split())
        assert first * voxels_per_chunk <= lo and (last + 1) * voxels_per_chunk > hi


def test_the_band_is_the_middle_1500_slices_of_the_tracked_range():
    begin, end = 4500, 16993  # the tracks' effective_z_bounds, read 2026-11-20
    middle = (begin + end) // 2
    assert (middle - 750, middle + 750) == (9996, 11496)
    assert 1808 < 9996 and 11496 < 16864  # inside the published axis's control points


def test_the_read_keeps_the_winners_tiling_unless_told_otherwise():
    text = (BAND / "run_studio_band.sh").read_text()
    assert 'case "${STUDIO_TILING:-winner}" in' in text
    assert "winner) TILING=(--stride 64 --blend hann) ;;" in text
    assert "published) TILING=() ;;" in text
    assert '"${TILING[@]}"' in text and "tiling=${STUDIO_TILING:-winner}" in text


def test_an_unknown_tiling_stops_the_read_before_anything_runs(tmp_path):
    text = (BAND / "run_studio_band.sh").read_text()
    block = text[
        text.index('case "${STUDIO_TILING:-winner}" in') : text.index(
            "esac", text.index("STUDIO_TILING:-winner")
        )
        + 4
    ]
    for value, code, args in (
        ("", 0, "--stride 64 --blend hann"),
        ("published", 0, ""),
        ("fast", 2, None),
    ):
        run = subprocess.run(["bash", "-uc", f'STUDIO_TILING="{value}"; [ -z "$STUDIO_TILING" ] && unset STUDIO_TILING\n{block}\necho "${{TILING[*]}}"'],
                             capture_output=True, text=True)  # fmt: skip
        assert run.returncode == code, (value, run.stderr)
        if args is not None:
            assert run.stdout.strip() == args


def _arc(
    path, radius, theta0, theta1, axis=(5000.0, 5000.0)
):  # tifxyz: coordinates stay positive
    import numpy as np
    import tifffile

    theta = np.linspace(
        theta0, theta1, max(10, int(radius * (theta1 - theta0) / 20))
    )  # nodes ~20 voxels apart
    z = np.arange(8) * 20.0 + 9000
    tt, zz = np.meshgrid(theta, z)
    xyz = np.stack(
        [axis[0] + radius * np.cos(tt), axis[1] + radius * np.sin(tt), zz], -1
    )
    path.mkdir(parents=True)
    for i, name in enumerate("xyz"):
        tifffile.imwrite(path / f"{name}.tif", xyz[..., i].astype(np.float32))
    return path


def test_against_the_axis_the_flip_follows_each_windings_way_where_the_band_centre_does_not(
    tmp_path,
):
    import importlib.util
    import json
    import sys

    spec = importlib.util.spec_from_file_location(
        "studio_band_axis", BAND / "studio_band.py"
    )
    sb = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = sb
    spec.loader.exec_module(sb)
    # a small inner arc inside a large outer arc on the same side: the nodes' mean lies out beyond the inner arc,
    # so from it the inner arc's radial direction is reversed
    inner = _arc(tmp_path / "w010.tifxyz", 150.0, 3.0, 4.2)
    outer = _arc(tmp_path / "w011.tifxyz", 3000.0, 3.0, 4.2)
    axis = tmp_path / "umbilicus.json"
    axis.write_text(
        json.dumps(
            {
                "control_points": [
                    {"x": 5000, "y": 5000, "z": 0},
                    {"x": 5000, "y": 5000, "z": 20000},
                ]
            }
        )
    )
    by_axis = sb.orientation([inner, outer], axis)
    assert by_axis["reference"] == "scroll_axis"
    shares = {
        k: v["share_of_normals_pointing_inward"] for k, v in by_axis["windings"].items()
    }
    assert (
        set(shares.values()) <= {0.0, 1.0} and len(set(shares.values())) == 1
    )  # both arcs point the same way
    assert len({v["render"] for v in by_axis["windings"].values()}) == 1
    by_centre = sb.orientation([inner, outer])
    assert by_centre["reference"] == "band_centre"
    assert (
        by_centre["windings"]["w010"]["render"] != by_axis["windings"]["w010"]["render"]
    )


def test_the_read_orients_against_the_published_axis():
    text = (BAND / "run_studio_band.sh").read_text()
    assert (
        'orient "$OUT/orient.json" "${FINALS[@]}" --umbilicus "$R/dataset/umbilicus.json"'
        in text
    )


def test_the_chain_densifies_the_selected_windings_only_when_asked():
    text = (BAND / "run_band_and_read.sh").read_text()
    assert (
        text.index("step select")
        < text.index("step densify densify_selected")
        < text.index("step read")
    )
    assert (
        'READ_ARM=full\nif [ -n "${FL_DENSIFY:-}" ]; then\n  READ_ARM=fulldense' in text
    )
    assert (
        '"$HERE/densify_winding.py" "$base/$w" "$dest/$w" --factor "$FL_DENSIFY"'
        in text
    )
    assert 'bash "$HERE/run_studio_band.sh" "$READ_ARM"' in text
    assert (BAND / "densify_winding.py").exists()
