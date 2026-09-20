# The gap fix's 10% ink loss is not duplicate removal — the canvas never shrank

**2026-09-19.** No new fits; the meshes were already on disk.
`scripts/analyse_gap_fix_mechanism.py`, numbers in `reports/gap_fix_mechanism.json`.

## The hypothesis worth killing

`reports/gap_fix_costs_ink_established.md` established that raising
`model_gap_expander_num_windings` 130 → 133 costs **10.35%** of `total_fg_pixels` (p=0.0018, twelve
fits, w120-w129). That change is a **correctness fix**: it clears a warning that the gap-expander
capacity was short of `shell_outer_winding_idx = 130`.

A correctness fix that loses 10% of the objective is either a real cost or a **measurement artefact**,
and there was a specific reason to suspect the latter.
`reports/duplicate_coverage_inflates_the_objective.md` showed an arm gaining **+12.59%** ink from a
mesh adding **zero new papyrus** — the objective demonstrably rewards duplicated coverage. If the fix
removed some, its "cost" would be deflation of an inflated number, not lost text, and the finding's
meaning would reverse.

**It is not. The hypothesis is refuted, and what it leaves is sharper.**

## What actually moved

| quantity | baseline (6) | gap133 (6) | rel | p |
|---|---:|---:|---:|---:|
| **ink** `total_fg_pixels` | 1.720e6 | 1.542e6 | **−10.35%** | **0.0018** |
| **ink density** `overall_fg_fraction` | 0.004784 | 0.004268 | **−10.78%** | **0.0015** |
| 2D strip area | 3.595e8 | 3.612e8 | +0.45% | 0.682 |
| 3D occupied cells (quant 4) | 1.156e7 | 1.151e7 | −0.46% | 0.0002 |
| duplicated cells, all windings | 11,374 | 11,037 | −2.96% | 0.281 |
| duplicated cells, **w≥120** | 9,214 | 8,910 | −3.30% | 0.269 |

**Every coverage measure is flat.** The strip the scorer sees is the same size (+0.45%, p=0.68). The
3D surface is within half a percent. Duplication does not fall significantly, at either scale — and
the outer-winding cut is the one that matters, because that is where the fix acts and where the
scoring happens.

Duplication would need to fall by roughly the ink loss to explain it. It falls by **3.3%, not
significant**, against an ink loss of **10.35% at p=0.0018**.

## So the same canvas yields 10% less ink

That is the finding. The fix does not remove surface and does not remove double-counting; it
**relocates or re-samples** the surface it produces. The same area of papyrus is rendered, and 10%
less ink is found on it.

Consistent with `reports/SPIRAL_FINDINGS_SUMMARY.md` finding 19 (satisfaction falls with radius) — the outer windings where scoring
happens are exactly where the fit is least constrained, so a correctness change there can move the
sheet a little without changing how much sheet there is. **Which of relocation or depth re-sampling
it is, this does not settle.**

## The consequence for villa's loop, which is the part that generalises

`spiral-fitting/autoresearch.md` names `overall_fg_fraction` as its anti-gaming guard: it "will
collapse" if a change inflates the surface with garbage geometry.

**On this change that guard falls 10.78% (p=0.0015) — and the change is villa's own correctness fix.**

The guard is built to catch surface added over blank papyrus. It fires identically when *correct*
geometry moves off inked papyrus, because both look like "less ink per unit surface". It cannot
distinguish a change that made the geometry worse from one that made it more right and moved it away
from ink. A loop optimising `total_fg_pixels` under that guard would reject this fix twice over: once
on the objective, once on the guard.

## An independent confirmation, noted in passing

**~80% of duplicated cells involve a winding at w≥120** (79.5%–82.0% across all twelve fits),
matching `reports/duplicate_coverage_is_an_outer_winding_phenomenon.md`, which was measured by a
different route.

## Limits

One dataset, one ROI, `w120-w129`, one scorer, quantisation 4 voxels. "Duplicated cells" counts
distinct spliced windings claiming the same quantised cell at winding gap ≥ 2, which cannot see
duplication finer than 4 voxels or between adjacent windings. `total_fg_pixels` is an area count and
cannot distinguish text from false positives — so "10% less ink" is not the same claim as "10% less
readable text", and nothing here establishes which.
