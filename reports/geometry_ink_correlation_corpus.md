# Across 24 fits, `satisfied_area` shows no usable relationship with recovered ink

**2026-09-07.** Observational, from artifacts already on disk; no new compute.
`scripts/correlate_geometry_ink.py`, tested in `tests/test_correlate_geometry_ink.py`.

## What this adds to the four case studies

Four pre-registered studies each found `satisfied_area` and `total_fg_pixels` moving independently.
This asks the same question of every scored fit we hold at once — 24 of them, spanning a **27% range
in recovered ink** (1,448,920 to 1,834,470) and `satisfied_area` from 0.8308 to 0.9804.

| group | n | r | 95% CI |
|---|---:|---:|---|
| ALL fits | 24 | **-0.121** | [-0.50, +0.30] |
| seed-only baselines | 6 | -0.404 | [-0.92, +0.61] |
| patch-selection arms | 9 | -0.183 | [-0.76, +0.55] |
| constraint-ablation arms | 3 | 0.538 | n too small for a CI |

## The interval is the result, not the point estimate

**-0.121 alone would overclaim in the direction we already believe.** The interval spans
[-0.50, +0.30], which does not establish "no relationship".

What it does establish: **a strong positive correlation is excluded.** A usable guard needs
higher satisfaction to mean more ink; the data cap that at r = +0.30 even at the optimistic end of
the interval, with a negative point estimate. A guard with r <= 0.3 against the quantity it is
guarding is not doing the job the loop assigns it.

## Amended 2026-09-11: the corpus is now two tiers, and they must not be pooled

Current villa recovers **67.6% more ink** than the tree these 24 fits were measured on, through a
byte-identical scorer (`reports/current_code_baseline.md`). Pooling the new current-code arms with
these manufactures a spread that is the *code change*, not a relationship.

The script did exactly that once the new arms landed — reporting **27 fits, "100% spread",
r = -0.090** — before it was made tier-aware. That number is an artefact and was never published.

**The figure in this report is and remains the PINNED tier: r = -0.121, 95% CI [-0.50, +0.30] over
24 fits.** `correlate_geometry_ink.py` now separates the tiers, refuses to compute a pooled
correlation at all, and is tested against the near-miss that `nosame_s*` (pinned) and `nosamecur_s*`
(current) differ by three characters.

Whether this relationship holds on current code is **open**, and is what
`docs/preregistration/2026-09-11_decoupling_on_current_code.md` is measuring.

## What this is not

* **Not causal.** The 24 fits differ in patch selection, config flags and constraint sets. This is a
  correlation across heterogeneous manipulations, which is why subgroups are reported separately.
* **Not powered to find a replacement.** The obvious constructive follow-up — search for a cheap
  geometric quantity that *does* predict ink — needs to distinguish candidate proxies from each
  other. At n=24 every candidate would carry an interval about this wide, so ranking them is not
  possible with this corpus. That follow-up is **not attempted**; it would need roughly 40-60 fits,
  or a manipulation designed to vary ink over a wider range than 27%.
* **Not generalisable** past `spiral_datasets/PHercParis4`, w120-w129, one scorer.

## Why it is worth having anyway

The four case studies each answer "did this change move both metrics together?" This answers "over
everything we have measured, does the guard track the objective at all?" — and the answer, bounded
honestly, is that it cannot be shown to, and cannot be strongly positive.

That is the form the claim should take in anything outward-facing. `docs/VILLA_DRAFT_metrics_disagree.md`
currently argues from two cases; the corpus view is a stronger and more honest framing than adding a
third and fourth anecdote.
