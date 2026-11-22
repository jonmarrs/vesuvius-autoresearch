#!/usr/bin/env python3
"""Probe scratch gated_unet FP16 forward/backward memory on a CUDA device.

This is a search over tested sizes, not a full-training capacity estimate.
There is no optimizer, data loader, checkpoint load or prize-eligibility gate.
Use an idle device; allocator peaks cover this process's allocated tensors.
"""

import argparse
import gc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))

BATCH_SIZES = (8, 16, 32, 64, 128)
PATCH_SIZES = (64, 96, 128, 192, 256, 384)


def _runtime():
    import torch

    return torch


def _cuda_device(runtime, device):
    target = runtime.device(device)
    if target.type != "cuda":
        raise ValueError("device must be cuda or cuda:N")
    if not runtime.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no memory measurement was run")
    return target


def _run_trial(runtime, device, patch_size, batch_size, num_layers, base_feat):
    import vesuvius_model

    if Path(vesuvius_model.__file__).resolve() != ROOT / "vesuvius_model.py":
        raise RuntimeError("probe model came from another checkout")
    config = vesuvius_model.VesuviusConfig(
        patch_size=patch_size,
        batch_size=batch_size,
        num_layers=num_layers,
        base_feat=base_feat,
        in_channels=1,
    )
    model = vesuvius_model.InkDetectorOptimized(config).to(device).train()
    inputs = runtime.randn(
        batch_size, 1, num_layers, patch_size, patch_size, device=device
    )
    with runtime.amp.autocast("cuda"):
        outputs = model(inputs, return_fiber=True, return_qc=True)
        loss = sum(output.float().mean() for output in outputs)
    if not runtime.isfinite(loss).item():
        raise RuntimeError("probe produced a nonfinite loss")
    loss.backward()


def check_memory(patch_size, batch_size, num_layers=16, base_feat=64, *, device="cuda"):
    """Return a measured pass/OOM result; unavailable CUDA and other failures raise."""
    for name, value in (
        ("patch_size", patch_size),
        ("batch_size", batch_size),
        ("num_layers", num_layers),
        ("base_feat", base_feat),
    ):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    runtime = _runtime()
    target = _cuda_device(runtime, device)
    print(
        f"Testing scratch gated_unet: patch_size={patch_size}, batch_size={batch_size}, num_layers={num_layers}, base_feat={base_feat}, device={target}"
    )
    # Context matters: empty_cache() otherwise acts on the caller's current GPU.
    with runtime.cuda.device(target):
        gc.collect()
        runtime.cuda.empty_cache()
        runtime.cuda.reset_peak_memory_stats(target)
        try:
            try:
                # A separate frame lets failed trial tensors go out of scope
                # when the OOM handler ends, before cleanup and another trial.
                _run_trial(
                    runtime, target, patch_size, batch_size, num_layers, base_feat
                )
                runtime.cuda.synchronize(target)
                peak = runtime.cuda.max_memory_allocated(target) / 1024**2
            except runtime.cuda.OutOfMemoryError:
                passed = False
            else:
                passed = True
        finally:
            gc.collect()
            runtime.cuda.empty_cache()
    if passed:
        print(f"  PASS: peak allocated {peak:.2f} MiB")
    else:
        print("  OOM: this tested configuration did not fit")
    return passed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device", default="cuda", help="CUDA device, for example cuda:0"
    )
    args = parser.parse_args(argv)
    try:
        _cuda_device(_runtime(), args.device)
        print(
            "Scratch gated_unet FP16 forward/backward probe; optimizer and data pipeline excluded."
        )
        print(
            "These sizes do not determine prize eligibility or production-training capacity."
        )
        best_batch = best_patch = None
        for batch in BATCH_SIZES:
            if not check_memory(64, batch, device=args.device):
                break
            best_batch = batch
        for patch in PATCH_SIZES:
            if not check_memory(patch, 4, device=args.device):
                break
            best_patch = patch
    except (ImportError, RuntimeError, ValueError) as exc:
        print(f"Memory probe failed: {exc}", file=sys.stderr)
        return 1
    if best_batch is None or best_patch is None:
        print(
            "Memory probe incomplete: at least one search had no passing trial.",
            file=sys.stderr,
        )
        return 1
    print(f"Largest tested passing batch at patch_size=64: {best_batch}")
    print(f"Largest tested passing patch at batch_size=4: {best_patch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
