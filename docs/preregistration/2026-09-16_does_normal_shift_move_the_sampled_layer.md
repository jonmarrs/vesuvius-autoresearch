# Pre-registration: does normal surface separation move which layer the detector reads?

**Written 2026-09-16, before the statistic is computed.**

## The chain this tests

Three results constrain the placement instability so far: the scorer is excluded (0.0009%), a
tangential slide is excluded (offsets incoherent), normal separation contributes weakly
(median ρ = −0.117), and per-bin scatter grows as `mean^0.72` — **faster than counting noise**, so
something systematic scales with ink content.

This tests the mechanism that would produce exactly that: **a normal surface shift changes which
papyrus depth the detector samples.** Ink is layer-specific, so moving the sampled stack changes how
much ink is found without moving anything tangentially — invisible to the angular test, and scaling
with content rather than with √content.

**The data supports it directly, which is why this is worth doing now.** Each arm retains
`ink/00–04.tif`: **five depth layers** spanning the full strip, verified distinct — adjacent layers
correlate 0.978, the most separated 0.758, with mean intensity declining monotonically 17.03 → 15.11.
That is a real depth gradient, not five copies.

## Design

Render-clean arms only (`s4–s9`, `be09a8503`), the same three disjoint pairs and the same (z, θ)
binning and derived axis as the two prior studies.

Per arm, per bin: **layer centroid** `c = Σ(k · ink_k) / Σ(ink_k)` over `k = 0…4`, the ink-weighted
mean depth index. Per pair: `Δc = |c_A − c_B|`, and the **signed** `c_A − c_B`.

Two questions, both fixed now:

1. **Primary — does normal separation move the sampled layer?** Spearman ρ between per-bin normal
   separation `|r_A − r_B|` (as measured in the normal-separation study) and `Δc`.
2. **Secondary — is there a systematic direction?** Mean signed `c_A − c_B` per pair, against a
   shuffled control. A consistent sign across pairs would mean one arm systematically samples deeper.

## Decision rule, fixed now, on the median ρ of question 1

| median ρ | conclusion |
|---|---|
| **ρ ≥ +0.30** | **CHAIN SUPPORTED.** Normal separation moves the sampled layer, which is a mechanism that scales with content and explains the faster-than-Poisson scatter. |
| **+0.10 ≤ ρ < +0.30** | **WEAK.** Present but small; reported as a contributor, not the explanation. |
| **−0.10 < ρ < +0.10** | **REFUTED.** Surface separation does not move the sampled depth, so the layer route is not how normal displacement acts, and the systematic component remains unattributed. |
| **ρ ≤ −0.10** | **ANOMALOUS.** Larger separation associated with *less* layer shift makes no mechanical sense; treat as a bug in the statistic, not a finding. |

## Prediction, fixed now

**ρ ≥ +0.30, CHAIN SUPPORTED.** Reasoning: the two surfaces sit a median 3.5–5.0 voxels apart, and
five layers sample a depth range plausibly of that order, so a separation of that size should move the
centroid materially. Recorded so it can be a miss — and the honest counter-case is that the render
resamples *relative to each arm's own surface*, in which case both arms centre their stack on their
own sheet and the centroid difference could be near zero regardless of where those sheets sit.

**That counter-case is the more interesting outcome**, because it would mean each arm reads its own
surface consistently and the disagreement is about *which surface is right*, not about depth sampling.

## Controls

* **Shuffled control** on both questions; the observed value must exceed it.
* Bins with ink in **both** arms only, with the excluded count reported.
* Axis **derived**, not assumed.
* Layers verified distinct **before** the test, not assumed from filenames.

## What this cannot show

It cannot say which arm's surface is correct — there is no positional ground truth on PHercParis4,
as recorded elsewhere in `reports/`. It measures whether the two disagree about depth, not who is right.
