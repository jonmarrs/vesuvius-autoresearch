# August 2026 Progress Prize, form field answers

**Status: FILED 2026-08-23** by Jon, at commit `ed1a27c2`, eight days ahead of the
deadline. Version A (120 words) was used for the contribution description.

**Submission Date:** 2026-08 (deadline 11:59pm Pacific, August 31st 2026, confirmed live)
**Submission Form:** https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform
(verified against https://scrollprize.org/prizes on 2026-08-23. July's
`forms.gle/xoF5C3QsYutKP97x7` is stale and is NOT the August form.)
**Target Prize Tier:** open to review-team judgment
**Submitter:** Jon Marrs <jdmarrs@gmail.com>
**Artifacts:** https://github.com/jonmarrs/scrollgt (headline),
https://github.com/jonmarrs/vesuvius-autoresearch (methodology),
https://github.com/jonmarrs/placement-check, https://github.com/jonmarrs/scroll-frames
**License:** MIT throughout
**Contribution to villa:** issue
[#1522](https://github.com/ScrollPrize/villa/issues/1522), filed 2026-08-18
**Discord:** `#robots` top-level post 2026-08-18 (verbatim record in
`DISCORD_POSTED_robots_2026-08-18.md`)

Companion to `PRIZE_FILING_2026-08_DRAFT.md`, which is pasted verbatim into the form's main
field and therefore carries no submission metadata. These are the short per-field answers.
Keep them consistent with the writeup; a judge may read both.

**House style: no em-dashes or en-dashes as punctuation.** Check with
`grep -c '[—–]' <file>` before pasting.

> **Why these are written fresh rather than adapted from July.** Every short answer in
> `PRIZE_FILING_2026-07_FORM_ANSWERS.md` rests on two claims we have since retracted: that
> our own models read at chance on held-out ground truth, and that ground-truth fine-tuning
> made held-out reading worse. Both were artifacts of a hardcoded `LEVEL0_SHAPE` in our
> registration code. Reusing those answers would file a false statement.

---

## "Short description of how your contributions substantially increase the probability of reading complete scrolls"

### Version A (120 words), use this one

Reading a scroll is not the hard part on its own. Knowing whether you have read it is. We
build the measurement side: ScrollGT scores a prediction against registered human ground
truth, held out, with floors that show what a trivial answer scores.

This month it caught us. A hardcoded constant in our own registration displaced a label by
1766 voxels and produced a published result that our models read at chance. They do not: the
corrected numbers are 0.731 and 0.746 ROC-AUC held out, against 0.518 for our near-chance
reference. We retracted it publicly, fixed the cause, and added the check that would have
caught it.

Measurement that only confirms you is not measurement.

### Version B (77 words), if the field is tight

We build the measurement side of reading: ScrollGT scores predictions against registered,
held-out human ground truth, with published floors showing what a trivial answer scores.

This month it caught our own error. A hardcoded constant displaced a label by 1766 voxels and
produced a published claim that our models read at chance. They do not. We retracted it,
fixed the cause, and shipped the check that would have caught it.

### Long version (301 words), if a field allows detail

Reading a scroll and knowing you have read it are different problems. We work on the second.

ScrollGT is an MIT benchmark that scores an ink prediction against registered human ground
truth on the open SOTA geometry, held out, with floors published alongside so a reader can
see what a trivial answer scores. It runs offline, no GPU and no network.

This month it caught us rather than anyone else. A hardcoded `LEVEL0_SHAPE` in our
registration code displaced a held-out label by about 1766 voxels, which produced a published
claim that our own models read held-out ink at chance. They do not. Re-registered, our clean
students score 0.731 and 0.746 ROC-AUC against 0.518 for our near-chance reference. We
published the retraction, fixed the root cause, and added the check that catches it: agreement
must peak at zero shift, which a tight residual never tested.

We also measured what the benchmark cannot do. Two of its three target families are capped at
one target each by available data, and we published why rather than leaving it as future work.
The fiber family grew from six targets to eleven, and its headline result is that coverage and
precision cannot rank a tracer at all.

---

## "Has this been used by anyone else?"

No external adoption is demonstrated yet, and the writeup says so plainly. What exists is
outbound: a `#robots` post on 2026-08-18 and villa issue
[#1522](https://github.com/ScrollPrize/villa/issues/1522) the same day, reporting that 204 of
311 open-data segments ship meshes whose declared scale is identical while their voxel sizes
differ by up to 40.33x. The issue reports a defect and asks for nothing. Both are recent
enough that no response would be expected yet.

## "What is released, and under what license?"

Four public MIT repositories. ScrollGT (2026-07-11), the methodology repo, placement-check
(2026-08-15) and scroll-frames (2026-08-18). All data needed to reproduce every published
number ships in-repo; scoring needs no GPU and no network.
