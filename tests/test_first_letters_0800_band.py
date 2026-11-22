"""Finding 133: PHerc. 0800 in the band scripts (8.64 um, clockwise), its band, and its registration's choices."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"
REG = ROOT / "docs/preregistration/2026-11-20_first_letters_0800_band_read.md"


def _env(tmp_path, **extra):
    env = {
        "PATH": "/usr/bin:/bin",
        "FL_ROOT": str(tmp_path),
        "FL_SCROLL": "PHerc0800",
        **extra,
    }
    out = subprocess.run(
        ["bash", "-c", '. "$0"; printf "%s\\n" "$R" "$SENSE" "$CT_NAME" "$VOXEL_UM" "$Z_BEGIN" "$Z_END" "$UMBILICUS_STAMP"',
         str(BAND / "env.sh")],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.splitlines()  # fmt: skip
    return dict(
        zip(
            ("R", "sense", "ct_name", "voxel_um", "z0", "z1", "umbilicus"),
            out,
            strict=True,
        )
    )


def test_pherc0800_is_clockwise_at_its_scans_resolution_with_the_middle_of_its_tracked_range(
    tmp_path,
):
    env = _env(tmp_path, FL_Z_BEGIN="10250", FL_Z_END="11750")
    assert env["sense"] == "CW" and env["voxel_um"] == "8.640"
    assert env["ct_name"] == "20250521135224-8.640um-1.2m-116keV-masked.zarr"
    assert env["umbilicus"] == "20260924033751"
    assert env["R"] == f"{tmp_path}/pherc0800_band"
    # the middle 1,500 slices of the tracks' effective_z_bounds 4500-17500, inside the axis (z 1728-23008)
    assert (4500 + 17500) // 2 - 750 == 10250 and (env["z0"], env["z1"]) == (
        "10250",
        "11750",
    )


def test_finding_133_is_registered_before_its_data_and_before_the_verdicts_it_waits_on():
    reg = REG.read_text()
    flat = " ".join(reg.split())
    assert "Finding 133" in reg
    assert (
        "before any input of PHerc. 0800 has been downloaded or fitted, and before findings 131 and 132 have run"
        in flat
    )
    assert "FL_SCROLL=PHerc0800 FL_Z_BEGIN=10250 FL_Z_END=11750 FL_OVERLAP=1" in flat
    assert "run_after_controls.sh bash run_band_and_read.sh" in flat
    assert "STUDIO_TILING=published" not in flat
    for v in (
        "`SKIP_ADOPTED`",
        "`DENSE_READS_WORSE`",
        "`STUDIO_SKIP_EMPTY=1`",
        "`FL_DENSIFY=2`",
    ):
        assert v in flat
    assert "--finding 133" in flat and "--quality-arm full" in flat
    assert "--top-to-bottom false --left-handed false --geometry" in flat


def test_the_chain_passes_the_choices_through_to_the_read():
    """run_after_controls.sh exports them; the chain runs the read with its environment, adding only the windings."""
    chain = (BAND / "run_band_and_read.sh").read_text()
    assert (
        'step read env STUDIO_WINDINGS="$R/work/studio_windings_full.txt" bash "$HERE/run_studio_band.sh" "$READ_ARM"'
        in chain
    )
    assert (
        'if [ -n "${FL_DENSIFY:-}" ]; then' in chain and "READ_ARM=fulldense" in chain
    )
    read = (BAND / "run_studio_band.sh").read_text()
    assert "${FL_OVERLAP:-0}" in read and "${STUDIO_SKIP_EMPTY:-0}" in read
