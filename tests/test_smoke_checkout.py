"""Smoke must use the current checkout and enforce its CPU-only contract."""

import os
import subprocess
import sys
from pathlib import Path


def test_smoke_overrides_foreign_editable_install_and_visible_gpu(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    foreign = tmp_path / "foreign/src"
    core = foreign / "vesuvius_autoresearch/core"
    core.mkdir(parents=True)
    (core / "__init__.py").write_text(
        "raise AssertionError('foreign checkout imported')\n"
    )
    code = """
import os, runpy, sys, types
from pathlib import Path
sys.path.insert(0, sys.argv[2])
sys.modules['torch'] = types.ModuleType('torch')
smoke = Path(sys.argv[1])
sys.argv = [str(smoke), '--list-only']
try:
    runpy.run_path(str(smoke), run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
assert os.environ['CUDA_VISIBLE_DEVICES'] == ''
import vesuvius_autoresearch.core as core
assert Path(core.__file__).resolve().is_relative_to(smoke.parents[1] / 'src')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            code,
            str(repo / "scripts/smoke_test.py"),
            str(foreign),
        ],
        cwd=tmp_path,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "best_model_loads" in result.stdout
