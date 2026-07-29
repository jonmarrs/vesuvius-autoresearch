# July 2026 Progress Prize, form field answers

**Submission Date:** 2026-07 (deadline 2026-07-31 11:59pm PT)
**Submission Form:** https://forms.gle/xoF5C3QsYutKP97x7
**Target Prize Tier:** open to review-team judgment (Best of month $20k / Gold Aureus $20k /
Denarius $10k / Sestertius $2.5k / Papyrus $1k)
**Submitter:** Jon Marrs <jdmarrs@gmail.com>
**Artifacts:** https://github.com/jonmarrs/scrollgt (headline) +
https://github.com/jonmarrs/vesuvius-autoresearch (methodology, renderer)
**License:** MIT
**Community listing PR:** https://github.com/ScrollPrize/villa/pull/1280
**Discord announcement:** posted to `#robots` 2026-07-29 (verbatim record in
`DISCORD_POSTED_robots_2026-07-29.md`, local-only)
**Status:** NOT YET FILED as of 2026-07-29.

Why this is a separate file rather than inlined the way `PROGRESS_PRIZE_SUBMISSION_2026-05.md`
inlined its form metadata: `PRIZE_FILING_2026-07_SUBMIT.md` is pasted verbatim into the form's
main field, so it has to stay free of submission metadata and per-field answers.

Companion to `PRIZE_FILING_2026-07_SUBMIT.md` (the long writeup). These are the short
free-text answers for individual fields on the Google Form
(https://forms.gle/xoF5C3QsYutKP97x7). Keep them consistent with the writeup, since a judge
may read both.

**House style for these answers: no em-dashes or en-dashes used as punctuation.** Jon's
call, 2026-07-29: dash-heavy prose reads as machine-generated. Use periods, semicolons,
commas, or parentheses instead. En-dashes inside numeric ranges (0.84-0.89) should be written
as plain hyphens here for the same reason. Check any new answer with:
`grep -c '[—–]' <file>` before pasting.

---

## "Short description of how your contributions substantially increase the probability of reading complete scrolls"

### Version A (118 words), use this one

We haven't built a better reader. Our own models read at chance on held-out ground truth, and
we publish that. What we've done is remove two blockers. First, Scroll 3's segments and PHerc
1667's merged reading geometry ship as mesh-only in the open bucket, so nobody outside the
core team can run ink detection on them at all. Our renderer turns them into detector-ready
surface volumes, validated against the released volumes (NCC 0.78 gate pass). Second, no human
ground truth is aligned to the SOTA geometry, which makes "my model reads ink"
indistinguishable from "my model reproduces another model." ScrollGT supplies registered
held-out ground truth, and it caught 0.79+ train-exposed collapsing to ~0.55 held-out in our
own models.

### Version B (76 words), if the field is tight

We haven't built a better reader. Our own models read at chance on held-out ground truth, and
we publish that. What we've done is remove two blockers. Scroll 3's segments and PHerc 1667's
merged reading geometry ship as mesh-only, so nobody outside the core team can run detection
on them; our renderer makes them detector-ready (NCC 0.78 gate pass). And ScrollGT supplies
the registered held-out ground truth that separates reading ink from reproducing another
model's output.

### Long version (215 words), kept in case a field allows detail

Neither tool is a better reader. On held-out human ground truth our own models read at chance,
and we publish that. They remove two things standing between the community and complete
readings.

**Unreadable data.** Scroll 3's two segments and PHerc 1667's merged full-reading geometry
ship in the open bucket as *mesh-only*, with no surface volumes, so no one outside the core
team can run ink detection on them at all. Our renderer rebuilds detector-ready surface
volumes from the released geometry, gate-validated against released volumes on two scrolls
(PHerc 1667 NCC 0.78 pass; all 26 emitted layers matching the released stack at 0.84 to 0.89).
You cannot read what you cannot feed to a detector, and these are the live First-Letters
scroll and the geometry behind the June-2026 complete reading.

**Unmeasurable progress.** With no human ground truth aligned to the SOTA geometry, "my model
reads ink" is indistinguishable from "my model reproduces another model's predictions."
ScrollGT supplies registered, held-out ground truth with an anti-gaming gate, and it caught
exactly that failure in our own work: 0.79+ on train-exposed regions collapsing to ~0.55
held-out, with distillation faithfully reproducing a teacher including its failures. Effort
spent on models that only appear to read is effort not spent reading scrolls. Every negative
is published as a baseline row so nobody has to re-walk that dead end.
