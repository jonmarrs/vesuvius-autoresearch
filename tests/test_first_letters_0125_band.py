"""Finding 139: PHerc. 0125 in the band scripts (9.362 um, no published direction), its band, and its registration."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"
REG = ROOT / "docs/preregistration/2026-11-24_first_letters_0125_band_read.md"
FLAT = " ".join(REG.read_text().split())


def _env(tmp_path, **extra):
    env = {
        "PATH": "/usr/bin:/bin",
        "FL_ROOT": str(tmp_path),
        "FL_SCROLL": "PHerc0125",
        **extra,
    }
    return subprocess.run(
        ["bash", "-c", '. "$0"; printf "%s\\n" "$R" "$SENSE" "$CT_NAME" "$VOXEL_UM" "$Z_BEGIN" "$Z_END" "$UMBILICUS_STAMP"',
         str(BAND / "env.sh")],
        env=env, capture_output=True, text=True,
    )  # fmt: skip


def test_pherc0125_needs_a_declared_direction(tmp_path):
    run = _env(tmp_path)
    assert run.returncode != 0
    assert "PHerc0125 has no published direction: set FL_SENSE" in run.stderr


def test_pherc0125_declared_clockwise_at_its_scans_resolution_with_the_middle_of_its_tracked_range(
    tmp_path,
):
    run = _env(tmp_path, FL_SENSE="CW", FL_Z_BEGIN="10250", FL_Z_END="11750")
    assert run.returncode == 0, run.stderr
    r, sense, ct, um, z0, z1, umb = run.stdout.splitlines()
    assert sense == "CW" and um == "9.362"
    assert ct == "20250821151825-9.362um-1.2m-113keV-masked.zarr"
    assert umb == "20260808111524"
    assert r == f"{tmp_path}/pherc0125_band"
    # the middle 1,500 slices of the tracks' effective_z_bounds 4500-17500, inside the axis (z 2140-20354)
    assert (4500 + 17500) // 2 - 750 == 10250 and (z0, z1) == ("10250", "11750")
    assert 2140 < 10250 and 11750 < 20354


def test_finding_139_is_registered_before_any_fit_or_read_of_pherc0125():
    assert "Finding 139" in FLAT
    assert "**Written 2026-11-24, before any fit or read of PHerc. 0125.**" in FLAT
    assert (
        "FL_SCROLL=PHerc0125 FL_SENSE=CW FL_Z_BEGIN=10250 FL_Z_END=11750 FL_OVERLAP=1"
        in FLAT
    )
    assert "run_after_controls.sh bash run_band_and_read.sh" in FLAT
    assert "--finding 139 --quality-arm full" in FLAT
    assert "--top-to-bottom false --left-handed false --geometry" in FLAT
    assert "outer_sheets.py` and `sheet_coverage.py`" in FLAT
    for script in (
        "outer_sheets.py",
        "sheet_coverage.py",
        "band_fit_verdict.py",
        "band_geometry.py",
    ):
        assert (BAND / script).exists(), script


@pytest.mark.skipif(
    not (ROOT / "villa/spiral-fitting").is_dir(),
    reason="needs the villa submodule (the portable job has none)",
)
def test_the_direction_is_declared_by_villas_default_not_by_evidence():
    assert (
        "**`FL_SENSE=CW`**" in FLAT and "not on any evidence about this scroll" in FLAT
    )
    for tool in ("flatten_spiral_checkpoint.py", "find_inconsistent_windings.py"):
        source = (ROOT / "villa/spiral-fitting" / tool).read_text()
        assert "or 'CW'" in source or 'or "CW"' in source, tool
        assert f"`{tool}`" in FLAT
    f137 = " ".join(
        (ROOT / "docs/preregistration/2026-11-22_first_letters_0211_wrong_hand_read.md")
        .read_text()
        .split()
    )
    assert (
        "a band read of PHerc. 0125 may be registered with either direction declared"
        in f137
    )
    assert "may be registered with either direction declared" in FLAT


def test_a_wrong_top_to_bottom_flag_turns_every_image_by_half_a_turn():
    """band_index.py: the flag multiplies both flips' signs; the mirror's sign comes from the mesh's own theta."""
    src = (BAND / "band_index.py").read_text()
    assert "s = -1 if top_to_bottom else 1" in src
    assert (
        '"flip_ud": s * sign_z > 0' in src
        and '"flip_lr": s * t * sign_theta > 0' in src
    )
    assert "every image on the page stands turned by 180 degrees" in FLAT


def test_the_disk_needed_follows_finding_129s_sizes():
    import json

    f129 = json.loads(
        (ROOT / "reports/first_letters_0813_studio_band.json").read_text()
    )
    disk = f129["bytes_on_disk"]
    assert round(disk["renders"] / 1e9) == 47 and round(disk["studio_maps"] / 1e9) == 20
    assert "47 GB of renders and 20 GB of Studio's maps" in FLAT
    assert (
        "**at least 140 GB free**" in FLAT
        and "what to free is the owner's decision" in FLAT
    )
    assert "Nothing of PHerc. 0125 enters the November filing" in FLAT
