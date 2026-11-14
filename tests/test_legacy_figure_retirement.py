"""Retired figure entrypoints must not import ML code or replace evidence."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "entry", ["generate_fiber_image", "generate_real_scroll_evidence"]
)
@pytest.mark.parametrize("help_only", [False, True])
def test_legacy_entrypoints_are_read_only_without_gpu_imports(
    tmp_path, entry, help_only
):
    for name in ["numpy", "cupy", "torch", "matplotlib", "tools", "zarr"]:
        (tmp_path / f"{name}.py").write_text(
            "raise AssertionError('scientific import attempted')\n"
        )
    evidence = tmp_path / "reports/real_scroll_evidence/summary.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"preserve historical evidence")
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / f"{entry}.py"),
            *(["--help"] if help_only else []),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == (0 if help_only else 2), result.stdout + result.stderr
    assert "retired" in result.stdout + result.stderr
    assert "scientific import attempted" not in result.stdout + result.stderr
    assert evidence.read_bytes() == b"preserve historical evidence"


def test_importing_the_old_entrypoints_never_runs_a_figure_generator():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import generate_fiber_image, generate_real_scroll_evidence; assert 'cupy' not in sys.modules and 'numpy' not in sys.modules",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
