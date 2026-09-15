# The render-tree change moves placement ten times less than reseeding does

**2026-09-14.** Registered in `docs/preregistration/2026-09-14_render_confound_at_placement.md`,
written and committed before the numbers were computed. No arm of triplet C was scored when this ran,
and this study does not touch C.

## Result

`curbase_s1` and `curbase_s1rr` are the **same fit, same seed, same meshes**. Only the render and
scoring code differ — `d8c5f488a` against `d82e13edf`, which `check_render_equivalence.py` reports
INTERCHANGEABLE with triplet C's `be09a8503`. Ink compared as a (z, θ) histogram in **volume
coordinates**, so no flattening artefact enters.

| comparison | what varies | r |
|---|---|---:|
| **`s1` vs `s1rr`** | **render + scoring code only** | **0.9715** |
| `s1` vs `s2` | optimiser seed | 0.8076 |
| `s1` vs `s3` | optimiser seed | 0.6843 |
| `s2` vs `s3` | optimiser seed | 0.6614 |
| | **mean within-A seed pair** | **0.7178** |

Decorrelation is the quantity to compare: **0.0285 for the render change against 0.2822 for a
reseed**. The render change moves where ink lands **9.9× less than changing the seed does**.

**VERDICT: BOUNDED AND MINOR**, by the registered rule (r ≥ 0.95).
**Registered prediction r ≥ 0.95: MET.**

## What this changes

The second amendment to the consensus registration reported the A-vs-C render confound as
**unbounded at the placement endpoint**. That was correct at the time — the only measurement in hand,
+1.44% inert against ±2%, bounds a *count*, and this entire line of work exists because the count
reproduces to 1.2% while placement reproduces to only r ≈ 0.70.

It is now bounded, and it is small: **about a tenth of the seed noise the study is built to measure.**
A-vs-C is interpretable with that bound attached.

The seed pairs also reproduce the headline finding independently — mean r = 0.7178 against the
established r ≈ 0.70, on arms and an axis choice that were not used to derive it.

## What it does not license

* **n = 1 arm.** This bounds the render change for one fit. It is not "the render change moves
  placement by 2.85%" in general, and must not be quoted that way.
* **A high r does not retire the confound**, it bounds it. A-vs-C still carries a difference B-vs-C
  does not, and both comparisons are still reported exactly as registered.
* `s2` and `s3` are *assumed* to share `s1`'s tree. That is reconstructed from the reflog, not logged,
  and `s3` sits only 20 minutes before the ref moved.
* The three seed pairs are not independent of each other — they share arms — so the mean is a scale,
  not an estimate with three degrees of freedom.

## A near-miss worth recording

This ran while `curbase_s7` was mid-render. Loading four arms drove **available RAM to 0 G**, and
`repro/spiral_render/preflight.sh` says in terms: *"measured headroom DURING a render is ~1G. Do not
start the test suite, a second arm, or a container build while one is in flight."* The render
survived. That was luck, not judgement — an OOM would have cost a 3-hour fit plus the render.

The warning was, once again, **prose addressed to a human**, which is exactly the failure mode the
`VILLA_SHA` fix was introduced to correct. `scripts/guard_heavy_analysis.py` now makes it a check:
it refuses to proceed when a render is in flight and free RAM is below a floor.

A second, smaller slip: diagnosing the scare, I checked for a live render by grepping `cmdline` for
`render_ink|run_render` and concluded nothing was alive. The pipeline was in its **lasagna flatten**
stage, so the pattern matched nothing while the render was perfectly healthy. Matching on a
*substring of one stage* is the same error as matching `pgrep -f` on a string — the guard now matches
the villa venv interpreter, which is common to every stage.
