# Conditional pre-registration: does selection help once outer evidence is held equal?

**Written 2026-09-04, while arms 4-6 of the patch-bootstrap study were still running and with every
endpoint of that study unread.** That timing is the point. This design exists to answer a question
the main study cannot, and writing it now means it cannot be shaped by the answer it is meant to
explain.

## The gap this closes

`reports/patch_bootstrap_outer_evidence_deficit.md` establishes that BOOTSTRAP carries about **11%
less relative area inside the scored strip** than its area-matched RANDOM control, because
satisfaction falls with radius (r = -0.21) and a 0.90 threshold therefore drops outer patches
preferentially.

So if the main study finds an ink deficit, two explanations survive it and it cannot separate them:

1. selecting on satisfaction picks *worse* evidence for reading ink; or
2. selecting on satisfaction simply leaves *less* evidence where the ink is measured.

RANDOM matches BOOTSTRAP globally, not inside the strip, so the main study is silent on which.

## Design

A third arm, **STRIPMATCH**: a random draw constrained to match BOOTSTRAP on **both** total patch
area and in-strip area share, compared against the **existing** BOOTSTRAP arms. With outer evidence
equalised by construction, a remaining difference is selection quality and nothing else.

Feasibility was demonstrated before registering, not assumed:

| | patches | total area | in-strip share | mean satisfied fraction |
|---|---:|---:|---:|---:|
| BOOTSTRAP | 26,728 | 13,875,737,778 | 0.4120 | 0.9908 |
| STRIPMATCH (constructed) | 29,661 | 13,876,185,706 (100.00%) | 0.4120 (gap 0.0000) | 0.8084 |
| full population | 38,439 | 18,170,581,072 | 0.4648 | 0.8003 |

The quality contrast survives the extra constraint (0.8084 vs 0.9908), so this is still a real
manipulation rather than a draw forced to resemble BOOTSTRAP in every respect.

In-strip share uses the calibrated radial support of w120-w129, **radius 1,593 to 3,311**
(`scripts/calibrate_radius_to_winding.py`), with each patch's area apportioned by the fraction of its
radial extent falling inside that window -- not by a centroid, for the reason recorded in
`check_patch_spatial_balance.py`.

## When this runs, decided now while blind

| main-study verdict | run STRIPMATCH? |
|---|---|
| **HARMS** (ink down, significant) | **Yes.** Distinguishing "worse evidence" from "less evidence" is then the whole question. |
| **FAILURE** (ink null, geometry up) | **Yes.** If the deficit is evidence-driven, "crop good regions *but preserve outer coverage*" is a usable refinement of villa's avenue rather than a dead end. |
| **WORKS** (ink up, significant) | **No.** The method succeeded despite the deficit; the mechanism is not blocking anything. |
| **NULL** (both null) | **No.** Nothing to explain at this budget. |

## Endpoints, rule, cost

Same as the parent study: `total_fg_pixels` on w120-w129 primary, `satisfied_area_fraction`
secondary, Welch two-sided, alpha 0.05, three seeds (1, 2, 3), fits pinned to villa-spiral
`6847063f` and renders to `5479453a`. **A geometry-only gain remains a FAILURE, not a partial
success.** Three arms at the observed ~5h20m each: **about 16 hours.**

Before any fit runs, the STRIPMATCH builder must be a committed, tested script, and
`scripts/check_patch_selection.py` plus `scripts/check_patch_spatial_balance.py` must both pass on
the built dataset. The feasibility sampler used above is a throwaway and is deliberately **not** the
builder.

## Prediction, fixed now and blind

**I predict STRIPMATCH shows no ink advantage for BOOTSTRAP either** -- that equalising outer
evidence does not rescue the method, because satisfaction is the fit's own residual and selecting on
it is close to circular regardless of where the evidence sits.

If that is right, the honest summary of both studies is that this avenue does not work and the outer
deficit is a side effect rather than the cause. If it is wrong -- if BOOTSTRAP beats STRIPMATCH once
coverage is equal -- then the avenue does work and the main study understated it, which would be the
more useful result for villa and the one I am betting against. Recorded so it can be a miss; I have
been wrong on three of five registered predictions.
