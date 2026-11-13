"""Archived v3 launchers must refuse before importing ML code or touching state."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("entry", ["run_v3", "trainer"])
@pytest.mark.parametrize("module_mode", [False, True])
@pytest.mark.parametrize("help_only", [False, True])
def test_archived_launcher_is_read_only_and_needs_no_ml_imports(
    tmp_path, entry, module_mode, help_only
):
    traps = tmp_path / "imports"
    traps.mkdir()
    for name in ("torch", "numpy", "trainer", "vesuvius"):
        (traps / f"{name}.py").write_text(
            "raise AssertionError('ML import attempted')\n"
        )
    state = tmp_path / "config.yaml"
    state.write_text("not even a valid training configuration\n")
    before = state.read_bytes()
    invocation = (
        ["-m", f"v3_training.{entry}"]
        if module_mode
        else [str(ROOT / "v3_training" / f"{entry}.py")]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            *invocation,
            *(["--help"] if help_only else [str(state)]),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(traps), str(ROOT)))},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == (0 if help_only else 2), result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "retired" in output.lower()
    assert "scripts/training/train.py" in output
    assert "ML import attempted" not in output and "Traceback" not in output
    assert state.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["config.yaml", "imports"]


def test_importing_the_old_launcher_does_not_import_its_archived_trainer():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import v3_training.run_v3; assert 'torch' not in sys.modules; assert 'v3_training.trainer' not in sys.modules",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
