# The render does not reproduce: 3.04% on identical geometry, identical code

**2026-09-20.** Registered in `docs/preregistration/2026-09-20_is_the_noise_floor_actually_the_render.md`
and decided by `scripts/analyse_render_reproducibility.py`, **both committed while the repeat was on
its final fold with no `metrics.json`**. `reports/render_reproducibility.json`.

## The measurement

Two renders differing in **nothing but being run twice**: same mesh set (combined tif hash
`4576eacfa2d40cdd`), same pinned villa `be09a8503`, byte-identical `render_ink.py`, same machine,
same day.

| quantity | run A | run B | rel |
|---|---:|---:|---:|
| **`total_fg_pixels`** | 1,698,831 | 1,750,482 | **+3.04%** |
| `total_pixels` (canvas) | 352,131,600 | 351,305,000 | −0.23% |
| `overall_fg_fraction` | 0.004824 | 0.004983 | +3.28% |

**Registered prediction was ≥3%. MET, at 3.04%** — and only just, which is worth saying: the band was
set at 3% and the result landed 0.04 points inside it. Treat the band as met, not the margin as
informative.

## What it overturns

**The "pipeline determinism floor" of 1.42% is too small by at least 2×**, and its stated mechanism
was wrong. `reports/the_determinism_floor_rests_on_one_draw.md` attributed the spread to
"threshold-boundary pixels under three-fold nnU-Net ensembling and GPU non-determinism". Measured:

| source | spread on `total_fg_pixels` |
|---|---:|
| scorer alone, one fixed strip, n=3 | **0.0032%** |
| **render + score, same tree, same meshes** | **3.04%** |
| claimed "pipeline determinism" | 1.42% |
| pinned-tier "seed" CV (df=18) | 5.14% |

The scorer is **950× too small** to produce 1.42%. The render is the source.

**The mechanism is the lasagna flatten, which is a stochastic optimisation.** The two runs produced
different output grids — 82660×**4260** vs 82660×**4250** — from identical input. The corpus already
held the same evidence unnoticed: `curbase_s1` and its rerender `curbase_s1rr` flattened
9143×**451** → 8982×449 against 9143×**449** → 8990×446.

## The consequence that reaches the whole corpus

**Every arm here is a separate fit AND a separate render+score, so the "seed CV" has always contained
both, and was never decomposed.**

> **Corrected 2026-09-20.** This originally read "this pair explains **59%** of the pinned-tier
> 5.14%", computed as 3.04/5.14. That divides a **single pair difference** by a **CV** — different
> quantities. Done properly, one difference gives sigma = |d|/(2/sqrt(pi)) = **2.69%**, a variance
> share of **27%**, with a df=1 interval on sigma of **[0.96%, 68.6%]** — a share anywhere from 3%
> to 100%. **One pair cannot apportion the seed CV**, and no percentage-explained is claimed.

Three renders of geometry identical to float32 ULP span **5.32%** (1,698,831 / 1,750,482 / 1,789,206)
— a range indistinguishable from the seed CV that six differently-seeded *fits* produce.

**So extra fit seeds buy much less than assumed: the variance is downstream of the fit.** A study that
adds seeds to tighten its floor is mostly paying for more renders of the same noise.

## Does this still hold against current villa? Checked 2026-09-21

The measurement was made at pinned `be09a8503`. Upstream is now 37 commits ahead and the hot path
has changed — almost entirely in **`lasagna/`**, the flattener this report names as the noise source
(`model.py` alone +391/−166). Two checks on that diff:

* **No commit touches seeding or determinism.** A grep of the `lasagna/model.py` and `optimizer.py`
  diffs for `seed`, `manual_seed`, `deterministic`, `random`, `rng`, `generator`, `benchmark` returns
  nothing. The three hot-path commits are a flush-worker fix (#1752), flatten memory (#1783), and
  recording which model snapshot scored (#1805). **The flatten is as stochastic on current villa as
  on the pin.**
* **Villa's new `test_flatten_state_handoff.py` tests the wrong stage for this.** It asserts an
  in-memory checkpoint handoff reproduces the file-driven export "bit for bit". That is *export*
  determinism — the same optimised state written two ways. The non-reproducibility measured here is
  in the *optimisation itself*: two runs from identical input reach different states. Villa's test
  would pass on a flattener that lands 7 vx apart every run, and it does.

So the finding is not an artifact of the pin. It is a property of the current flattener, and the
test that would catch it — flatten the same input twice, compare the surfaces — does not exist
upstream.

## What it does NOT overturn

**No published verdict flips.** Every null in `reports/no_lever_has_improved_reading.md` was already
quoted against a floor of 10-12%, which is *larger* than this. The gap-expander's −10.35% was
established on 6v6 with complete separation, and 3.04% of render noise does not reach it. The effect
of this finding is on **attribution and design**, not on any existing conclusion.

**It does not give a render CV.** This is **one pair**, so it is a point estimate with no interval —
exactly the error `reports/noise_floor_by_tier.md` has now made three times. The defensible claim is
a **lower bound**: render reproducibility is no better than ~3% on this pipeline. Whether the true
figure is 2% or 6% needs more pairs.

## What it does to the radial displacement study

The study registered a **1.42%** floor on the strength of the determinism report. That floor is wrong,
and the honest consequence is that the study is weaker than registered: an IN arm losing 10% would be
~3× a 3.04% floor rather than ~7× a 1.42% one, from single arms with no interval.

**Not abandoned, but re-scoped before IN and OUT are interpreted.** Two ZERO renders now exist, so
their spread is the floor estimate, and IN should be read against the ZERO *mean* rather than either
run. Whether one arm per displacement is enough is a question the registration answered with the wrong
number, and it needs answering again before the result is called.

## Limits

One mesh set, one ROI (`w120-w129`), one machine, two runs. The flatten's stochasticity is
*demonstrated* by the differing grids but its distribution is not characterised. `total_fg_pixels` is
an area count; a 3% swing in it is not 3% more readable text.
