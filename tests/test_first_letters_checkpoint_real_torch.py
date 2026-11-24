"""The PHerc. 343 checkpoint checker against the real Torch loader.

tests/test_first_letters_checkpoint_reporting.py replaces Torch with a stub to
test the checker's control flow. These cases ask the installed Torch whether
the restricted load the checker requests refuses what it should.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

CHECKER = (
    Path(__file__).resolve().parents[1] / "repro/first_letters/pherc343/check_ckpt_safe"
).with_suffix(".py")


class _RunsCodeWhenLoaded:
    def __reduce__(self):
        return (print, ("pickle code ran",))


def _check(*paths):
    return subprocess.run(
        [sys.executable, str(CHECKER), *map(str, paths)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=dict(os.environ, CUDA_VISIBLE_DEVICES=""),
    )


def test_a_tensor_only_checkpoint_loads_restricted(tmp_path):
    path = tmp_path / "plain.pt"
    torch.save({"state_dict": {"w": torch.zeros(2, 2)}, "epoch": torch.tensor(3)}, path)
    result = _check(path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("WEIGHTS_ONLY_OK plain.pt")


def test_a_pickle_that_would_run_code_is_refused_without_running_it(tmp_path):
    path = tmp_path / "payload.pt"
    torch.save({"payload": _RunsCodeWhenLoaded()}, path)
    result = _check(path)
    assert result.returncode == 1
    assert result.stdout.startswith("NOT_WEIGHTS_ONLY payload.pt")
    assert "pickle code ran" not in result.stdout


def test_a_legacy_format_checkpoint_is_refused_before_it_is_loaded(tmp_path):
    # A non-zip checkpoint is refused before torch.load. The message says to
    # convert it offline to zip.
    path = tmp_path / "legacy.pt"
    torch.save({"w": torch.zeros(2)}, path, _use_new_zipfile_serialization=False)
    result = _check(path)
    assert result.returncode == 1
    assert result.stdout.startswith("NOT_WEIGHTS_ONLY legacy.pt ValueError")
    assert "convert it offline to zip" in result.stdout
