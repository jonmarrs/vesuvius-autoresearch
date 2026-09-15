# Pre-registration: how far does the render-tree change move ink PLACEMENT?

**Written 2026-09-14 while `curbase_s7` is rendering. No arm of triplet C is scored, and this
study does not touch C.**

## Why this exists

The second amendment to `2026-09-14_consensus_retest_calibrated.md` established that triplet A
(`s1–s3`) rendered from `d8c5f488a` while B and C are on `be09a8503`, and reported the A-vs-C
confound as **unbounded at the placement endpoint**. That was the honest thing to say, because the
only existing measurement — `reports/rerender_test_verdict.md`, +1.44% inert against ±2% — bounds a
**count**, and this line of work exists precisely because the count reproduces to 1.2% while
placement reproduces to only r ≈ 0.70.

"Unbounded" is honest but weak, and it is cheaply improvable. `outer_curbase_s1rr` is `curbase_s1`'s
**same fit, same seed, same meshes**, re-rendered on `d82e13edf`, which `check_render_equivalence.py`
reports INTERCHANGEABLE with `be09a8503`. Correlating those two maps measures the render change at
the endpoint that matters, with no new compute.

## Design

`corr(volume_map(outer_curbase_s1), volume_map(outer_curbase_s1rr))` — the (z, θ) ink histogram in
**volume coordinates**, the same instrument used throughout, so no flattening artefact enters.
Between these two arms the fit, the seed and the meshes are identical; only the render and scoring
code differ. Any decorrelation is the render change.

**Measured against the seed scale on the same instrument**, which is the comparison that gives the
number meaning: `corr` for the three within-A seed pairs `s1-s2`, `s1-s3`, `s2-s3`. A θ-rotated
shuffle null sits at about −0.09.

## Prediction, fixed now

**r ≥ 0.95** — the render confound is small relative to seed noise. Reasoning: the meshes are
identical and the flatten is deterministic given a mesh, so the changed code should move where ink
lands far less than a different optimiser seed does. Recorded so it can be a miss. The honest
counter-case is that `lasagna/fit.py` **is** the flatten, and it is one of the two paths that
changed, so a large move is entirely possible.

## Decision rule

| r(s1, s1rr) | conclusion for A-vs-C |
|---|---|
| **≥ 0.95** | confound is small against the seed scale; A-vs-C's confound is **bounded and minor**, and the comparison is interpretable with the bound stated |
| **0.80 – 0.95** | **material**; A-vs-C is reported with this number attached as a quantified confound |
| **< 0.80** | confound is comparable to the effect being measured; **A-vs-C is uninterpretable at this endpoint** and is reported as such |

Whatever this returns, **A-vs-C is still computed and reported** in the consensus test. This
registration changes what the number means, never whether it is shown.

## Limits, stated before the result

* **n = 1 arm.** This bounds the render change for one fit, not a distribution over fits. It cannot
  become "the render change moves placement by X" in general.
* `s2` and `s3` are assumed to share `s1`'s render tree. That is reconstructed, not logged, and `s3`
  sits only 20 minutes before the ref moved.
* A high r here does **not** retire the confound; it bounds it.
