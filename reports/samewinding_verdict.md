# Removing 5,413 same-winding constraints degrades the fit and does not change reading

**2026-09-07.** Three ablated arms against the six existing full-input baselines, analysed by
`scripts/analyse_same_winding.py` exactly as committed before the first arm was fitted.
Registration: `docs/preregistration/2026-09-06_same_winding_ablation.md`.

## The question, and whose it is

villa's `39_winding_annotations.md`: *"the fastest way to unroll scrolls at scale is to develop
methods for creating winding constraints that are precise and fast enough to use widely"*, and
*"We don't know the exact minimum amount of winding evidence necessary."*

Five projects in villa's catalogue generate or evaluate winding constraints. **All validate on
geometry.** This measures winding evidence against **recovered ink**.

## Result

| endpoint | BASELINE (n=6) | ABLATED (n=3) | relative | p |
|---|---:|---:|---:|---:|
| `total_fg_pixels` | 1,720,000 | 1,690,000 | -1.74% | 0.6114 |
| `satisfied_area_fraction` | 0.8390 | 0.8331 | **-0.69%** | **0.0027** |

**VERDICT: NULL on reading.** No ink effect larger than **8.3%** (80% power at 3v6, computed before
the fits). Bounded, not zero.

## The geometry result is stronger than the registration allowed for

The registration made `satisfied_area` **report-only**, reasoning that removing 5,413 of the inputs
satisfaction is computed against could make the metric *rise* simply because there is less left to
satisfy. The 200-step smoke fit showed exactly that rise, and I predicted it.

**It fell instead, significantly.** That caveat does not apply to a fall: the fit satisfies its
remaining inputs *less* well despite having fewer of them to satisfy. The confound could only
manufacture a rise, so the degradation is not explainable by the manipulation's arithmetic.

So the constraints do measurably improve the geometry fit — and **that improvement does not reach
reading**.

## Fourth instance of the two metrics coming apart

| case | `satisfied_area` | `total_fg_pixels` |
|---|---|---|
| gap-expander config (n=12) | +1.03% | **-10.35%** |
| patch bootstrap (n=6) | **+17.66%** | -0.83% (null) |
| stripmatch (n=6) | +16.24% | -3.80% (null) |
| **same-winding ablation (3v6)** | **-0.69%** | -1.74% (null) |

This is the one that bears on strategy. The other three concern fitting choices; this one concerns
**the winding constraints villa names as the scaling path**. Removing 5,413 of them is visible in the
geometry diagnostic and invisible in recovered ink at this budget.

## What this does not say

* **Not that winding constraints are useless.** It bounds their contribution to *reading on this ROI*
  at under ~8.3%. A real effect below that survives.
* **Not that the geometry gain is worthless.** Geometry may matter for downstream uses this endpoint
  does not measure.
* **Not generalisable beyond** `spiral_datasets/PHercParis4`, w120-w129, one ablation, all-or-nothing.
  A dose-response over constraint count would be the better study and was rejected on cost.

## A prediction half wrong, and the reason worth keeping

Registered: *"ink NULL and satisfied_area RISES"*. Ink was null; the direction of the geometry move
was wrong. I reasoned from the 200-step smoke fit, which did show a rise.

**A 200-step fit predicted the wrong sign at convergence** (`satisfied_area` 0.13 vs 0.84). Smoke
fits here establish that an observable responds; they do not establish which way it moves. That
limitation was already recorded for the drift measurements in the same registration, and it applies
to effect direction too.

## Validity

* all three arms passed the registered non-blank control (48.1%, 46.6%, 46.6% nonzero), 240 mesh
  entries each, all ten outer windings;
* arms differ in 5,413 constraints and nothing else — same 38,442-patch input, same config, seeds
  1/2/3, fits pinned to villa-spiral `6847063f`, renders to `5479453a`;
* `abs_winding.json` untouched, so absolute numbering stays anchored and the scored strip means the
  same papyrus across arms (measured drift +5.60 vx, against -71.7 for the rejected
  `loss_weight_abs_winding` ablation);
* the analysis refuses a partial sample and was invoked through
  `scripts/run_patch_bootstrap_verdict.py --study samewinding`, which errors rather than guessing if
  a tag matches more than one fit directory.

Machine-readable: `reports/samewinding_verdict.json`.
