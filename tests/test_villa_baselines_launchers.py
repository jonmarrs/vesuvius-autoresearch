"""Dry-run smoke tests for the three villa-baseline launchers.

These tests confirm each launcher emits a marker JSON, surfaces the correct
non-submittable / submittable flags, and never invokes a real subprocess in
default mode. They do NOT spend GPU; --execute is never set.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _script(name: str) -> Path:
    """Locate a launcher under scripts/, wherever it currently lives.

    The launchers moved into scripts/training/ and scripts/inference/ in June
    2026 (4d9388e1, a0a1b10b) and this file kept pointing at scripts/<name>,
    so all five tests have been failing on a missing file ever since --
    passing the `check=True` subprocess a path that does not exist. Resolving
    the name means the next reorganisation cannot silently re-break them.
    """
    hits = sorted((REPO_ROOT / "scripts").rglob(name))
    assert len(hits) == 1, f"expected exactly one {name} under scripts/, found {hits}"
    return hits[0]


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_script(script)), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def test_launch_gp_winner_writes_baseline_marker(tmp_path):
    config_out = tmp_path / "gp.yaml"
    proc = _run(
        "launch_gp_winner.py",
        "--config-out",
        str(config_out),
        "--output-dir",
        str(tmp_path / "ckpt"),
        "--model-name",
        "gp_smoke",
        "--marker-out",
        str(tmp_path / "gp_marker.json"),
    )
    assert proc.returncode == 0
    marker = tmp_path / "gp_marker.json"
    assert marker.exists()
    data = json.loads(marker.read_text())
    assert data["submittable"] is False
    assert data["patch_size"] == [16, 256, 256]
    assert data["executed"] is False
    assert config_out.exists()


def test_launch_mutex_writes_marker_and_blocks_execute_without_data(tmp_path):
    data_path = tmp_path / "mutex_data"  # intentionally empty
    config_out = tmp_path / "mutex.yaml"
    proc = _run(
        "launch_mutex.py",
        "--data-path",
        str(data_path),
        "--config-out",
        str(config_out),
        "--model-name",
        "mutex_smoke",
        "--marker-out",
        str(tmp_path / "mutex_marker.json"),
    )
    assert proc.returncode == 0
    marker = tmp_path / "mutex_marker.json"
    data = json.loads(marker.read_text())
    assert data["submittable"] is True  # default patch=64
    assert data["data_prepared"] is False
    assert data["executed"] is False


def test_launch_finetune_lejepa_uses_submittable_patch_and_finds_pretrain(tmp_path):
    config_out = tmp_path / "ft.yaml"
    proc = _run(
        "launch_finetune_lejepa.py",
        "--config-out",
        str(config_out),
        "--output-dir",
        str(tmp_path / "ckpt"),
        "--model-name",
        "ft_smoke",
        "--marker-out",
        str(tmp_path / "ft_marker.json"),
    )
    assert proc.returncode == 0
    marker = tmp_path / "ft_marker.json"
    data = json.loads(marker.read_text())
    assert data["patch_size"] == [32, 64, 64]
    assert data["submittable"] is True
    assert data["executed"] is False
    # In this repo's known state there is a LeJEPA pretrain checkpoint and the
    # labeled Paris2Fr47 fragment; both should be auto-resolved.
    assert data["pretrained_lejepa_checkpoint"], (
        "expected LeJEPA pretrain ckpt to be discovered"
    )
    assert data["labeled_volumes"], "expected PHercParis2Fr47 to be discovered"
    assert data["ready"] is True
    assert config_out.exists()


def test_launch_finetune_lejepa_flags_non_submittable_when_patch_too_large(tmp_path):
    config_out = tmp_path / "ft_big.yaml"
    proc = _run(
        "launch_finetune_lejepa.py",
        "--config-out",
        str(config_out),
        "--output-dir",
        str(tmp_path / "ckpt"),
        "--model-name",
        "ft_smoke_big",
        "--patch",
        "32",
        "128",
        "128",
        "--marker-out",
        str(tmp_path / "ft_big_marker.json"),
    )
    assert proc.returncode == 0
    marker = tmp_path / "ft_big_marker.json"
    data = json.loads(marker.read_text())
    assert data["patch_size"] == [32, 128, 128]
    assert data["submittable"] is False


def test_launch_neural_tracing_falls_back_to_the_hf_sentinel(tmp_path):
    """The contract changed on 2026-06-05 (318d6b85) and this test did not.

    It used to assert that a missing local checkpoint is a blocker. That commit
    made the launcher fall back to villa's HuggingFace sentinel
    `extrap_displacement_latest` instead, so a missing local checkpoint stops
    being a blocker by design. The test kept asserting the old contract and had
    no way to pass; it was masked by the path breakage that made every test in
    this file error before reaching its assertions.

    What is pinned now is the new contract: the launcher always resolves SOME
    checkpoint, wires it into the command, and never blocks on it.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "inference"))
    from launch_neural_tracing import _find_neural_tracing_checkpoint

    local = _find_neural_tracing_checkpoint()
    expected = str(local) if local else "extrap_displacement_latest"

    marker_out = tmp_path / "trace.json"
    proc = _run(
        "launch_neural_tracing.py",
        "--scroll-id",
        "0125",
        "--division",
        "div_100",
        "--marker-out",
        str(marker_out),
    )
    assert proc.returncode == 0
    assert marker_out.exists()
    data = json.loads(marker_out.read_text())

    assert data["checkpoint"] == expected
    cmd = data["command"]
    assert cmd[cmd.index("--checkpoint_path") + 1] == expected
    assert not any("checkpoint" in b for b in data["blockers"])
    assert data["socket_path"].endswith(".sock")
    # `ready` is not asserted: it turns on whether this machine happens to have
    # the OME-zarr volume, which is not what this test is about.
