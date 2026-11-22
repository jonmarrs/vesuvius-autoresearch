# Scratch-model CUDA memory probe

[vram_saturation_test.py](../scripts/vram_saturation_test.py) now refuses a
CPU-only run. The old script returned success for every size when CUDA was
unavailable, then printed batch size 128 and patch size 384 as successful
configurations. Those outputs were not memory measurements.

On an idle CUDA device in the research checkout:

```sh
uv run --no-sync python scripts/vram_saturation_test.py --device cuda:0
```

`--help` needs no scientific imports. Execution requires PyTorch and CUDA;
unavailable CUDA or another runtime failure exits **1**. The command creates
no artifact and does not update configurations or checkpoints.

## What a trial measures

Each trial builds this checkout's scratch `gated_unet` (`InkDetectorOptimized`),
with random input, one input channel, 16 layers, base width 64 and the model's
other defaults. It executes an FP16 autocast forward for ink/fiber/QC, forms a
float32 mean loss and backpropagates. A nonfinite loss is a failure. The code
does not load a checkpoint or run the current production `resenc_unet` recipe.

Trials use the requested device context, clear disposable objects/cache and
reset the allocator's peak before construction. A large earlier trial therefore
does not become a later smaller trial's peak. Typed CUDA OOMs are reported as
failed fits; other errors propagate to a failing command. Trial-local tensors
are released before OOM cleanup and the next trial.

The printed peak is `torch.cuda.max_memory_allocated` in MiB: the high-water
mark of this process's allocated tensors on that device. Unrelated tensors
already resident in the process are included. Reserved allocator memory,
driver/library allocations and other processes' memory are not represented by
that number. A passing trial is not a total VRAM-use estimate.

## Search and limits

The batch search tests 8, 16, 32, 64 and 128 at patch size 64. The patch search
tests 64, 96, 128, 192, 256 and 384 at batch size 4. Each stops at its first OOM.
Only sizes actually tested and passed can be printed as the largest tested
passing sizes. If either search has no passing trial, the command exits **1**
without printing winners.

There is no optimizer step/state, data loader, ridge preprocessing, validation,
ensemble residency or checkpoint-publication workload. These results cannot set
the production training batch size, replace representative RTX 4090 profiling,
or establish prize eligibility. The old global 64-pixel prize-cap assertion was
removed; consult the [current rules and research strategy](RESEARCH_STRATEGY.md).

This audit tested CPU refusal, a small real CPU model's forward/backward, and
controlled allocator/OOM lifecycles. It did **not** execute a CUDA trial or
measure a usable GPU configuration. GPU profiling remains an owner-review item.
