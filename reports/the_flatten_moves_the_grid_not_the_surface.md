# The flatten moves the grid, not the surface: 0.25 voxels along the normal, not 7

**2026-09-22.** A correction to `reports/the_flatten_lands_on_different_surfaces.md`. That report and
several later documents, including villa PR #1866, say two stock flattens of identical meshes
"land on surfaces 7.15 vx apart". **They land on the same surface.** They place their sampling grids
differently within it. `scripts/measure_flatten_normal_offset.py`; per-pair numbers in
`reports/flatten_normal_offset/`.

## What was wrong with the metric

`scripts/measure_flatten_divergence.py` reports **nearest-neighbour** distance between the two
flattened tifxyz point sets. The flat grid is spaced **20 vx** (median; p90 21.8), so two samplings of
**one** sheet, offset by a random amount within the sheet, read about **7.7–8.0 vx** apart by nearest
neighbour (Monte Carlo on a 20 vx lattice: mean 7.65, median 7.97). Nearest-neighbour distance cannot
tell a surface that moved from a surface that was re-sampled.

The new tool splits each nearest-neighbour vector along the **reference surface's own normal**,
computed from its grid. That part is displacement; the rest lies in the plane of the sheet and is
re-sampling.

## The measurement

| pair | NN p50 | **along the normal**, \|d\| p50 (p90) | in-plane p50 |
|---|---:|---:|---:|
| control: the same surface shifted +4 vx radially | 4.00 | **3.58** (3.94) | 1.75 |
| control: `rad0` re-sampled at its own cell centres (synthetic; exploratory run, same computation, no JSON) | 13.03 | **0.91** (10.0) | 12.78 |
| **stock vs stock, outer** (`radial_work_rad0` / `rad0b`) | 7.39 | **0.25** (2.21) | **7.07** |
| **stock vs stock, inner** (`render_lasagna` / `dup_armREPEAT`) | 0.25 | **0.01** (0.07) | 0.25 |
| deterministic vs stock `rad0` (`flatten_det_a`) | 7.67 | **0.26** (2.56) | 7.37 |
| deterministic vs stock `rad0b` | 6.75 | **0.23** (2.26) | 6.33 |
| deterministic vs deterministic (`det_a` / `det_b`) | 0.00 | 0.00 | 0.00 |

**The two controls bracket the instrument.** A real 4 vx radial shift reads 3.58 vx along the normal,
which implies the radial direction sits about 26° off the local normal on average (3.58 / 4 = cos 26.5°).
That angle is inferred, not measured separately. A synthetic
re-sampling of one sheet at the largest possible in-plane offset (half a cell) reads 0.91 vx along
the normal. That 0.91 is chord error across a 28 vx cell diagonal on a curved sheet: the floor for
"same sheet".

**The stock pair reads 0.25 vx along the normal, below that floor.** Its signed median is −0.00, so
there is no systematic offset either. The whole 7 vx is in the plane of the sheet. The same holds
for the deterministic flatten against either stock one, which the earlier report read as "6.6–7.3 vx
from both stock surfaces".

A radial-only version of the same test, run first, agrees: a signed radial median of +0.025 vx and a
consistency ratio of 0.015, against 1.000 for the +4 vx control.

## What changes and what does not

**Unchanged — each rests on byte comparisons, not on this metric:**

* The flatten is non-deterministic, and the cause is CUDA reduction order.
* Under `FLATTEN_DETERMINISTIC=1` two flattens are byte-identical.
* The ink cost of re-flattening is real: `total_fg_pixels` moves 3.04% (outer) and 1.42% (inner).
* Holding the flatten fixed collapses the floor to 0.0014%.

**Changed:**

* **"Lands on surfaces 7 vx apart" is wrong.** The flatten lands on the same surface to 0.25 vx and
  **re-parametrises it**: the same material ends up at different grid positions, about 7 vx apart
  in-plane in the outer region. The 3.04% ink difference therefore comes from *how the sheet is laid
  out*, not from *where the surface is*.
* **Per-voxel ink sensitivities built on the 7.15 figure are void**, including the "0.43 %/vx" in
  the original report. They divided an ink change by a re-sampling distance.
* **The radial-displacement design was still invalid, for a restated reason.** It was declared
  invalid because the flatten "moves the surface 7.15 vx by itself, 1.8× the manipulation". The
  surface does not move, but the re-flatten still adds 3.04% of ink noise, so the design still could
  not resolve its effect. The redesign that holds the flatten fixed stands.

## What this does not settle

* **Why an in-plane re-parametrisation moves ink 3%.** Plausibly the scorer sees a strip that is
  shifted or stretched, and its fixed-threshold count responds; that is untested.
* **Whether it is part of the seed-to-seed *placement* instability** (r ≈ 0.70). It would be if
  placement was compared in strip coordinates, and would not be if it was compared in the volume
  frame. Not checked here, so not claimed.
* **One region pair and one inner pair.** The flat grid spacing (20 vx) is a property of the render
  configuration, so the in-plane magnitude should hold wherever that spacing does. That is an
  expectation, not a measurement.

## How this was caught

While designing a follow-up, I asked whether `rad0b`'s +3.04% ink over `rad0` could be read off the
offset sweep, which it could if `rad0b` were a radial offset of `rad0`. The prediction was written
down before computing. It **failed**: no radial offset. Chasing why the 7 vx had no radial component
led to the grid spacing. Two instrument errors of my own were caught on the way by the ±4 vx control.
Subsampling the reference surface manufactured a 17% tail, and briefly made the original 7.15 figure
look unreliable. With the full reference, the nearest-neighbour number is right; it is only the
**reading of it as a displacement** that was wrong.
