#!/usr/bin/env python3
"""
Vesuvius Autoresearch: 24GB VRAM Saturation Test (Sprint 004)
Automates the search for the maximum patch_size and batch_size without hitting OOM.

Constraints:
  Any evolved config with `patch_size > 64` must be tagged as non-submittable
  per the milestone prize rules (<= 0.5x0.5 mm window).

Usage:
  uv run scripts/vram_saturation_test.py
"""

import gc

import torch

from vesuvius_model import InkDetectorOptimized, VesuviusConfig


def check_memory(patch_size, batch_size, num_layers=16, base_feat=64):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        print("CUDA not available. Simulation only.")
        return True

    print(
        f"Testing: patch_size={patch_size}, batch_size={batch_size}, num_layers={num_layers}"
    )

    try:
        # Clear cache before test
        torch.cuda.empty_cache()
        gc.collect()

        config = VesuviusConfig(
            patch_size=patch_size,
            num_layers=num_layers,
            base_feat=base_feat,
            in_channels=1,
        )
        model = InkDetectorOptimized(config).to(device)
        model.train()  # Set to train to allocate gradient memory

        # Create dummy data
        x = torch.randn(
            batch_size, 1, num_layers, patch_size, patch_size, device=device
        )

        # Forward pass
        with torch.amp.autocast("cuda"):
            out_ink, out_fiber, out_qc = model(x, return_fiber=True, return_qc=True)

        # Backward pass simulation
        loss = out_ink.sum() + out_fiber.sum() + out_qc.sum()
        loss.backward()

        # Check peak memory
        peak_mb = torch.cuda.max_memory_allocated(device) / (1024**2)
        print(f"  Success! Peak VRAM: {peak_mb:.2f} MB")

        # Cleanup
        del model, x, out_ink, out_fiber, out_qc, loss
        torch.cuda.empty_cache()
        return True

    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"  OOM! Failed at patch_size={patch_size}, batch_size={batch_size}")
            torch.cuda.empty_cache()
            return False
        else:
            raise e


def main():
    print("--- Starting 24GB VRAM Saturation Search ---")
    print(
        "Note: The competition strictly limits window sizes to 64x64 for submissions."
    )
    print("Configs > 64 will be flagged as non-submittable.")

    # We test increasing batch sizes for patch_size=64
    print("\nPhase 1: Max Batch Size for patch_size=64 (Submittable)")
    best_batch_size_64 = None
    for batch_size in [8, 16, 32, 64, 128]:
        if check_memory(patch_size=64, batch_size=batch_size):
            best_batch_size_64 = batch_size
        else:
            break
    print(f"=> Best submittable config: patch_size=64, batch_size={best_batch_size_64}")

    # We test increasing patch sizes for batch_size=4 (Research only)
    print("\nPhase 2: Max Patch Size for batch_size=4 (Research Only)")
    best_patch_size = None
    for patch_size in [64, 96, 128, 192, 256, 384]:
        if check_memory(patch_size=patch_size, batch_size=4):
            best_patch_size = patch_size
        else:
            break

    print(f"=> Best research config: patch_size={best_patch_size}, batch_size=4")

    print("\nVRAM Saturation Search Complete.")


if __name__ == "__main__":
    main()
