# Pre-registration: is it coverage or parameterisation density?

**Written 2026-09-18, before the statistic is computed.** Follow-up to
`reports/sampling_density_tracks_ink_but_not_proportionally.md`, which found the per-bin ink ratio
strongly associated with the sample-count ratio (slopes +0.656, +1.252, +1.952) and stated that it
**cannot separate surface extent from parameterisation density, because both change the sample count.**
That separation is this study.

## Why it matters beyond the ledger

If the association is **parameterisation density** — one arm's grid locally finer over the same
papyrus — it is a measurement artefact of comparing two stretchings through a shared volume grid.

If it is **partial coverage** — one arm's surface simply not extending as far — then
`total_fg_pixels` is partly counting *how much surface was fitted* rather than how well it reads.
That is a property of **villa's own objective**, and it would sit alongside the four documented cases
where geometry and recovered ink move independently.

The two license different conclusions about a metric other people optimise, which is why this is worth
a sixth test in a line with otherwise diminishing returns.

## Design

Render-clean arms (`s4–s9`), the same three disjoint pairs, same (z, θ) binning and derived axis as
the four prior studies. Same primary statistic as the parent study: the least-squares slope `s` of
`log(ink_A/ink_B)` on `log(n_A/n_B)`.

**Stratify by how well-covered a bin is in both arms.** Let `c = min(n_A, n_B)`, the sample count of
the sparser arm — a bin is well covered only if *both* arms put surface there. Split bins into
**quartiles of `c`**, and fit `s` within each quartile separately.

* **Q1** (lowest `c`) — edge and partial-coverage bins.
* **Q4** (highest `c`) — bins both arms cover fully.

Coverage effects live where `c` is small and vanish where both arms are fully present. Parameterisation
density does not: two grids can differ in fineness anywhere, including in the interior.

## Decision rule, fixed now, on `s` in Q4 (the well-covered bins), median across pairs

| Q4 median s | conclusion |
|---|---|
| **s < 0.30** | **COVERAGE.** The association is an edge effect. `total_fg_pixels` is partly measuring fitted surface extent, and the parent study's "density" reading is withdrawn. |
| **0.30 ≤ s < 0.70** | **BOTH.** Coverage carries part, density carries part; neither is dismissed. |
| **s ≥ 0.70** | **DENSITY.** The association survives where both arms are fully present, so it is not an edge effect, and parameterisation density stands as the parent study named it. |

**Reported regardless:** `s` in all four quartiles for all three pairs, and the bin counts. A monotone
decline of `s` from Q1 to Q4 is itself evidence for coverage whatever the Q4 value lands at, and will
be stated if seen.

## Prediction, fixed now

**Q4 median s < 0.30 — COVERAGE.** Reasoning: the parent study's slopes *exceeded 1.0* on two pairs,
which parameterisation density cannot produce (twice the samples is at most twice the ink pixels),
whereas coverage can, because `n` and ink fall to zero together at a surface edge. The super-
proportional slope is the signature of an edge effect.

Recorded so it can be a miss. My last two predictions in this line were both wrong — one refuted
outright, one missed toward a stronger effect.

## Controls

* **Shuffled control within each quartile**; a slope that does not clear its own stratum's null is
  reported as null for that stratum.
* **Bin counts per quartile reported**, so a stratum too thin to fit is visible rather than silently
  driving the median.
* Axis derived, not assumed.

## What this cannot show

It cannot establish that coverage differences are *wrong* — an arm whose surface genuinely extends
further may deserve more ink. It measures whether the ink ratio is driven by extent, not whether that
is desirable.
