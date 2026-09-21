"""The determinism shim must be inert by default, active on request, and reachable
from run_render.sh -- verified by RUNNING an interpreter, not by reading the file.

Why the third property: on 2026-09-21 the first wiring of FLATTEN_DETERMINISTIC=1
into run_render.sh printed its banner and did nothing. The shim path was resolved
after a `cd`, PYTHONPATH pointed at a directory that did not exist, and Python
silently ignored it. A six-arm study nearly ran at stock speed under a
deterministic label. The banner is not evidence; the interpreter's own state is.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SHIM = REPO / "repro" / "spiral_render" / "determinism_shim"
RUN_RENDER = REPO / "repro" / "spiral_render" / "run_render.sh"
PROBE = (
    "import torch, os; "
    "print('DET', torch.are_deterministic_algorithms_enabled(), "
    "torch.backends.cudnn.deterministic, "
    "os.environ.get('CUBLAS_WORKSPACE_CONFIG', 'unset'))"
)


def _has_torch() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except Exception:
        return False


def _run(env_extra: dict) -> str:
    env = {**os.environ, "PYTHONPATH": str(SHIM), **env_extra}
    env.pop(
        "FLATTEN_DETERMINISTIC", None
    ) if "FLATTEN_DETERMINISTIC" not in env_extra else None
    r = subprocess.run(
        [sys.executable, "-c", PROBE], env=env, capture_output=True, text=True
    )
    return r.stdout + r.stderr


@pytest.mark.skipif(not _has_torch(), reason="torch not importable in this interpreter")
def test_shim_is_inert_without_the_flag():
    out = _run({})
    assert "DET False False unset" in out, out
    assert "[determinism-shim]" not in out


@pytest.mark.skipif(not _has_torch(), reason="torch not importable in this interpreter")
def test_shim_activates_with_the_flag():
    out = _run({"FLATTEN_DETERMINISTIC": "1"})
    assert "DET True True :4096:8" in out, out
    assert "[determinism-shim] torch.use_deterministic_algorithms" in out


def test_run_render_resolves_the_shim_before_cd():
    """The exact bug: SHIM_DIR must be computed from $0 BEFORE `cd "$W/..."`."""
    # Match EXECUTABLE lines, not comments: the script's own comment explains the
    # bug by quoting the cd, and a bare substring search found that first and
    # failed a correct script. Same trap as the tier test flagging its postmortem.
    lines = [
        ln
        for ln in RUN_RENDER.read_text().splitlines()
        if not ln.lstrip().startswith("#")
    ]
    i_shim = next(i for i, ln in enumerate(lines) if ln.startswith("SHIM_DIR="))
    i_cd = next(
        i for i, ln in enumerate(lines) if ln.startswith('cd "$W/spiral-fitting"')
    )
    assert i_shim < i_cd, (
        "SHIM_DIR is resolved after the cd; it will point into the work dir"
    )
    assert any(
        ln.startswith('[ -f "$SHIM_DIR/sitecustomize.py" ] ||') for ln in lines
    ), "no existence check"


def test_run_render_puts_the_shim_on_pythonpath():
    src = RUN_RENDER.read_text()
    assert re.search(r'PYTHONPATH="\$SHIM_DIR:', src), "shim not first on PYTHONPATH"


def test_shim_file_exists_where_run_render_expects_it():
    assert (SHIM / "sitecustomize.py").is_file()
