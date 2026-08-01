# Is the orientation field good enough to trace? A ground-truth characterisation

**Date:** 2026-08-01
**Status:** approved, ready for planning
**Repo:** `vesuvius-autoresearch` (read-only analysis; no tracer behaviour changes)

## Why this, and why now

Three walker-level fixes are spent. Tangent smoothing, bounded coasting and seed non-maximum
suppression were implemented, measured under a pre-registered contract, and reported in
`reports/fiber_tracer_improvement.md`: no cube cleared its connected-components floor on either
metric, and connected components still wins raw ERL by 4.6-6.6x.

Two findings from that work motivate this one.

**The gain we did get was abstention, not tracing.** At the shipped `tangent_window=5`,
`high_curvature` stops *rose* against the window-1 baseline — 750 → 876 (+17%) on
`s1_00497_01497_03997_256` and 664 → 738 (+11%) on `s1_00497_02497_02997_256`. A longer window
makes the reference tangent lag, so gently curving fibers trip the turn test more often. Walks
became shorter and more numerous (splits rose on five of six cubes) and committed fewer merges,
which merge-penalized ERL rewards. Correction published 2026-08-01.

**Coverage was never the problem.** It sits at 0.602-0.697 across cubes: the tracer *finds* the
fibers. It cannot hold one identity along them.

Together these say further walker tuning will keep buying ERLpen through abstention while
fragmentation — which this project's own analysis calls "the entire problem" — gets worse. Before
building anything else, one unmeasured assumption underlies every walker fix attempted so far:
**that the orientation field is accurate enough to follow.** It has never been checked.

## The measurement

For every in-bounds ground-truth node in all six cubes, compare:

- **True tangent** — the local direction along the hand-traced polyline, from the node's
  neighbours in the fiber's edge graph.
- **Predicted tangent** — `dirs[z, y, x]` from `fiber_direction(hessian(P))`, where `P` is the
  `scrollprize/fiber_hz_vt` probability volume, computed through the same code path
  `bench_cli.cmd_trace` uses (`gauss_sigma=2, sigma=3`).

Angular error is taken **mod 180 degrees**. An orientation field is defined only up to sign, so a
signed comparison would report perfectly good tangents as ~180-degree failures. This is the same
sign ambiguity `_direction_at` and the smoothing code already handle, and getting it wrong here
would invalidate the whole result.

Nodes where `valid[z, y, x]` is False are reported as a separate **coverage-of-field** statistic
rather than silently dropped: a field that is accurate but undefined at 30% of fiber nodes is a
different problem from one that is defined everywhere and wrong.

## What the answer decides

The walker's turn limit is `max_angle_deg = 25`. Read against that:

| median error | reading | implication |
| --- | --- | --- |
| well above ~25 deg | the field cannot support any walker | every termination rule is a band-aid; multi-scale Hessian or a structure tensor becomes the target |
| a few degrees, thin tail | the field is fine | greedy sequential walking is the wrong algorithm; global assembly is the target |
| small median, fat tail | isolated bad voxels dominate | this is what coasting was supposed to fix and did not — understand why before anything else |

This is a genuine three-way fork, and the outcome is not predicted here. Whatever it says is the
result.

## Secondary cuts

Each answers a question the tracer work has been guessing at:

1. **Error versus distance to the fiber centreline.** Does the field degrade off-axis? Bears
   directly on whether ridge-peaked seeding matters, and on whether `claim_radius` is claiming
   territory where the orientation is unreliable.
2. **Error versus local ground-truth curvature.** Separates "the field is noisy" from "the field
   is fine but fibers genuinely bend more than 25 degrees per step". If it is the latter,
   `max_angle_deg` is simply mis-set, and that is a one-line change this work has been stepping
   around.
3. **Per-cube, including the cross-scroll cube.** Does field quality explain why some cubes are
   harder? `s1_08997_02997_02497_256` has the largest floor gap (75.1) and
   `s5_03997_01497_03997_256` is a different scroll.

## Scope

**In:** a read-only analysis script and a report.

**Out:** any change to `trace.py`, any new mechanism, any tuning, anything touching the frozen
configuration or a published result. This produces a measurement, not an improvement.

The script reuses `parse_nml`, `hessian` and `fiber_direction` as `cmd_trace` calls them, so it
characterises the field the tracer actually consumes rather than a reimplementation. Fiber
probability volumes are already cached in `local_data/fiber_skeletons/*_fiberprob.npy`.

## Ground-truth tangent: the one real subtlety

A hand-traced node's tangent is estimated from its neighbours in the fiber graph, and the
estimate is only as good as the annotation's spacing. Three cases must be handled explicitly
rather than averaged over:

- **Interior node, two neighbours:** central difference between them.
- **Endpoint, one neighbour:** forward or backward difference.
- **Branch node, three or more neighbours:** **excluded**, and counted. A branch point has no
  single well-defined tangent, and silently picking one would inject fake error.

Node spacing is not uniform, so report the spacing distribution alongside the errors. If typical
spacing is large relative to fiber curvature, the "true" tangent is itself smoothed and the
measured error is an upper bound — which must be stated rather than discovered later.

## Testing

- Synthetic check with a known answer: a straight tube along a fixed axis with a hand-built
  orientation field must yield ~0 degree median error; the same field rotated by a known angle
  must recover that angle. This catches a wrong axis convention, which is the most likely defect
  and would otherwise look like a plausible research finding.
- A sign-ambiguity test: negating the predicted field must not change any reported error.
- A branch-node test: a synthetic Y-junction must exclude its branch node and report the count.
- The existing fiber suite must still pass unchanged, since nothing in `trace.py` moves.

## Success criteria

1. Median, p90 and p99 angular error reported per cube and pooled, against the 25-degree limit.
2. Field-undefined rate at ground-truth nodes reported separately from error.
3. All three secondary cuts reported.
4. Branch-node and endpoint handling disclosed with counts, and node-spacing distribution
   reported so the upper-bound caveat is visible.
5. A stated verdict naming which of the three forks the data supports, written before any
   follow-on work is designed.
6. No file under `src/vesuvius_autoresearch/fibers/` modified.
