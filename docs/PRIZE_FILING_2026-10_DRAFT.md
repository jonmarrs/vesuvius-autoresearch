# October 2026 Progress Prize — DRAFT (not submit-ready)

**Status: draft, started 2026-10-03. The October round OPENED 2026-10-03** (villa #1947, `ed426faf0`):
* **deadline 11:59pm Pacific, October 31st, 2026**;
* form `https://docs.google.com/forms/d/e/1FAIpQLSc4flEfgK2nyjoczz2_U_XrIGMlgrnSknWatLqrFPnbtKfZwg/viewform`,
  a new URL again.

The criteria text is unchanged from September: #1947 touched only the deadline and form lines. The form
was read on 2026-10-03. It asks for name, team description and Discord name, then the two fields this
draft answers: the URL list (required), and "What is your contribution?" with the same four parts as
September (required). Then T&C. **Re-check it on filing day.** In September the criteria changed
mid-month.

**For pasting, open this file. Never copy from terminal output.** In September a terminal-wrapped line
clipped "#1780" to "#17".

## Filing-day checklist

1. Re-read the **whole** Progress section of villa `scrollprize.org/docs/34_prizes.md` at current
   upstream: form URL, deadline and criteria. The criteria changed mid-month in September.
2. The runner PR is villa #2022: opened 2026-10-09 after the gate passed 33/33 at `a329895ea`. On filing day,
   record its state (open, merged or closed) and quote any maintainer reply verbatim.
   Re-check #1928's state.
3. Re-run `tests/test_filing_2026_10_numbers.py`. Every number below is bound to the file it comes from.
4. Check every URL returns 200.

---

## URL field

```
https://github.com/jonmarrs/vesuvius-autoresearch
https://github.com/jonmarrs/inkdelta
https://github.com/jonmarrs/inkagree
https://github.com/jonmarrs/scrollgt/tree/v0.4.1
https://github.com/ScrollPrize/villa/pull/1928
https://github.com/ScrollPrize/villa/pull/2022
```

---

## "What is your contribution?"

**(1) Which scroll data.** PHerc. Paris 4 (Scroll 1):
* villa's spiral-fitting dataset (windings w120–w129);
* the **8 segments for which villa now publishes ink labels** on the current 2.4 µm frame
  (`20230702185753`, `20230929220926`, `20231007101619`, `20231012184424`, `20231016151002`,
  `20231031143852`, `20231106155351`, `20231210121321`), rendered from villa's published 3D ink
  prediction (`v3-78k-fullsup`).

Published villa artifacts only, one consumer GPU.

**(2) How it increases the probability of reading.** villa's autoresearch loop keeps or discards a
change by one number, `total_fg_pixels`. This month we checked three things that number silently
depends on, against villa's own code and villa's own ink labels:

* **The runner villa ships does not match the doc the loop follows.** Launched with the doc's
  environment variables, `runners/run_single.py` exits before starting. With its required flags added
  but GPUs pinned as documented, the fit silently runs as a single process. A config change passed
  through the environment, the documented way to try a variant, is silently dropped, so the
  "variant" runs as the baseline. Measured by running villa's runner with its steps stubbed.
  [villa #2022](https://github.com/ScrollPrize/villa/pull/2022), opened 2026-10-09, fixes the doc.
* **A new render setting moves the metric far more than it moves reading.** villa #1818 added
  `vc_render_tifxyz --surface-interpolation smooth`. Its default is byte-identical to earlier builds.
  On the 8 labelled segments, in villa's own scoring pipeline:
  * on villa's fine segment meshes, smooth moves `total_fg_pixels` by −3.6% to +4.1% per segment, and
    the scorer's agreement with villa's labels does not change (|ΔAP| < 0.001 in all 8, none resolved);
  * on grids as coarse as the spiral surfaces villa's loop scores, the count moves by −7.9% to +19.4%
    per segment (−31.9% to +41.5% per window). The raw render agrees only slightly better with villa's labels (about
    1% of AP), and the scorer's agreement does not consistently change.

  The effect scales with grid cell size (measured). Comparing runs rendered in different modes would
  bias a keep/discard decision by more than the gains the loop chases.
* **The install route changes how well the metric's renders agree with villa's labels, not only how much
  ink they find.**
  villa's published sampler image samples a thinner band than any current source build (finding 66:
  −5% to −9% ink count). Against villa's labels at the metric's own settings, on all 8 segments and
  where the labels are defined, the source build's band agrees better (8 of 8, about +5% AP), and a band
  twice as wide agrees better still (8 of 8, about +8%). The stale image costs agreement (on segments the ink model trained on),
  and the metric's default band is narrower than the best tested.
