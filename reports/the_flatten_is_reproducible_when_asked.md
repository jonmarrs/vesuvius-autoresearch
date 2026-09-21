# The flatten is bit-reproducible when asked: reduction order is the whole cause

**2026-09-21.** Registered in `docs/preregistration/2026-09-21_deterministic_flatten.md`, decided by
`scripts/analyse_deterministic_flatten.py`, both committed before either surface existed.
`reports/deterministic_flatten_verdict.json`.

## The result

Two flattens of one mesh set (`4576eacfa2d40cdd`, the same input that landed 7.15 vx apart under
stock settings), both under `FLATTEN_DETERMINISTIC=1`:

| | value |
|---|---:|
| mean nearest-neighbour distance | **0.0000 vx** |
| `x.tif` / `y.tif` / `z.tif` md5 | **byte-identical**, all three |
| stock-mode pair, same input | 7.151 vx |
| escaped-op warnings | 0 |
| stage0 throughput | 16.4 it/s vs ~155 stock — **9.5× slower** |
| wall time per flatten (incl. export) | 637 s, 679 s vs ~4 min stock |

Not close. Not within tolerance. **The same bytes.** The loss trajectories matched at every sampled
step (2.4901, 2.0966, 1.8213, 1.4713, 1.5804; stage1 1.5460) where the stock pair diverged at the
third decimal (1.5857 vs 1.5839).

## Band: WHOLE CAUSE. Prediction: MISS

**I predicted the middle band, 0.01–1 vx**, on the reasoning that the fused Triton Adam kernel sits
outside `torch.use_deterministic_algorithms`' scope and does atomic accumulation every step, so a
residual would survive. **It did not.** Either the Triton kernel is deterministic as written, or
its drift is exactly zero rather than merely small. The miss is in the *good* direction, and it is
recorded as a miss.

**What is established:** `reports/the_flatten_has_no_seed_to_set.md` attributed the flatten's
non-determinism to CUDA reduction order and said it was *necessary but not shown sufficient*. It is
now shown sufficient: request deterministic algorithms, and two runs produce identical files.
There is no other source.

## What it means

**The 3.04% render floor is optional.** Every study here that compares different *fits* — the six
manipulations, every seed replicate, villa's own loop — has been paying ~3% of flatten noise that
no fit seed touches. That noise can be turned off with an environment variable and a 10× slower
flatten. On this box that is ~11 minutes per arm instead of ~4, against renders that take ~2 hours.
**The cost is negligible relative to the pipeline it sits in.**

**Reproducible is not the same as correct.** `det_a` sits 6.6–7.3 vx from *both* stock surfaces —
as far as they sit from each other. Deterministic mode does not find a canonical answer; it fixes
one reduction order and lands on an arbitrary member of the same distribution the stock runs
sample from. Two studies on deterministic flattens are comparable *to each other*; neither is more
right than a stock run.

**For villa:** `autoresearch.md` already names "CUDA non-determinism" alongside the seed (line
52). What it does not say is *where* — the flatten, not the fit — nor *how much* — 3% on the
objective — nor that it is removable with `torch.use_deterministic_algorithms(True)` plus
`CUBLAS_WORKSPACE_CONFIG=:4096:8` at a 10× flatten cost. Villa's new
`test_flatten_state_handoff.py` tests export determinism; this is optimisation determinism, and it
is the one that moves the ink count.

## How to use it

`repro/spiral_render/determinism_shim/sitecustomize.py`: put its directory on `PYTHONPATH` and set
`FLATTEN_DETERMINISTIC=1`. Inert otherwise. Combined with `RENDER_REUSE_FLATTEN=1`, a study can
now flatten *once, reproducibly*, and branch — or flatten *per arm, reproducibly*, and compare fits
with the flatten's contribution to noise at exactly zero.

## Limits

One mesh set, one machine, one GPU (RTX 4090), one torch (2.11.0+cu128), two runs. Bit-identity
across two runs on one machine does not establish bit-identity across machines or driver versions —
deterministic CUDA algorithms are deterministic *per configuration*. The 9.5× slowdown is this
flatten's; a different config or a much larger mesh could scale differently. And the escaped-op
count of zero is a property of torch 2.11's coverage; an older torch may warn where this one did
not.
