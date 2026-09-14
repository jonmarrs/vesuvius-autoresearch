# Pre-registration: does the 09-11 render change move the ink?

**Written 2026-09-14, before the re-render starts.** Settles the confound in
`reports/URGENT_render_code_changed_mid_corpus.md`, which bears on two published verdicts.

## The confound

`setup_workdir.sh` builds render work dirs from the villa submodule's `origin/main`. Our pin moved
`d8c5f488a → be09a8503` on 2026-09-11 13:22, and the extracted trees differ:

| path | across the 09-11 bump |
|---|---|
| `spiral-fitting` | identical |
| **`lasagna`** (the flatten) | **DIFFERS** |
| **`vesuvius/src`** (tifxyz reader) | **DIFFERS** |

`curbase_s1–s3` are the **only** arms rendered before that bump. Every comparison against them —
including the same-winding ablation (+0.28%, reported null) and the anchor ablation (−0.86%, reported
null) — has the ablated arm on new render code and the baseline on old.

## The test

**Re-render `curbase_s1`'s existing fitted meshes with the current code, and re-score.** The fit is
untouched: same meshes, same seed, same everything. Only the render and scoring code differ.

```
run_outer_arms.sh <spiral_out> 120 129 curbase_s1rr=<curbase_s1 fitted meshes>
```

Output goes to a **new** tag `curbase_s1rr`; the original `outer_curbase_s1` is not overwritten.
Cost ≈ 2 hours, no new fit.

**Original value to beat: `total_fg_pixels` = 2,904,520.**

## Decision rule, fixed now

| re-rendered `total_fg_pixels` | conclusion |
|---|---|
| within **±2%** of 2,904,520 (2,846,430–2,962,610) | **Render change is INERT.** The 09-11 split does not bias ink, and both published nulls stand unmodified. |
| **> +2%** | **Render change ADDS ink.** The same-winding and anchor verdicts each compared a new-code arm against an old-code baseline, and both must be recomputed against re-rendered baselines before being trusted. |
| **< −2%** | Render change removes ink; same consequence, opposite sign. |

±2% is chosen because the effect in question is ~4% (the s4/s5 excess over s1–s3) and the within-arm
seed CV on a *re-render of the same fit* should be far below that — a re-render is deterministic given
the same code, so any difference is code, not noise.

## Validity gate

* The re-render must consume **the same mesh directory** as the original. If the mesh count or strip
  size differs materially (>5%), something other than code changed and the result is void.
* `<workdir>/VILLA_SHA` must record a commit whose extracted trees differ from `d8c5f488a` — i.e. the
  re-render genuinely used new code. Any of `be09a8503`, `bfef6abe0`, `3b398f7cc`, `d82e13edf`
  qualifies; their extracted trees are identical to each other and differ from `d8c5f488a`.

## What it cannot settle

* One arm. If the render change has an effect that varies by fit, one re-render measures it for this
  fit only.
* It cannot say which of `lasagna` or `vesuvius/src` is responsible.

## Prediction

**None registered.** But the stakes are asymmetric and worth stating: a result inside ±2% leaves two
published verdicts intact, and a result outside it means both need recomputing. I would prefer the
first, which is exactly why the threshold is written down before the number.
