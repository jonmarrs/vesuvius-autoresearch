"""Observed process/allocator scope and opt-in prediction metadata."""

import json
import sys
from types import SimpleNamespace

import numpy as np
import psutil
import pytest
import torch
from test_volume_inference_contracts import setup_prediction

from scripts.inference import ensemble_predict as ensemble, predict as single
from vesuvius_autoresearch.core import regional_memory as memory


@pytest.mark.parametrize(
    "platform,expected", [("linux", 7168), ("darwin", 7), ("win32", None)]
)
def test_lifetime_peak_rss_units_are_platform_specific(monkeypatch, platform, expected):
    monkeypatch.setattr(memory, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setitem(
        sys.modules,
        "resource",
        SimpleNamespace(
            RUSAGE_SELF=0, getrusage=lambda _: SimpleNamespace(ru_maxrss=7)
        ),
    )
    assert memory._process_lifetime_peak_rss() == expected


def test_cpu_profile_does_not_probe_cuda_or_relabel_lifetime_peak(monkeypatch):
    def no_cuda(*args, **kwargs):
        pytest.fail("CPU profiling touched CUDA")

    for name in (
        "is_available",
        "current_device",
        "get_device_properties",
        "synchronize",
        "reset_peak_memory_stats",
        "memory_allocated",
    ):
        monkeypatch.setattr(torch.cuda, name, no_cuda)
    monkeypatch.setattr(
        psutil,
        "Process",
        lambda: SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=100)),
    )
    monkeypatch.setattr(memory, "_process_lifetime_peak_rss", lambda: 900)
    profiler = memory.RegionalMemoryProfile("cpu")
    initial = profiler.report()
    profiler.sample("models_loaded")
    record = profiler.report()
    assert len(initial["observations"]) == 1
    assert len(record["observations"]) == 2
    assert record["cpu_peak_scope"].startswith("process lifetime")
    assert not record["cuda_peak_counters_reset"]
    assert record["cuda_device"] is None
    assert not record["capacity_guaranteed"]
    for observation in record["observations"]:
        assert observation["process_rss_bytes"] == 100
        assert observation["process_lifetime_peak_rss_bytes"] == 900
        assert observation["cuda"] is None
    json.dumps(record, allow_nan=False)


def test_unavailable_lifetime_peak_is_null_not_a_sampled_peak(monkeypatch):
    monkeypatch.setattr(memory, "_process_lifetime_peak_rss", lambda: None)
    record = memory.RegionalMemoryProfile("cpu").report()
    assert record["observations"][0]["process_rss_bytes"] > 0
    assert record["observations"][0]["process_lifetime_peak_rss_bytes"] is None


