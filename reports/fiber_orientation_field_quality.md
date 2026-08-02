# Is the orientation field good enough to trace? A ground-truth characterisation

**Date:** 2026-08-01
Spec: `docs/superpowers/specs/2026-08-01-orientation-field-quality-design.md`.
Raw numbers: `reports/fiber_orientation_field_quality.json`.

## Why

Three walker-level fixes to the fiber tracer — tangent smoothing, bounded coasting and seed
non-maximum suppression — were implemented, measured under a pre-registered contract, and fell
well short: no cube cleared its connected-components floor on either metric
(`reports/fiber_tracer_improvement.md`). The one gain they produced turned out to be
**abstention** rather than better tracing: at the shipped `tangent_window=5`, `high_curvature`
stops *rose* (750 → 876 and 664 → 738), walks became shorter and more numerous, and
merge-penalized ERL paid for the reduced merges.

Every one of those fixes rested on an assumption nobody had checked: **that the orientation field
is accurate enough to follow.** This measures it.

## Method

For every in-bounds ground-truth node in all six cubes, compare the hand-traced tangent against
the model's tangent:

- **True tangent** — from the node's neighbours in the NML edge graph. Interior nodes use a
  length-weighted chord between the two neighbours; endpoints use a one-sided difference.
- **Predicted tangent** — `fiber_direction(hessian(P, gauss_sigma=2, sigma=3))` where `P` is the
  `scrollprize/fiber_hz_vt` probability volume. This is exactly how `bench_cli.cmd_trace` builds
  the field, so this characterises the field the tracer consumes, not a reimplementation.
- **Error is taken modulo 180 degrees.** An orientation field is defined only up to sign, so a
  flipped tangent is correct and scores 0, not 180. Errors live in [0, 90].
- Sampling is **nearest-voxel**, matching `_direction_at`, so this measures what a walk sees.

**Excluded and counted, never guessed at:** branch nodes (degree >= 3, no single tangent is
defined), isolated nodes, and zero-length tangents. Nodes where the field itself is undefined are
reported separately rather than dropped silently — see the undefined-rate column.

**15,986 nodes scored** across the six cubes.

### Validation

Three synthetic checks feed a constructed field straight into the analysis: a field built to be
exactly right scores ~0 degrees; one rotated by a known 17 degrees returns 17; negating the entire
field changes nothing. **These prove the analysis does not permute axes; they do not exercise
`hessian` → `fiber_direction`**, so they cannot catch an axis-convention error in the
field-production path. That path is covered separately by the pre-existing
`tests/test_fiber_orientation.py` (see its `(z, y, x)` ordering tests).

A further regression test pins the one bug known to have been introduced here: NML node order is
arbitrary, so curvature and spacing must come from the edge graph rather than from array-adjacent
rows. The test is built on a geometry where the two genuinely disagree, and was verified by
mutation — reverting the fix makes it fail.

## Results

| cube | median | p90 | p99 | over 25 deg | out of bounds | undefined (in-bounds) | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 8.76 | 44.29 | 87.06 | 16.9% | 14.2% | 2.25% | 2652 |
| s1_00497_02497_02997 | 7.28 | 27.15 | 82.50 | 11.3% | 13.0% | 2.89% | 2856 |
| s1_00997_02497_02997 | 7.63 | 34.85 | 87.12 | 13.9% | 47.3% | 7.40% | 1665 |
| s1_08997_02997_02497 | 9.97 | 32.79 | 83.51 | 13.8% | 39.1% | 2.65% | 4842 |
| s1_10997_02997_02997 | 8.11 | 25.40 | 82.21 | 10.2% | 35.1% | 3.78% | 2035 |
| s5_03997_01497_03997 (cross-scroll) | 8.83 | 37.93 | 85.39 | 14.5% | 33.5% | 3.63% | 1936 |

Ranges quoted below are across cubes; summary figures are **unweighted per-cube aggregates**, not
node-weighted. The headline is the **median of the six per-cube medians, 8.435 degrees** (their
unweighted mean is 8.430 — the two coincide here), against the walker's `max_angle_deg = 25`.

## Verdict: fork 3 — a good field with a fat tail

Of the three outcomes pre-registered in the spec, the data supports the third.

**The field is not broadly bad.** A median of 7.3-10.0 degrees is comfortably inside the 25-degree
turn limit, and it is remarkably consistent across cubes — including the cross-scroll cube, which
is indistinguishable from the Scroll 1 cubes at 8.83. Multi-scale orientation or a structure
tensor would be solving a problem that is not the binding one.

