# Pre-registration: does villa #1818's `--surface-interpolation smooth` change what the scorer reads?

**Written 2026-10-02, after the one-crop smoke and before any window below was rendered.** Chain
`repro/spiral_render/run_interp_windows.sh`, analysis `scripts/analyse_interp_windows.py`. Both are
committed with this file.

## What is already known (smoke, `reports/interp_smoke.json`)

On one 2048×1024 crop of `detfit_up1`'s saved flat, sampled exactly as `render_ink.py` samples it:

* The pre-#1818 source build (`75c79ac5f`) and the post-#1818 build (`f637f3b35`) at the default are
  **byte-identical**, and both equal the same window of the PR #1905 build's full render. #1818's
  default (`linear`) is inert, and so is everything else between those two commits.
* `smooth` changes 6.3% of max-composite pixels. `total_fg_pixels` moves 38,927 → 38,893 (−0.09%).
  A re-score of identical input is 0 px apart.
* `overall_line_score` moves 0.523 → 0.621, but on 9 vs 10 detected gaps. The score carries an
  evidence factor `min(1, gaps/10)`, so most of that change is one extra peak. **Not evidence.**

## The question

Across the surface, how much does `smooth` change (a) `total_fg_pixels`, villa's objective, and
(b) `overall_line_score`, the scorer's text-line measure, when each is measured on enough lines to
mean something? This is descriptive: it gives a range, not a hypothesis test.

## Method

* **Surface:** `detfit_up1`'s saved flat (md5 of x/y/z checked before each window). One surface.
  This is a characterisation of the flag, not of surfaces.
* **Windows:** 8 full-height crops, 2048 px wide × 4460 px tall (y 0..4460). The range
  [32768, 90680), from the start of the well-covered region to the strip's end, is split into 8 equal
  sectors. In each sector, the 2048-px window (x step 512) that lies **entirely inside the sector**
  and has the **largest valid coverage** in the published render's slice 02 is chosen, so windows
  cannot overlap. They are chosen on coverage alone, never on ink or on any linear/smooth output.
  The analysis script recomputes the choice and checks it. *(Drafting fix before any render: the
  first rule used fixed 8192-px sectors to 98304, which left the last sector empty past the strip's
  90,680-px width and let adjacent sectors pick overlapping windows, 65024 and 65536.)*
* **Arms per window:** `vc-render:sampler-f637f3b35` at the default (`linear`) and with
  `--surface-interpolation smooth`. Same image and arguments as the smoke otherwise
  (`--scale-segmentation 4 --scale 0.25 --group-idx 1 --num-slices 5`, remote ink zarr).
* **Scoring:** max-composite → p95 → JPEG q95, exactly as `render_ink.py` builds a strip, per window.
  Then the pinned scorer (`detfit_up1/spiral-fitting`, serial folds), one arm per window and mode.
* **Integrity:** a skipped render, a failed render or score, or `smooth` not engaging fails the
  chain. Disk guard: stop if the remote cache exceeds 200 GB.

## Reported

* Per window: Δ`total_fg_pixels` (smooth/linear − 1), Δ`overall_line_score`, and the line gap counts.
* Across windows: the median and range of each, and how many windows have each sign.

## Prediction, fixed now

* **`total_fg_pixels`: |Δ| < 1% in every window.** Confidence moderate. The smoke crop moved 0.09%,
  and 6% of pixels changing mostly by a few grey levels should barely move a thresholded count.
* **`overall_line_score`: no consistent direction**, i.e. not all 8 of one sign. Confidence low. The
  author's mechanism (steps and creases at cell edges) could sharpen lines, but the smoke's
  apparent gain was an artifact.

If both predictions hold, the conclusion is that the flag is safe to switch on for the loop's
objective and does not, on this evidence, read text better. Then **no full-strip study is warranted.**

## Cost

16 crop renders on the new build (each a few minutes, cold windows longer) and 16 crop scorings.
About 1.5–3 h, unattended. No fits, no full-strip renders.
