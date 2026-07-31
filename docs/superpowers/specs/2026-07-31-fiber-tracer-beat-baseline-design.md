# Clearing our own published baseline: fiber tracer improvements

**Date:** 2026-07-31
**Status:** approved, ready for planning
**Repo:** `vesuvius-autoresearch` (the tracer is the benchmark's *entrant*, not part of the benchmark)

## Problem

We published a fiber connectivity benchmark whose baseline our own tracer does not clear.
On all six 256³ cubes, connected components beats the tracer on both metrics. The published
standing on `s1_00497_01497_03997_256`:

| row | ERL | ERLpen | coverage | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- |
| tracer (strict + relink) | 26.60 | 23.16 | 0.623 | 1872 | 38 | 669 |
| floor: connected components | 197.11 | 37.13 | 0.918 | 265 | 66 | 299 |

**Fragmentation is the entire problem**: 1872 splits over 87 ground-truth fibers is ~21.5
fragments per fiber. Coverage is respectable, so the tracer finds the fibers; it cannot hold one
identity along them, so every run is short and ERL is low.

Live stop-reason distribution at full-cube scale, strict setting:

| stop reason | count | share |
| --- | --- | --- |
| `high_curvature` | 750 | 46% |
| `collision` | 455 | 28% |
| `low_response` | 243 | 15% |
| `out_of_bounds` | 196 | 12% |

## The pre-registered contract

Written before any tuning run, and not revisable afterwards.

- **Primary metric: merge-penalized ERL.** Target: on each cube, beat **that cube's own**
  connected-components ERLpen. The floor is per-cube, not a single number:

  | dev cube | tracer ERLpen | cc ERLpen | gap |
  | --- | --- | --- | --- |
  | `s1_00497_01497_03997_256` | 23.16 | 37.13 | 1.60x |
  | `s1_00497_02497_02997_256` | 33.60 | 64.27 | 1.91x |

  Held-out gaps, recorded here so they cannot be renegotiated later: `s1_00997_02497_02997`
  29.8 vs 56.5 (1.89x), `s1_08997_02997_02497` 30.8 vs 106.1 (3.45x), `s1_10997_02997_02997`
  34.2 vs 57.7 (1.69x), `s5_03997_01497_03997` 25.4 vs 51.1 (2.01x).
- **Raw ERL is reported every time, improved or not.** Current 26.60 against 197.11, a 7.4x gap.
- **Splits, merges, coverage, and instance count are reported every time.**
- **Automatic failure condition: ERLpen improves while merges rise.** A merge-bought win is not a
  win, and the benchmark exists to say so.

### Why the primary metric is ERLpen, stated in advance

Connected components earns its raw-ERL score **by merging**: 66 merges, which is exactly why its
ERLpen collapses from 197.11 to 37.13. Raw ERL rewards fusing touching fibers into single long
components — the behaviour this benchmark's merge penalty exists to punish, because a merge
corrupts the U/V parameterization fibers are wanted for. An abstaining tracer is therefore
structurally disadvantaged on raw ERL in a way that has nothing to do with tracing quality.

This argument is only credible stated **before** seeing whether the fixes work, which is why it is
recorded here rather than in the eventual report. If the tracer clears ERLpen but not raw ERL,
the report says exactly that, quotes both numbers, and does not claim the benchmark was beaten
outright.

### Anti-tuning protocol

We own the benchmark being optimized against, so the split is fixed here:

| role | cubes |
| --- | --- |
| **dev** (all decisions made here) | `s1_00497_01497_03997_256`, `s1_00497_02497_02997_256` |
| **held out** (looked at once, at the end) | `s1_00997_02497_02997_256`, `s1_08997_02997_02497_256`, `s1_10997_02997_02997_256` |
| **never touched** (no decision, ever) | `s5_03997_01497_03997_256` (cross-scroll) |

The number of configurations tried is counted and disclosed in the report. A gain that appears on
dev and vanishes on held-out is reported as such, not re-tuned away.

## Fix A: smooth the tangent (targets `high_curvature`, 46%)

**Root cause.** `step` is 0.7 voxels and `_direction_at` uses **nearest-neighbour** lookup, so the
orientation field is piecewise-constant per voxel and jumps discontinuously at voxel boundaries.
`_walk` compares each new direction against `prev`, the single immediately-preceding step. One
noisy voxel, crossed once, terminates the walk permanently. This is quantization noise being read
as curvature, not fibers bending.

**Correction (2026-07-31, before implementation).** An earlier version of this spec proposed
tangent smoothing alone. That is insufficient, and the gap was found by probing the synthetic
geometry before any implementation: smoothing the *reference* tangent does not reject a bad
*sample*. At a wildly-wrong voxel the incoming direction is perpendicular, so `dot(d, ref)` fails
the threshold whether `ref` is smoothed or not. Measured on a synthetic tube with one corrupted
voxel: 2 instances instead of 1, with `high_curvature: 1`.

Two distinct failure modes therefore need two mechanisms, and they are kept as separate parameters
so their contributions can be measured independently:

| failure mode | mechanism | parameter |
| --- | --- | --- |
| mild jitter across many voxels | compare against a smoothed reference | `tangent_window` |
| a single wildly-wrong voxel | coast past a bounded run of rejections | `max_skip_steps` |

**Change 1 — smoothed reference.** Compare the new direction against a sign-aligned mean of the
last `k` step directions rather than against the single previous one.

- `k = ceil(2 / step)` = 3 at the default step. Principled: it spans two voxels, so a single bad
  voxel cannot terminate a walk, while a genuine sustained bend still trips the test.
- **Sign alignment is mandatory.** The orientation field is defined only up to sign. Each
  direction must be flipped into the frame of the running mean before being averaged, or two
  equally valid opposing vectors cancel to near-zero — the same failure `_direction_at`'s
  docstring already warns about for spatial interpolation.
- The comparison threshold `max_angle_deg` is **unchanged**. This fix makes the existing test
  robust; it does not loosen it. Raising the angle instead would buy coverage by letting walks
  jump between fibers, which costs merges and fails the pre-registered condition.
- Before `k` steps have accumulated, compare against the mean of what exists (seeded with
  `seed_dir`), so behaviour at the start of a walk is well defined.

**Change 2 — bounded coast.** On a curvature rejection, do not terminate immediately. Step along
the reference direction instead, and count consecutive rejections. Resume normally as soon as the
field agrees again; terminate with `HIGH_CURVATURE` only once `max_skip_steps` consecutive
rejections have accumulated.

- `max_skip_steps = 2` at the default step of 0.7 voxels, which spans ~1.4 voxels — enough to
  cross one corrupted voxel, not enough to cross a genuine fiber boundary and keep going.
- The counter resets on any accepted step, so the budget is for *consecutive* rejections. A walk
  that repeatedly coasts is following something the field does not support, and must still stop.
- Coasted steps are still subject to every other gate: response, bounds, and collision. Coasting
  suspends only the curvature test.
- **This is the mechanism most likely to buy merges**, since coasting is exactly how a walk could
  cross into a neighbouring fiber. The pre-registered failure condition — ERLpen up while merges
  rise — exists to catch precisely this, and `max_skip_steps = 0` must reproduce
  smoothing-only behaviour so the two are separable.

## Fix B: seed non-maximum suppression (targets `collision`, 28%)

**Root cause.** Seeds are chosen wherever the vesselness ranking exceeds a percentile, subsampled
by `seed_stride`. Several seeds land across one fiber's cross-section. The first walk claims a
tube of `claim_radius`; the rest start inside it and stop immediately with `COLLISION`.

**Change.** Greedy non-maximum suppression over seed candidates, perpendicular to the tangent.

- Sort candidates by seed response descending; accept greedily.
- Reject a candidate if its displacement from any accepted seed, **projected perpendicular to that
  accepted seed's tangent**, is below `r_perp`.
- Distance *along* the tangent is unconstrained, so a long fiber can still be re-seeded beyond a
  gap. Suppressing along the tangent would prevent legitimate re-seeding and lose coverage.
- `r_perp = 2` voxels, from fiber geometry rather than tuning: papyrus fibers are roughly
  10-20 um and the frame is 7.91 um/voxel.

**Expected contribution.** Smaller than Fix A. A collided seed wastes a walk but does not fragment
an *existing* fiber — the stub is discarded by `min_length`. Every `high_curvature` stop, by
contrast, cuts one fiber into two instances. Fix B mainly buys speed and reduces spurious short
instances.

## Scope

Both fixes live in `src/vesuvius_autoresearch/fibers/trace.py`. Fix A changes `_walk`; Fix B adds
a suppression pass over seed candidates in `trace_fibers`. New parameters go on `TraceParams` with
the principled defaults above.

**Out of scope:** changing the semantic model, the benchmark, the metrics, `relink_fragments`, or
anything in `scrollgt`. The tracer is the benchmark's entrant; touching the benchmark to make the
entrant look better is the exact failure the anti-tuning protocol exists to prevent.

## Testing

- **Regression first:** assert the published `tracer_strict_relink` numbers reproduce before any
  change, so the baseline being improved on is the real one.
- **Fix A:** a synthetic straight fiber whose orientation field is deliberately corrupted at one
  voxel must be traced end to end after the change and must terminate at that voxel before it.
  A synthetic fiber with a genuine sustained bend beyond `max_angle_deg` must still terminate —
  the fix must not silently disable the curvature test.
- **Fix B:** two parallel synthetic fibers 6 voxels apart must yield two accepted seeds; a single
  fiber's cross-section must yield one. A seed far along the same fiber's tangent must still be
  accepted, proving suppression is perpendicular-only.
- Existing tracer tests must continue to pass unchanged.

## Success criteria

1. ERLpen beats **each dev cube's own** connected-components ERLpen (37.13 and 64.27
   respectively), with merges not above that cube's current tracer merge count.
2. The held-out cubes are scored once, at the end, and reported whatever they show.
3. `s5_03997_01497_03997_256` is scored once, at the end, and never informs a decision.
4. Raw ERL, splits, merges, and coverage are reported for every cube regardless of outcome.
5. The configuration count is disclosed.
6. If the result is negative, it is published in the same style as the existing negatives.
