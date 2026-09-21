# The flatten has no seed to set: its non-determinism is CUDA reduction order

**2026-09-21.** Follow-up to `reports/the_render_is_the_noise_floor.md`, which measured the lasagna
flatten landing 7.15 vx apart on identical input and left open whether it is fixable. No new compute;
this is a reading of the flatten code at the pinned tree.

## What the code does not contain

A grep of `fit.py`, `optimizer.py` and `model.py` for every RNG idiom — `manual_seed`, `randn`,
`rand(`, `randint`, `shuffle`, `permutation`, `np.random`, `torch.rand` — returns **nothing**. Every
"seed" in the tree is a *geometric* seed: `cylinder_seed`, `seed_xyz`, `snaps_seed` — spatial
initialisation points, not RNG state. The flatten config has no seed key.

**So there is no seed to set.** The non-determinism is not explicit randomness, and `torch.manual_seed`
would change nothing.

## What it does contain

| source of run-to-run variation | present |
|---|---|
| scatter / atomic-add call sites (`index_add_`, `scatter_add`, `index_put_`, …) | **174** |
| `grid_sample` (CUDA backward uses atomic adds) | throughout `model.py` |
| a fused Triton Adam kernel (`fused_flatten_adam_clamp=1`) | yes |
| any request for determinism (`use_deterministic_algorithms`, `cudnn.deterministic`, `CUBLAS_WORKSPACE_CONFIG`) | **none** |

This is the textbook signature of **CUDA reduction-order non-determinism**: floating-point sums
accumulated by atomic operations complete in a different order each run, the results differ in the
last bits, and an optimiser run for 5,500 steps amplifies last-bit differences into a different
converged surface. The two ZERO renders differing by 7 vx is not a large perturbation — it is a tiny
one integrated over a long trajectory.

## Why this is the important kind

It means the finding is **not** a bug report. There is no line to fix and no flag to flip. It is a
property of running an iterative optimiser on non-deterministic GPU kernels, and it is exactly the
class of non-determinism most projects never measure because "we set the seed" feels sufficient.

It also means the fix has a known cost, not an unknown one. PyTorch's
`torch.use_deterministic_algorithms(True)` forces deterministic scatter paths and errors on the
operations that have none; Triton kernels are outside its scope entirely. Making this flatten
reproducible would mean **replacing atomics with sorted segment-reductions and abandoning the fused
kernel** — a performance cost, not a correctness fix.

## What is and is not established

**Established:** no RNG exists on the path; atomics and a custom kernel do; determinism is never
requested. That is sufficient for the non-determinism to arise and necessary for it to be
non-seedable.

**Not established, and testable:** that reduction order is the *whole* cause. The test is cheap in
design and expensive in runtime: run the flatten twice under `CUBLAS_WORKSPACE_CONFIG=:4096:8` with
`torch.use_deterministic_algorithms(True, warn_only=True)`, and see whether the surfaces converge or
the run errors on an unsupported op. Either outcome is informative. ~2h per flatten on this box, so
~4h; not run today.

## TESTED 2026-09-21: sufficient, and bit-exact

The experiment above ran. Two flattens under `torch.use_deterministic_algorithms(True)` produced
**byte-identical `x/y/z.tif`** — mean NN distance 0.0000 vx, zero escaped-op warnings, at a 9.5×
throughput cost. Reduction order is the **whole** cause; there is no other source.
`reports/the_flatten_is_reproducible_when_asked.md`. The "not established" paragraph above is now
established, and the prediction that a Triton residual would survive was a miss.

## What it changes downstream

**For villa's loop:** "run two seeds" — the robustness check `autoresearch.md` prescribes — varies
the *fit* seed. The flatten downstream of both fits then adds ~3% of noise that no fit seed touches.
The two-seed check is measuring fit variance plus flatten variance and attributing all of it to the
fit.

**For this project:** `RENDER_REUSE_FLATTEN=1` remains the only available lever, and it only helps
studies that branch from one surface. Fit comparisons cannot use it and there is nothing cheaper
than the deterministic-algorithms experiment above.
