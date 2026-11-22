"""A shell-requested CPU run must not start the test suite's CUDA probe."""

import subprocess
import sys
from types import SimpleNamespace

import conftest
import pytest


@pytest.fixture(autouse=True)
def clear_availability_cache():
    conftest.gpu_available_ambiently.cache_clear()
    yield
    conftest.gpu_available_ambiently.cache_clear()


def set_process_visibility(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    else:
        monkeypatch.setenv("CUDA_VISIBLE_DEVICES", value)


@pytest.mark.parametrize("process_visibility", ["", None, "0"])
def test_shell_cpu_request_never_starts_a_probe(monkeypatch, process_visibility):
    monkeypatch.setattr(conftest, "_AMBIENT_CUDA_VISIBLE_DEVICES", "")
    set_process_visibility(monkeypatch, process_visibility)
    calls = []

    def fake_probe(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(conftest.subprocess, "run", fake_probe)
    assert not conftest.gpu_available_ambiently()
    assert not calls


@pytest.mark.parametrize(
    "ambient_visibility,process_visibility",
    [(None, ""), (None, "3"), ("0", ""), ("2,3", "")],
)
def test_unmasked_shell_probe_restores_ambient_visibility(
    monkeypatch, ambient_visibility, process_visibility
):
    monkeypatch.setattr(conftest, "_AMBIENT_CUDA_VISIBLE_DEVICES", ambient_visibility)
    set_process_visibility(monkeypatch, process_visibility)
    calls = []

    def fake_probe(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(conftest.subprocess, "run", fake_probe)
    assert conftest.gpu_available_ambiently()
    ((command, options),) = calls
    assert command[:2] == [sys.executable, "-c"]
    assert "getDeviceCount" in command[2]
    assert options["env"].get("CUDA_VISIBLE_DEVICES") == ambient_visibility
    assert ("CUDA_VISIBLE_DEVICES" in options["env"]) == (
        ambient_visibility is not None
    )
    assert options["capture_output"] and options["timeout"] == 120


@pytest.mark.parametrize("returncode", [1, 2, -9])
def test_failed_probe_still_reports_unavailable(monkeypatch, returncode):
    monkeypatch.setattr(conftest, "_AMBIENT_CUDA_VISIBLE_DEVICES", None)
    monkeypatch.setattr(
        conftest.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=returncode),
    )
    assert not conftest.gpu_available_ambiently()


@pytest.mark.parametrize(
    "error", [OSError("probe unavailable"), subprocess.TimeoutExpired(["probe"], 120)]
)
def test_probe_errors_still_report_unavailable(monkeypatch, error):
    monkeypatch.setattr(conftest, "_AMBIENT_CUDA_VISIBLE_DEVICES", None)

    def fail_probe(*args, **kwargs):
        raise error

    monkeypatch.setattr(conftest.subprocess, "run", fail_probe)
    assert not conftest.gpu_available_ambiently()


def test_unmasked_probe_result_is_still_cached(monkeypatch):
    monkeypatch.setattr(conftest, "_AMBIENT_CUDA_VISIBLE_DEVICES", None)
    calls = []

    def fake_probe(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(conftest.subprocess, "run", fake_probe)
    assert conftest.gpu_available_ambiently()
    assert conftest.gpu_available_ambiently()
    assert len(calls) == 1


def test_process_mask_still_short_circuits_in_process_gpu_check(monkeypatch):
    monkeypatch.setattr(conftest, "_AMBIENT_CUDA_VISIBLE_DEVICES", None)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    calls = []

    def fake_probe(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(conftest.subprocess, "run", fake_probe)
    assert not conftest.gpu_is_available()
    assert not calls
