# Pre-registration: does moving a strip on its canvas move the ink score?

**Written 2026-09-22 ~15:30, before any arm of this study was built or scored.** Written from
`docs/preregistration/TEMPLATE.md`. Builder `scripts/build_shifted_strip_arm.py`, decision code
`scripts/analyse_scorer_translation.py`, tests `tests/test_scorer_translation.py`, all committed
with this file.

## The question

Two stock flattens of identical meshes (`radial_work_rad0` / `rad0b`) lie on the **same surface**:
0.25 vx apart along the normal (`reports/the_flatten_moves_the_grid_not_the_surface.md`). They also
cover the **same strip area** to 0.2% (`covered>8` ratio 0.9978, `covered>0` 0.9993; control
`flat_study_probe`/`rad0` 1.000000). Yet `total_fg_pixels` differs by **3.04%**, and all of it is
**ink density**: 1.0319× foreground per covered pixel. Counted today, before registering, with the
expectation file written first.

So the scorer reads a re-laid-out copy of the same sheet differently. The simplest part of "layout"
is **position**. The scorer (`scrollprize/ink-coverage-32um`, nnU-Net `2d`, patch 768 × 2048,
`tile_step_size` 0.5, Gaussian blending, mirroring TTA) tiles the strip on a grid, and moving the
content moves that grid over it. **If a shift of a few pixels moves the score, part of villa's
objective is where the scorer's tiles fall, not what is on the sheet.** Any fit change that
re-lays-out the strip would then move `total_fg_pixels` for that reason alone.

## Reachability — checked before designing the validation

* **The scorer accepts PNG** (`IMAGE_EXTS` includes `.png`) and treats a single `w120-129_flat.png`
  as the whole strip (`collect_tiles`).
* **The builder reproduces the scorer's input exactly.** `load_strip` on `rad0`'s six tiles is
  byte-identical to `get_ink_metrics.load_concat_strip` (4260 × 82660 uint8, checked by
  `np.array_equal`). The shifted arm pads black on the top and left, writes a lossless PNG, and
  re-reads it to assert every source pixel survived. No JPEG re-encode, so no compression confound.

## Arms (all from `rad0`'s strip)

| arm | dx | dy | purpose |
|---|---:|---:|---|
| `stx_d0a`, `stx_d0b` | 0 | 0 | repeat floor; PNG vs the source's JPEG score (pipeline check) |
| `stx_x1`, `stx_x2`, `stx_x8`, `stx_x64`, `stx_x512` | 1, 2, 8, 64, 512 | 0 | along the strip; 512 is half a tile stride |
| `stx_y1`, `stx_y8`, `stx_y64` | 0 | 1, 8, 64 | across the strip |

Padding also changes the canvas size, which nnU-Net uses to space its tiles. So a shifted arm moves
the whole tile grid, not only the content under a fixed grid. That is the layout question as posed.

## The floor

`max(|d0a − d0b| / mean, 24 px / 1,698,831)`. The second term is the recorded scorer-and-render
floor (0.0014%) on this exact strip.

## Prediction, fixed now

**SENSITIVE, SMALL: a spread above 3F but under 1%.** Reasoning: 50% overlap with Gaussian weighting
blends every pixel from several tiles, which should damp position effects, but nnU-Net with a fixed
0.5 threshold is not translation-equivariant, so zero effect would surprise me. Confidence
**moderate at best**. My magnitude predictions have missed repeatedly this week.

## Decision rule

`spread` = (max − min) / mean of `total_fg_pixels` over all ten arms.

| spread | verdict |
|---|---|
| ≥ 1% | **LAYOUT-SENSITIVE.** Part of the objective is tile placement. It plausibly accounts for a large share of the 3.04% between two flattens of the same surface, and bounds how precisely any fit comparison can be read. |
| 3F ≤ spread < 1% | **SENSITIVE, SMALL.** Real but minor; cannot explain most of the 3.04%. |
| < 3F | **INSENSITIVE.** Position is not the mechanism; the 3.04% must come from local distortion (stretch or shear) in the re-parametrisation. |

## What the result cannot do

* **It cannot say which layout is "right".** A translation-sensitive scorer has no correct offset.
* **It does not test distortion.** A shift is rigid; the two flattens also differ by local stretch.
  INSENSITIVE points there but does not measure it.
* **One strip, one region, one model.**

## Cost

Ten scoring runs, about 17 min each, serial: **~3 h.** No renders, no flattens. Queued behind the
flatten-transmission study: the scorer takes several GB and must not overlap a render.
