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
   #2022, #2044 and any other open PR, and quote any maintainer reply verbatim. villa #2141 (the track-DBM fix)
   opened 2026-10-18 and villa #2155 (the README's pip route) on 2026-10-19; neither had merged on 10-19. If either
   merges, add it with the before → after its PR body measured:
   * #2141: on Python 3.10 and 3.11, villa's own reader fails to open a published track store (a WAL database) in a
     read-only directory, with "attempt to write a readonly database". With the fix it opens it.
   * #2155: on Linux x86-64 the README's pip command installs neither track-extraction backend. With the fix it
     installs `brook-cu12`, `cucim-cu12` and `cupy-cuda12x`.

   `scripts/check_filing_upstream_claims.py --month 2026-10 --filing
   docs/PRIZE_FILING_2026-10_DRAFT.md` must PASS: it fails while an October merge of ours has no "(merged
   YYYY-MM-DD)" claim, or a claim gives the wrong Pacific date. villa #1928 (the inkdelta
   catalogue entry) was closed by villa's 14-day inactivity bot on 2026-10-14 with no maintainer comment, so the
   URL field no longer cites it.
3. ScrollGT 0.6.0 (the held-out split) was tagged on 2026-10-11, 0.7.0 (the ERL fix, finding 85) on 2026-10-12, and
   0.8.0 (villa's neural tracer as an entrant, finding 91) and 0.8.1 (the pitch note on its Scroll-3 lead, finding 92)
   on 2026-10-19, and 0.8.2 (the placement note on five in-sample cubes, #157, and the tolerance note, finding 94) on
   2026-10-20. The URL field cites
   `tree/v0.8.2`; the test binds the cite to ScrollGT's newest tag, so a later
   release must update it. Findings 84–85 are folded in (2026-10-12). Finding 93 and the placement measurements
   (#151, #157) are folded in (2026-10-20).
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
https://github.com/jonmarrs/scrollgt/tree/v0.8.2
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
the runner villa ships with the flags it takes. Followed as written before, the launch failed in 5 measured ways
(below). In one of them, a variant launched the documented way ran as the baseline.

[villa #2044](https://github.com/ScrollPrize/villa/pull/2044) (**merged 2026-10-11 Pacific**).
`get_ink_metrics.py` launched every fold together, exhausting workstation memory on outer windings.
The fix adds opt-in `--sequential-folds`, averages folds in place and prints a hint for `rc=-9` failures.
Its before/after runs used one RTX 4090 in a 26 GiB memory limit:
* on the w120–w129 strip (352M px), stock scoring was killed for lack of memory 70 s in, at ≥ 27.6 GB;
  `--sequential-folds` scored it with a 13.8 GB peak in 1,009 s;
* on a smaller inner strip, the three modes' counts agree to within 0.005%, the scorer's run-to-run noise.

The default fold concurrency is preserved; sequential execution is slower and reduces peak memory.

villa's autoresearch loop keeps or discards a change by one number, `total_fg_pixels`. This month we checked
three things that number silently depends on, against villa's own code and villa's own ink labels:

* **The runner documentation did not match the shipped CLI.** Run with its steps stubbed (`a329895ea`), villa's
  `runners/run_single.py` failed the documented launch in 5 ways, none with a warning:
  * launched with the documented environment variables, it exited with status 2 before starting;
  * with its required flags added but 4 GPUs pinned as documented, it ran the fit as 1 process, not 4;
  * a config change passed through the environment, the documented way to try a variant, was dropped, so the
    "variant" ran as the baseline;
  * W&B logging stayed on, and output directories could not be shared.

  #2022 fixed the doc (1 file, +11/−10).
* **A new render setting moves the metric far more than it moves reading.** villa #1818 added
  `vc_render_tifxyz --surface-interpolation smooth`. Its default is byte-identical to earlier builds.
  On the 8 labelled segments, in villa's own scoring pipeline:
  * on villa's fine segment meshes, smooth moves `total_fg_pixels` by −3.6% to +4.1% per segment, and
    the scorer's agreement with villa's labels does not change (|ΔAP| < 0.001 in all 8, none resolved);
  * on grids as coarse as the spiral surfaces villa's loop scores, the count moves by −7.9% to +19.4%
    per segment (−31.9% to +41.5% per window). The raw render agrees only slightly better with villa's labels (about
    1% of AP), and the scorer's agreement does not consistently change.

  The effect scales with grid cell size (measured): about 1% per window on 20-voxel meshes, a 6.2% median on
  80-voxel grids. For scale, the loop metric's fit-to-fit noise on spiral fits is 7.4% (pooled CV, 95% CI
  5.1–13.4%, finding 57). A run rendered in one mode cannot be compared with a baseline rendered in the other.
* **The install route changes how well the metric's renders agree with villa's labels, not only how much
  ink they find.**
  villa's published sampler image samples a thinner band than any current source build (finding 66:
  −5% to −9% ink count). Against villa's labels at the metric's own settings, on all 8 segments and
  where the labels are defined, the source build's band agrees better (8 of 8, about +5% AP), and a band
  twice as wide agrees better still (8 of 8, about +8%). The stale image costs agreement (on segments the ink model trained on),
  and the metric's default band is narrower than the best tested.
* **The comparison tool now reads what villa's runner writes.** On a tree written by villa's own runner, inkdelta
  0.3.0 failed 3 of the 4 runs we tried: `check` on `--seeds` output, plus `compare` and `noise`, which reported fresh
  runs as not fresh. On the same tree, 0.4.0's `compare` and `noise` return results. 0.5.x refuses to compare runs
  rendered in different modes.

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

We also measured villa's own neural fiber tracer
([#2045](https://github.com/ScrollPrize/villa/pull/2045) (merged 2026-10-11); checkpoint
`scrollprize/fiber_single_small`, volume mode, every default) on the same 21 cubes, pre-registered (finding 91; all
four predictions held):
* **On Scroll 3, which no entrant trained on, it ranks first on merge-penalized ERL.** It is above our tracer on 8 of
  8 cubes (1.11–1.33×, median 25.30 against 20.98), and above #1934's generator and connected components on 8 of 8.
  It covers less: median coverage 0.480, against our tracer's 0.551 (below it on 7 of 8) and connected components'
  0.826.
* **Everywhere else it trails, including Scroll 1, its own training scroll.** On the 11 cubes the reference mask
  trained on, our tracer leads on all 11 (median 7.82 against 20.75). Those cubes favour our tracer and connected
  components, which are built from that mask. On the two held-out Scroll-5 cubes its coverage is 0.134 and 0.096.
* **The Scroll-3 lead depends on the pitch it ran at** (finding 92, pre-registered). Resampled from the cubes' 7.91 µm
  to its 9.6 µm training pitch, it scores lower on all 21 cubes (merge-penalized ERL a median 0.63 of the rows above)
  and leads our tracer on none of the 8 Scroll-3 cubes. It still trails on all 11 in-sample cubes, so pitch is not
  why the scrolls differ. Its runs are deterministic: both repeated cubes reproduce exactly.
* **Not its seeding** (finding 93, pre-registered; all three predictions failed). Its seeding is set in grid voxels,
  so at 9.6 µm it starts fewer traces. Seeded per micrometre there, it recovers only to 0.67 of the native rows (from
  0.63) and leads our tracer on 0 of 8 Scroll-3 cubes. Seeded as sparsely at 7.91 µm, it keeps 0.88 and its lead on
  7 of 8. So the lead depends on the pitch the network reads, or on the resampling, and ScrollGT 0.8.1's note stands.
* **Where the scrolls differ** (measured after finding 92, not pre-registered). On the 512³ cubes, only the two thin
  entrants, this tracer and #1934's generator, score higher on Scroll 3 than on Scroll 5's three in-sample cubes
  (2.71× and 2.12×), and at a 4-voxel tolerance most of that goes (1.26× and 0.81×). On those Scroll-5 cubes their
  centrelines lie 2–4 voxels from the ground truth more often. On 5 of the 11 in-sample cubes the ground truth itself
  sits about a voxel off the CT's fibers: the two entrants agree on the shift, and the CT alone puts the fibers'
  centres 0.51–0.93 voxels off. Correcting for it recovers part of the gap (0.06–0.09 of this tracer's share within 2
  voxels), not all. The scan, fiber width and how precisely each scroll was annotated remain untested.
* **At a 4-voxel tolerance** (finding 94, pre-registered; one of its two predictions failed). Its Scroll-3 lead holds
  and widens: a median 2.22 times our tracer's merge-penalized ERL, against 1.26 at 2, on 8 of 8 cubes. Its in-sample
  deficit narrows from 0.36 to 0.71 of ours, and reverses on the three in-sample 512³ cubes (median 49.50 against
  43.69). It still trails on the eight 256³ ones and both held-out cubes.

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
  * 0.5.0 moves three fiber targets to villa's current annotations (22–53% more annotated fibers) and discloses that
    the reference mask trained on every target. The mask's coverage of those three falls from 0.88–0.93 to
    0.76–0.82, and no published ranking reverses (finding 82).
  * 0.6.0 adds finding 83's 10 cubes as a `held_out` split. Each row must equal finding 83's, and it refuses to average
    held-out scores with in-sample ones.
  * 0.7.0 closes a gaming route in its fiber metric (finding 85). ERL was averaged over covered fiber only, so
    deleting a labelling's short fragments raised it. Deleting our tracer's instances under 400 voxels raised it
    17% (35.39 → 41.46) while coverage fell from 0.62 to 0.38. It now divides by the ground-truth length. All 126 published
    rows were re-scored and each reproduces its old value exactly under the old definition. One claim reverses:
    held out, our tracer leads connected components on merge-penalized ERL on 9 of 10 cubes, not 10.
  * 0.8.0 adds villa's own neural fiber tracer (villa #2045) as a third entrant, with finding 91's rows and their
    provenance, so the benchmark's published tables now carry its Scroll-3 lead and its deficit elsewhere.
  * 0.8.1 notes, wherever that lead is claimed, that it depends on the pitch: resampled to its 9.6 µm training pitch,
    the tracer leads ours on none of the 8 Scroll-3 cubes (finding 92). No row changes.
  * 0.8.2 notes, on those 5 in-sample cubes, that the hand-traced centrelines sit about a voxel off the CT's fibers:
    the two thin entrants agree on a shift of 1.01–1.53 voxels, and the CT puts the fibers' centres 0.51–0.93 voxels
    off (#157). It also notes, where the neural tracer's in-sample deficit is claimed, that the deficit is a
    tolerance-2 result on the 512³ cubes (finding 94). No row changes.

**(4) Evidence.**
* Each study was pre-registered before its data, and each has a report and its scripts in
  https://github.com/jonmarrs/vesuvius-autoresearch (findings 69–85 in
  `reports/SPIRAL_FINDINGS_SUMMARY.md`; findings 91–94 in `reports/neural_tracer_entrant.md`,
  `reports/neural_tracer_pitch.md`, `reports/neural_tracer_seeding.md` and `reports/tolerance4_rescore.md`; the
  placement and ground-truth offset
  measurements in the last section of `reports/neural_tracer_entrant.md`).
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
* **Twenty-two of my registered predictions failed**, and the reports say so:
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
  * finding 92 predictions 2 and 3 (at its 9.6 µm training pitch, villa's neural tracer would keep its Scroll-3 lead
    on at least 6 of 8 cubes: it kept it on 0; its median merge-penalized ERL would stay within 0.85–1.15 of the
    native rows: 0.63).
  * finding 93 predictions 1–3 (seeded per micrometre at 9.6 µm, villa's neural tracer would recover to at least 0.85
    of the native rows: 0.67; regain its Scroll-3 lead on at least 6 of 8 cubes: 0; and, seeded as sparsely at
    7.91 µm, fall to at most 0.80: 0.88).
  * finding 94 prediction 2 (at tolerance 4, villa's neural tracer would still trail our tracer on at least 9 of 11
    in-sample cubes: it trailed on 8).
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
* Not "villa rejected inkdelta". #1928 was closed by the inactivity bot, not by a maintainer.
* Not "villa's objective mis-ranks fits". Finding 78 shows its count is sparse (about 2% of annotated
  ink), not that it ranks fits wrongly, and its render-side comparison is in-sample.
* Not "the fiber mask does not generalize". It holds on Scroll 3 and fails on two Scroll-5 cubes, cause unknown.
* Not "deleting fragments cannot raise ERL" under ScrollGT 0.7.0. When the scorer's tolerance joins the runs around a
  deleted fragment, ERL can still rise legitimately.
* Not "the #1934 generator is worse than our tracer" as a headline. One setting (its defaults), cubes below its
  training resolution, and in-sample rows on 11 cubes. Coverage is the measured gap.
* Not "villa's neural tracer beats ours" or "trails ours" as a headline. It ranks first on merge-penalized ERL on
  Scroll 3 with less coverage, and at tolerance 2 trails on the other 13 cubes, for reasons only partly measured (at
  4 it leads on three of them, finding 94). One checkpoint,
  defaults.
* Not "ScrollGT's ground truth is wrong on five cubes". Two entrants and the CT agree on an offset of about a voxel
  there, measured after the fact. It explains part of the in-sample gap, and the ground truth is unchanged.
* Not "the Scroll-5 miss is the annotators". Finding 84 rules out a frame offset and a threshold, nothing more.
* Not "held out" as secrecy. The fiber ground truth is public; `held_out` means only that the reference mask did
  not train on the cube.
* Not "agrees with ground truth" for any label-based number. The render is in-sample on the labelled
  segments.