**But 10-17% of ground-truth nodes exceed the turn limit outright**, and the tail is severe: p90
reaches 25-44 degrees and p99 is 82-87 degrees, near the 90-degree maximum.

**A caveat on what that number does and does not say.** Error-against-ground-truth is a statement
about field *accuracy*; it is not directly a prediction of walker behaviour, because the walker
never compares against ground truth. It compares the field at the current voxel against a running
mean of recent *field* directions, so a field wrong by a consistent 40 degrees but locally smooth
is perfectly followable.

The walker-relevant quantity is **field self-consistency** — the turn in the field itself between
adjacent ground-truth nodes. Measured directly: median **7.2-13.2 degrees**, exceeding 25 degrees
at **12.3-23.9%** of edges.

The **over-25-degree fraction is higher than the accuracy figure on every cube**, so the conclusion
survives and strengthens. (The *median* is not uniformly higher — it is lower on
`s1_08997_02997_02497` (7.57 vs 9.97) and `s1_10997_02997_02997` (7.21 vs 8.11). It is the tail
that matters here, and the tail is worse.)

**These are ground-truth-node steps of 4.9-15.1 voxels, 7-21x the walker's 0.7-voxel step**, so the
per-edge rate is not a per-walker-step rate. What it establishes is that a fiber traversed at
annotation resolution meets a field discontinuity exceeding the turn limit every four to eight
annotation intervals — not that one walker step in four to eight fails.

That is enough to explain fragmentation without any other cause.

**Fork 2 is not forced**, but the honest framing is narrower than "greedy is right": the field is
good enough in the median that a global-assembly rewrite is not *required* to make progress. A
purely local greedy rule is still fragile against a tail this heavy.

## Secondary cuts

**Real curvature does not stop walks** *(inference, not measurement)*. Median local turn per
ground-truth node-step is 11.6-19.4 degrees at node spacings of 4.9-15.1 voxels. Converting that
to a per-walker-step figure is not straightforward: turn angle *decreases* as spacing increases
(4.9 vox → 19.4 deg; 15.1 vox → 12.9 deg), which is the signature of annotation jitter rather than
of curvature — under true curvature the turn over a longer chord would be larger, not smaller. The
per-cube rate spans 0.85-3.95 degrees per voxel, a 4.6x spread.

The conclusion holds regardless, and holds *a fortiori*: if the measured turn is inflated by
jitter, true curvature is smaller still. Even taking the largest per-cube rate at face value,
a 0.7-voxel walker step implies well under 3 degrees against a 25-degree limit. `max_angle_deg`
is not mis-set, and the stops are field noise rather than real bends.

**Field error is not explained by genuine bending** (spec secondary cut 2). Error and curvature are
node-aligned, so this is a direct comparison rather than an inference from their marginals:
Pearson r is **0.029-0.156**, and median error at above-median-curvature nodes exceeds
below-median-curvature nodes by only **0.7-2.2 degrees**. Curvature explains almost none of the
error — which is what the paragraph above argues, now measured rather than reasoned.

**The field degrades only gently off the centreline.** Median error at 0, 1, 2 and 3 voxels
perpendicular to the fiber: 8.43, 8.76, 9.42, 9.72 degrees. Ridge-peaked seeding is therefore
worth having but is not critical, and `claim_radius` is not claiming territory where the
orientation is meaningfully worse.

**The ground-truth tangent estimator is not driving the result.** The interior tangent is a
length-weighted chord, which coincides with the bisector of the two edge directions only when
both edges are equal length — a real concern given irregular annotation spacing. Measured against
a second estimator that averages *unit* edge directions, the median disagreement is
**0.005-0.665 degrees** (p90 1.3-3.2). That is negligible against errors of 8-44 degrees, so the
measured field error is genuinely the field's, not an artifact of how we estimate the reference.

**A population note.** Curvature and estimator-disagreement figures are conditioned on nodes where
the field is defined; node spacing is computed over all edges. The degrees-per-voxel ratio above
therefore divides one population by the other, which is another reason to treat it as indicative.

**Node spacing** is 4.9-15.1 voxels (median ~8), so the ground-truth tangent is a chord over
roughly 8 voxels. Where a fiber is curving, that chord slightly smooths the true tangent, making
the reported error a mild **upper bound**. The estimator-disagreement figures above bound how
much.

