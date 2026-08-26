import subprocess
import sys

import numpy as np
import pytest
from conftest import machine_has_gpu


@pytest.mark.skipif(not machine_has_gpu(), reason="machine has no CUDA device")
def test_cli_vesselness_roundtrip(tmp_path, ambient_env):
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
        # Explicit env: probe test modules set CUDA_VISIBLE_DEVICES="" process
        # wide at import, and without this the child inherits it and dies with
        # cudaErrorNoDevice in a full-suite run while passing standalone.
        env=ambient_env,
    )
    assert r.returncode == 0, r.stderr
    res = np.load(out)
    assert res.shape == vol.shape
    assert np.isfinite(res).all()
    assert float(np.abs(res).sum()) > 0.0
