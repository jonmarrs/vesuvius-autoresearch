# Pre-registration: can villa's loop raise its objective by enlarging the strip rather than reading?

**Written 2026-09-19, before the statistic is computed.**

## The question, and why it is reachable

Findings 42–43 showed the per-bin ink ratio tracks the per-bin **sample-count** ratio
super-proportionally, surviving where both arms fully cover the bin. That was left mechanically
unexplained, and I closed the line rather than propose a fourth mechanism.

This is the **reachable** form of the same concern, asked at arm level about villa's objective:

> **Does `total_fg_pixels` scale with the rendered strip's area?**

Reachability was checked first, because the obvious version is not reachable. Render resolution is a
`render_ink.py` CLI option (`--scale`, default 0.25) and **not** a key in `config.py`, so the
autoresearch loop cannot tune it. But the loop *does* tune the fit, the fit determines the surface,
and the surface determines the strip — so strip area **is** reachable by the loop, at fixed resolution.

**If ink scales ~1:1 with area**, a config change that enlarges the strip raises the objective without
reading any better, and villa's loop can bank that as an improvement. **If ink is largely independent
of area**, the objective is measuring reading and the finding-42 association does not generalise to
the arm level.

## Design

All 41 scored arms on disk, from `<arm>/ink_metric/metrics.json`: `total_fg_pixels` and `total_pixels`.

**Stratified by code tier, and never pooled across them.** The two tiers differ ~15% in strip area and
~60% in ink fraction, so pooling would manufacture a correlation from the tier gap alone —
`reports/corpus_is_on_superseded_code.md` records that the tiers are not comparable.

* **current tier** (`be09a8503`): `curbase_s1–s9`, `anchor10cov_*`, `nosamecur_*`
* **pinned tier** (`6847063f`): `baseline01`, `seed02–06`, `gap133*`, `boot090*`, `rand090*`,
  `nosame_*`, `strip090*`

`curbase_s1rr` is excluded: it is a re-render of `s1`, not an independent arm.

**Primary statistic:** the least-squares slope `a` of `log(total_fg_pixels)` on `log(total_pixels)`,
fitted **within each tier**, with Spearman ρ reported alongside.

## Decision rule, fixed now, on the slope in the CURRENT tier

| slope a | conclusion |
|---|---|
| **a ≥ 0.80** | **AREA-DRIVEN.** The objective substantially measures strip size. A loop can raise it by enlarging the surface, and that is a defect worth reporting upstream. |
| **0.40 ≤ a < 0.80** | **PARTLY.** Area carries a real share; reported with the number, no claim that it dominates. |
| **0.10 ≤ a < 0.40** | **MINOR.** Present and small. |
| **a < 0.10** | **INDEPENDENT.** The objective does not track strip area at arm level, and finding 42's bin-level association does not generalise. |

The pinned tier is fitted the same way and reported as a **replication check**, not as the decision.

## Prediction, fixed now

**PARTLY, a between 0.40 and 0.80.** Reasoning: a larger strip genuinely covers more papyrus, so some
scaling is legitimate rather than artefactual — the confound and the finding are the same quantity
here, which is why the rule above is about size, not about blame. But arm-level ink varies far more
than area does (fraction spans 0.0068–0.0083 within the current tier while area spans ~6%), which
argues against ink being mostly area.

Recorded so it can be a miss. **My last three predictions in this line were all wrong.**

## What this cannot show

**It cannot separate "the strip got bigger" from "the strip got bigger *and* covered more text".**
A slope near 1 is consistent with both a metric artefact and a genuine gain, and distinguishing them
needs positional ground truth that PHercParis4 does not have. What a high slope *would* establish is
that **the objective is purchasable with surface area**, which is actionable regardless of which
interpretation is right.