def test_cuda_allocator_peaks_use_one_reset_and_the_selected_device(monkeypatch):
    events = []
    monkeypatch.setattr(
        torch.cuda,
        "get_device_properties",
        lambda _: SimpleNamespace(name="mock-device", total_memory=24 * 1024**3),
    )
    live = {
        "allocated": 100,
        "reserved": 200,
        "peak_allocated": 100,
        "peak_reserved": 200,
    }
    for name in ("synchronize", "reset_peak_memory_stats"):
        monkeypatch.setattr(
            torch.cuda,
            name,
            lambda device, name=name: events.append((name, str(device))),
        )
    for name, key in [
        ("memory_allocated", "allocated"),
        ("memory_reserved", "reserved"),
        ("max_memory_allocated", "peak_allocated"),
        ("max_memory_reserved", "peak_reserved"),
    ]:

        def metric(device, name=name, key=key):
            events.append((name, str(device)))
            return live[key]

        monkeypatch.setattr(torch.cuda, name, metric)
    profiler = memory.RegionalMemoryProfile("cuda:1")
    live.update(allocated=40, reserved=80, peak_allocated=150, peak_reserved=300)
    profiler.sample("inference_complete")
    record = profiler.report()
    assert events[:3] == [
        ("synchronize", "cuda:1"),
        ("reset_peak_memory_stats", "cuda:1"),
        ("synchronize", "cuda:1"),
    ]
    assert sum(name == "reset_peak_memory_stats" for name, _ in events) == 1
    assert all(device == "cuda:1" for _, device in events)
    assert record["observations"][-1]["cuda"] == {
        "allocated_bytes": 40,
        "reserved_bytes": 80,
        "peak_allocated_bytes": 150,
        "peak_reserved_bytes": 300,
    }
    assert record["cuda_device"]["name"] == "mock-device"
    assert record["cuda_device"]["total_memory_bytes"] == 24 * 1024**3
    assert not record["total_device_peak_measured"]
    assert record["cuda_peak_counters_reset"]
    json.dumps(record, allow_nan=False)


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_profile_is_opt_in_and_preserves_predictions(tmp_path, monkeypatch, mode):
    configs = (
        [{"patch_size": 8, "num_layers": layers, "base_feat": 4} for layers in (2, 3)]
        if mode == "ensemble"
        else None
    )
    run, argv, models, _, _ = setup_prediction(
        tmp_path, monkeypatch, mode, configs=configs
    )
    argv.extend(["--artifact_stem", "region"])
    real = memory.RegionalMemoryProfile
    module = single if mode == "single" else ensemble
    monkeypatch.setattr(
        module,
        "RegionalMemoryProfile",
        lambda *a: pytest.fail("profiling enabled by default"),
    )
    run()
    sidecar = tmp_path / "out/region_meta.json"
    assert "memory_profile" not in json.loads(sidecar.read_text())
    arrays = {
        name: np.load(tmp_path / f"out/region_{name}.npy") for name in ("ink", "fiber")
    }
    monkeypatch.setattr(module, "RegionalMemoryProfile", real)
    argv.append("--profile_memory")
    models.clear()
    run()
    record = json.loads(sidecar.read_text())["memory_profile"]
    assert record["device"] == "cpu" and record["units"] == "bytes"
    assert [o["phase"] for o in record["observations"]] == [
        "before_models",
        "models_loaded",
        "inference_complete",
        "metadata_ready",
    ]
    assert len(models) == (2 if mode == "ensemble" else 1)
    for observation in record["observations"]:
        assert observation["process_rss_bytes"] > 0
        assert observation["elapsed_seconds"] >= 0
        assert observation["cuda"] is None
    for name, before in arrays.items():
        np.testing.assert_array_equal(
            np.load(tmp_path / f"out/region_{name}.npy"), before
        )


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_profile_does_not_bypass_accumulator_preflight(tmp_path, monkeypatch, mode):
    run, argv, models, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv.extend(["--profile_memory", "--max_accumulator_bytes", "1"])
    monkeypatch.setattr(
        single if mode == "single" else ensemble,
        "RegionalMemoryProfile",
        lambda *a: pytest.fail("over-budget run initialized profiler"),
    )
    with pytest.raises(ValueError, match="max_accumulator_bytes"):
        run()
    assert not models and not (tmp_path / "out").exists()


def test_profile_includes_successful_optional_exports_and_coherence(
    tmp_path, monkeypatch
):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    argv.remove("--skip_active_learning")
    argv.extend(
        ["--profile_memory", "--compute_coherence", "--artifact_stem", "region"]
    )
    run()
    record = json.loads((tmp_path / "out/region_meta.json").read_text())
    assert record["uncertainty_export"]["status"] == "EXPORTED"
    assert record["fiber_coherence"] == 0
    phases = record["memory_profile"]["observations"]
    assert [o["phase"] for o in phases][-2:] == ["metadata_ready", "metadata_ready"]
    assert (
        len(phases) == 5
        and phases[-1]["elapsed_seconds"] >= phases[-2]["elapsed_seconds"]
    )


@pytest.mark.parametrize("mode", ["single", "ensemble"])
def test_failed_measurement_does_not_publish_success_metadata(
    tmp_path, monkeypatch, mode
):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, mode)
    argv.extend(["--profile_memory", "--artifact_stem", "region"])
    directory = tmp_path / "out"
    directory.mkdir()
    sidecar = directory / "region_meta.json"
    sidecar.write_text('{"old": true}')
    sample = memory.RegionalMemoryProfile.sample

    def fail_at_metadata(self, phase):
        if phase == "metadata_ready":
            raise OSError("measurement unavailable")
        sample(self, phase)

    monkeypatch.setattr(memory.RegionalMemoryProfile, "sample", fail_at_metadata)
    with pytest.raises(OSError, match="measurement unavailable"):
        run()
    assert (directory / "region_ink.npy").exists()
    assert not sidecar.exists()
