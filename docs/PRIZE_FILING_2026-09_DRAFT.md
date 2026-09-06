# September 2026 Progress Prize — DRAFT, not submitted

**Deadline: 11:59pm Pacific, 2026-09-30.** Nothing here is filed. Needs review before submission.

**Check the form URL against villa `scrollprize.org/docs/34_prizes.md` at current upstream before
filing.** It has changed every month — July was a `forms.gle` short link, August and September are
different `docs.google.com` IDs. As of villa `739eefd71` the September form is
`docs.google.com/forms/d/e/1FAIpQLScNBMj25FMnphngRG1Ciryv_2_Mkdq2YPJOD9WqPfZExII2iQ/viewform`,
but re-read it rather than trusting this line.

Tag the submitted commit `submission/2026-09`, matching `submission/2026-07` (06e4f4d0) and
`submission/2026-08` (ed1a27c2).

---

## "Short description of how your contributions substantially increase the probability of reading complete scrolls"

### Version A (118 words), use this one

`autoresearch.md` has villa's spiral loop optimise recovered ink with a satisfaction cross-check.
We measured, twice and pre-registered, that those two move independently — in opposite directions.
A config change raised `satisfied_area` 1.03% while costing **10.35% of the ink** (n=12). Refitting
on the fit's own well-satisfied patches raised it **17.66% for no ink gain at all** (n=6).

The second answers an avenue villa names in its open problems, and answers it with a registered
FAILURE. A third study, designed while the first's results were still unread, ruled out the obvious
confound: equalising evidence in the scored strip does not rescue it.

A guard that can move confidently the wrong way, and confidently the useless way, is not guarding.

### Version B (74 words), if the field is tight

villa's spiral loop optimises recovered ink with a satisfaction cross-check. We pre-registered two
cases where they come apart in opposite directions: +1.03% satisfaction for **-10.35% ink** (n=12),
and **+17.66% satisfaction for no ink gain** (n=6).

The second answers a villa-named open problem with a registered FAILURE, and a third study —
designed before the second's results were read — rules out the obvious confound.

### Long version (298 words), if a field allows detail

villa's spiral-fitting loop optimises `total_fg_pixels` with a `satisfied_area` cross-check. We have
two pre-registered measurements, eighteen fits in total, where those endpoints move independently in
opposite directions:

| case | `satisfied_area` | `total_fg_pixels` |
|---|---|---|
| one config flag, n=12 | +1.03% (p=3.9e-06) | **-10.35%** (p=0.0018) |
| refit on well-satisfied patches, n=6 | **+17.66%** (p<1e-4) | -0.83% (p=0.89) |

The second answers an avenue villa names directly — "automatically crop 'good' regions of the spiral
fit, and use these as surface patch inputs to a subsequent run" — with a **registered FAILURE**. The
geometry gain there is circular by construction, since the arm is selected on satisfaction and then
scored on it, which is exactly why a loop using that guard would read it as success.

We then found the confound in our own design and published it before knowing the outcome: because
satisfaction falls with radius (r = -0.21 over 35,963 patches), a 0.90 threshold matched total patch
area to 0.01 points while carrying **11% less area inside the strip where ink is scored**. A third
study, registered while those endpoints were still unread, built a control matched on in-strip area
too. Ink moved further against the method, not toward a hidden benefit.

Both nulls are bounded, not empty: at three fits per arm, 80% power reaches only ~10%. We say so
rather than claiming no effect.

Everything is MIT, runs from published artifacts on one consumer GPU, and every decision rule was
committed to code before the data existed. The analyses refuse a partial sample rather than reporting
one.

---

## "Has this been used by anyone else?"

No external adoption is demonstrated, and the writeup says so plainly.

What exists is outbound and, honestly, unanswered: six villa issues are open from us and five have
zero comments, the oldest since August. We checked upstream and none has been resolved. We are not
filing more issues while that backlog stands.

The one substantive external exchange remains @Bullo27's reply on #1660, which correctly identified
that half of it duplicated #1588. We verified this month that the fix referenced there, PR #1619, was
closed unmerged and the problem persists.

## "What is released, and under what license?"

MIT, public on GitHub. ScrollGT reached **v0.3.2** this month and now has tagged releases
(`v0.1.0`, `v0.3.1`, `v0.3.2`) — previously it had none, so no specific release could be installed or
diffed. Its 206 tests pass; the documented quickstart is exercised by a test after a cold clone once
failed.

New reusable tooling this month, all tested: patch-selection and radial-balance verification, a
radius/winding calibration, per-study verdict runners that refuse partial samples, and a checkpoint
pruner that refuses to delete any artifact a report cites.

All data needed to reproduce every published number ships in-repo. Scoring needs no GPU and no
network; the spiral work needs one consumer GPU and only published villa artifacts.

---

## What NOT to claim

* Not "the metrics are broken" — we measured two disagreements, not a general property.
* Not "the avenue is refuted" — both nulls are bounded at ~10%; a smaller effect survives.
* Not any adoption. There is none, and August's filing said so too.
* The geometry gains are **circular by construction**; do not present either as a partial win.
