"""Unimplemented launchers must refuse before imports, writes or success claims."""

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "run_cross_scan_registration": "1099f45104918d16f033442e238857a5e1b23b9eee26a48c15028f72269bf69f",
    "run_autoresearch_nnunet_bridge": "e20dc659624a4bfabb2c5b3ea8a2ceb568214e4a1aecbd9dbbdd647c508afc37",
}


def run(tmp_path, name, arguments, *, isolated=False):
    return subprocess.run(
        [
            sys.executable,
            "-B",
            *(["-I"] if isolated else []),
            str(ROOT / f"scripts/{name}.py"),
            *arguments,
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.mark.parametrize("name", SOURCES)
@pytest.mark.parametrize("isolated", [False, True])
def test_unsupported_launchers_have_dependency_free_help(tmp_path, name, isolated):
    for dependency in ("yaml", "numpy", "torch", "zarr", "registration"):
        (tmp_path / f"{dependency}.py").write_text(
            "raise AssertionError('unexpected scientific import')\n"
        )
    result = run(tmp_path, name, ["--help"], isolated=isolated)
    assert result.returncode == 0, result.stderr
    assert "retired" in result.stdout.lower()
    assert "unexpected scientific import" not in result.stdout + result.stderr


@pytest.mark.parametrize("auto", [False, True])
def test_registration_refuses_without_creating_directories_or_a_transform(
    tmp_path, auto
):
    # The former implementation could report success with these importable
    # dependencies while never calling align_zarrs or writing a transform.
    (tmp_path / "zarr.py").write_text("def open(*args, **kwargs): return object()\n")
    (tmp_path / "registration.py").write_text(
        "def align_zarrs(*args): raise AssertionError('alignment unexpectedly called')\n"
    )
    output = tmp_path / "new/transform.json"
    result = run(
        tmp_path,
        "run_cross_scan_registration",
        [
            "--fixed",
            "fixed",
            "--moving",
            "moving",
            "--out",
            str(output),
            *(["--auto"] if auto else []),
        ],
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "retired" in result.stderr.lower()
    assert "Transform saved" not in result.stdout + result.stderr
    assert not output.parent.exists()


def test_nnunet_bridge_preserves_a_config_at_its_old_fixed_output_path(tmp_path):
    config = tmp_path / "configs/config_nnunet_tmp.yml"
    config.parent.mkdir()
    original = b"configurations:\n- name: baseline\n  params:\n    initial_lr: 0.01\n    weight_decay: 0.001\n    num_epochs: 100\n"
    config.write_bytes(original)
    result = run(
        tmp_path,
        "run_autoresearch_nnunet_bridge",
        [
            "--config",
            str(config),
            "--evolve-attr",
            "initial_lr",
            "--evolve-val",
            "0.02",
            "--variant-name",
            "trial",
        ],
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "retired" in result.stderr.lower()
    assert config.read_bytes() == original
    assert "written" not in result.stdout


def test_nnunet_bridge_does_not_create_a_fixed_output_for_another_config(tmp_path):
    config = tmp_path / "base.yml"
    config.write_text("configurations: []\n")
    (tmp_path / "configs").mkdir()
    result = run(tmp_path, "run_autoresearch_nnunet_bridge", ["--config", str(config)])
    assert result.returncode == 2
    assert not (tmp_path / "configs/config_nnunet_tmp.yml").exists()


@pytest.mark.parametrize("name", SOURCES)
def test_importing_a_retired_launcher_preserves_import_state(name, monkeypatch):
    monkeypatch.setattr(sys, "path", sys.path[:])
    path = sys.path[:]
    modules = set(sys.modules)
    spec = importlib.util.spec_from_file_location(
        f"{name}_retired", ROOT / f"scripts/{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert sys.path == path
    assert not (
        {"yaml", "torch", "numpy", "zarr", "registration"}
        & (set(sys.modules) - modules)
    )


@pytest.mark.parametrize("name,digest", SOURCES.items())
def test_original_launcher_source_is_retained_byte_for_byte(name, digest):
    source = ROOT / f"scripts/archive/legacy_launchers/{name}.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
