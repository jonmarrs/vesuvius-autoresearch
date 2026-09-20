# Prediction, recorded before the ZERO-repeat is scored

**Written 2026-09-19 ~23:40 PT, while `radial_work_rad0b` was at band ~10/34 and no
`ink_metric/metrics.json` existed for it.** Recorded because the coincidence below would be far too
convenient to notice only after the fact.

## The observation that prompts it

The ZERO arm re-rendered `baseline01`'s meshes — geometry identical to **float32 ULP** (max coordinate
difference 0.000244 vx, identical bbox, identical valid-point counts) — and scored **−5.05%** against
`baseline01`'s stored value.

The pinned tier's pooled seed CV is **0.0514** (`reports/noise_floor_by_tier.md`, df=18).

**5.05% and 5.14%.** Those are measurements of supposedly different things: one is a pure re-render of
identical geometry, the other is attributed to fit RNG across differently-seeded fits.

## The hypothesis

**What this project calls "seed noise" may be largely RENDER noise.** Every arm in the corpus is a
separate fit *and* a separate render+score. A seed CV computed across arms therefore contains both,
and has never been decomposed. If the render stage alone contributes ~5%, then fit RNG contributes
little, and the two figures coinciding is not a coincidence.

## What the repeat will show, and what each outcome means

`radial_work_rad0b` is a second render+score of the **same** mesh set on the **same** pinned tree
(`be09a8503`, `render_ink.py` byte-identical, input meshes hash-identical at `4576eacfa2d40cdd`). It
differs from ZERO in nothing but being run again.

| |dT| between ZERO and its repeat | reading |
|---|---|
| **≥ 3%** | **The render stage is the dominant noise source.** The 1.42% determinism floor is wrong, the radial study needs a floor near this value, and — more broadly — extra fit seeds buy far less than assumed because the variance is downstream of the fit. |
| **1-3%** | Render noise is material but not dominant; the floor needs revising and the seed CV is partly render. |
| **≤ 1.42%** | Render is reproducible on one tree. The −5.05% is then **render-code drift** between 2026-09-01 and `be09a8503`, which is its own finding: comparisons spanning a villa bump are unreliable at ~5%. |

**I predict ≥ 3%**, i.e. the first row. Reasoning: the lasagna flatten is a stochastic optimisation
and its output grid already differed between the two ZERO renders (82670 → 82660 columns), which is a
mechanism for run-to-run variation that does not require any code change.

**Recorded so it can be a miss.** I have been wrong on the direction of an observable repeatedly in
this project, most recently predicting where a determinism discrepancy would localise.

## What it would change

If ≥ 3%: the radial study's registered 1.42% floor is replaced by the measured value **before** IN and
OUT are interpreted, and `reports/noise_floor_by_tier.md` needs a decomposition note — its CV is not
purely seed noise. IN/OUT would still be worth running, but a 10% effect against a ~5% floor is a much
weaker test than against 1.42%, and the arm count may need revisiting.

If ≤ 1.42%: the study proceeds as registered, and the −5.05% becomes a measurement of render-code
drift across a villa bump — directly relevant to
`reports/the_determinism_floor_rests_on_one_draw.md`, whose 1.42% pair had no recorded `VILLA_SHA`.
