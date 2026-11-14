"""A memory diagnostic must measure CUDA trials or refuse to report a fit."""

import contextlib
import os
import subprocess
import sys
import weakref
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from scripts import vram_saturation_test as probe

ROOT = Path(__file__).resolve().parents[1]


def test_cpu_cannot_pass_a_cuda_trial(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="CUDA"):
        probe.check_memory(64, 4)


def test_cpu_cli_never_publishes_successful_configurations(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.vram_saturation_test import main; raise SystemExit(main())",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT), "CUDA_VISIBLE_DEVICES": ""},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "CUDA" in result.stderr
    assert "largest" not in result.stdout.lower()
    assert "best" not in result.stdout.lower()
    assert "complete" not in result.stdout.lower()


def test_help_works_without_scientific_imports(tmp_path):
    for name in ("torch", "numpy", "vesuvius_model"):
        (tmp_path / f"{name}.py").write_text(
            "raise AssertionError('scientific import attempted')\n"
        )
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "scripts/vram_saturation_test.py"), "--help"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "forward/backward" in result.stdout


@pytest.fixture
def cuda(monkeypatch):
    class Allocator:
        OutOfMemoryError = torch.cuda.OutOfMemoryError

        def __init__(self):
            self.current = "cuda:0"
            self.peak = 0
            self.disposable = []
            self.cleanup_states = []

        def is_available(self):
            return True

        @contextlib.contextmanager
        def device(self, target):
            previous = self.current
            self.current = str(target)
            try:
                yield
            finally:
                self.current = previous

        def empty_cache(self):
            self.cleanup_states.append(
                (self.current, all(ref() is None for ref in self.disposable))
            )

        def reset_peak_memory_stats(self, target):
            assert str(target) == self.current
            self.peak = 0

        def allocate(self, mib):
            self.peak = max(self.peak, mib * 1024**2)

        def synchronize(self, target):
            assert str(target) == self.current

        def max_memory_allocated(self, target):
            assert str(target) == self.current
            return self.peak

    allocator = Allocator()
    runtime = SimpleNamespace(cuda=allocator, device=torch.device)
    monkeypatch.setattr(probe, "_runtime", lambda: runtime)
    return allocator


def test_each_trial_reports_its_own_peak_and_uses_the_requested_device(
    cuda, monkeypatch, capsys
):
    def trial(runtime, device, patch, batch, layers, width):
        assert str(device) == cuda.current == "cuda:1"
        cuda.allocate(100 * batch)

    monkeypatch.setattr(probe, "_run_trial", trial)
    assert probe.check_memory(64, 8, device="cuda:1") is True
    assert probe.check_memory(64, 4, device="cuda:1") is True
    output = capsys.readouterr().out
    assert "peak allocated 800.00 MiB" in output
    assert "peak allocated 400.00 MiB" in output
    assert all(device == "cuda:1" for device, _ in cuda.cleanup_states)
    assert cuda.current == "cuda:0"


def test_oom_releases_trial_objects_before_final_cleanup(cuda, monkeypatch, capsys):
    class TensorOwner:
        pass

    def trial(*args):
        owner = TensorOwner()
        cuda.disposable.append(weakref.ref(owner))
        raise cuda.OutOfMemoryError("synthetic allocator exhaustion")

    monkeypatch.setattr(probe, "_run_trial", trial)
    assert probe.check_memory(64, 4) is False
    assert cuda.disposable and all(ref() is None for ref in cuda.disposable)
    assert cuda.cleanup_states[-1] == ("cuda", True)
    assert "PASS:" not in capsys.readouterr().out


def test_unrelated_runtime_failures_are_not_classified_as_a_fit_or_oom(
    cuda, monkeypatch, capsys
):
    def broken(*args):
        raise RuntimeError("kernel contract failure")

    monkeypatch.setattr(probe, "_run_trial", broken)
    with pytest.raises(RuntimeError, match="kernel contract failure"):
        probe.check_memory(64, 4)
    output = capsys.readouterr().out
    assert "PASS:" not in output and "OOM:" not in output


@pytest.mark.parametrize(
    "field,value",
    [("patch_size", True), ("batch_size", 0), ("num_layers", -1), ("base_feat", 1.5)],
)
def test_invalid_dimensions_fail_before_accessing_a_device(monkeypatch, field, value):
    monkeypatch.setattr(
        probe, "_runtime", lambda: pytest.fail("invalid dimensions reached the runtime")
    )
    kwargs = {
        "patch_size": 64,
        "batch_size": 4,
        "num_layers": 16,
        "base_feat": 64,
        field: value,
    }
    with pytest.raises(ValueError, match=field):
        probe.check_memory(**kwargs)


def test_search_reports_only_tested_passes(cuda, monkeypatch, capsys):
    monkeypatch.setattr(
        probe,
        "check_memory",
        lambda patch_size, batch_size, **kwargs: batch_size <= 16 and patch_size <= 96,
    )
    assert probe.main([]) == 0
    out = capsys.readouterr().out
    assert "Largest tested passing batch at patch_size=64: 16" in out
    assert "Largest tested passing patch at batch_size=4: 96" in out
    assert "submittable config" not in out


def test_search_with_no_passing_trial_returns_failure(cuda, monkeypatch, capsys):
    monkeypatch.setattr(probe, "check_memory", lambda *args, **kwargs: False)
    assert probe.main([]) == 1
    captured = capsys.readouterr()
    assert "no passing trial" in captured.err
    assert "Largest" not in captured.out


def test_real_small_cpu_model_backpropagates_the_probe_loss(monkeypatch):
    import vesuvius_model

    measured = []

    class Observed(vesuvius_model.InkDetectorOptimized):
        def __init__(self, config):
            super().__init__(config)
            self.final_ink.weight.register_hook(
                lambda grad: measured.append(
                    bool(torch.isfinite(grad).all()) and bool(grad.abs().sum() > 0)
                )
            )

    monkeypatch.setattr(vesuvius_model, "InkDetectorOptimized", Observed)
    runtime = SimpleNamespace(
        randn=torch.randn,
        isfinite=torch.isfinite,
        amp=SimpleNamespace(autocast=lambda *_: contextlib.nullcontext()),
    )
    torch.manual_seed(0)
    probe._run_trial(runtime, torch.device("cpu"), 8, 1, 4, 8)
    assert measured == [True]


def test_cached_model_from_another_checkout_is_refused(monkeypatch, tmp_path):
    fake = SimpleNamespace(__file__=str(tmp_path / "vesuvius_model.py"))
    monkeypatch.setitem(sys.modules, "vesuvius_model", fake)
    with pytest.raises(RuntimeError, match="another checkout"):
        probe._run_trial(object(), "cuda", 64, 4, 16, 64)
