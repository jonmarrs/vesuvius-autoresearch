# The flatten's 3% is local rescoring of the same sheet, not more sheet

**2026-09-22.** `scripts/measure_layout_rescoring.py`; numbers in `reports/layout_rescoring/`.
It follows `reports/the_flatten_moves_the_grid_not_the_surface.md`, which showed that two stock
flattens of identical meshes (`radial_work_rad0`, `rad0b`) lie on the same surface, 0.25 vx apart
along the normal, and differ only in how the sheet is laid out. They still score **3.04%** apart on
`total_fg_pixels`. This asks where that 3% comes from. Each question had its expectation written
down before it was computed.

## 1. Not area: density

| `rad0b` / `rad0` | ratio |
|---|---:|
| strip area the sheet covers (strip value > 8) | **0.9978** |
| ink pixels (scorer mask) | 1.0304 |
| ink per covered pixel | **1.0327** |
| control: `flat_study_probe` / `rad0`, byte-identical strips | 1.0000 on all three |

The two layouts cover the same area to 0.2%, and brightness of the covered pixels is unchanged (mean
132.6 vs 132.2, from an exploratory count on a 1-in-50 sample of covered pixels, not in the JSON). So the scorer finds more ink per pixel in one layout of the same sheet than in the
other. A stretch that spreads the same ink over more pixels would have shown as area; it does not.

## 2. Not a global shift: local, both ways

Split along the strip into blocks of 2048 px (40 blocks):

| | value |
|---|---:|
| ink-weighted sd of the per-block change | **0.135** |
| blocks that LOSE ink | **16 of 40** |
| lag-1 correlation between neighbouring blocks | −0.01 |
| the scorer's own repeat noise at this block size (identical strips) | 0.000093 |

The per-block rescoring is about **1,450×** the scorer's repeat noise, so it is caused by the layout,
not by scorer non-determinism. It goes both ways, and **the net +3% is a residual**: independent
blocks at this spread imply ±2.6% on the total, and 3.07% is a 1.2-sd draw.

## 3. Fine-grained and close to independent

| block width (px) | 128 | 256 | 512 | 1024 | 2048 | 4096 | 8192 | 16384 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| blocks | 368 | 226 | 138 | 77 | 40 | 20 | 10 | 5 |
| sd, scaled to 2048 px | 0.106 | 0.115 | 0.130 | 0.138 | 0.135 | 0.151 | 0.109 | 0.101 |
| lag-1 | +0.03 | +0.01 | +0.03 | +0.01 | −0.01 | −0.29 | −0.20 | −0.50 |
| implied sd of the total | 0.031 | 0.030 | 0.031 | 0.030 | 0.026 | 0.025 | 0.018 | 0.016 |

Neighbouring blocks are uncorrelated from 128 px to 2048 px, and the independent-block model at
fine scale predicts **±3.0%**, which is the observed 3.07%. The large-block rows rest on 5–20 blocks
and are not interpretable.

**A claim I made and withdrew the same hour.** From the mild rise of the scaled sd between 128 and
4096 px, I first read a correlation length of about 1–4 kpx, near the scorer's 2048 px patch. The
lag-1 column does not support that: blocks are independent at every width where there are enough of
them. The rise is more plausibly an ink-weighting effect. So there is **no evidence** here for either
tile-driven or column-driven structure (the scorer's own column model assumes ~850 px columns).

## What it means

* **Re-laying out a strip re-draws its ink score locally, by ±13% per 2 kpx block, and the total
  moves by a few percent.** This happened with the surface held fixed to 0.25 vx. Any change that
  re-lays out the strip carries this, including every different fit villa's loop compares.
* This is the mechanism under the 3.04% flatten floor. It may also be part of the seed-to-seed
  ink-placement instability (r ≈ 0.70), but that was measured in the volume frame and is **not**
  tested here.

## What it does not settle

* **What about the layout the scorer responds to.** Position (tile placement over content) is
  tested directly by the queued `docs/preregistration/2026-09-22_scorer_translation.md`, which now
  also reports per-block spread. If a pure shift reproduces spread near 0.135, position is enough.
  If it does not, local stretch or shear in the re-parametrisation is the remaining candidate.
* **One pair, one region** (`w120–w129`).
