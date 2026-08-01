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

The synthetic checks that make a false finding hard: a field constructed to be exactly right
scores ~0 degrees; a field rotated by a known 17 degrees returns 17; negating the entire field
changes nothing. A wrong axis convention — the most likely way to produce a large, plausible,
completely false result — would fail all three.

## Results

| cube | median | p90 | p99 | over 25 deg | field undefined | n |
| --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 8.76 | 44.29 | 87.06 | 16.9% | 16.1% | 2652 |
| s1_00497_02497_02997 | 7.28 | 27.15 | 82.50 | 11.3% | 15.5% | 2856 |
| s1_00997_02497_02997 | 7.63 | 34.85 | 87.12 | 13.9% | 51.2% | 1665 |
| s1_08997_02997_02497 | 9.97 | 32.79 | 83.51 | 13.8% | 40.7% | 4842 |
| s1_10997_02997_02997 | 8.11 | 25.40 | 82.21 | 10.2% | 37.6% | 2035 |
| s5_03997_01497_03997 (cross-scroll) | 8.83 | 37.93 | 85.39 | 14.5% | 35.9% | 1936 |

Median-of-medians **8.43 degrees**, against the walker's `max_angle_deg = 25`.

## Verdict: fork 3 — a good field with a fat tail

Of the three outcomes pre-registered in the spec, the data supports the third.

**The field is not broadly bad.** A median of 7.3-10.0 degrees is comfortably inside the 25-degree
turn limit, and it is remarkably consistent across cubes — including the cross-scroll cube, which
is indistinguishable from the Scroll 1 cubes at 8.83. Multi-scale orientation or a structure
tensor would be solving a problem that is not the binding one.

**But 10-17% of ground-truth nodes exceed the turn limit outright**, and the tail is severe: p90
reaches 25-44 degrees and p99 is 82-87 degrees, near the 90-degree maximum. Roughly one node in
seven is a place where the field points somewhere the walker will refuse to follow.

That is enough to explain fragmentation without any other cause. It also means the *idea* behind
coasting was right and the implementation was wrong — see below.

**Greedy sequential walking is not obviously the wrong algorithm**, which was fork 2. It is the
right algorithm running on a field with isolated blowouts.

## Secondary cuts

**Real curvature does not stop walks.** Median local turn per ground-truth node-step is 11.6-19.4
degrees (mean 14.77) at a mean node spacing of 8.87 voxels. Scaled to the walker's 0.7-voxel step
that is about **1.2 degrees per step**, against a 25-degree limit. Genuine fiber bending is nowhere
near the turn limit; `max_angle_deg` is not mis-set, and the stops are field noise rather than real
bends.

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

**Node spacing** is 4.9-15.1 voxels (median ~8), so the ground-truth tangent is a chord over
roughly 8 voxels. Where a fiber is curving, that chord slightly smooths the true tangent, making
the reported error a mild **upper bound**. The estimator-disagreement figures above bound how
much.

## The finding that was not asked for: the field is often undefined

**The orientation field is undefined at 15.5-51.2% of ground-truth fiber nodes** (mean 32.8%).
On `s1_00997_02497_02997` it is undefined at more than half of them.

These are hand-traced fiber centres — the places a tracer most needs an orientation — and a third
of them have none. This is separate from the accuracy question and arguably larger: no walker can
follow a field that does not exist there, whatever its accuracy where it does.

This was not part of the original question and is reported because it fell out of the measurement.

## What this implies for the tracer

Stated as inference, not measurement.

The bad nodes are **isolated**, not clustered into long stretches: at 13.4% of nodes and ~8.9
voxel spacing, a blocking node appears roughly every 66 voxels of fiber. Coasting was designed for
exactly this — step past a bad region and resume. It failed for two reasons now visible:
`max_skip_steps=2` spans only 1.4 voxels where a bad *node* represents roughly 8 voxels of
annotation interval, and while coasting the walk follows a frozen reference direction and cannot
absorb a corrected one, so it can only continue straight.

A mechanism that survives a bad region by **re-acquiring** the field beyond it, rather than
freezing and hoping, is the shape the data suggests. That is a hypothesis this measurement
motivates; it is not established here, and the previous cycle is a reminder that a mechanism which
looks right on synthetic geometry can fail on real cubes.

## Reproducing

```bash
uv run python scripts/analyze_orientation_field.py
uv run python -m pytest tests/test_field_quality.py -q   # 27 tests, CPU
```

Nothing under `src/vesuvius_autoresearch/fibers/` was modified by this work except the new
`field_quality.py`; `trace.py`, `detection.py` and `skeleton_io.py` are untouched.
