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


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), *args],
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
    )
    assert proc.returncode == 0
    marker = REPO_ROOT / "reports" / "gp_winner_baseline.json"
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
    )
    assert proc.returncode == 0
    marker = REPO_ROOT / "reports" / "mutex_affinity_run.json"
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
    )
    assert proc.returncode == 0
    marker = REPO_ROOT / "reports" / "finetune_lejepa_run.json"
    data = json.loads(marker.read_text())
    assert data["patch_size"] == [32, 64, 64]
    assert data["submittable"] is True
    assert data["executed"] is False
    # In this repo's known state there is a LeJEPA pretrain checkpoint and the
    # labeled Paris2Fr47 fragment; both should be auto-resolved.
    assert data["pretrained_lejepa_checkpoint"], "expected LeJEPA pretrain ckpt to be discovered"
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
    )
    assert proc.returncode == 0
    marker = REPO_ROOT / "reports" / "finetune_lejepa_run.json"
    data = json.loads(marker.read_text())
    assert data["patch_size"] == [32, 128, 128]
    assert data["submittable"] is False


def test_launch_neural_tracing_reports_missing_checkpoint(tmp_path):
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
    assert data["ready"] is False
    assert any("checkpoint" in b for b in data["blockers"])
    assert data["socket_path"].endswith(".sock")
