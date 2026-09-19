# The bounds pilot was stopped 40 minutes in: the knob clips the scored region, it does not reshape it

**2026-09-19.** Registered in `docs/preregistration/2026-09-19_strip_extent_pilot.md`, launched 11:01,
**stopped 11:41 after a measurement that invalidated its premise.** ~10 h of compute not spent.

## What the pilot assumed

That `model_flow_bounds_radius` at 2720 and 3680 brackets the 3200 default **symmetrically**, giving a
two-sided manipulation of how much surface the fit produces.

## What is actually true

Radius of the scored windings (w120–129) about the **umbilicus** — `umbilicus.json`, 146 control
points, interpolated per-z, not a sampled centroid:

| percentile | radius |
|---|---:|
| p50 | 2361 |
| p90 | 2811 |
| p99 | 3135 |
| max | 3301 |

| bound | share of scored surface it excludes |
|---|---:|
| **`bounds_lo` 2720** | **14.8%** |
| default 3200 | 0.5% |
| `bounds_hi` 3680 | 0.0% |

**The default is already almost non-binding.** Raising it to 3680 buys 0.5%; lowering it to 2720 cuts
away 15% of the very region the metric scores. The manipulation is **one-sided clipping**, not a
symmetric extent knob.

## Why that kills the study it was sizing, not just the pilot

The pilot would have run to completion, reported |Δ area| ≈ 15%, and read **GO** — correctly by its own
rule, and for a mechanism that does not serve the question.

The six-arm study asks whether villa's loop can raise `total_fg_pixels` by **enlarging** the strip.
Varying area by clipping answers a different and nearly tautological question: remove 15% of the
surface and you remove the ink on it, so the slope is ≈ 1 by construction. That would have been a
33-hour confirmation that cutting away papyrus loses the writing on it.

**The interesting manipulation is one that changes how much surface the fit produces *within* the
scored region** — density or coverage at fixed bounds — not one that truncates the region.
`model_flow_bounds_radius` is not that knob.

## The ordering error, again

The registration checked *reachability* — is this key tunable by the loop? — and it is. It did not
check **what the key does to the scored region**, which is one `numpy` percentile away and would have
taken two minutes before launching rather than forty minutes after.

That is the same ordering mistake recorded in `reports/label_snapping_feasibility_probe.md`, one level
along: there I asked whether the condition was reachable before designing the validation; here I asked
whether the *knob* was reachable and forgot to ask whether the *manipulation* was the one I wanted.

**What the pilot cost:** 40 minutes of GPU and nothing else. **What it saved:** the ~11 h it would have
run, and the ~33 h study it would have greenlit on a tautology.

## Status

`bounds_lo` and `bounds_hi` are **abandoned, not paused** — their fits are incomplete and their scripts
remain in `spiral_out/` for provenance only. No artifact was produced, so
`scripts/analyse_bounds_pilot.py` correctly refuses: *"not scored yet … a partial sample is refused,
not reported."*
