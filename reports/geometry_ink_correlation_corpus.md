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

## Amended 2026-09-19: three arms were misfiled, and the current tier can now be reported

**The published pinned figure was never wrong, but re-running the script would have contradicted
it.** `correlate_geometry_ink.py` carried its own `CURRENT_TREE_PREFIXES = ("curbase_",
"nosamecur_")` and defaulted everything else to pinned. `anchor10cov` ran on **current** villa
(`docs/preregistration/2026-09-12_anchor_ablation.md`: "Current villa, 30,000 steps"), nobody added
it to the tuple, and the `else "pinned"` branch absorbed its three fits:

| pinned tier | n | r | 95% CI | ink range |
|---|---:|---:|---|---|
| as the drifted script had it | 27 | **-0.008** | [-0.39, +0.37] | 1.45M .. **2.95M** |
| corrected (this report's figure) | 24 | **-0.121** | [-0.50, +0.30] | 1.45M .. 1.83M |

The ink range is the tell: a 2x span is two populations, not one. `anchor10cov_s3` alone was setting
the pinned maximum. Nothing failed — the number just moved, and it moved the reported guard bound
from +0.30 to +0.37, i.e. **the drift loosened a bound in the direction that flatters us**.

This is the SECOND time this script pooled tiers and reported 27 fits; the note above records the
first. A defect that recurs after being fixed is structural, so the fix is structural: tier
membership now lives once, in `scripts/arm_tiers.py`, `measure_noise_floor.py` cross-checks it at
import, and **an unclassified arm raises instead of defaulting** — the silent default, not the wrong
prefix, was the actual bug. `tests/test_arm_tiers.py` covers it, including a verified check that
reintroducing a local prefix list fails.

### The open question above is now answerable

With its three rightful fits restored, the current tier reads:

| tier | n | r | 95% CI | a guard's best case |
|---|---:|---:|---|---|
| pinned `6847063f` | 24 | -0.121 | [-0.50, +0.30] | +0.30 |
| **current villa** | **15** | **-0.424** | **[-0.77, +0.11]** | **+0.11** |

**The relationship does not appear on current code either, and the bound is tighter there.** The
current tier caps a positive correlation at **+0.11**, against +0.30 on the pinned tree. A guard
needs a meaningfully positive r to do the job `autoresearch.md` assigns it, and +0.11 is not that.

Same caveats as the pinned figure, and one more: these 15 fits span fewer distinct manipulations
(current baselines, one constraint ablation, one anchor ablation) than the pinned 24, so the
heterogeneity that makes the pinned number observational is *narrower* here, not absent.

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
