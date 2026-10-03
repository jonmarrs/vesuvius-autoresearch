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
2. Fill in the runner PR's number (opened on or after 2026-10-06, if its gate passes) and its state.
   Re-check #1928's state.
3. Re-run `tests/test_filing_2026_10_numbers.py`. Every number below is bound to the file it comes from.
4. Check every URL returns 200.

---

## URL field

```
https://github.com/jonmarrs/vesuvius-autoresearch
https://github.com/jonmarrs/inkdelta
https://github.com/ScrollPrize/villa/pull/1928
<runner PR, if opened>
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
  `<runner PR>` fixes the doc.
* **A new render setting moves the metric without moving reading.** villa #1818 added
  `vc_render_tifxyz --surface-interpolation smooth`. Its default is byte-identical to earlier builds.
  On the 8 labelled segments, in villa's own scoring pipeline, smooth moves `total_fg_pixels` by
  −3.6% to +4.1% per segment, while the scorer's agreement with villa's labels does not change
  (|ΔAP| < 0.001 in all 8, none resolved). Comparing runs rendered in different modes would bias a
  keep/discard decision by about the size of the gains the loop chases. Smooth would not read more.
* **The comparison tool now reads what villa's runner writes.** inkdelta 0.3.0 rejected villa's real
  `--seeds` output as invalid; 0.4.0 reads it. 0.5.x refuses to compare runs rendered in different
  modes.

**(3) What it enables that was not possible before.**
* **A label-anchored check of render settings.** The 3D ink prediction is rendered through a
  segment's own mesh onto villa's label canvas, exactly (verified: same shape, alignment peak at zero
  offset). That turns "does setting X read better?" into an AP against villa's labels with a block
  bootstrap, in about an hour on one GPU. Scripts: `scripts/analyse_interp_vs_labels.py`,
  `scripts/analyse_scorer_vs_labels.py`.
* [inkdelta](https://github.com/jonmarrs/inkdelta) 0.5.1 (MIT, standard library only):
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

---

## Required disclosure — include it

* **Three of my registered predictions failed**, and the reports say so:
  * finding 70 (smooth would move the count < 1% in every crop window: it moved up to ±20%);
  * finding 71 prediction 1 (failed on three exclusions, one caused by a defect in my alignment gate);
  * finding 72 prediction 1 (the count was sensitive in 15% of windows, not ≥ 25%).
* **Finding 70's ±20% does not generalise.** It used per-crop normalisation. In villa's own pipeline
  the effect is about 1% per window. Quote finding 72, not finding 70.
* villa's scroll labels are partly pseudo-labels, made with default-mode geometry. That favours the
  default mode in any comparison against them, and still no difference appeared.

## Do not add

* Not "smooth is worse" or "smooth is better". It is neither, by villa's labels.
* Not "the scorer is fragile" as an established fact. Finding 72's sensitivity prediction failed.
* No adoption claim for inkdelta or the measurements unless one exists on filing day.
