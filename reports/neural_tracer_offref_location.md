Where villa's neural-tracer fibers are off the hand-traced reference: at tolerance 2, two-thirds of that length lies beside the fiber the trace follows or on fibers no reference passes, and a third is departure-shaped (exploratory, after the stop-trim screen, not registered; 2026-11-05)

The [stop-trim screen](neural_tracer_stop_trim_screen.md) found that even an oracle trim at the tracer's confidence
stops removes only 16% of its off-reference length, and could not say where the rest lies. This places all of it, on
development data only. It decides nothing.

**The method.** The same stock runs (findings 97/98: villa `ccb431818`, `scrollprize/fiber_single_small` at its
defaults, 128 voxels of CT context), on the eleven in-sample cubes. Inside the cube, a traced point is on the reference
if the voxel it rounds to lies within the tolerance of a voxel ScrollGT marks as reference (the screen's oracle test).
Each point is also assigned its nearest reference fiber, and carries half of each segment it touches. Pooled, this
point-based precision reproduces ScrollGT's pooled precision for the same runs: 0.4236 against 0.4187 at tolerance 2,
and 0.6976 against 0.6927 at tolerance 4 (the gate allows 0.01). Every off-reference voxel of length then goes to
exactly one place:

* **beside the same fiber**: an interior run of off-reference points whose on-reference neighbours on both sides are
  nearest the same reference fiber;
* **a whole fiber off the reference**: a fiber with no on-reference point;
* **a tail**: off-reference points before a fiber's first on-reference point or after its last, by that end's stop;
* **between two fibers**: an interior run whose neighbours are nearest two different reference fibers.

Script `scripts/neural_tracer_offref_location.py`, record `reports/evidence/neural_tracer_offref_location_2026-11-05.json`.

## Result

Share of the off-reference length, pooled over the eleven cubes:

| place | tolerance 2 | tolerance 4 |
|---|---|---|
| beside the same fiber | 39.2% | 22.1% |
| a whole fiber off the reference | 27.3% | 32.0% |
| a tail | 30.1% | 37.1% |
| between two fibers | 3.4% | 8.8% |

* **The largest share at tolerance 2 lies beside the fiber the trace is following.** It is 33,047 short runs. Their
  length falls from 226,530 voxels at tolerance 2 to 67,058 at tolerance 4, so most of it is within 4 voxels of that
  fiber. It is placement, not departure.
* **1,233 fibers never come within 2 voxels of the reference.** The reference is one hand tracing per cube. Whether
  these are real fibers no one traced, duplicates or false traces, this cannot say.
* **Departure-shaped length, the tails and the runs between two fibers, is 33.5% at tolerance 2** (45.9% at
  tolerance 4). At tolerance 2, tails behind the screen's ends (interior, unlinked confidence stops) are 5.1% of the
  off-reference length. Tails behind collision stops (`owned_or_live`) are 11.5%, and tails at or beyond the cube's
  faces (`bounds`, or an end outside the cube) are 12.4%.
* **The ceiling for a departure rule.** If a rule cut exactly the departure-shaped length and nothing on the
  reference, pooled precision would rise from 0.4236 to 0.525 at tolerance 2, and from 0.6976 to 0.810 at tolerance 4.

**Where each point set sits on the CT.** Each set was shifted by up to 3 voxels along each axis, and the mean CT
(trilinear) taken at its points. At the traced points that mean peaks within 0.10 voxel of no shift on every axis,
pooled. At the reference's points it peaks 0.53 voxel off in y (the same sign on 9 of 11 cubes), and within 0.13 in z
and x. So the tracer shows no systematic offset from the bright CT structure, and the reference does, in y.

## What it changes

**A departure rule for this tracer could reach at most a third of its tolerance-2 off-reference length.** villa #2377
proposes a per-step stop score for the C++ beam tracer, and villa #2451 made reverse checks the default in that
tracer's streaming. A rule like either would be worth at most 0.101 of pooled precision here, and only if it cut
nothing on the reference. That bounds what a GPU test of such a rule could show.

**At tolerance 2, ScrollGT's precision for this tracer mostly measures placement.** Over a third of the off-reference
length lies within a few voxels of the fiber being followed. Tolerance 4 is the better reading of departures.

## What it cannot say

* **Eleven in-sample cubes from Scrolls 1 and 5,** one checkpoint at its defaults, one context protocol.
* **The reference is one hand tracing per cube.** A tail past the last on-reference point can be a real fiber going on
  where the hand tracing stopped. A whole fiber off the reference can be a real fiber no one traced.
* **The brightest CT is not the fiber's centre.** The CT peaks say where each point set sits on the bright structure,
  not which set is on the fiber. This cannot tell whether the reference's offset in y is where the hand tracing sits
  on the sheet or an offset in its frame.