* **The comparison tool now reads what villa's runner writes.** inkdelta 0.3.0 rejected villa's real
  `--seeds` output as invalid; 0.4.0 reads it. 0.5.x refuses to compare runs rendered in different
  modes.

**(3) What it enables that was not possible before.**
* [inkagree](https://github.com/jonmarrs/inkagree) (MIT; first released 2026-10-03, now 0.3.0, which evaluates only
  where villa's labels are defined): **a label-anchored
  check of render settings, scorers or models.** It renders a segment's published 3D ink prediction
  through the segment's own mesh, exactly onto villa's label canvas (same shape, alignment peak at zero
  offset). Then it compares two arms: exact AP/AUC against villa's labels, an alignment gate, and a
  paired block bootstrap. "Does setting X read better?" becomes about an hour on one GPU per segment.
  **First use:** villa's tutorial renders with `--slice-step 0.5` for a "focused band". Against villa's
  labels (where defined) on all 8 segments, 0.5 beats a thinner band (0.25: 8 of 8, about −6% of AP) and a
  much wider one (2.0: 8 of 8, about −20%). Against 1.0 there is no consistent difference. The tutorial's
  choice sits in the best range.
* [inkdelta](https://github.com/jonmarrs/inkdelta) 0.5.2 (MIT, standard library only):
  * runs directly on villa's `run_single --seeds` output;
  * finds sweep logs;
  * checks `aggregate_metrics.json`;
  * flags mixed render modes from the render log.

**(4) Evidence.**
* Each study was pre-registered before its data, and each has a report and its scripts in
  https://github.com/jonmarrs/vesuvius-autoresearch (findings 69–72 in
  `reports/SPIRAL_FINDINGS_SUMMARY.md`).
* Every figure here is bound by a test to the file that produced it.
* inkdelta: CI on Python 3.10–3.13. Its corpus validations are unchanged since 0.3.0.
* inkagree reproduces findings 71 and 72 exactly (16 of 16 segment results, every interval), and its
  CI covers Python 3.10–3.13 (`reports/inkagree_validation.md`).
* **Community use:** ScrollGT, our benchmark from earlier rounds, received its first outside contribution.
  * Luke Finigan found that its fiber scorer depended on the order its ground-truth edge rows are
    stored in. He fixed it and rescored all 11 targets
    ([scrollgt#1](https://github.com/jonmarrs/scrollgt/pull/1)).
  * [v0.4.0](https://github.com/jonmarrs/scrollgt/tree/v0.4.0) versions the scorer and refuses to compare
    scores across versions. It verifies every published floor against the new scorer (55 of 55) and
    publishes the correction.
  * [v0.4.1](https://github.com/jonmarrs/scrollgt/tree/v0.4.1) re-measures our own tracer with the corrected
    scorer, pre-registered (vesuvius-autoresearch finding 80), and reverses one of our published claims; see the
    disclosure below.

---

## Required disclosure — include it

* **A published claim of ours reversed (finding 80).** ScrollGT said our fiber tracer lost to connected
  components on both metrics on every cube. Re-measured with the corrected scorer on all 11 cubes:
  * it still loses on raw ERL everywhere (3.9–6.3×);
  * on merge-penalized ERL it is ahead on 4 of 11, all three 512³ cubes among them;
  * one prediction failed: I predicted it would trail on all eight 256³ cubes, and it leads on one.

  Its labellings reproduce the old rows exactly under the old scorer, so the reversal is the scorer's.
  `reports/tracer_rescore.md`.
* **A correction, made and registered before recomputing:** my label-based analyses (findings 71–76)
  first scored the whole surface. villa's labels exist only inside its supervision mask (3–13% of each
  segment), so unannotated ink counted as a miss. Re-analysed where the labels are defined:
  * most findings survive;
  * finding 75 survives with smaller effects;
  * finding 74 does not survive as stated (step 0.5 vs 1.0 is not consistent).

  inkagree 0.3.0 makes the supervised region its default. `reports/supervised_reanalysis.md`.
* **Thirteen of my registered predictions failed**, and the reports say so:
  * finding 70 (smooth would move the count < 1% in every crop window: it moved up to ±20%);
  * finding 71 prediction 1 (failed on three exclusions, one caused by a defect in my alignment gate);
  * finding 72 prediction 1 (the count was sensitive in 15% of windows, not ≥ 25%).
  * per-crop normalisation as the cause of finding 70's size (re-scored with one shared p95,
    the median |Δ| stayed at 4.7%, not < 2.5%).
  * finding 73 prediction 2 (smooth's scorer output would agree better with the labels on coarse grids:
    2 of 8, not ≥ 6).
  * finding 74 predictions 2 and 3 (no difference between slice steps 0.25 or 1.0 and the tutorial's 0.5:
    0.5 was better in 8 of 8 and 7 of 8).
  * finding 75 predictions 1 and 2 (no difference between the published image's band, or a wider one, and
    the source build's: the source build beat the first, and the wider band beat it, both in 8 of 8).
  * finding 76 prediction 1 (villa's ink count would track labelled-ink density across regions: ρ = +0.04,
    an ambiguous null, since the raw render does not track it either).
  * the correction's prediction 3 (findings 74 and 75 would survive: 75 did, 74 did not as stated).
  * finding 79 prediction 1 (an unthresholded ink count would be less noisy across seeds on pinned code:
    R = 0.91 [0.56, 1.47], no detectable difference; it was on current code, R = 0.52 [0.35, 0.91]).
  * finding 80 prediction 2 (the tracer would trail connected components on merge-penalized ERL on all
    eight 256³ cubes: it leads on `s5_14997`, 38.56 vs 33.09).
* **The effect's size depends on grid cell size** (finding 73, measured): about 1% per window on
  villa's 20-voxel segment meshes, a 6.2% median and up to ±40% per window on 80-voxel grids like the
  spiral surfaces. Quote the size with the grid.
* villa's scroll labels are partly pseudo-labels, made with default-mode geometry. That favours the
  default mode in any comparison against them, and still no difference appeared.
* **The rendered ink prediction is in-sample on these segments.** The 3D ink model's own config
  (`scrollprize/ink_3d_dino_guided`, copied to `reports/evidence/`) trains on villa's PHercParis4 ink
  dataset, which is exactly these 8 segments, with full supervision and no held-out regions.
  * Agreement with the labels is therefore training-set agreement.
  * Comparisons between render settings of the same model measure which setting best reproduces what the
    model was trained toward. That can favour settings that match how its targets were made (a ±3-voxel
    projection).
  * Finding 78, `reports/scorer_tracking_gap.md`.

## Do not add

* Not "smooth reads better". Only its raw render is slightly more faithful, on coarse grids; the
  scorer's agreement does not change.
* Not "the scorer is fragile" as an established fact. Finding 72's sensitivity prediction failed.
* No adoption claim for inkdelta or the measurements unless one exists on filing day.
* Not "villa's objective mis-ranks fits". Finding 78 shows its count is sparse (about 2% of annotated
  ink), not that it ranks fits wrongly, and its render-side comparison is in-sample.
* Not "agrees with ground truth" for any label-based number. The render is in-sample on the labelled
  segments.
