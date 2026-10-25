# October 2026 Progress Prize — DRAFT (evidence checked; not submitted)

**Readiness review, 2026-10-23:** all 31 existing number/version checks pass,
the live upstream-claim check passes, and all 19 links in the pre-update draft
returned HTTP 200. The live form still says “October 2026 Progress Prizes”.
It also requires an email address, full name, team description and agreement
to the terms; Discord display name is optional. These personal fields and
consent have not been submitted. Re-check the form, links and live PR state
on filing day.

Use [the concise form answers](PRIZE_FILING_2026-10_FORM_ANSWERS.md) for the
small-fix bundle. This detailed draft preserves the broader research evidence
and disclosures. The [final-week plan](PRIZE_PLAN_2026-10_FINAL_WEEK.md) separates
work already landed from optional additions before the deadline.

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
   #2022, #2044, #2155 and any other open PR, and quote any maintainer reply verbatim.
   villa #2155 (the README's pip route) **merged 2026-10-21 Pacific**
   (`2026-10-21T19:50:31Z`, [merge commit](https://github.com/ScrollPrize/villa/commit/e016bc71d9b873b3e52871f42aa3e7a34520cfb1)).
   villa #2141 (the track-DBM fix), opened 2026-10-18, remains open at the 2026-10-23 review.
   Its latest update handles recognized SQLite stores on every Python version and preserves committed WAL pages;
   all five reader tests pass. If it merges, add its measured before → after:
   * #2141: on Python 3.10 and 3.11, villa's own reader fails to open a published track store (a WAL database) in a
     read-only directory, with "attempt to write a readonly database". With the fix it opens it.

   **Checked 2026-10-20:** #2141 also has [independent Windows validation from @vincentl065](https://github.com/ScrollPrize/villa/pull/2141#issuecomment-6290970541),
   the author of the original fallback: baseline leaves SQLite sidecars, the fix passes on Windows 11 / Python
   3.12.10 (2 passed, 2 skipped). Their reply ends “LGTM”. This is contributor feedback, not a merge; keep the
   filing's merged-contribution list unchanged until GitHub records one.

   #2258 (fractional fiber seed planes) and #2259 (headless AppImage CLI docs)
   are also open. Their available GitHub Actions runs and those of #2141 pass;
   Vercel previews need authorization. The linked integration cannot merge
   Villa PRs or open the prepared native-retry and reference-provenance PRs
   (HTTP 403). Pushed branches and passing local tests are not merged credits.

   `scripts/check_filing_upstream_claims.py --month 2026-10 --filing
   docs/PRIZE_FILING_2026-10_DRAFT.md` must PASS: it fails while an October merge of ours has no "(merged
   YYYY-MM-DD)" claim, or a claim gives the wrong Pacific date. villa #1928 (the inkdelta
   catalogue entry) was closed by villa's 14-day inactivity bot on 2026-10-14 with no maintainer comment, so the
   URL field no longer cites it.
