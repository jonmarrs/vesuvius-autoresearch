# Pre-registration: which install route's sampling agrees better with villa's labels, at the metric's settings?

**Written 2026-10-04, before any arm of this study was rendered.** Chain
`repro/spiral_render/run_metric_band_vs_labels.sh`. It uses inkagree 0.2.2 (`4add4cd`), pinned in its own
environment. Committed with this file.

## Why

Finding 66: the post-#1146 sampler (any source build after 2026-07-14) samples a band twice as thick as
villa's published image (built 2026-05-13). On the same surface that alone raised villa's ink count by
+5.0% to +9.2%. Which route's sampling is **more faithful** was never measured. Finding 74 (the
tutorial's level and band) found an interior optimum, but at a different level, slice count and band
width, so its direction does not transfer by assumption.

**Equivalence relied on** (finding 66, `reports/source_sampler_cannot_complete_here.md`): #1146 removed
`dsScale` (0.5 at group 1) from the slice offsets. So at group 1, the published image at step *s* samples
like a post-#1146 build at step *s*/2. That was verified to rounding for published step 2 vs post-#1146
step 1. Hence the published image's default (step 1) is a post-#1146 build at **step 0.5**.

## Method

* **Segments:** the 8 with villa labels on the 2.4 µm frame.
* **Arms:** inkagree's `metric` preset (`--group-idx 1 --scale 0.25 --num-slices 5`, villa's spiral-metric
  render settings, label level 3) on `vc-render:sampler-f637f3b35`:
  * step **1.0**: the post-#1146 / source-build default (reference A);
  * step **0.5**: the published image's sampling;
  * step **2.0**: a wider band, for the trend.

  Each arm is the max over slices, i.e. the raw rendered 3D-ink prediction. villa's 2D scorer is not
  applied; finding 72 showed it adds noise without adding faithfulness.
* **Comparisons:** `inkagree compare SEG DIR step1.0.tif stepX.tif --level 3` for X ∈ {0.5, 2.0}, with
  inkagree's defaults; then `inkagree summarize --k 6` per X.

## Predictions, fixed now

1. **0.5 vs 1.0 (published-image route vs source-build route): no consistent difference.** Confidence
   low. Finding 74 found the thinner band slightly worse at its level; this band is narrower to start
   with.
2. **2.0 vs 1.0: no consistent difference.** Confidence low. These metric bands are far narrower than
   finding 74's optimum, so widening may help rather than hurt; I do not predict a direction.

Whatever the verdicts, the result tells villa which install route's renders agree better with its labels
at the metric's own settings. That is the direct follow-up to finding 66.

## Known confounds

* Labels are partly pseudo-labels; the render setting used to refine them is unknown here. Neither arm is
  known to be favoured.
* One scroll, one 3D ink model; the segments share both.
* Raw renders only. villa's metric then applies its 2D scorer, which finding 72 found leaves label
  agreement unchanged.

## Cost

24 whole-segment renders at group 1 (finding 72's renders at this level took about 4–8 min each and
streamed a large chunk cache) and 16 comparisons: about 3–4 h unattended. Cache under
`spiral_out/route_cache`, guarded at 400 GB.
