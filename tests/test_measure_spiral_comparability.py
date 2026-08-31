"""The comparability check decides whether two fits can be compared at all.

It is what ruled out the obvious confound in the smoke-vs-baseline overlap
result: that the near-unfitted run might simply be more spread out. If its
radius or step arithmetic were wrong, that confound would have been dismissed
on a bad number.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

tifffile = pytest.importorskip("tifffile")

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "measure_spiral_comparability.py"


def write_spiral(
    root: Path, n_windings: int, step: float, centre=(1000.0, 1000.0)
) -> Path:
    """A synthetic spiral: winding k is a ring of radius k*step about `centre`."""
    root.mkdir(parents=True, exist_ok=True)
    for k in range(n_windings):
        th = np.linspace(0, 2 * np.pi, 200, endpoint=False)
        r = (k + 1) * step
        pts = np.stack(
            [
                centre[0] + r * np.cos(th),
                centre[1] + r * np.sin(th),
                np.full(th.size, 500.0),
            ],
            1,
        )
        d = root / f"w{k:03d}_spliced_t"
        d.mkdir()
        for i, c in enumerate("xyz"):
            tifffile.imwrite(d / f"{c}.tif", pts[:, i].astype(np.float32)[None, :])
    return root


def run(*dirs):
    args = [f"{tag}={path}" for tag, path in dirs]
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=True
    ).stdout


def parse(stdout):
    """Rows look like:
    a   centre ( 1000.0, 1000.0)  radius  20.0..  80.0  median inter-winding step  20.00  monotone 3/3
    """
    out = {}
    for line in stdout.splitlines():
        if "monotone" not in line:
            continue
        p = line.split()
        out[p[0]] = {"step": float(p[-3]), "monotone": p[-1]}
    return out


def test_recovers_a_known_inter_winding_step(tmp_path):
    """A synthetic spiral with a known ring spacing must report that spacing."""
    write_spiral(tmp_path / "a", n_windings=8, step=20.0)
    r = parse(run(("a", tmp_path / "a")))
    assert abs(r["a"]["step"] - 20.0) < 0.5
    assert r["a"]["monotone"] == "7/7", "radii must increase with winding index"


def test_separates_a_tighter_spiral_from_a_wider_one(tmp_path):
    """The comparison that mattered: the smoke fit was packed TIGHTER than the
    converged one, which is what ruled out 'it is just more spread out'."""
    write_spiral(tmp_path / "tight", n_windings=8, step=16.0)
    write_spiral(tmp_path / "wide", n_windings=8, step=24.0)
    r = parse(run(("tight", tmp_path / "tight"), ("wide", tmp_path / "wide")))
    assert r["tight"]["step"] < r["wide"]["step"]
    assert abs(r["tight"]["step"] - 16.0) < 0.5 and abs(r["wide"]["step"] - 24.0) < 0.5


def test_non_monotone_spiral_is_reported_as_such(tmp_path):
    """A fit whose radii do not increase with winding index is not a spiral, and
    must not be silently compared as one."""
    root = write_spiral(tmp_path / "bad", n_windings=6, step=20.0)
    # swap two windings' geometry so the radius order breaks
    import shutil

    shutil.rmtree(root / "w002_spliced_t")
    (root / "w005_spliced_t").rename(root / "tmp")
    (root / "tmp").rename(root / "w002_spliced_t")
    r = parse(run(("bad", root)))
    assert r["bad"]["monotone"] != "4/4", (
        "a broken radius order must not read as fully monotone"
    )
