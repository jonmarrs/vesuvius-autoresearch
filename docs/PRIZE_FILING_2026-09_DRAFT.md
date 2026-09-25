# September 2026 Progress Prize — DRAFT, not submitted

> **SUPERSEDED 2026-09-21 — do not edit or file from this document.** The submit-ready text is
> `docs/PRIZE_FILING_2026-09_SUBMIT.md`. This draft is kept for history only and contains figures
> that have since been **withdrawn** (the 0.0263 seed CV, the 6% resolution, the "1.2%" count
> agreement); the withdrawn-claims guard flagged it on 2026-09-21. Every number below is stale as
> of the SUBMIT file's last correction.

**Deadline: 11:59pm Pacific, 2026-09-30.** Nothing here is filed. Needs review before submission.

**VERIFIED 2026-09-12 against villa `be09a8503`** (current upstream HEAD), in
`villa/scrollprize.org/docs/34_prizes.md`:

* **Form:** `docs.google.com/forms/d/e/1FAIpQLScNBMj25FMnphngRG1Ciryv_2_Mkdq2YPJOD9WqPfZExII2iQ/viewform`
  — sits directly under the `{/* progress-prizes:form:start */}` marker, so it is the Progress Prize
  form and not one of the three other `forms.gle` links in that file (those are Grand Prize / First
  Letters / Title).
* **Deadline:** "11:59pm Pacific, September 30th, 2026", under `progress-prizes:deadline:start`.

**Re-verify anyway immediately before filing.** The URL has changed every month — July was a
`forms.gle` short link, August and September are different `docs.google.com` IDs — and this check is
only as fresh as the submodule pin. Identify it by the `progress-prizes:form:start` marker, not by
position in the file.

Tag the submitted commit `submission/2026-09`, matching `submission/2026-07` (06e4f4d0) and
`submission/2026-08` (ed1a27c2).

---

## "Short description of how your contributions substantially increase the probability of reading complete scrolls"

> **Rewritten 2026-09-12.** The earlier drafts led with "villa's satisfaction guard does not track
> ink", stated flat. That is true of villa-spiral `6847063f` and **was not established on current
> villa** — the registered attempt to extend it failed
> (`reports/decoupling_does_not_cleanly_reproduce.md`). Leading with it would have invited villa to
> check on the code they actually run and find it unsupported. These versions lead with the
> **current-code** results instead, which turn out to be the stronger material anyway.

### Version A (~179 words), use this one

Three measurements on the villa spiral loop **as it runs today**.

**The robustness check `autoresearch.md` prescribes accepts one null change in six.** Requiring both
runs of a change to beat both baseline runs is a rank test: under no effect it passes with
probability exactly **1/C(2k,k)**, independent of noise, metric or code version. Two seeds is 1/6;
**three seeds is 1/20**, for 1.5× compute.

**Its seed noise is 0.0263** *(withdrawn 2026-09-19; now 0.0536)* on `total_fg_pixels` (nine 30,000-step fits, pooled within-arm), so the
loop resolves about **6%** at three fits per arm — worth knowing before chasing smaller ones. We
first published 0.0125 from six fits and withdrew it when a third arm doubled the estimate; the
number here is the one that survived.

**Two registered ablations bound what winding constraints buy for *reading*** — the endpoint every
such project in villa's catalogue leaves unmeasured. Removing 5,413 same-winding constraints:
**+0.28%, CI [−2.56%, +3.13%]**. Cutting the hand-drawn absolute anchors from 50 to 10, the ones
villa wants automated: **−0.86%, CI [−10.21%, +8.50%]** — ten read as well as fifty, though that
interval is wide.

**We also ran the one community geometry evaluator against reading.** spiralcheck's intrinsic winding
checks (pre-registered, on the same twelve current-villa fits) separate none of three constraint
configs on the whole family, and within a config none of its four metrics tracks recovered ink (every
p ≥ 0.10). Its violated-bin fraction moves **7.4%** between fits that differ only by seed — a figure
its own validation, run at a fixed seed, could not give.

