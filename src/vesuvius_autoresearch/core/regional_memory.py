"""Opt-in inference memory observations.

CPU high-water RSS belongs to the process lifetime. CUDA peaks belong to the
selected device's PyTorch allocator since this profiler reset its counters;
they include allocations already live at reset and exclude other allocators.
Callers own the process/device while profiling. Sampling synchronizes CUDA.
"""

from __future__ import annotations

import sys
import time


def _process_lifetime_peak_rss():
    # getrusage's RSS unit differs between the two supported implementations.
    # Do not guess units on other platforms or report a sampled RSS as a peak.
    if sys.platform not in {"linux", "darwin"}:
        return None
    import resource

    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value * 1024 if sys.platform == "linux" else value


class RegionalMemoryProfile:
    """Collect a few phase observations without retaining tensors or models."""

    def __init__(self, device):
        import psutil
        import torch

        self._torch = torch
        self.device = torch.device(device)
        self._process = psutil.Process()
        self._started = time.perf_counter()
        self._observations = []
        self._cuda_device = None
        if self.device.type == "cuda":
            if self.device.index is None:
                self.device = torch.device("cuda", torch.cuda.current_device())
            properties = torch.cuda.get_device_properties(self.device)
            self._cuda_device = {
                "name": properties.name,
                "total_memory_bytes": int(properties.total_memory),
                "torch_cuda_build_version": torch.version.cuda,
            }
            torch.cuda.synchronize(self.device)
            torch.cuda.reset_peak_memory_stats(self.device)
        self.sample("before_models")

    def sample(self, phase):
        if not isinstance(phase, str) or not phase:
            raise ValueError("memory profile phase must be a nonempty string")
        cuda = None
        if self.device.type == "cuda":
            backend = self._torch.cuda
            backend.synchronize(self.device)
            cuda = {
                "allocated_bytes": int(backend.memory_allocated(self.device)),
                "reserved_bytes": int(backend.memory_reserved(self.device)),
                "peak_allocated_bytes": int(backend.max_memory_allocated(self.device)),
                "peak_reserved_bytes": int(backend.max_memory_reserved(self.device)),
            }
        self._observations.append(
            {
                "phase": phase,
                "elapsed_seconds": time.perf_counter() - self._started,
                "process_rss_bytes": int(self._process.memory_info().rss),
                "process_lifetime_peak_rss_bytes": _process_lifetime_peak_rss(),
                "cuda": cuda,
            }
        )

    def report(self):
        return {
            "schema_version": 1,
            "device": str(self.device),
            "torch_version": str(self._torch.__version__),
            "cuda_device": self._cuda_device,
            "units": "bytes",
            "start": "after first checkpoint/configuration preflight, before first model construction",
            "end": "latest metadata_ready observation, before JSON serialization",
            "cpu_peak_scope": "process lifetime, including work before profiling",
            "cpu_rss_source": "psutil.Process.memory_info().rss",
            "cpu_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss, converted to bytes; null on unsupported platforms",
            "cuda_peak_scope": "selected device PyTorch allocator since reset; includes already-live allocations",
            "cuda_peak_counters_reset": self.device.type == "cuda",
            "cuda_synchronized_at_observations": self.device.type == "cuda",
            "total_device_peak_measured": False,
            "capacity_guaranteed": False,
            "observations": list(self._observations),
        }
