"""The frame probe decides whether a render will be blank, so its arithmetic must
be right. A wrong scale here sends someone off to debug a black strip that is
actually a coordinate bug, or worse, blesses a scale that is wrong.

These tests use a fake zarr-like array so no network or 81 TB volume is needed.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

tifffile = pytest.importorskip("tifffile")

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "probe_ink_volume_frame.py"


def write_mesh(d: Path, pts: np.ndarray) -> None:
    d.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate("xyz"):
        tifffile.imwrite(d / f"{c}.tif", pts[:, i].astype(np.float32)[None, :])


def run_probe(mesh_dir: Path, fake_volume: Path, scales="1 2 4"):
    """Run the probe against a stub volume injected through a sitecustomize shim."""
    shim = mesh_dir.parent / "stub"
    shim.mkdir(exist_ok=True)
    (shim / "sitecustomize.py").write_text(f'''
import numpy as np, sys, types
vol = np.load(r"{fake_volume}")
class _Arr:
    shape = vol.shape
    dtype = vol.dtype
    def __getitem__(self, k): return vol[k]
z = types.ModuleType("zarr")
z.open = lambda *a, **k: {{"0": _Arr()}}
sys.modules["zarr"] = z
f = types.ModuleType("fsspec")
f.get_mapper = lambda *a, **k: None
sys.modules["fsspec"] = f
''')
    env = {"PYTHONPATH": str(shim), "PATH": "/usr/bin:/bin"}
    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(mesh_dir),
            "--scales",
            *scales.split(),
            "--samples",
            "50",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return out.stdout


def parse(stdout):
    rows = {}
    for line in stdout.splitlines():
        p = line.split()
        if len(p) == 6 and p[1].endswith("%") and p[3].endswith("%"):
            rows[float(p[0])] = float(p[3].rstrip("%"))
    return rows


def test_correct_scale_reads_signal_and_wrong_scale_reads_zero(tmp_path):
    """A volume with data only in a far region: mesh coords at 1x land on empty
    space, at 4x they land on the data. The probe must show exactly that."""
    vol = np.zeros((400, 400, 400), np.uint8)
    vol[200:260, 200:260, 200:260] = 200  # signal only at 4x the mesh coords
    vp = tmp_path / "vol.npy"
    np.save(vp, vol)
    pts = np.stack([np.full(60, 55.0), np.full(60, 55.0), np.linspace(50, 64, 60)], 1)
    write_mesh(tmp_path / "m", pts)
    rows = parse(run_probe(tmp_path / "m", vp))
    assert rows[1.0] == 0.0, "raw coords must read empty"
    assert rows[4.0] > 80.0, "4x must land on the data"


def test_all_scales_in_bounds_is_not_evidence(tmp_path):
    """The failure this probe exists to catch: every scale is in bounds while only
    one reads signal. If in-bounds were the check, all three would pass."""
    vol = np.zeros((400, 400, 400), np.uint8)
    vol[200:260, 200:260, 200:260] = 200
    vp = tmp_path / "vol.npy"
    np.save(vp, vol)
    pts = np.stack([np.full(60, 55.0), np.full(60, 55.0), np.linspace(50, 64, 60)], 1)
    write_mesh(tmp_path / "m", pts)
    out = run_probe(tmp_path / "m", vp)
    inb = [
        ln.split()[1]
        for ln in out.splitlines()
        if len(ln.split()) == 6 and ln.split()[1].endswith("%")
    ]
    assert inb == ["100.0%"] * 3


def test_invalid_vertices_are_excluded(tmp_path):
    """-1 marks unmapped grid cells. Sampling them would read the volume origin,
    which is empty, and dilute every scale toward zero."""
    vol = np.full((400, 400, 400), 7, np.uint8)
    vp = tmp_path / "vol.npy"
    np.save(vp, vol)
    good = np.stack([np.full(30, 50.0), np.full(30, 50.0), np.linspace(50, 60, 30)], 1)
    bad = np.full((30, 3), -1.0)
    write_mesh(tmp_path / "m", np.concatenate([good, bad]))
    rows = parse(run_probe(tmp_path / "m", vp, scales="1"))
    assert rows[1.0] == 100.0, "with -1 excluded every sample sits on nonzero data"
