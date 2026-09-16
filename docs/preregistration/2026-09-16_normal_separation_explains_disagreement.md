# Pre-registration: does NORMAL surface separation explain where two seeds disagree about ink?

**Written 2026-09-16, before the statistic is computed.**

## The question, and why it is this one

`reports/ink_offsets_are_not_coherent.md` ruled out the *tangential* form of the surface explanation —
a smooth angular slide — and then named the test it did not run:

> "the surface explanation is not dead; its *tangential* form is. Testing the normal form needs a
> different statistic — **ink agreement as a function of local surface separation between the two
> arms** — which this does not attempt."

This is that test. A purely **normal** displacement moves the fitted sheet through the volume without
rotating it, changing *which voxels the detector samples* while shifting nothing angularly, so the
earlier test was blind to it by construction.

It bears on the deepest open item in this line: placement reproduces between seeds at only
**r ≈ 0.70** while the count reproduces to **1.2%**, and the mechanism has been unexplained through
two failed attempts. The scorer is already excluded — re-scoring one strip moves the count by
**0.0009%** — so the variance is in fitting or flattening, both of which move the surface.

## Design

Arms are compared in **volume coordinates**, not in flat (u,v): the arms are independent fits whose
flattened strips differ in shape (s7 16384×4430, s8 ×4700, s9 ×4570), so (u,v) does not correspond
across them. The (z, θ) binning of `scripts/compare_ink_in_volume.py` is the common frame, as used
throughout this line of work.

Per (z, θ) bin, for a pair of arms:

* **separation** — `|r_A − r_B|`, the difference in mean radial position of the fitted surface,
  where `r = hypot(x − cx, y − cy)` about an axis **derived from the sampled points**, never a
  hardcoded guess. (A hardcoded centre produced a radius effect roughly half its true size once
  already this week.)
* **agreement** — per-bin ink agreement between the two arms.

**Pairs: render-clean arms only** (`s4–s9`, all on `be09a8503`), so the render-tree confound bounded
elsewhere does not enter. Three disjoint pairs: `s4–s7`, `s5–s8`, `s6–s9`.

## Primary statistic

**Spearman ρ between per-bin separation and per-bin agreement**, across bins with ink in both arms.
Spearman rather than Pearson: neither quantity is expected to be linear or normal, and rank
correlation is what the earlier work in this line used.

Reported per pair, with the median as the summary. The three pairs share no arm, so unlike the k=2
study they are genuinely disjoint — but they sample one scroll region, so they are not independent
evidence about scrolls in general.

## Decision rule, fixed now

| median ρ | conclusion |
|---|---|
| **ρ ≤ −0.30** | **SUPPORTED.** Bins where the two surfaces sit further apart agree less about ink. Normal displacement is a real contributor, and the surface explanation survives in its normal form. |
| **−0.30 < ρ ≤ −0.10** | **WEAK.** A detectable but small contribution; reported as such, and explicitly not as the mechanism. |
| **−0.10 < ρ < +0.10** | **REFUTED.** Normal separation does not explain where seeds disagree. Combined with the tangential null, the surface explanation is then dead in both forms and the instability is elsewhere — most likely in what the detector sees at fixed geometry. |
| **ρ ≥ +0.10** | **ANOMALOUS.** Agreement rising with separation makes no mechanical sense; treat as evidence of a bug in the statistic and report it as such, not as a finding. |

## Prediction, fixed now

**ρ between −0.10 and −0.30, i.e. WEAK.** Reasoning: the count reproduces to 1.2% while placement
reproduces at 0.70, so whatever moves ink largely preserves how much there is — consistent with a
surface sliding normally through a roughly layered signal. But the earlier test found offsets
*incoherent*, which argues against one dominant geometric cause. Recorded so it can be a miss;
predictions in this project have been wrong before and the misses were the useful part.

## Validity controls

* **A shuffled control**: bin labels permuted, ρ recomputed. The observed ρ must exceed the shuffled
  distribution or the result is void.
* **Axis derived, not assumed**, and the derived value reported.
* Bins with ink in only one arm are **excluded**, and the excluded fraction reported — dropping them
  silently would bias toward agreement.

## What this cannot show

It cannot separate **fitting** from **flattening**: both move the surface, and this measures the
surface, not its cause. A positive result localises the instability to surface geometry; it does not
say which stage produced it.