### Version B (~89 words), if the field is tight

Three measurements on villa's spiral loop as it runs today. The two-seed robustness check in
`autoresearch.md` accepts a null change **1 time in 6** — exactly 1/C(2k,k), a rank test no amount of
better fitting improves; **three seeds makes it 1 in 20**. Current seed noise is **0.0263** *(withdrawn 2026-09-19; now 0.0536)*, so the
loop resolves ~6%. And two ablations bound what winding constraints buy for
*reading*: removing 5,413 same-winding constraints gives **+0.28%, CI [−2.56%, +3.13%]**, and cutting
the hand-drawn anchors 50 → 10 gives **−0.86%, CI [−10.21%, +8.50%]**.

### Long version (~410 words), if a field allows detail

Everything below is on **current villa**, with pre-registered decision rules and analysis code
committed before the data existed.

**1. The prescribed robustness check accepts one null in six.** `autoresearch.md` suggests running a
change under two seeds and keeping it if the gain survives. Under no effect, the chance that both
change runs beat both baseline runs is exactly **1/C(2k, k)** — a rank statistic, so it depends on
nothing: not the noise, the metric, or the code version. Two seeds = **1/6**. **Three seeds = 1/20**,
at 1.5× compute. A loop evaluating many changes accumulates false wins in proportion to how many it
tries.

**2. Its noise floor, measured.** Pooling within-arm deviations over nine 30,000-step fits gives a
seed CV of **0.0263** on `total_fg_pixels`, so at three fits per arm the loop resolves about **6%**.
We published 0.0125 from six fits, and a third arm moved it to 0.0263 — the new value sat inside the
old confidence interval all along, so we withdrew the claim rather than defend it. Also: **do not normalise ink by
strip area.** `overall_fg_fraction` is 2.6× noisier, because the ink count is quieter than the strip
it sits on and dividing injects the canvas's jitter.

**3. What winding constraints buy for reading.** Two registered ablations, both on current villa,
both against recovered ink — the endpoint every winding-constraint project in villa's catalogue
leaves unmeasured, since they all validate on geometry.

| removed | effect on reading | 95% CI |
|---|---:|---|
| 5,413 **same-winding** constraints | +0.28% | [−2.56%, +3.13%] |
| 40 of 50 **absolute anchors** (hand-drawn) | −0.86% | [−10.21%, +8.50%] |

The second is the one villa asks humans to draw and wants automated. **Ten anchors read as well as
fifty** on this ROI — but that interval is wide, because the ablated arm turned out 3.4× noisier than
the baselines, and we report the bound we got rather than the one we designed for.

**On the superseded tree** (`6847063f`, 24 scored fits) we additionally found the satisfaction guard
failing to track ink in four pre-registered cases, including a config change costing **10.35% of the
ink** while improving satisfaction. We re-ran that on current code and **it did not extend** — the
ink null reproduced, the geometry evidence did not. We report the failure rather than the headline.

The same habit caught our own errors. We published that re-measurement quoting a bound taken from
the superseded tree's noise constant; tracing where that number came from produced measurement 2, and
showed the null actually excludes ±3% rather than ±10% — and that every earlier bound on the old tree
was ~12%, not ~10%, so those nulls had excluded *less* than we claimed. Both corrections are
published, one in our favour and one against.

Nulls here are bounded, not empty, and we give the interval rather than claiming no effect.

Everything is MIT, runs from published artifacts on one consumer GPU, and every decision rule was
committed to code before the data existed. The analyses refuse a partial sample rather than reporting
one.

---

## "Has this been used by anyone else?"

No external adoption of the *measurements* is demonstrated, and the writeup says so plainly.

**What is upstream: two merged fixes, two pending.** The criteria reward resolving bugs in tools you
use yourself, so these are named rather than left out:

