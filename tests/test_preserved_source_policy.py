"""Automatic edits must skip byte-preserved sources and retain active coverage."""

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FROZEN = [
    "scripts/archive/legacy_figures/generate_fiber_image.py",
    "scripts/archive/legacy_figures/generate_real_scroll_evidence.py",
    "scripts/archive/legacy_launchers/run_cross_scan_registration.py",
    "scripts/archive/legacy_launchers/run_autoresearch_nnunet_bridge.py",
]


@pytest.mark.parametrize(
    "path",
    FROZEN
    + [
        "config.json",
        "autoresearch_history.json",
        "recent_configs.json",
        "history.tsv",
        "prize_readiness.tsv",
        ".current_day_shift_log",
        "repro/villa_preserved/source.py",
    ],
)
def test_precommit_never_autofixes_protected_sources_or_live_state(path):
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    assert re.search(config["exclude"], path), path


@pytest.mark.parametrize(
    "path",
    [
        "scripts/training/train.py",
        "scripts/run_validation_tests.py",
        "scripts/archive/legacy_launchers/README.md",
    ],
)
def test_preservation_exclusions_retain_checks_for_maintained_code_and_notes(path):
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    assert not re.search(config["exclude"], path), path


def test_default_ruff_discovery_skips_only_the_frozen_archive_sources():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--show-files", "scripts"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    selected = {
        Path(line).resolve().relative_to(ROOT).as_posix()
        for line in result.stdout.splitlines()
    }
    assert not selected.intersection(FROZEN)
    assert "scripts/training/train.py" in selected
    assert "scripts/archive/download_chunks.py" in selected
