# Pre-registration: how wide a band should the ink render sample? Tested against villa's labels with inkagree

**Written 2026-10-03, before any arm of this study was rendered.** Chain
`repro/spiral_render/run_band_vs_labels.sh`. It runs inkagree **0.2.1, installed from GitHub at
`b739f51`** into its own environment, so nothing reads the working tree. Committed with this file.

## Why

* villa's 3D-ink tutorial renders with `--num-slices 16 --slice-step 0.5`. Its stated reason: step 0.5
  "samples a focused band around the surface without accumulating as much papyrus texture as a wider
  step". That is a claim about agreement with ink, and villa's labels can test it.
* Finding 66: the post-#1146 sampler doubled the band (slice step) and raised villa's ink count by
  5–9%. Whether a wider band is **more faithful**, or only finds more, was never measured. This study is
  the label-anchored version of that question, at the tutorial's level (level 2, 16 slices), which is not
  the spiral metric's (level 3, 5 slices). The link to finding 66 is indirect, and stated as such.

## Method

* **Segments:** the 8 with villa labels on the 2.4 µm frame (`inkagree segments`).
* **Arms:** inkagree's `tutorial` preset (`--group-idx 2 --scale 1 --num-slices 16`) on
  `vc-render:sampler-f637f3b35`, with `--slice-step` ∈ {**0.25, 0.5, 1.0, 2.0**}. 0.5 is the tutorial's
  value and the reference. Max over slices.
* **Comparisons:** `inkagree compare SEG DIR step0.5.tif stepX.tif --level 2` for X ∈ {0.25, 1.0, 2.0}
  (A = 0.5, B = X), with inkagree's defaults: whole-domain gate (±2 px, min_gain 0.002), 256-px blocks,
  2000 resamples, seed 20261003.
* **Aggregation:** `inkagree summarize --k 6` per X: a verdict only if resolved in the same direction in
  at least 6 compared segments.

## Predictions, fixed now

1. **Step 2.0 agrees worse than 0.5** ("A agrees better" by the k = 6 rule). Confidence moderate. This
   is the tutorial's rationale: a wide band accumulates texture.
2. **Step 0.25 vs 0.5: no consistent difference.** Confidence low.
3. **Step 1.0 vs 0.5: no consistent difference.** Confidence low. If this fails toward "A agrees
   better", a doubled band reads slightly worse at this level. If toward "B", it reads better.

## Known confounds

* As in findings 71–73, the labels are partly pseudo-labels made with default rendering. If they were
  made at or near step 0.5, that favours the reference arm.
* One scroll, one 3D ink model; the 8 segments share both.

## Cost

32 whole-segment renders at level 2 (about 3–5 min each, cold cache first) and 24 comparisons:
about 2.5–3.5 h unattended. A new chunk cache under `spiral_out/band_study/vchome`, guarded at 300 GB.
