# Pilot: does varying the flow bounds move strip extent enough to test anything?

**Written 2026-09-19. A pilot to size a study, not the study.**

## Why a pilot and not the study

`reports/the_strip_area_test_was_uninformative.md` failed for one reason: the predictor barely moved.
Strip area spanned **6.5%** across 39 arms while ink spanned 27%, so the log-log slope had a 95% CI of
[−0.36, +1.87] — every branch of its own decision rule inside the interval.

The fix is arms with **deliberately** varied extent. The full study is six arms
(~3 h fit + ~2.5 h render each, **≈33 h**). Committing that before knowing whether the manipulation
produces usable variation would repeat today's mistake at 33× the cost.

## What the pilot asks

**Does changing `model_flow_bounds_radius` move `total_pixels` materially more than seed noise does?**

Seed noise on strip area is already measured: **CV 0.0199** across fits differing only in seed
(`reports/outer_winding_noise_floor.md`). That is the floor any deliberate manipulation must clear.

## Design

**Two arms, ~11 h total.**

* `bounds_pilot_lo` — `model_flow_bounds_radius` reduced 15% from default
* `bounds_pilot_hi` — increased 15%

Everything else identical to `curbase`: same dataset, same `VILLA_REF=be09a8503`, same winding range
w120–129, same render scale. Seed fixed at 1 for both, so the pair differs in exactly one config key.

Both arms' `total_pixels` are compared against the `curbase_s1–s9` distribution, whose area CV is
known.

## Decision rule, fixed now

| |Δ area| between lo and hi | conclusion |
|---|---|
| **≥ 15%** | **GO.** Roughly 7× the seed-noise CV and more than twice the incidental spread that sank the last study. The six-arm study is worth its 33 h. |
| **6–15%** | **MARGINAL.** Better than the 6.5% incidental spread but not decisively; the six-arm study would need more arms than budgeted, and that is a fresh decision rather than an automatic go. |
| **< 6%** | **NO GO.** The manipulation does not move extent more than fitting already does by accident. The question is not answerable by this route, and the direction closes without spending the 33 h. |

## Prediction, fixed now

**MARGINAL, 6–15%.** Reasoning: a bounds parameter sounds like it should directly set extent, but the
fit is a global optimisation and the surface it produces is constrained by the data as much as by the
bound — a 15% bound change may be largely absorbed. Recorded so it can be a miss; four of my last five
predictions in this line were wrong or untestable.

## What the pilot cannot show

Nothing about the objective. **It measures only whether the knob moves the predictor**, which is the
prerequisite the failed study lacked. Two arms cannot say anything about ink, and this registration
makes no claim that they can.

## Cost and status

**~11 h of otherwise-idle compute, and it is not launched.** Memory is the binding constraint
(31.3 GiB against a ~28.5 GiB render peak) so the arms must run sequentially, and
`complete_triplet_c.sh`-style chaining plus `recover_arm.sh`'s precheck already handle that.