3. ScrollGT 0.6.0 (the held-out split) was tagged on 2026-10-11, 0.7.0 (the ERL fix, finding 85) on 2026-10-12, and
   0.8.0 (villa's neural tracer as an entrant, finding 91) and 0.8.1 (the pitch note on its Scroll-3 lead, finding 92)
   on 2026-10-19, and 0.8.2 (the placement note on five in-sample cubes, #157, and the tolerance note, finding 94) on
   2026-10-20. 0.8.3 (the seed-rule note on the 256³ cubes, findings 96–97) and 0.9.0 (the scan around each cube,
   findings 97–98) were merged on 2026-10-24 and tagged together as v0.9.0. The URL field cites
   `tree/v0.9.0`; the test binds the cite to ScrollGT's newest tag, so a later
   release must update it. Findings 84–85 are folded in (2026-10-12). Finding 93 and the placement measurements
   (#151, #157) are folded in (2026-10-20), finding 94 on 2026-10-20, findings 95–97 on 2026-10-23, finding 98
   on 2026-10-24, and finding 99 on 2026-10-25.
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
https://github.com/ScrollPrize/villa/pull/2155
https://github.com/jonmarrs/vesuvius-autoresearch
https://github.com/jonmarrs/inkdelta
https://github.com/jonmarrs/inkagree
https://github.com/jonmarrs/scrollgt/tree/v0.9.0
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

[villa #2155](https://github.com/ScrollPrize/villa/pull/2155) (merged 2026-10-21).
The spiral-fitting README's pip route now selects `--group cuda`. On Linux x86-64, the old command
installed neither track-extraction backend; the corrected command installs `brook-cu12`, `cucim-cu12`
and `cupy-cuda12x`, matching the CUDA dependency group used by the documented uv route.

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
    the scorer's agreement with villa's labels does not change (where the labels are defined, its |ΔAP| is
    < 0.01 in all 8; 1 of 8 resolved, by 0.006);
  * on grids as coarse as the spiral surfaces villa's loop scores, the count moves by −7.9% to +19.4%
    per segment (−31.9% to +41.5% per window). The raw render agrees only slightly better with villa's labels (about
    1% of AP), and the scorer's agreement does not consistently change.

  The effect scales with grid cell size (measured): about 1% per window on 20-voxel meshes, a 6.2% median on
  80-voxel grids. For scale, the loop metric's fit-to-fit noise on spiral fits is 7.4% (pooled CV, 95% CI
  5.1–13.4%, finding 57). A run rendered in one mode cannot be compared with a baseline rendered in the other.
* **The install route changes how well the metric's renders agree with villa's labels, not only how much
  ink they find.**
  villa's published sampler image samples a thinner band than any current source build (finding 66:
  −5% to −8% ink count). Against villa's labels at the metric's own settings, on all 8 segments and
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
  Eight of the 11 are 256³ cubes, where a large part of the deficit is how we ran it (findings 96 and 97, below).
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
* **Scoring-window size does not explain that deficit** (finding 95, pre-registered; its prediction held). Cropping the
  saved whole-volume predictions into 24 octants of 256³ preserves the neural tracer's tolerance-4 lead on
  19 of 24, while at tolerance 2 it leads on 0 of 24. At tolerance 4 its merge-penalized ERL is a median
  1.08 times our tracer's across the octants. The identity checks against the whole-cube results pass. Nor is the scroll alone
  the cause, since the three Scroll-5 256³ cubes trail too.
  Both tracers originally saw the whole 512³ cubes: this tests scoring-window size, not tracing context.
  All octants come from three Scroll-5 cubes and are not independent samples.
* **Much of the 256³ deficit is how we ran it** (finding 96, exploratory: found after the fact, not pre-registered).
  villa's tracer drops any seed whose 77-voxel CT window crosses the edge of the CT it is given, and ScrollGT's
  protocol gave it each cube's CT alone. No traced seed lies closer than 19 trace-grid voxels (38 CT voxels) to a
  face on any of the 21 cubes. On the ten 256³ cubes it drops 0.54–0.70 of its seed dots, and its output is
  0.28–0.78 of the ground-truth length. On the eleven 512³ cubes those are 0.26–0.36 and 0.83–1.43. Both separate
  by cube size across scrolls, while our tracer's coverage does not. Ten of the 13 cubes on which it trails at
  tolerance 2 are 256³. Finding 96 could not say how much of the gap this explains; finding 97 measured it.
* **With real CT around each 256³ cube, it keeps its seeds** (finding 97, pre-registered and widened to Scroll 1 before
  the run; all three predictions held on both scrolls). Given 128 voxels of the real scan around each of the ten
  256³ cubes, the box still the cube, it drops 0.002–0.010 of its seed dots on the eight in-sample ones, against
  0.542–0.678. Its coverage rises 1.76–2.78× on all ten. At tolerance 4 it then leads our tracer on 8 of the 10, 4
  of the 5 Scroll-1 cubes among them. At tolerance 2 it leads on both held-out cubes and still trails on the eight
  in-sample ones, at a median 0.60–0.65 of our tracer rather than 0.27–0.36. Our tracer's rows and the reference
  mask are unchanged, and both come from the cube alone.
* **On the 512³ cubes too** (finding 98, pre-registered; all four predictions held on both scrolls). Given the scan
  around each of the eleven 512³ cubes, it drops 0.004–0.012 of its seed dots on the three in-sample Scroll-5 ones,
  against 0.258–0.283, and 0.011–0.088 on the eight held-out Scroll-3 ones, against 0.256–0.357. Its coverage rises
  1.19–1.35× on all eleven, less than on the 256³ cubes, as registered. The ranking against our tracer does not
  change: at tolerance 4 it leads on all eleven, and at tolerance 2 it leads on Scroll 3 and trails on Scroll 5, at a
  median 0.59 of our tracer rather than 0.44. Across all 21 cubes, given the scan around each, it leads our tracer on
  19 at tolerance 4 (11 with the cube alone) and on 10 at tolerance 2 (8).
* **What still drops seeds where it is held out** (finding 99, exploratory: not pre-registered, though its three
  expectations were pushed before it ran; two failed, below). Given the scan, it still drops 0.266 and 0.353 of its
  seed dots on the two held-out Scroll-5 256³ cubes, and 0.011–0.088 on Scroll 3. On all 21 cubes, every classified
  dot that fails does so at one check in villa's seed heading: the CT's axis for the dot's fiber family lies more
  than 35° from the dot's direction from the presence. On the 512³ cubes a 2,000-dot sample was classified. At the
  dropped dots near the ground truth on those ten held-out cubes, the presence direction lies a median 10–16° from
  its tangent, and the CT's axis 58–81°. The sheet the CT shows there is tilted a median 52–74° from vertical, and
  villa takes an H fiber to run along the sheet's horizontal line. Per cube, the share of dots in sheets tilted more
  than 45° tracks the share dropped (Pearson r 0.98 over the 21 cubes, Spearman 0.92). That is an association, not
  a demonstrated cause: nothing was traced again.
  It classifies all 12,471 dots on the ten 256³ cubes and a fixed sample of 2,000 on each 512³ cube; this does not
  classify the unsampled dots. On the two held-out Scroll-5 cubes specifically, the presence direction is a median
  13–15° from its tangent, while the CT family axis is 58°. No tracing or coverage improvement was measured here.

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
  * 0.8.3 notes, on the ten 256³ cubes, that ScrollGT's protocol kept the neural tracer from seeding near the faces
    (finding 96), and gives each cube's values with the scan around it (finding 97). No row changes.
  * 0.9.0 lets an entrant use the public scan around each cube. `tools/context_ct.py` fetches it, converted as the
    cube's CT was, and checks that the core is the cube. The release adds the neural tracer run that way as a new row
    on all 21 cubes (findings 97 and 98), beside the cube-only one: first on merge-penalized ERL on 10 of the 21,
    against 8. Scoring and every existing row are unchanged.

**(4) Evidence.**
* Registered studies were pre-registered before their data; exploratory analyses are labelled separately. Reports and scripts are in
  https://github.com/jonmarrs/vesuvius-autoresearch (findings 69–85 in
  `reports/SPIRAL_FINDINGS_SUMMARY.md`; findings 91–94 in `reports/neural_tracer_entrant.md`,
  `reports/neural_tracer_pitch.md`, `reports/neural_tracer_seeding.md` and `reports/tolerance4_rescore.md`; the
  placement and ground-truth offset
  measurements in the last section of `reports/neural_tracer_entrant.md`).
  Finding 95 is in `reports/octant_crop_rescore.md`, with its committed JSON and pre-registration.
  Finding 96 is exploratory, not pre-registered. It is in `reports/neural_tracer_boundary.md`, with its committed JSON.
  Finding 97 is in `reports/neural_tracer_ct_context.md`, with its committed JSON and pre-registration (amended
  before its run). Finding 98 is in `reports/neural_tracer_ct_context_512.md`, with its committed JSON and
  pre-registration. Finding 99 is exploratory, not pre-registered. It is in `reports/neural_tracer_heading_residual.md`,
  with its two committed JSONs.
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
  first scored the whole surface. villa's labels exist only inside its supervision mask (4–15% of each
  segment's mesh-valid area), so unannotated ink counted as a miss. Re-analysed where the labels are defined:
  * most findings survive;
  * finding 75 survives with smaller effects;
  * finding 74 does not survive as stated (step 0.5 vs 1.0 is not consistent).

  inkagree 0.3.0 makes the supervised region its default. `reports/supervised_reanalysis.md`.
