# Fiber tracing: connectivity evaluation (ERL, splits, merges)

**Date:** 2026-07-29
**Headline: the tracer does not yet beat connected components.** It wins on merges and loses
badly on fragmentation. Reported because the floors are what make the number interpretable.

## Setup

Cube `s1_00497_01667...` sub-volume `s1_00497_01497_03997_256[0:128]³`, **22** hand-traced
ground-truth fibers with in-bounds geometry, tolerance **2.0 voxels**, 7.91 um frame. Fiber
probability from `scrollprize/fiber_hz_vt`; mask for all floors is `P(fiber) >= 0.5`.

Metric definitions in `src/vesuvius_autoresearch/fibers/eval_trace.py`. ERL is the
length-weighted mean run length `sum(L^2)/sum(L)` over maximal contiguous stretches of each
ground-truth fiber assigned to one predicted instance. `ERLpen` zeroes every run belonging to an
instance that merges two ground-truth fibers. **Splits count runs, not distinct labels**, so a
fiber traced as two disconnected halves under one id still counts as fragmented.

## Results

| Row | ERL | ERLpen | coverage | precision | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- | --- |
| *oracle (GT rasterized) — DISCLOSED ORACLE* | *127.69* | *120.39* | *1.000* | *1.000* | *2* | *1* | *22* |
| floor: single instance | 111.49 | **0.00** | 0.960 | 0.229 | 21 | 21 | 1 |
| **floor: connected components** | **110.66** | **22.47** | 0.960 | 0.229 | 24 | 11 | 41 |
| floor: one instance per voxel | 0.96 | 0.96 | 0.960 | 0.229 | 3045 | 1 | 122736 |
| floor: 50 random instances | 0.99 | 0.00 | 0.960 | 0.229 | 2986 | 946 | 50 |
| tracer, coverage-max | 9.02 | 8.42 | 0.875 | 0.285 | 577 | 6 | 373 |
| tracer, balanced | 23.14 | 20.17 | 0.827 | 0.250 | 353 | 5 | 200 |
| tracer, strict | **27.87** | **24.27** | 0.686 | 0.266 | 220 | **5** | 104 |

## What this says

**The naive baseline is strong and we do not beat it.** Connected components of the probability
mask scores ERL 110.66 against the tracer's best 27.87. Connected components achieves this by
fusing touching fibers into single long components: it commits **11 merges** where the tracer
commits **5**, and its merge-penalized ERL collapses from 110.66 to 22.47. On the penalized
metric the tracer's best (24.27) is marginally ahead of connected components (22.47), but
"marginally ahead of the naive baseline on one of two metrics" is not a result worth announcing.

**Fragmentation is the whole problem.** 220-577 splits over 22 fibers is 10-26 fragments per
fiber. Coverage is genuinely good (0.686-0.875 of ground-truth length is claimed by *something*),
so the tracer finds the fibers; it just cannot keep one identity along them. ERL is low purely
because runs are short.

**The abstention knob behaves correctly**, which is the one piece of good news about the design:
tightening from coverage-max to strict moves ERL 9.02 -> 23.14 -> 27.87 while coverage falls
0.875 -> 0.827 -> 0.686 and splits fall 577 -> 353 -> 220. That is the intended
coverage-for-correctness trade, monotone in the right direction.

## Why the floors were worth building

Every floor scores **identical coverage (0.960) and precision (0.229)**, because those are
properties of the shared mask rather than of the instance labelling. A submission reporting
coverage and precision alone would be unable to distinguish a correct tracer from
one-instance-per-voxel or from 50 random labels. Only ERL and the merge count separate them.

The single-instance floor is the sharpest illustration: raw ERL **111.49**, which would look like
a near-oracle result, and merge-penalized ERL **exactly 0.00**. Publishing raw ERL alone would be
gameable by a tracer that simply labels everything once.

## Oracle caveat

The oracle scores 2 splits and 1 merge rather than a clean zero. At tolerance 2.0 two
ground-truth fibers in this cube pass within ~2 voxels of each other, so label growth bridges
them. This is a property of the tolerance, not of the harness: at tolerance 0 the oracle is
exact, and a unit test pins that. It also sets a practical ceiling — no method can score better
than 127.69 / 1 merge at this tolerance on this cube.

## Next step, and what it is not

The fix is **not** more tuning: the sweep already shows the knob is monotone and the ceiling on
this configuration is ~28 ERL. The fix is to stop fragmenting, which means one of:

1. **Fragment re-linking.** Join collinear fragment endpoints whose tangents agree and whose gap
   is short. This directly attacks 10-26 fragments per fiber and is the highest-value change.
2. **Seed non-maximum suppression** perpendicular to the tangent, so one fiber yields one seed
   rather than several across its cross-section. `collision` was the dominant stop reason at high
   coverage, which is the signature of exactly this.
3. Revisiting `high_curvature` termination, still the dominant stop reason in the strict setting.

Until fragmentation is addressed there is nothing here worth submitting: the honest current
statement is "high coverage, correct abstention behaviour, loses to connected components on run
length".
