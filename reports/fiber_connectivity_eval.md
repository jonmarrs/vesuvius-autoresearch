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

## Fragment re-linking: attempted, marginal (2026-07-30)

Re-linking joins fragment endpoints whose tangents are collinear across a short gap, with
strict thresholds because a wrong link is a merge. Implemented in `trace.relink_fragments`,
13 tests including every refusal case (perpendicular, side-by-side, over-long gap, three-way
junction, cycles).

| Row | ERL | ERLpen | coverage | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- |
| **floor: connected components** | **110.66** | 22.47 | 0.960 | 24 | 11 | 41 |
| tracer strict | 27.87 | 24.27 | 0.686 | 220 | 5 | 104 |
| tracer strict + relink (best) | **29.51** | **25.32** | 0.688 | 214 | 6 | 89 |
| tracer balanced | 23.14 | 20.17 | 0.827 | 353 | 5 | 200 |
| tracer balanced + relink (best) | 23.23 | 20.26 | 0.829 | 346 | 5 | 167 |

**A real defect was found and fixed en route.** The first implementation concatenated fragment
point lists without filling the bridged gap, so the rasterized instance stayed discontinuous:
the instance count fell 200 -> 167 while ERL moved 23.14 -> 23.17, a link that changed no
connectivity metric at all. Filling gaps with interpolated points is now done and regression
tested. It is a good example of why instance count is not a proxy for connectivity.

**The gain is nonetheless marginal: +6% ERL on the strict setting, ~0 on balanced.** Re-linking
removes only 4-6 splits out of 214-353. The remaining fragments fail the collinearity test
legitimately: walks stop on `high_curvature`, which means the direction really was changing at
the endpoint, so the tangents disagree and a strict linker correctly refuses.

## Assessment after three attempts at the limiting error

The tracer is at **29.51 ERL against a 110.66 connected-components baseline**, having gone
through: classical vesselness (chance), the learned semantic model (detection solved),
orientation from the probability field (5x coverage), and now re-linking (+6%). The gap is not
closing incrementally.

Connected components is a genuinely strong method on this data because the semantic model
already separates most fibers in this cube; it pays 11 merges for that, but 11 merges over 22
fibers still leaves long runs. Our tracer trades those merges away (5-6) and loses far more to
fragmentation than it gains.

**The defensible contribution here is the measurement layer, not the tracer.** Specifically: the
first ERL/split/merge harness for scroll fiber tracing, the anti-gaming floors, the finding that
all five floors score identical coverage and precision so those metrics cannot rank a tracer,
and the finding that **connected components is a strong baseline that a real tracer must beat**.
That is a directly useful result for anyone else entering this lane, and it is the same shape of
contribution as ScrollGT.

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
