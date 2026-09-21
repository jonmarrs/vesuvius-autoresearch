# Pre-registration: does requesting deterministic CUDA algorithms make the flatten reproducible?

**Written 2026-09-21, before either arm is launched.**

## The question

`reports/the_flatten_has_no_seed_to_set.md` established the lasagna flatten has no RNG on its path
and attributes its 7.15 vx run-to-run variation to CUDA reduction order — 174 scatter/atomic sites,
`grid_sample` backward, a fused Triton kernel, no determinism requested. It named this test and did
not run it. **This runs it.**

## The manipulation

`repro/spiral_render/determinism_shim/sitecustomize.py`, activated by `FLATTEN_DETERMINISTIC=1` on
`PYTHONPATH`. It calls `torch.use_deterministic_algorithms(True, warn_only=True)`, sets
`cudnn.deterministic`, disables `cudnn.benchmark`, and sets `CUBLAS_WORKSPACE_CONFIG=:4096:8`.
**Verified before registering:** inert without the flag; active with it; `index_add_` runs with no
warning under it on torch 2.11.

`warn_only=True` is deliberate: an op with no deterministic path warns rather than raises, so the run
completes and the log records which ops escaped. That is more informative than a crash.

## Arms

Two flattens of `radial_study/rad0`'s meshes — the same input as `radial_work_rad0` and `rad0b`,
which landed 7.15 vx apart — both under the shim, on pinned `be09a8503`, nothing else changed.

| arm | shim | compared to |
|---|---|---|
| **DET-A** | on | DET-B |
| **DET-B** | on | DET-A |

Surfaces compared with `scripts/measure_flatten_divergence.py` (nearest-neighbour distance), the
same instrument that produced the 7.15 vx / 0.535 vx figures.

## Outcomes, fixed now

| DET-A vs DET-B, mean NN distance | reading |
|---|---|
| **< 0.01 vx** | **Reduction order is the whole cause.** The flatten is reproducible when asked, at whatever speed cost the log shows. The 3.04% floor becomes optional for every study, including fit comparisons. |
| 0.01 – 1 vx | Determinism mode removes most of it; a residual source exists — plausibly the Triton kernel, outside torch's determinism scope. Report the residual and the warnings. |
| **≥ 1 vx, no warnings** | Determinism mode did not act on the sources that matter. The mechanism attribution is **wrong or incomplete** — reported as such. |
| ≥ 1 vx, with warnings | The escaped ops named in the warnings are the residual source. Report which. |
| run errors | An op has no deterministic path even with `warn_only`. The error names it. |

**Prediction: the middle band, 0.01–1 vx.** `use_deterministic_algorithms` covers torch's own
scatter/index ops but the fused Triton Adam kernel is outside its reach, and it does atomic
accumulation on every step. I expect the surfaces to converge by an order of magnitude and not to
zero. Recorded so it can be a miss.

**Also recorded:** the wall time of a deterministic flatten versus the ~4m the stock one takes on this
box. Deterministic scatter paths are known to be slower; if the cost is large, that is part of the
answer to "is it fixable".

## Cost

Two flattens plus renders, ~2h each, strictly serial: **~4-5h**. No fits, no scoring — the surfaces
are compared directly, so `vc_render_tifxyz` need not run at all. The chain stops after the flatten.
