# Pre-registration: do same-winding constraints improve *reading*, or only geometry?

**Written 2026-09-06, before any arm is fitted.** Dataset variant built and smoke-tested; no
scored arm exists.

## The question, and whose it is

villa's `39_winding_annotations.md` states the strategy plainly:

> "the fastest way to unroll scrolls at scale is to develop methods for creating winding constraints
> that are precise and fast enough to use widely"

and concedes the open quantity:

> "We don't know the exact minimum amount of winding evidence necessary for a given scroll ahead of
> time, but we know it is certainly *much less than full wrap segmentation*."

Five projects in villa's community catalogue generate or evaluate winding constraints
(winding-sync, winding-ruler, FASP, spiralcheck, axiosdevs' annotator). **Every one validates on
geometry.** We hold the only ink-endpoint rig, and our two completed studies measured geometry and
ink moving independently — twice, in opposite directions. So the untested question is whether
winding evidence buys *reading*, not whether it buys a better-looking fit.

## Manipulation

`data/spiral_s1` ships three constraint files, all read by the fit:

| file | constraints |
|---|---:|
| `same_windings.json` | 154 collections, **5,413 points** |
| `relative_windings.json` | 300 collections, 2,173 points |
| `abs_winding.json` | 59 points |

**ABLATED arm: `same_windings.json` emptied** (5,413 constraints removed), everything else identical.
**CONTROL: the six existing full-input baselines** (`baseline01`, `seed02`-`seed06`), already fitted
and scored, same dataset and config apart from seed.

## Why this ablation and not the obvious one

Ablating `loss_weight_abs_winding` was tried and **rejected before registration**: absolute winding
numbering comes solely from `abs_winding.json`, so zeroing it unanchors the numbering and the
w120-w129 strip stops meaning the same papyrus across arms. Measured drift in median winding radius,
200-step smoke fits:

| manipulation | mean drift at w120/124/129 |
|---|---:|
| `loss_weight_abs_winding` = 0 | **-71.7 vx** — fatal |
| 10 of 59 anchors kept | -15.8 vx |
| **this ablation: all same-windings removed** | **+5.60 vx** |

`abs_winding.json` is untouched here, so numbering stays anchored. +5.6 vx is under half a winding of
median-radius spacing (~12.6 vx). **Measured at 200 steps, not at convergence** — that limitation is
recorded now, not discovered later.

## Endpoints

* **Primary: `total_fg_pixels`** on w120-w129, Welch two-sided, alpha = 0.05, ABLATED vs BASELINE.
* **`satisfied_area_fraction` is REPORT-ONLY here, and is NOT an endpoint.** This differs from our
  previous two registrations and the reason matters: satisfaction measures how well a fit satisfies
  **the inputs it was given**. Removing 5,413 constraints removes competing demands, so the metric
  can rise *because there is less to satisfy*. The 200-step smoke already shows this (0.13466 ->
  0.13766). Comparing it across arms with different input sets is not like-for-like, and treating a
  rise as "better geometry" would be an error.

## Decision rule

| outcome (ABLATED vs BASELINE) | conclusion |
|---|---|
| ink **down**, p < 0.05 | Same-winding constraints **improve reading**. villa's emphasis is validated on the endpoint that matters, and the 5,413 constraints are earning their cost. |
| ink **up**, p < 0.05 | Removing them *improves* reading. Surprising; would need a mechanism before it is believed. |
| ink **null** | No reading effect larger than ~10%. Combined with any geometry move, a further instance of the two metrics decoupling — and directly relevant to "how much winding evidence is necessary". |

Power: at 3 vs 6 and the measured outer CV of 0.0421, 80% power reaches about **8.3%**
(`2.802 * 0.0421 * sqrt(1/3 + 1/6)`). A null must be reported as "no effect larger than ~8.3%",
never "no effect". Tighter than the 9.6% of the two 3v3 studies, because the control already has six
arms.

*Corrected before any arm was fitted: this first read 7.9%, which was arithmetic I did not check. The
test pinning `mde(3, 6)` failed against the registration and the registration was wrong.*

## Prediction, fixed now

**I predict ink is null and `satisfied_area` RISES.** Reasoning: satisfaction gets easier with fewer
constraints to satisfy, and our two prior studies found ink indifferent to large geometry moves. If
that holds it is the third such decoupling, and it would say these constraints buy geometry rather
than reading — which is worth knowing before anyone automates producing more of them.

Recorded so it can be a miss. I have been wrong on three of six registered predictions, and one
design in this same area had to be discarded for circularity before reaching registration.

## Cost

Three arms at the observed ~5.3 h each: **about 16 hours**, because the control already exists.
Fits pinned to villa-spiral `6847063f`, renders to `5479453a`, both enforced by
`tests/test_villa_spiral_refs_pinned.py`. Analysis committed before the first fit starts.
