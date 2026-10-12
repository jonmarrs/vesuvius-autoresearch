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
2. **Lead with what landed in villa.** September paid $250 for "assorted useful merged villa PRs" and cited nothing
   else in the filing. villa #2022 was opened 2026-10-09 after its gate passed 33/33 at `a329895ea` and MERGED
   2026-10-11 by @pmh47 ([merge commit](https://github.com/ScrollPrize/villa/commit/7a7b3f677991954ec5ecff17b9b08ab30ff6a926)).
   villa #2044 (`get_ink_metrics --sequential-folds`, a code fix) opened 2026-10-11 Pacific and
   **merged 2026-10-11 Pacific** (`2026-10-12T01:49:09Z`,
   [merge commit](https://github.com/ScrollPrize/villa/commit/9afddaf0fdc12efe088bab7b82534c4f9a79e536)).
   On filing day, list every villa PR merged in October first in part (2) and in the URL field, then re-check
   #2022, #2044, #1928 and any other open PR, and quote any maintainer reply verbatim.
3. ScrollGT 0.6.0 (the held-out split) was tagged on 2026-10-11 and 0.7.0 (the ERL fix, finding 85) on 2026-10-12.
   The URL field cites `tree/v0.7.0`; the test binds the cite to ScrollGT's newest tag, so a later release must update
   it. Findings 84–85 are folded in (2026-10-12).
4. Finding 85 measures an open villa PR (#1934). The user-approved comment sharing it with the author was posted
   2026-10-12 (https://github.com/ScrollPrize/villa/pull/1934#issuecomment-6131993208) and is cited in part (2). On filing day, re-read the thread: quote any reply verbatim, record
   whether #1934 is still open, and do not characterise silence.
5. Re-run `tests/test_filing_2026_10_numbers.py`. Every number below is bound to the file it comes from.
6. Check every URL returns 200.

---

## URL field

```
https://github.com/ScrollPrize/villa/pull/2022
https://github.com/ScrollPrize/villa/pull/2044
https://github.com/jonmarrs/vesuvius-autoresearch
https://github.com/jonmarrs/inkdelta
https://github.com/jonmarrs/inkagree
https://github.com/jonmarrs/scrollgt/tree/v0.7.0
https://github.com/ScrollPrize/villa/pull/1928
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

**(2) How it increases the probability of reading.**

**Merged into villa this month:**
[villa #2022](https://github.com/ScrollPrize/villa/pull/2022) (merged 2026-10-11). `autoresearch.md` now launches
the runner villa ships with the flags it takes. Before, a variant launched the documented way ran as the baseline.

[villa #2044](https://github.com/ScrollPrize/villa/pull/2044) (**merged 2026-10-11 Pacific**).
`get_ink_metrics.py` launched every fold together, exhausting workstation memory on outer windings.
The fix adds opt-in `--sequential-folds`, averages folds in place and prints a hint for `rc=-9` failures.
Its before/after runs show the w120–w129 strip completing on one GPU where concurrent folds were killed
for lack of memory. The default fold concurrency is preserved; sequential execution is slower and
reduces peak memory.

villa's autoresearch loop keeps or discards a change by one number, `total_fg_pixels`. This month we checked
three things that number silently depends on, against villa's own code and villa's own ink labels:

* **The runner documentation did not match the shipped CLI.** Before the fix,
  `runners/run_single.py` exited before starting when launched with the documented
  environment variables. With its required flags added
  but GPUs pinned as documented, the fit silently ran as a single process. A config change passed
  through the environment, the documented way to try a variant, was silently dropped, so the
  "variant" ran as the baseline. Measured by running villa's runner with its steps stubbed.
  #2022 fixed the doc.
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

Separately, on fiber tracing, we tested whether villa's published fiber segmentation model,
`scrollprize/fiber_hz_vt`, works on cubes it never trained on. Its training fingerprint matches villa's
Dataset002, which holds all 11 fiber cubes of our ScrollGT benchmark (finding 82). villa's Dataset004 adds 10
annotated cubes the model never saw, and we pre-registered predictions for them (finding 83):
* **On Scroll 3, a scroll it never saw, it holds.** Median connected-components coverage of the hand-traced
  fibers is 0.826, against 0.822 on the in-sample 512³ cubes.
* **On two new Scroll-5 cubes it fails.** Coverage is 0.64 and 0.53, against 0.82–0.91 on the in-sample
  Scroll-5 256³ cubes. A pre-registered follow-up (finding 84) shows it is a real miss:
  * not a frame offset: the best shift within ±4 voxels gains at most 0.0020;
  * not a threshold: at P ≥ 0.1 coverage is 0.764 and 0.689, still below every in-sample Scroll-5 cube;
  * 19.6% and 25.2% of their hand-traced fiber has no voxel at P ≥ 0.05 within 2 voxels, against 5.2–16.9% in
    sample and 5.7–10.7% on Scroll 3.

  The cause (the region of the scroll, the cubes' content or their annotators) is unknown, and two cubes cannot
  separate them.

We also scored an open villa PR's automated fiber generator
([#1934](https://github.com/ScrollPrize/villa/pull/1934), every default) on all 21 cubes, pre-registered (finding 85):
* its fibers cover 19–38% of the hand-traced fiber length on 19 cubes, and 4% and 8% on the two new Scroll-5 cubes,
  where the mask it was fine-tuned from also fails;
* before ScrollGT 0.7.0, merge-penalized ERL ranked it above our tracer on all 8 Scroll-3 cubes. That lead came from
  covering about half as much fiber. ERL was averaged over covered fiber only, so dropping short fragments raised it.
  Normalised by ground-truth length, it trails our tracer on 21 of 21 cubes (raw) and 20 of 21 (merge-penalized).
* the cubes are at 7.91 µm, finer than the 8.64 and 9.362 µm pitches its fine-tune trained on (its model card),
  and only the defaults were run;
* the measurement was shared with its author on the PR ([comment](https://github.com/ScrollPrize/villa/pull/1934#issuecomment-6131993208), 2026-10-12).

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
* [ScrollGT](https://github.com/jonmarrs/scrollgt) (MIT), our fiber and ink benchmark, now measures generalization:
  * 0.5.0 moves three fiber targets to villa's current annotations and discloses that the reference mask trained
    on every target. No published ranking reverses (finding 82).
  * 0.6.0 adds finding 83's 10 cubes as a `held_out` split. Each row must equal finding 83's, and it refuses to average
    held-out scores with in-sample ones.
  * 0.7.0 closes a gaming route in its fiber metric (finding 85). ERL was averaged over covered fiber only, so
    deleting a labelling's short fragments raised it. It now divides by the ground-truth length. All 126 published
    rows were re-scored and each reproduces its old value exactly under the old definition. One claim reverses:
    held out, our tracer leads connected components on merge-penalized ERL on 9 of 10 cubes, not 10.

**(4) Evidence.**
* Each study was pre-registered before its data, and each has a report and its scripts in
  https://github.com/jonmarrs/vesuvius-autoresearch (findings 69–85 in
  `reports/SPIRAL_FINDINGS_SUMMARY.md`).
* Every figure here is bound by a test to the file that produced it.
* [villa #2044](https://github.com/ScrollPrize/villa/pull/2044) records the memory limits, hardware,
  before/after runs and the averaging comparison behind the scorer fix. The full GPU scorer has
  run-to-run variation; bit-identical output was checked for the averaging step, not the whole run.
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
  * it still loses on raw ERL everywhere (3.9–6.2×);
  * on merge-penalized ERL it is ahead on 4 of 11, all three 512³ cubes among them;
  * one prediction failed: I predicted it would trail on all eight 256³ cubes, and it leads on one.

  Its labellings reproduce the old rows exactly under the old scorer, so the reversal is the scorer's.
  `reports/tracer_rescore.md`.
* **ScrollGT's fiber scores were in-sample, and it did not say so until 0.5.0.** Its reference mask trained on all
  11 of its fiber targets (finding 82). On those, a score built on the mask measures the instance step on a
  segmentation that has seen the cube.
* **A correction, made and registered before recomputing:** my label-based analyses (findings 71–76)
  first scored the whole surface. villa's labels exist only inside its supervision mask (3–13% of each
  segment), so unannotated ink counted as a miss. Re-analysed where the labels are defined:
  * most findings survive;
  * finding 75 survives with smaller effects;
  * finding 74 does not survive as stated (step 0.5 vs 1.0 is not consistent).

  inkagree 0.3.0 makes the supervised region its default. `reports/supervised_reanalysis.md`.
* **Sixteen of my registered predictions failed**, and the reports say so:
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
  * finding 83 prediction 1 (the fiber mask's coverage would drop on Scroll 3, which it never saw: the median is
    0.826, against 0.822 on the in-sample 512³ cubes).
  * finding 84 prediction 3 (the mask's misses on the two new Scroll-5 cubes would be no softer than in sample: the
    soft-miss fraction is 0.340 on both, above the in-sample maximum of 0.289).
  * finding 85 prediction 1 (the generator's raw ERL would beat our tracer's on 9 of 11 in-sample cubes: it did on 5).
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
* Not "the fiber mask does not generalize". It holds on Scroll 3 and fails on two Scroll-5 cubes, cause unknown.
* Not "deleting fragments cannot raise ERL" under ScrollGT 0.7.0. When the scorer's tolerance joins the runs around a
  deleted fragment, ERL can still rise legitimately.
* Not "the #1934 generator is worse than our tracer" as a headline. One setting (its defaults), cubes below its
  training resolution, and in-sample rows on 11 cubes. Coverage is the measured gap.
* Not "the Scroll-5 miss is the annotators". Finding 84 rules out a frame offset and a threshold, nothing more.
* Not "held out" as secrecy. The fiber ground truth is public; `held_out` means only that the reference mask did
  not train on the cube.
* Not "agrees with ground truth" for any label-based number. The render is in-sample on the labelled
  segments.
