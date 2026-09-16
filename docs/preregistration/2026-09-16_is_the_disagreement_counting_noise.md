# Pre-registration: is the residual seed disagreement counting noise rather than relocation?

**Written 2026-09-16, before the statistic is computed.**

## The question

`reports/normal_separation_contributes_but_does_not_explain.md` found normal surface separation to be
a real contributor (median ρ = −0.117) and a small one, leaving most of the between-seed disagreement
unexplained. It also found the disagreement **concentrated in sparse, low-ink bins**: about half the
ink-bearing bins are one-armed, yet they carry only 14–20% of the ink.

That admits a duller explanation than any mechanism: **small bins disagree because they are small.**
If per-bin ink behaves like a count, its seed-to-seed scatter grows as **√mean**, and bins with little
ink will flip between "present" and "absent" without anything having relocated.

Distinguishing that from genuine relocation matters, because the two license opposite conclusions. If
it is counting noise, the instability is substantially a measurement artefact of binning and the
r ≈ 0.70 placement figure understates how much the pipeline actually agrees. If it scales
multiplicatively, something is moving ink in proportion to how much is there, which is relocation.

## Design

Render-clean arms only (`s4–s9`, `be09a8503`), three disjoint pairs — `s4–s7`, `s5–s8`, `s6–s9` — the
same pairs and the same (z, θ) binning as the normal-separation study, axis derived from the data.

For bins with ink in **both** arms:

* `m` = mean ink of the two arms in that bin
* `d` = |ink_A − ink_B|

Fit `log d = a + b · log m` by least squares over bins with `m > 0` and `d > 0`.

**The exponent `b` is the discriminator:**

| b | interpretation |
|---|---|
| ≈ 0.5 | **Poisson-like.** Scatter grows as √mean: counting noise. |
| ≈ 1.0 | **Multiplicative.** Scatter proportional to content: relocation or gain variation. |

## Decision rule, fixed now

On the **median `b`** across the three pairs:

| median b | conclusion |
|---|---|
| **b < 0.65** | **COUNTING NOISE DOMINATES.** The residual disagreement is substantially a binning artefact; r ≈ 0.70 understates pipeline agreement, and "placement instability" needs restating in those terms. |
| **0.65 ≤ b < 0.85** | **MIXED.** Both contribute; reported as such, with no claim that either dominates. |
| **b ≥ 0.85** | **RELOCATION.** Scatter tracks content, so ink is genuinely moving. Counting noise is excluded as the main explanation and the mechanism question stays open. |

## Prediction, fixed now

**b between 0.65 and 0.85 — MIXED**, and if forced to one side, nearer the counting-noise end.
Reasoning: the one-armed bins being ink-poor is exactly what counting noise predicts, but the count
itself reproduces to 1.2%, which a purely Poisson process at these totals would beat easily — so
something systematic is present too. Recorded so it can be a miss.

## Controls

* **A shuffled control**: pair bins at random across arms and refit. The observed `b` must differ from
  the shuffled distribution, or the fit is measuring the binning rather than the data.
* **Reported alongside**: the number of bins entering each fit, and the fraction dropped for `d = 0`.
  Dropping exact ties silently would bias `b` upward.
* **Axis derived, not assumed.**

## What this cannot show

It cannot identify what the systematic part *is*, only bound how much room is left for it. And it is
three pairs from one scroll region, as with everything else in this line.
