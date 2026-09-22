# The flatten lands on different surfaces: 0.5 voxels inner, 7.2 outer, from identical input

> **CORRECTED 2026-09-22: the title's claim is wrong.** The two flattens lie on the **same surface**:
> **0.25 vx** apart along the surface normal (outer) and **0.01 vx** (inner). The 7.15 vx below is a
> nearest-neighbour distance between two samplings of one sheet on a 20 vx grid, offset in-plane.
> It is a re-parametrisation, not a displacement. The ink changes (3.04%, 1.42%) are real; the
> per-voxel sensitivities below divided them by a re-sampling distance and are void. See
> `reports/the_flatten_moves_the_grid_not_the_surface.md`. The text below is kept as written.

**2026-09-20.** Follow-up to `reports/the_render_is_the_noise_floor.md`, which established that
re-rendering one mesh set on one pinned tree moves `total_fg_pixels` by 3.04%. This measures the
geometric cause. `scripts/measure_flatten_divergence.py`.

## Two independent pairs, one metric

Nearest-neighbour surface distance between two flattens of the **same meshes**:

| pair | region | mean | p50 | p90 | ink |
|---|---|---:|---:|---:|---:|
| `render_lasagna` / `dup_armREPEAT` | w010-019 (inner) | **0.535 vx** | 0.247 | 1.393 | 1.42% |
| `radial_work_rad0` / `rad0b` | w120-129 (outer) | **7.151 vx** | 7.342 | 10.754 | 3.04% |

**The flatten is non-deterministic in both regions**, and the magnitude is region-dependent by more
than an order of magnitude. The outer pair's surfaces sit **7 voxels apart on average** — nearly half
a winding gap (16.17 vx) — from byte-identical input meshes on byte-identical code.

The inner pair kept the same grid shape (303, 883) while the outer did not (426 vs 425 rows), so the
outer flatten varies in its parameterization as well as its surface.

## A law I nearly published, and the point that killed it

Two measurements agreed almost exactly on ink cost per voxel of displacement:

| source | displacement | ink | %/vx |
|---|---:|---:|---:|
| gap-expander fix | 3.96 vx radial | 10.35% | **2.61** |
| inner flatten pair | 0.535 vx NN | 1.42% | **2.65** |

Agreement to 1.5% from independent measurements is exactly what a real relationship looks like, and
it predicted the outer pair's 3.04% would come from ~1.17 vx.

**Measured: 7.151 vx, i.e. 0.43 %/vx — a 6× miss.** The sensitivity is not constant, and the
agreement was two points coinciding. This is the same trap `reports/noise_floor_by_tier.md` recorded
after two arms agreed at 0.0124 and 0.0127: **two points agreeing is not replication.**

Recorded because the near-miss is the useful part. What survives is only that displacement and ink
loss co-occur, with **strongly sublinear and region-dependent** scaling — 7 voxels in the outer strip
costs 3% while half a voxel in the inner costs 1.4%.

## A measurement error caught on the way

The outer pair's divergence first read **20.9 vx** by comparing cell `[i,j]` to cell `[i,j]`. Their
grids differ by one row, so that compares different material points; 46% of cells appeared >16 vx
apart and the max was 1049 vx. Nearest-neighbour gives **7.151 vx**, and the gap between the two
numbers is parameterization offset, not movement.

Index-wise is valid only when grids match exactly, as they do for the inner pair — where it agrees
with NN to three decimals (0.533 vs 0.535), which is the check that the two metrics agree when both
are applicable.

## It also resolves an apparent contradiction

`seedarm_04` and `probe_innerprob` agree to **four pixels (0.0016%)**, which cannot happen if every
render diverges by percent. **`probe_innerprob` never re-rendered**: its log contains zero
render-stage lines — no trim grid, no bands, no lasagna. It re-scored an existing strip.

So that figure belongs with the scorer-only measurements (0.0032%, `score_arms.sh` header), not with
the render+score pairs. The three-way split in `reports/the_determinism_floor_rests_on_one_draw.md`
is now four measurements in two clean groups:

| what varies | measurements |
|---|---|
| scorer only | 0.0032%, 0.0016% |
| flatten + render + score | 1.42%, 3.04% |

## Limits

Two pairs, one per region, one machine. The flatten's distribution is not characterised — these are
two draws, and the region difference rests on one pair each, which is precisely the sample size this
report's own middle section warns about. `total_fg_pixels` is an area count.
