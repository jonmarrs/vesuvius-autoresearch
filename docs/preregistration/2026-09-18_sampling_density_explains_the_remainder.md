# Pre-registration: is the systematic remainder a sampling-density artefact?

**Written 2026-09-18, before the statistic is computed.**

## The candidate, and why it fits what is left

The ledger after four tests: scorer excluded, tangential slide excluded, depth sampling excluded,
normal separation present but small (ρ = −0.117), counting noise present and substantial (b = 0.72),
and a **systematic remainder that scales with ink content and acts before the detector** — that last
constraint from finding 41, which showed each arm reads its own surface faithfully.

**Sampling density fits all three constraints.** Ink is predicted on the *flattened strip in pixels*
and then attributed to volume (z, θ) bins. Two arms are independent fits with independent
parameterisations, so they need not place the same number of flat-grid pixels into the same volume
bin. Where one arm's parameterisation is locally denser, it contributes more ink *pixels* for the same
physical papyrus — an inflation **proportional to how much ink is there**, arising in the fit rather
than the detector, and with nothing to do with depth.

If this is large, part of what has been called "placement instability" is an artefact of comparing
two differently-stretched parameterisations through a shared volume grid.

## Design

Render-clean arms (`s4–s9`), the same three disjoint pairs, the same (z, θ) binning and derived axis
as the three prior studies.

Per arm, per bin, two quantities already computed in this line:

* `n` — the **count of surface grid samples** falling in the bin (sampling density)
* `i` — binned ink

For bins with `n > 0` and `i > 0` in both arms, and with all four quantities log-transformed:

* **density ratio** `log(n_A / n_B)`
* **ink ratio** `log(i_A / i_B)`

**Primary statistic: the least-squares slope `s` of `log(i_A/i_B)` on `log(n_A/n_B)`.**

`s ≈ 1` means ink tracks sampling density one-for-one — the disagreement in those bins is density, not
reading. `s ≈ 0` means density differences do not propagate to ink at all.

## Decision rule, fixed now, on the median `s` across pairs

| median s | conclusion |
|---|---|
| **s ≥ 0.70** | **DENSITY DOMINATES.** Most of the systematic remainder is a parameterisation artefact. The placement figure must be restated as a comparison of two stretchings, and the ink metric itself is density-sensitive. |
| **0.30 ≤ s < 0.70** | **SUBSTANTIAL.** A real and large contributor, but not the whole remainder. |
| **0.10 ≤ s < 0.30** | **MINOR.** Present, small; the remainder stays mostly unattributed. |
| **s < 0.10** | **REFUTED.** Sampling density does not explain the remainder, and a fourth route closes. |

## Prediction, fixed now

**s between 0.30 and 0.70 — SUBSTANTIAL.** Reasoning: the mechanism is real and unavoidable — two
independent parameterisations cannot place identical pixel counts per volume bin — so `s` should be
clearly positive. But binning at 96 × 256 averages over many grid samples, which damps the effect, and
`b = 0.72` already showed the scatter is not purely proportional. Recorded so it can be a miss; the
last prediction in this line was one.

**Counter-case worth naming**: if the renderer normalises ink per unit surface area rather than per
pixel, density would cancel by construction and `s ≈ 0`. That would be a REFUTED reading caused by the
pipeline being better designed than the hypothesis assumes, and should be reported that way rather
than as a null finding.

## Controls

* **Shuffled control**: permute the density ratios against the ink ratios and refit; the observed `s`
  must exceed it.
* **Reported alongside**: bins entering the fit, and the spread of `log(n_A/n_B)` — if the two arms
  have near-identical densities everywhere, there is no variation to regress on and the test is
  uninformative rather than negative. **That check comes first.**
* Axis derived, not assumed.

## What this cannot show

It cannot attribute the remainder to any *other* cause if refuted, and it cannot separate a genuine
difference in surface extent from a difference in parameterisation density — both change `n`.