## Corrected: the field is defined almost everywhere the model detects a fiber

An earlier draft of this report claimed the field was "undefined at 15.5-51.2% of ground-truth
nodes (mean 32.8%)" and called it arguably larger than the accuracy finding. **That was wrong by
roughly an order of magnitude, and it was a claim about someone else's model.** It is corrected
here rather than quietly amended.

The defect: `sample_field` reports a position as not-defined when it is *either* out of bounds
*or* flagged invalid, which is correct for excluding nodes from an error statistic and wrong as a
coverage-of-the-field statistic. The union was published as the latter. Split apart:

- **Out of bounds: 13.0-47.3% of nodes.** Annotators traced beyond the cube edge, so these nodes
  simply lie outside the 256³ volume. This is a fact about our own ground truth, not about
  `fiber_hz_vt`. It is also already documented in `skeleton_io`, which is why `in_bounds_mask`
  exists.
- **Genuinely undefined, among in-bounds nodes: 2.25-7.40% (mean 3.77%).**

**And that residual is a recall observation, not an orientation one.** `fiber_direction`'s `valid`
flag is `best_norm > 1e-8`, a magnitude guard on a quantity that scales with the fourth power of
the Hessian and is not normalised by matrix scale — multiplying the Hessian by 1000, a
mathematical no-op for eigenvector *direction*, moves volume-wide `valid` from 43.5% to 97.1% on
`s1_00497_01497_03997`. So
`valid=False` means "the response here is numerically weak", not "no orientation exists".

At ground-truth nodes the picture is unambiguous: median model fiber-probability at the
genuinely-undefined nodes is **0.0003-0.0009**, against **0.994-0.998** at defined nodes. The
model did not detect a fiber there at all. That is a statement about recall, and a much weaker
and differently-framed one than what was originally published.

Two positive results fall out of the same measurement. The median probability of ~0.995 at
ground-truth nodes independently corroborates that the NML-to-cube registration is correct — the
annotations land where the model sees fibers. And `hessian`'s internal `zero_mask` is empty on
five of the six cubes (non-empty on `s1_00497_02497_02997` only), so it is not a meaningful
source of missing orientations.

## What this implies for the tracer

Stated as inference, not measurement.

The bad nodes are **clustered**, not isolated — and this is measured, not assumed. Run-lengths of
consecutive over-25-degree nodes along the annotation chain average **1.28-1.70** against the
**1.11-1.20** that the per-node rate alone would predict under independence; **21-36%** of runs are
multi-node, and the longest runs reach **6-10 nodes**. Measured by summing the real inter-node
distances inside each cube's longest run, that is **20.7-94.7 voxels** of continuously-bad field
(p95 run span 16.7-25.5 voxels).

(An earlier draft asserted the opposite. Its argument — "a blocking node appears every ~66 voxels",
from rate divided by spacing — presupposes independence and therefore could not be evidence of
isolation. The corrected picture reverses the recommendation below.)

One caveat carries over from the Verdict section: these runs are runs of field-versus-ground-truth
error, the quantity disclaimed above as not directly predicting walker behaviour. The
walker-relevant version — runs of over-25-degree *self-consistency* edges — is not computed here,
though the machinery now exists. Treat the sizing below as indicative rather than exact.

Coasting was designed for exactly this shape of problem — step past a bad region and resume — and
failed for two reasons now visible. `max_skip_steps=2` spans 1.4 voxels against bad regions whose
p95 span is 16.7-25.5 voxels and whose longest reach 20.7-94.7, so the budget was short by an order
of magnitude. And while
coasting the walk follows a frozen reference direction and cannot absorb a corrected one, so it can
only continue straight — over tens of voxels of a curving fiber, straight is badly wrong, which is
consistent with coasting having *raised* merges when it was measured.

A mechanism that survives a bad region by **re-acquiring** the field beyond it, rather than
freezing and hoping, is the shape the data suggests. That is a hypothesis this measurement
motivates; it is not established here, and the previous cycle is a reminder that a mechanism which
looks right on synthetic geometry can fail on real cubes.

## Reproducing

```bash
uv run python scripts/analyze_orientation_field.py
uv run python -m pytest tests/test_field_quality.py -q   # 42 tests, CPU
```

Nothing under `src/vesuvius_autoresearch/fibers/` was modified by this work except the new
`field_quality.py`; `trace.py`, `detection.py` and `skeleton_io.py` are untouched.
