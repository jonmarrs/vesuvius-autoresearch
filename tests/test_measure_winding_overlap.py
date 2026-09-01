"""The overlap probe must count what it says it counts.

Written against synthetic tifxyz meshes with a known answer, because the real
measurement (0.09% of cells) is small enough that a counting bug would look
exactly like the result.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

tifffile = pytest.importorskip("tifffile")

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "measure_winding_overlap.py"


def write_mesh(d: Path, pts: np.ndarray) -> None:
    """One tifxyz mesh whose valid cells are `pts`, as a 1 x N grid."""
    d.mkdir(parents=True)
    for i, c in enumerate("xyz"):
        tifffile.imwrite(d / f"{c}.tif", pts[:, i].astype(np.float32)[None, :])


def run(meshes: Path, out: Path, quant: int = 4):
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(meshes),
            "--quant",
            str(quant),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return json.loads(out.read_text())["quant"][str(quant)]


def test_disjoint_windings_report_no_overlap(tmp_path):
    m = tmp_path / "meshes"
    for w, off in ((10, 0.0), (11, 100.0), (12, 200.0)):
        write_mesh(
            m / f"w{w:03d}_spliced_t",
            np.stack(
                [np.arange(20, dtype=float) * 8 + off, np.zeros(20), np.zeros(20)], 1
            ),
        )
    r = run(m, tmp_path / "o.json")
    assert r["multi"] == 0 and r["far_gap2"] == 0


def test_two_windings_on_the_same_points_are_all_overlap(tmp_path):
    """Identical geometry under two winding indices 3 apart: every cell is
    multiply claimed AND every one counts toward gap>=2."""
    m = tmp_path / "meshes"
    pts = np.stack([np.arange(16, dtype=float) * 8, np.zeros(16), np.zeros(16)], 1)
    write_mesh(m / "w010_spliced_t", pts)
    write_mesh(m / "w013_spliced_t", pts)
    r = run(m, tmp_path / "o.json")
    assert r["occupied"] == 16
    assert r["multi"] == 16
    assert r["far_gap2"] == 16
    assert r["gap_hist"] == {"3": 16}


def test_adjacent_overlap_is_not_counted_as_far(tmp_path):
    """Gap-1 overlap is the quantisation artefact the report sets aside; it must
    land in `multi` but never in `far_gap2`."""
    m = tmp_path / "meshes"
    pts = np.stack([np.arange(16, dtype=float) * 8, np.zeros(16), np.zeros(16)], 1)
    write_mesh(m / "w010_spliced_t", pts)
    write_mesh(m / "w011_spliced_t", pts)
    r = run(m, tmp_path / "o.json")
    assert r["multi"] == 16 and r["far_gap2"] == 0


def test_non_spliced_meshes_are_ignored(tmp_path):
    """render_ink.py renders only `_spliced`, so counting the plain variant would
    invent a 100% overlap that the real pipeline never sees."""
    m = tmp_path / "meshes"
    pts = np.stack([np.arange(16, dtype=float) * 8, np.zeros(16), np.zeros(16)], 1)
    write_mesh(m / "w010_spliced_t", pts)
    write_mesh(m / "w010_t", pts)  # same geometry, plain variant
    r = run(m, tmp_path / "o.json")
    assert r["multi"] == 0


def test_invalid_cells_are_dropped(tmp_path):
    """-1 marks an unmapped grid cell. Two meshes sharing only -1 padding must not
    read as overlapping."""
    m = tmp_path / "meshes"
    a = np.stack(
        [
            np.r_[np.arange(8, dtype=float) * 8, np.full(8, -1.0)],
            np.r_[np.zeros(8), np.full(8, -1.0)],
            np.r_[np.zeros(8), np.full(8, -1.0)],
        ],
        1,
    )
    b = a.copy()
    b[:8, 0] += 1000.0
    write_mesh(m / "w010_spliced_t", a)
    write_mesh(m / "w014_spliced_t", b)
    r = run(m, tmp_path / "o.json")
    assert r["occupied"] == 16 and r["multi"] == 0


def test_it_detects_approximate_not_only_exact_overlap(tmp_path):
    """Every duplicate arm measured so far used an EXACT mesh copy, so cells
    coincided perfectly. Fit-produced overlap is approximate: two sheets near each
    other, not identical. If the detector only fired on near-exact coincidence, a
    null on a real fit would be an instrument limit misread as absence.

    It degrades gracefully instead. Two windings five apart in index, one displaced
    by delta voxels, quant 4:

        delta 0 vx -> 100%   delta 4 vx -> 28%
        delta 2 vx ->  56%   delta 8 vx -> 10%

    so detection falls with displacement but never to zero over the range that
    matters (the fit's own sheet spacing is 16.17 vx).
    """

    def build(root, delta):
        th = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
        base = np.stack(
            [
                1000 + 1000 * np.cos(th),
                1000 + 1000 * np.sin(th),
                np.full(th.size, 500.0),
            ],
            1,
        )
        for name, off in (("w010_spliced_t", 0.0), ("w015_spliced_t", delta)):
            write_mesh(root / name, base + np.array([off, 0.0, 0.0]))

    fracs = {}
    for delta in (0.0, 4.0, 8.0):
        root = tmp_path / f"d{int(delta)}"
        build(root, delta)
        fracs[delta] = run(root, tmp_path / f"o{int(delta)}.json")["far_frac"]

    assert fracs[0.0] > 0.95, "an exact copy must read as near-total overlap"
    assert fracs[4.0] > 0.10, "a 4-voxel displacement must still be clearly detected"
    assert fracs[8.0] > 0.02, "even half the sheet spacing must not read as zero"
    assert fracs[0.0] > fracs[4.0] > fracs[8.0], (
        "detection must fall monotonically with displacement"
    )