| PR | status | what it fixes |
|---|---|---|
| **#1721** | **MERGED** 2026-09-07 | `spiral-fitting/autoresearch.md` instructed readers to run a script that does not exist |
| **#1722** | **MERGED** 2026-09-14 | `get_ink_metrics.py` writes two metrics; neither was documented |
| #1723 | open | which resident-pool sidecars the defaults actually load |
| #1728 | open | `render_ink` silently produced an entirely black strip; now warns |

Every one came out of running villa's own pipeline here. #1728 in particular is the fix for a failure
that cost us hours: a blank render is indistinguishable from a successful one in the logs, which is
how we first mis-diagnosed a mistyped path as a VOID result.

**This is four PRs against a merged total of two, both documentation fixes.** It is
offered as evidence of the practice, not as an adoption claim.

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

**It now ships a Docker image** (660 MB), which is the criteria's requested reproduction path:

```bash
docker build -t scrollgt . && docker run --rm --network none scrollgt pytest -q
```

The offline claim is demonstrated rather than asserted — **all 206 tests pass inside the container
with networking disabled**, in 8m02s, verified 2026-09-13. An earlier draft said "20 core tests",
inherited from the project README, which understated it. System requirements: any x86-64 host with Docker, no GPU, ~200 MB of disk.

New reusable tooling this month, all tested: patch-selection and radial-balance verification, a
radius/winding calibration, per-study verdict runners that refuse partial samples, and a checkpoint
pruner that refuses to delete any artifact a report cites.

All data needed to reproduce every published number ships in-repo. Scoring needs no GPU and no
network; the spiral work needs one consumer GPU and only published villa artifacts.

---

## Disclosure that must appear in any version filed

**Every number above was measured on villa-spiral `6847063f`, and villa has moved past it.** Three
baselines on current villa (`d8c5f488a`, seeds 1-3, 30,000 steps, same dataset, byte-identical
renderer and scorer) recover **67.6% more ink**: 2,882,256 against 1,720,000, with ink *density* up
48%. That is villa's own fitting work, measured through the same apparatus
(`reports/current_code_baseline.md`).

So the four studies and the r = -0.121 corpus correlation are **measurements of superseded code**.
They stand as such — the arithmetic is unchanged and the registrations were honoured — but whether
the guard still fails to track ink *on current villa* is an open question.

**The re-measurement has landed, and it went against us.**
`docs/preregistration/2026-09-11_decoupling_on_current_code.md` repeated the same-winding ablation on
current code. Result (`reports/decoupling_does_not_cleanly_reproduce.md`): **the ink null reproduces
(+0.28%, p=0.80, 95% CI [-2.56%, +3.13%]), the decoupling evidence does not.** On the old tree
`satisfied_area` FELL 0.69% (p=0.0027) while ink held, and that fall was the evidence because the
"less left to satisfy" confound can only produce a rise. On current code it ROSE 1.18% (p=0.0175) —
the uninterpretable direction.

**So the filing must not claim the guard fails to track ink on current villa.** What is defensible:
it failed to do so on `6847063f`, over four pre-registered studies and 24 fits; and on current code,
removing 5,413 same-winding constraints does not measurably change reading. The stronger, more
quotable version is not supported and must not be written.

Stating this unprompted costs a little and is worth more: a reviewer who checks will find the gap
anyway, and finding it disclosed is different from finding it hidden.

## What NOT to claim

* Not "the metrics are broken" — we measured two disagreements, not a general property.
* Not "the avenue is refuted" — the current-code null bounds ±3% and the pinned-tier ones ~12%; a smaller effect survives.
* Not any adoption. There is none, and August's filing said so too.
* **Not that these results describe current villa.** They describe `6847063f`. See the disclosure
  above; do not drop it to save words.
* **Not that the decoupling holds on current code.** It was tested and it did not extend. Saying
  "four pre-registered cases" without that correction would be the single most misleading sentence
  available here.
* The geometry gains are **circular by construction**; do not present either as a partial win.
