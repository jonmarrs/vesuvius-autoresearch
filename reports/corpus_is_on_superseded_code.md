# Our 24-fit corpus is on superseded code that fits measurably worse

**2026-09-07.** Discovered while designing the first optimisation attempt, before any of it ran.

## The drift

All 24 scored fits are pinned to villa-spiral `6847063f` (2026-08-26). Since then
`spiral-fitting` has moved **35 files, +3,385 / -332, across 10 commits**.

That is not a refactor. At a **matched 200 steps, matched seed and matched config**:

| tree | `satisfied_area` at 200 steps |
|---|---:|
| pinned `6847063f` | 0.13466 |
| current `d8c5f488a` | **0.16149** |

**+20% relative.** Current code fits better, so our baselines are a *handicapped* reference and any
optimisation measured against them would have flattered itself.

## The lever we were going to pull no longer exists

The one manipulation we ever found that moved ink significantly was
`model_gap_expander_num_windings` 130 -> 133, costing **10.35% of the ink** (p=0.0018, n=12). The
plan was to reverse it.

PR #1625 split that knob. Upstream now says it is a *"Legacy/fallback physical winding-count estimate
used by exporters; it does not allocate the gap lattice"* — allocation moved to
`model_gap_expander_capacity_windings`. **The knob we measured no longer does the thing we measured.**

## A slowdown that was our own error, recorded so it is not repeated

First attempt at running current code gave **0.0 it/s, ETA 17h40m for 200 steps**, GPU idle at 0%,
against 5.3 it/s on the pinned tree. That looked like a serious upstream regression and was nearly
written up as one.

It was not. Current *source* was run against the pinned tree's *venv*, so `vc_spiral` resolved to
`villa-spiral/spiral-fitting/vc_spiral/__init__.py` with `.so` files compiled from old source — new
Python against old native extensions. Built properly (fresh venv, `uv pip install -e .`,
`CC`/`CXX` set explicitly because the build environment's `CXX` pointed at a missing compiler),
current villa runs at **4.5 it/s**.

**Before attributing a performance claim to upstream, verify the native extensions resolve to the
tree you think you are running.**

## What was done about it

`villa-spiral-current/` holds current `spiral-fitting`, `lasagna` and `vesuvius`, with its own built
venv. **The pinned tree is untouched** and `tests/test_villa_spiral_refs_pinned.py` still passes, so
the existing corpus stays reproducible.

Three baselines on current code (`curbase_s1..s3`, seeds 1-3, 30,000 steps, fit and render/score)
were launched 2026-09-07 18:18. `setup_workdir.sh` takes `VILLA` from the environment, so the render
comes from the submodule at `d8c5f488a` while villa-spiral stays pinned. Both scoring patches
(`serial_folds`, `keep_probabilities`) apply to current `get_ink_metrics.py`.

## What this costs

Every cross-corpus comparison is now two-tier: the 24 old fits are internally comparable and the new
arms are internally comparable, and **the two groups are not comparable with each other**. Published
results stand as measured; they are simply measurements of older code.
