# Holding the flatten fixed collapses the noise floor 2000×, to 24 pixels

**2026-09-20.** The floor measurement registered in
`docs/preregistration/2026-09-20_radial_displacement_on_the_flat_surface.md`, decided by
`scripts/analyse_flat_displacement.py` — both committed while the arm was still rendering.
`reports/flat_displacement_floor.json`.

## The measurement

Two renders of **one byte-identical flat surface**. `flat_study_probe` reuses
`radial_work_rad0`'s own flatten — verified identical across `x/y/z.tif` and `meta.json` — via
`RENDER_REUSE_FLATTEN=1`, so `vc_render_tifxyz` and the scorer are the only things that run twice.

| | `total_fg_pixels` |
|---|---:|
| `radial_work_rad0` | 1,698,831 |
| `flat_study_probe` | 1,698,807 |
| **difference** | **24 pixels = 0.0014%** |

**Registered prediction was F < 1.5%. MET by a factor of ~1000.**

## The decomposition is now complete

| what varies between the two runs | spread on `total_fg_pixels` |
|---|---:|
| flatten + render + score | **3.04%** |
| **render + score, flatten held fixed** | **0.0014%** |
| scorer alone, one fixed strip | 0.0032% |

**The lasagna flatten accounts for essentially all of the render noise.** Holding it fixed drops the
floor by roughly **2000×** — to *below* the scorer's own measured variation, which is where a
deterministic sampler plus a near-deterministic scorer should land.

The canvas agrees: the probe rendered 82660×4260 with p95 98.0, identical to `rad0`, where the
independently re-flattened `rad0b` drifted to 82660×**4250** with p95 99.0.

## Why this matters beyond one study

**A comparison that re-flattens pays a 3.04% floor. The same comparison reusing one flatten pays
0.0014%.** That is the difference between needing many arms to see a 10% effect and resolving it with
one, at ~2h per render.

It also isolates where to look if the flatten is ever to be made reproducible: not the scorer, not
`vc_render_tifxyz`, but the forward flattener's own optimisation.

**Design consequence, stated as a rule:** any study here that varies its input and re-flattens is
measuring its manipulation *plus* a re-solve that moved the surface 7.15 vx in the outer region
(`reports/the_flatten_lands_on_different_surfaces.md`). Flatten once, branch downstream, and the
variance is gone by construction rather than averaged down.

## What it does not show

**It is one pair.** F is a point estimate with no interval, exactly like the 3.04% it replaces. What
is established is that F is *small* — 24 pixels — not its distribution.

**It does not make `vc_render_tifxyz` proven deterministic.** 24 pixels is not zero. The sampler
streams from S3 and the scorer is known non-deterministic at 0.0032%; this pair cannot separate those
two contributions, and does not need to, because both are negligible against any effect this study
could care about.

**It says nothing about displacement.** The three effect arms (ZERO/IN/OUT at 0, −4, +4 vx) are
running now. This result only establishes that the floor is tight enough to interpret them, which is
the gate the registration put in front of them.
