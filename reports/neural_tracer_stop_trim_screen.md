Trimming villa's neural-tracer fibers at their confidence stops buys little precision; even an oracle trim removes only 16% of the off-reference length (exploratory screen after finding 101, not registered; 2026-11-05)

Finding 101 found that two-thirds of the tracer's interior confidence stops lie off the hand-traced fibers. It said this
"does not show that a stop or trim rule would help". This screen asks whether one would, on development data only. It
decides nothing.

**The rule.** In each stock run of findings 97/98 (villa `ccb431818`, `scrollprize/fiber_single_small` at its
defaults, 128 voxels of CT context), every interior, unlinked confidence-stop end loses its last k voxels of arclength.
These are finding 101's real stops: no link, at least 6 voxels from a cube face. A piece left shorter than the runs'
`--min-length` (48 points) is dropped, as villa drops short pieces when it writes them. A trim applied after tracing
changes no other trace, so these runs give its result exactly, with no GPU. ScrollGT re-scores each cube at tolerances 2
and 4.

**The ceiling.** No tracer could apply the oracle trim: it cuts each such end back to its last point within 2 voxels of
a hand-traced fiber, and drops a piece with none. It bounds what any trim at confidence stops could buy.

**The data.** The eleven in-sample cubes. With k = 0 the screen reproduces finding 104's recorded baseline rows on all
eleven, at both tolerances. The ten held-out cubes were not read, so a later rule can still be tested on them. Script
`scripts/neural_tracer_stop_trim_screen.py`, record `reports/evidence/neural_tracer_stop_trim_screen_2026-11-05.json`.

## Result

Median change over the eleven cubes at tolerance 2, with each cube's ERLpen (merge-penalized ERL) after over before:

| trim | precision | coverage | ERLpen | ERLpen rose on | merges (all cubes) |
|---|---|---|---|---|---|
| 10 voxels | +0.0028 | −0.0051 | 0.992× | 0 of 11 | 721 → 696 |
| 20 voxels | +0.0053 | −0.0099 | 0.984× | 0 of 11 | 721 → 682 |
| 40 voxels | +0.0088 | −0.0178 | 0.966× | 1 of 11 | 721 → 657 |
| oracle | +0.0187 | −0.0016 | 0.999× | 3 of 11 | 721 → 708 |

* **A fixed trim loses about twice the coverage it gains in precision, and costs continuity.** ERLpen fell on every
  cube at 10 and 20 voxels. Merges fell 3.5–8.9%. At tolerance 4 the pattern is the same: at 20 voxels precision +0.0079,
  coverage −0.0155.
* **Even the oracle buys a median 0.019 of precision** (+0.011 to +0.057; above 0.03 on five cubes), for a median
  0.0016 of coverage.
* **Most off-reference length is not at confidence stops.** Over all eleven cubes the oracle removes 16.0% of the
  off-reference length at tolerance 2 (26.7% at tolerance 4), and 9.5% of all traced length. The other 84% lies
  elsewhere on the traces: mid-trace, or behind ends that stopped for another reason.

## What it changes

**Trimming at confidence stops is closed as a precision lever for this tracer.** A fixed trim is a bad trade, and a
perfect one is worth under 0.02 of median precision. Finding 104 asked for a rule that decides whether a continuation is
on the fiber before keeping it; this screen bounds the matching rule at the stops, and the bound is small.

**Precision for this tracer lies mid-trace.** villa #2377 (open) ends villa's C++ beam tracer before it slides onto a
neighbouring fiber. It reads presence, agreement between the fiber's direction and the step, and a stronger fiber to
the side, at every step rather than at stops. Its author reports that most bad beam traces were ones that "slid onto
the next fiber over and just kept going". The 84% here is consistent with the same failure in the neural tracer, but
this screen does not locate it. Testing that would need per-step features along the traces; these runs record only
points and stop reasons.

## What it cannot say

* **Eleven in-sample cubes from Scrolls 1 and 5,** one checkpoint at its defaults, one context protocol.
* **The reference is one hand tracing per cube.** "Off the reference" includes real fibers no one traced, as ScrollGT's
  precision does.
* **The oracle reads the reference.** It is a ceiling, not a rule.
