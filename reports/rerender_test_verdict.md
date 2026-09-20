# The render-code split does not bias the ink — both published nulls stand

**2026-09-14.** Registered in `docs/preregistration/2026-09-14_render_code_rerender_test.md`, decided
by `scripts/analyse_rerender_test.py`, which was committed while the render was at band 12 of 35.
`reports/rerender_test_verdict.json`.

## Result

`curbase_s1`'s existing meshes, re-rendered with current villa code. Same fit, same seed, same
meshes — only the render and scoring code differ.

| quantity | original (`d8c5f488a`) | re-render (`d82e13edf`) | change |
|---|---:|---:|---:|
| **`total_fg_pixels`** | **2,904,520** | **2,946,318** | **+1.44%** |
| `total_pixels` (strip) | 403,291,800 | 400,954,000 | −0.58% |
| `overall_fg_fraction` | 0.00720 | 0.00735 | +2.03% |
| `overall_line_score` | 0.32914 | 0.33533 | +1.88% |
| `overall_column_score` | 0.14101 | 0.13630 | −3.33% |

Validity gate passed: `VILLA_SHA` = `d82e13edf` (not the old code), strip area within ±5%.

**VERDICT: RENDER CHANGE IS INERT** — +1.44% is inside the registered ±2% band.

## Amended 2026-09-20: there was no same-code control, and the noise is larger than the effect

This compared `d8c5f488a` with `d82e13edf` and booked the whole **+1.44%** to the code change. **A
same-code repeat was never run**, so that number is (code effect + render noise) with the split
unknown.

It is now measured: two renders of one mesh set on **one** tree differ by **3.04%**
(`reports/the_render_is_the_noise_floor.md`). **The noise is larger than the effect this report
attributes to code.** The trim grids here differ too — 9143×451 → 8982×449 against 9143×449 →
8990×446 — which is the flatten's stochasticity, not necessarily the code's.

**The verdict "render change is inert" stands and is if anything strengthened**: +1.44% sits inside
both the registered ±2% band and the render's own noise. What is withdrawn is the reading that the
render change *adds about 1.4% ink* — it cannot be distinguished from a re-run.

## +1.44% is not zero, and that is worth saying

The verdict is "inert" by a threshold I set in advance, not because nothing moved. The render change
adds about 1.4% ink on this fit. What the registration bought is that the threshold was fixed before
the number, so "+1.44% is basically nothing" is a rule being applied rather than a judgement being
made while looking at it.

**Taking the +1.44% at face value and adjusting both affected verdicts:**

| study | observed | adjusted for render | its 95% CI | still null |
|---|---:|---:|---|:---:|
| same-winding ablation | +0.28% | −1.16% | [−2.56%, +3.13%] | **yes** |
| anchor ablation | −0.86% | −2.30% | [−10.21%, +8.50%] | **yes** |

Both adjusted effects stay inside their own registered intervals. **Neither verdict changes.**

## The pre-result observation was confirmed exactly

Before this number existed, I recorded that the flatten produces a different grid from identical
meshes: 8982 × 449 → 8990 × 446, a **−0.58%** area change. The scorer independently reports
`total_pixels` **−0.58%**. Two different measurements of the same thing agreeing to two decimal
places is a small but real check that the instrument is consistent.

## Status of the alarm

The confound was **real and worth chasing**: the extracted trees genuinely differ in `lasagna` and
`vesuvius/src`, the flatten genuinely produces different output, and `curbase_s1–s3` genuinely are the
only arms rendered before the change. **The inference I drew from it was wrong** — I attributed a
~4% triplet difference to it, when decomposition showed most of that was strip area and ordinary
density spread, and direct measurement now puts the render effect at 1.4%.

Three things went right and are worth keeping:

1. the threshold was registered before the measurement;
2. the flatten observation was timestamped before the endpoint;
3. the correction to my own overstatement was published before the result, not after it could be
   framed as vindication.

One thing went wrong: **I escalated to URGENT on a count without decomposing it into area and
density**, one day after establishing that the count is the wrong quantity for exactly this kind of
reasoning. The decomposition took one command.

## What this settles and what it does not

**Settles:** the same-winding and anchor verdicts stand as published. No recomputation is needed, and
the ~6 hours of re-rendering baselines that would have required is not spent.

**Does not settle:** this is **one fit**. If the render change interacts with fit geometry, 1.4% is
its effect here and not necessarily elsewhere. And it says nothing about which of `lasagna` or
`vesuvius/src` is responsible.

**Practical rule going forward:** `setup_workdir.sh` now records `VILLA_SHA` in every work dir, so a
mid-corpus split is a `cat` rather than an archaeology exercise. Pin `VILLA_REF` for the duration of a
multi-arm study.
