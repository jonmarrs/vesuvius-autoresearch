# Sampling density tracks the ink disagreement strongly — and not the way the hypothesis predicted

**2026-09-18.** Registered in `docs/preregistration/2026-09-18_sampling_density_explains_the_remainder.md`,
written before the statistic was computed.

## Result

Render-clean arms (`s4–s9`), three disjoint pairs, same binning and derived axis as the three prior
studies. Slope of `log(ink_A/ink_B)` on `log(n_A/n_B)`, where `n` is the count of surface grid samples
per volume bin:

| pair | bins | log density ratio p5/p95 | **slope s** | shuffled 95% | |
|---|---:|---|---:|---|---|
| s4–s7 | 2,429 | −0.247 / +0.234 | **+0.656** | [−0.239, +0.342] | differs |
| s5–s8 | 2,753 | −0.233 / +0.199 | **+1.252** | [−0.247, +0.275] | differs |
| s6–s9 | 2,323 | −0.225 / +0.249 | **+1.952** | [−0.294, +0.251] | differs |

**Median s = 1.252 → DENSITY DOMINATES** by the registered rule. **Prediction (SUBSTANTIAL,
0.30–0.70): MISSED**, in the direction of a stronger association.

The control that the registration required to run *first* passes: `log(n_A/n_B)` spans roughly ±0.23
at the 5th/95th percentiles, so the arms genuinely differ in sampling density and there is variation
to regress on. This is not an uninformative test.

## Why the headline overstates it

**The three slopes disagree by a factor of three (0.656 → 1.952), and two exceed 1.0.**

A pure sampling-density artefact predicts `s = 1` exactly: if a bin receives twice the grid samples,
it contributes twice the ink pixels for the same papyrus. **`s = 1.95` means doubling the density
nearly quadruples the ink, which density alone cannot do.** So while the association is real,
strong and clears every null, the *mechanism* named in the registration does not account for its
size or its instability.

By the registered rule this reads DENSITY DOMINATES. Taken as a claim about mechanism, it does not,
and reporting only the verdict would misrepresent what the numbers show.

## The leading alternative, named but not tested

**Partial coverage is a confound that would produce exactly this.** Bins at the edge of the strip, or
where a fit's surface does not extend, receive both fewer grid samples *and* less ink — not because
stretching inflated anything, but because there is less surface there. That drives density and ink
together and can push the slope past 1 when coverage differences are large.

**This was not tested, deliberately.** Restricting to full-coverage bins is a new analysis, and
running it now — after seeing a result that needs rescuing — is the sweep this project's
registrations exist to prevent. It belongs in its own registration with its own prediction, or not at
all.

## What the ledger can and cannot claim

| contribution | status |
|---|---|
| scorer | excluded — 0.0009% |
| tangential slide | excluded |
| depth/layer sampling | excluded — ρ = −0.006 |
| normal separation | present, small — ρ = −0.117 |
| small-bin counting noise | present, substantial — b = 0.72 |
| **sampling density / coverage** | **strongly associated, mechanism unresolved** — s = 0.66–1.95 |

The remainder is **no longer unattributed, but it is not explained either.** Something about how much
surface each arm places in a bin dominates the per-bin ink ratio. Whether that is parameterisation
stretch, partial coverage, or both, this test does not separate.

## Limits

* The registered statistic cannot separate a genuine difference in surface *extent* from a difference
  in parameterisation *density* — both change `n`. That limit was stated in advance and is the one
  that bites.
* Slope instability across pairs means the median is a poor summary; the range is the honest figure.
* Three pairs, one scroll region.