* **Twenty-two of my registered predictions failed**, and the reports say so:
  * finding 70 (smooth would move the count < 1% in every crop window: it moved up to ±20%);
  * finding 71 prediction 1 (failed on three exclusions, one caused by a defect in my alignment gate. Re-analysed
    with inkagree's gate where the labels are defined, all 8 pass and it holds, while prediction 2, held on the
    whole surface, fails there: smooth's ΔAP > 0 in 7 of 8, not at most 5);
  * finding 72 prediction 1 (the count was sensitive in 15% of windows, not ≥ 25%).
  * per-crop normalisation as the cause of finding 70's size (re-scored with one shared p95,
    the median |Δ| stayed at 4.7%, not < 2.5%).
  * finding 73 prediction 2 (smooth's scorer output would agree better with the labels on coarse grids:
    2 of 8, not ≥ 6).
  * finding 74 predictions 2 and 3 (no difference between slice steps 0.25 or 1.0 and the tutorial's 0.5:
    0.5 was better in 8 of 8 and 7 of 8; where the labels are defined, prediction 3 holds: 4 of 8).
  * finding 75 predictions 1 and 2 (no difference between the published image's band, or a wider one, and
    the source build's: the source build beat the first, and the wider band beat it, both in 8 of 8).
  * finding 76 prediction 1 (villa's ink count would track labelled-ink density across regions: ρ = +0.04,
    an ambiguous null, since the raw render does not track it either; where the labels are defined it is
    undetermined, since no window qualifies).
  * the correction's prediction 3 (findings 74 and 75 would survive: 75 did, 74 did not as stated).
  * finding 79 prediction 1 (an unthresholded ink count would be less noisy across seeds on pinned code:
    R = 0.91 [0.56, 1.47], no detectable difference; it was on current code, R = 0.52 [0.34, 0.91]).
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
* **Two of finding 99's three expectations failed too.** They were pushed before it ran, but finding 99 was not
  pre-registered, so they are not in the count above. I expected the presence direction to be the further from the
  ground truth at most nearby dropped dots; it was the closer. Pooled over the 21 cubes, the CT's axis is the closer
  at 0.12 of those 1,347 dots, and at fewer than half of them on 18 of the 21 cubes. I expected fewer than 0.10 of
  all dots to be dropped on every cube but the two held-out Scroll-5 ones; two Scroll-3 cubes dropped 0.127 and 0.169
  of their sampled dots.
* **The effect's size depends on grid cell size** (finding 73, measured): about 1% per window on
  villa's 20-voxel segment meshes, a 6.2% median and −32% to +42% per window on 80-voxel grids like the
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
  4 it leads on three of them, finding 94). On the ten 256³ ones, our protocol kept it from seeding near the faces
  (finding 96). Given the scan around them, it leads on 8 of the 10 at tolerance 4 (finding 97). In sample it still
  trails at tolerance 2 on all 11 cubes given the scan (findings 97 and 98). One checkpoint, defaults.
* Not "tilted sheets cause the held-out seed loss", nor "following the sheet would add coverage". Finding 99 is
  exploratory and shows an association on the classified dots; nothing was traced again.
* Not "ScrollGT's ground truth is wrong on five cubes". Two entrants and the CT agree on an offset of about a voxel
  there, measured after the fact. It explains part of the in-sample gap, and the ground truth is unchanged.
* Not "the Scroll-5 miss is the annotators". Finding 84 rules out a frame offset and a threshold, nothing more.
* Not "held out" as secrecy. The fiber ground truth is public; `held_out` means only that the reference mask did
  not train on the cube.
* Not "agrees with ground truth" for any label-based number. The render is in-sample on the labelled
  segments.
