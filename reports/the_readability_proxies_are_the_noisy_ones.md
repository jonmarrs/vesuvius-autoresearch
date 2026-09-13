# The metrics that measure *reading* are the ones you cannot measure

**2026-09-13. EXPLORATORY.** Computed from `metrics.json` files already on disk across nine
current-code arms; no new compute. Corroborates
`reports/ink_placement_in_volume.md` from an independent direction.

## Seed-to-seed reproducibility of every metric villa's scorer emits

Within-arm CV across three seeds, pooled over the three current-code triplets:

| metric | curbase | nosamecur | anchor10cov | pooled CV | MDE at 3v3 |
|---|---:|---:|---:|---:|---:|
| `total_fg_pixels` | 0.0124 | 0.0127 | 0.0419 | **0.0223** | **5.1%** |
| `overall_fg_fraction` | 0.0285 | 0.0351 | 0.0307 | 0.0315 | 7.2% |
| `overall_line_score` | 0.0287 | 0.0282 | 0.0691 | 0.0420 | 9.6% |
| **`overall_column_score`** | **0.2664** | 0.0492 | 0.1359 | **0.1505** | **34.4%** |

## The ordering is the finding

**The metric villa optimises is the most reproducible one it has, and the metrics that come closest to
measuring *reading* are the least.** `overall_column_score` varies by 27% between seeds in one triplet
— runs identical but for their RNG.

That is not a coincidence of definitions. `total_fg_pixels` counts ink and is indifferent to where it
lands. Line and column scores ask whether the ink *forms lines and columns*, which depends entirely on
placement — and placement is the thing that only reproduces at r ≈ 0.70
(`ink_placement_in_volume.md`).

**So this is the placement instability showing up in villa's own metrics.** Two independent routes to
the same conclusion: comparing ink maps directly, and comparing the scores computed from them.

## What it costs in practice

At three fits per arm, a study can detect a **5.1%** change in the ink count, a **9.6%** change in line
score, and only a **34.4%** change in column score. To resolve column score as finely as the count is
resolved today would take **≈137 fits per arm — a 46× compute increase.**

**`overall_column_score` is therefore not usable as an endpoint at any budget we have.** Every study
in this repo has correctly used `total_fg_pixels` as primary; this says why that was the only
available choice rather than a preference.

## The uncomfortable implication

The count is measurable *because* it is insensitive to placement, and the readability proxies are
unmeasurable *because* they are not. **Optimising what can be measured is not the same as optimising
what matters**, and on this evidence the gap between them is not small.

This is not an argument for switching endpoints — a 34% MDE is useless. It is an argument for knowing
that a 5% gain in `total_fg_pixels` carries no information about whether the text became more legible,
and for treating consensus across seeds (which the placement work shows recovers ~0.88 reproducibility
at k=3) as the cheaper route to stability than more seeds per arm.

## This answers a question another report left explicitly open

`reports/gap_fix_outer_windings_still_not_established.md` declined to claim a 46.6% column-score fall,
and gave as its second reason:

> *"The floor is transferred from a different region. Every CV on record was measured on w010-w019.
> Nothing establishes that the outer windings are equally stable, and there is positive reason to
> doubt it."*

**Every arm measured here is w120-w129 — the outer region.** So:

| region | `overall_column_score` CV | implied floor at that arm's n |
|---|---:|---:|
| inner, w010-w019 (as used there) | 0.1343 | 26.9% |
| **outer, w120-w129 (measured here)** | **0.1505** | **~30%** |

**The doubt was justified in direction:** the outer windings are *less* stable on column score, by
about 12%, so the floor that report transferred was too generous. Its observed −46.57% still exceeds
the corrected ~30% floor, so its **decision does not change** — but it declined to claim the result
for a reason that has now turned out to be right, rather than merely cautious.

That is worth recording as a small vindication of refusing to promote an unregistered observable: the
caveat it attached was not boilerplate, it was load-bearing, and the data arrived eleven days later.

## Limits

* Three seeds per triplet, so each CV has df = 2 and is itself unstable. The **ordering** is
  consistent across all three triplets; the individual values are not precise.
* `curbase`'s column CV (0.2664) is much higher than `nosamecur`'s (0.0492). With df = 2 that spread
  is unremarkable, but it means "0.1505" should be read as "large", not as a measurement.
* Pinned-tier work measured a comparable column CV (0.2139, `outer_winding_noise_floor.md`), so this
  is not new to current code.
