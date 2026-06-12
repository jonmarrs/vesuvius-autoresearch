import subprocess
import sys

import numpy as np


def test_cli_vesselness_roundtrip(tmp_path):
    vol = np.random.default_rng(0).random((16, 32, 32)).astype(np.float32)
    inp = tmp_path / "vol.npy"
    out = tmp_path / "out.npy"
    np.save(inp, vol)
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "vesuvius_autoresearch.fibers.cli",
            "--input",
            str(inp),
            "--filter",
            "vesselness",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert r.returncode == 0, r.stderr
    res = np.load(out)
    assert res.shape == vol.shape
    assert np.isfinite(res).all()
    assert float(np.abs(res).sum()) > 0.0
