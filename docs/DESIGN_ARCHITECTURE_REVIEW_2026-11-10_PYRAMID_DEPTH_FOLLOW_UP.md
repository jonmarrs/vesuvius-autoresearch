# Design and architecture follow-up — the pyramid depth check and the confidence guide

Date: 2026-11-10. Baseline: `57afdb70` (main after round #160's merge).
Reviewer: Claude (Anthropic), at the owner's request.

The owner merged nothing after round #160, and asked for the engineering work to continue. This round takes up the
gaps that round #160 recorded in two places where a change is allowed:
- `repro/sota_data/pyramid_depth.py` (#389), which no registration covers;
- `docs/CONFIDENCE_REPRODUCIBILITY.md` (#388), an undated guide to a registered script. The script is unchanged.

## What changed

### `--compare` pools depth by the level's declared z scale

The pixel check compared each coarse slice with two layouts of level 0:
- the slice with the same index, XY-pooled;
- the mean of consecutive slices, XY-pooled.

It took the number of consecutive slices from the XY pooling factor. That is right only when depth and XY were pooled
alike. A correct level pooled 2 in depth and 4 in XY (scale `[2, 4, 4]`) passed the header check as `depth_pooled`, but
its pixels read as `ambiguous`, so the command failed it with exit 1.

The depth pool now has its own width:
- **A level that declares a coarser z** is pooled by its z ratio. The level above now passes, with
  `depth_factor` 2.
- **A level that declares z unchanged** keeps the XY factor. There the question is whether the level is an isotropic
  downsample whose z scale was never updated. A level pooled 4 in depth but labelled z 1 still reads as
  `depth_pooled` and fails.
- **A z ratio that is not an integer pool**, such as 2.5, is refused with exit 2.

`content_agreement` takes the width as an optional keyword, `depth_factor`. Without it the function behaves as before,
and its report now includes the width.

### The header check holds each level's height and width to its declared scale

The header check read only the z scale and the depth. Round #160 found a silent pass: the 17-of-65 level with its scale
written in x, y, z order (`[4, 4, 1]`) read as z 4, called itself `depth_pooled` and exited 0. This happened even
though its declared x ratio of 1 contradicts a width four times smaller than level 0's.

A level whose height or width is not level 0's over its declared Y or X scale is now `inconsistent`. The tolerance is
the one the depth check uses: one voxel or 8%. The reason names the axis, and each record carries
`xy_matches_declared_scale`. Ceil-halved odd extents (15 → 8 → 4 and 17 → 9 → 5) still match.

One existing test kept every level at 8 × 8 while declaring XY scales up to 32, which the new check refuses. Its levels
now halve from 64 × 64, as their scales say, and every assertion is unchanged. No other existing test changed.

### `depth_pooled` needs a z scale above 1

`assess_levels` documents that `depth_pooled` "has a Z scale above 1", but the code accepted any z ratio away from 1.
A level deeper than level 0 at a finer z scale (130 slices at 0.5) was therefore called usable. It is now
`inconsistent`.

### The tool's docstring states the window alignment and the exit statuses

- The origin, not only the window's height and width, must divide by the level's XY scale. An unaligned origin was
  already refused.
- The exit statuses are 0, 1 and 2, with what each means.
- The docstring explains the depth-pool width above.

### The confidence guide says three things the code does

`docs/CONFIDENCE_REPRODUCIBILITY.md` now says:
- **Where each version counts ink.** Version 2 counts ink from the re-score's saved masks in
  `ink_metric_prob/predictions`. Version 1 counted it from the published `ink_metric/predictions` masks, through
  `ink_per_cell` in `scripts/compare_ink_in_volume.py`. The guide's paragraph on the version change listed every other
  change but not this one.
- **The probability map must be alone.** The code counts every `*_prob.npy` in the predictions directory, so the
  whole-strip `*_flat_prob.npy` must be the only one there.
- **The metrics size limit.** Each `metrics.json` is read whole and refused above 1 MiB.

Each sentence has a test that fails on the old guide. Two of those tests also check the code's behaviour: two
probability maps are refused, and a metrics file of 1 MiB plus one byte is refused.

## Verified, no change needed

- **The 13 new pyramid cases fail on the previous tool and pass now.** The XY and z-ratio cases fail on its
  classification. The `depth_factor` cases fail on its signature and report.
- **All 14 mutants of the new code are killed by the module's tests.** They are:
  - the fallback width set to 1, or the compare passing no width;
  - the pool's start or stop taken from the XY factor;
  - the fractional-ratio refusal off;
  - the keyword's default set to 1;
  - each of its two validity checks dropped;
  - the XY check off;
  - x held to y's scale, or y to x's extent;
  - the z-above-1 condition reverted;
  - the width left out of the report;
  - the XY flag inverted.
- **The existing classifications are unchanged.** The 17-of-65 level with its scale written in z, y, x order is still
  `truncated`, and the same depth at z scale 4 is still `depth_pooled`. Every existing case keeps its status, including
  the one whose fixture changed.

## Observations for the owner (not changed)

- **The 8% tolerance now applies to XY as well.** Ceil-halving stays within one voxel, so the XY check could be
  tighter. It shares the depth tolerance so that one rule governs both, and it still catches a mislabelled axis, which
  is off by a factor.
- **A level whose y and x scales differ but match its shape** passes the header check. `--compare` refuses it, as
  before, because it has no single XY pooling factor.
- **The other #389 observations from round #160 still stand:**
  - sparse arrays are refused;
  - a cut-short Blosc chunk that was stored uncompressed can decode silently;
  - real CT has not met `--compare`.
- **#388's test observations from round #160 stand.** Three of its tests pass for a reason other than the one they
  name, and its duplicate-arms test patches a function version 2 no longer calls. Round #160's tests reach each of
  those guards directly.

## Verification

- **The touched modules pass.**
  - `test_ink_pyramid_depth.py` gives 84 passed, against 71 on `57afdb70`: 13 new cases from 9 new test functions.
  - `test_confidence_analysis_contracts.py` gives 77 passed, against 74: three new tests.
  - With the confidence modules, the suite guard, the doc-reference audit (without its standing whole-repository
    failure) and the quotation and withdrawn-claim checks, the touched set gives 238 passed and 1 skipped.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` and `format` are clean on the three changed Python files.
  - Mypy is clean over the whole repository: 939 files, with `--python-executable ./.venv/bin/python` as the hook runs
    it.
- **The standard suite.** The 196 modules give round #153's 70 failing ids, as on `57afdb70`.
- **The test modules outside the suite.** The 250 modules give 2,387 passed, 86 skipped, 13 failed and 21 errors, as
  in round #160. The failing ids are round #153's 34.
- **The doc audit**, run alone, lists exactly round #160's unresolved references. It checks 2,246 path and 834
  commit references, against 2,243 and 833 then.

## A note on this round's work

- **The 02:12 UTC firing arrived while this round ran.** Main had not moved, so this round's PR covers it.
