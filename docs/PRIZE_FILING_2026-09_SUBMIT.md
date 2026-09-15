# September 2026 Progress Prize — SUBMIT-READY TEXT

**NOT YET FILED.** This file is the exact text to paste into the form, with no internal commentary.
The reasoning, alternatives and guardrails live in `PRIZE_FILING_2026-09_DRAFT.md`; nothing here
should be edited without editing that too.

**Before pasting, do these four things:**

1. **Re-read the form URL** from villa `scrollprize.org/docs/34_prizes.md` at *current* upstream, and
   identify it by the `{/* progress-prizes:form:start */}` marker — that file contains three other
   `forms.gle` links belonging to the Grand Prize, First Letters and Title prizes. Verified
   2026-09-12 against `be09a8503` as
   `docs.google.com/forms/d/e/1FAIpQLScNBMj25FMnphngRG1Ciryv_2_Mkdq2YPJOD9WqPfZExII2iQ/viewform`,
   and re-verified 2026-09-14 against current upstream `983c20fef` through the GitHub API
   (unchanged). The file carries four form links, so the marker is what distinguishes them.
2. **Confirm the deadline still reads 11:59pm Pacific, September 30th, 2026** under
   `progress-prizes:deadline:start`. Verified at `983c20fef` on 2026-09-14.
3. **Run `pytest tests/test_filing_numbers_match_sources.py`** — every figure below is bound to a json
   artifact, and that test fails if any has drifted or if a withdrawn one has crept back.
4. **Run `./.venv/bin/python scripts/check_filing_upstream_claims.py`** — check 3 covers figures
   bound to json artifacts, which the claims about *upstream* are not. Those are live GitHub state
   and go stale whenever a maintainer acts or we open something; two of them were stale on
   2026-09-14. Exit 1 means a claim is stale, exit 2 means a claim could not be located in the
   text, which is a failure and not a pass.

After submitting, tag the commit `submission/2026-09`, matching `submission/2026-07` (06e4f4d0) and
`submission/2026-08` (ed1a27c2).

---

## Field 1 — "Short description of how your contributions substantially increase the probability of reading complete scrolls"

Three measurements on the villa spiral loop **as it runs today**.

**The robustness check `autoresearch.md` prescribes accepts one null change in six.** Requiring both
runs of a change to beat both baseline runs is a rank test: under no effect it passes with
probability exactly **1/C(2k,k)**, independent of noise, metric or code version. Two seeds is 1/6;
**three seeds is 1/20**, for 1.5× compute.

**Its seed noise is 0.0263** on `total_fg_pixels` (nine 30,000-step fits, pooled within-arm), so the
loop resolves about **6%** at three fits per arm — worth knowing before chasing smaller ones.

**Two registered ablations bound what winding constraints buy for *reading*** — the endpoint every
such project in villa's catalogue leaves unmeasured. Removing 5,413 same-winding constraints:
**+0.28%, CI [−2.56%, +3.13%]**. Cutting the hand-drawn absolute anchors from 50 to 10, the ones
villa wants automated: **−0.86%, CI [−10.21%, +8.50%]** — ten read as well as fifty, though that
interval is wide.

---

## Field 2 — "Has this been used by anyone else?"

No external adoption of the *measurements* is demonstrated, and the writeup says so plainly.

**What is upstream: two merged fixes, three pending.** The criteria reward resolving bugs in tools you
use yourself, so these are named rather than left out:

| PR | status | what it fixes |
|---|---|---|
| **#1721** | **MERGED** 2026-09-07 | `spiral-fitting/autoresearch.md` instructed readers to run a script that does not exist |
| **#1722** | **MERGED** 2026-09-14 | `get_ink_metrics.py` writes two metrics; neither was documented |
| #1723 | open | which resident-pool sidecars the defaults actually load |
| #1728 | open | `render_ink` silently produced an entirely black strip; now warns |
| #1780 | open | `autoresearch.md` overstated what the two-seed robustness check accepts |

Every one came out of running villa's own pipeline here. #1728 in particular is the fix for a failure
that cost us hours: a blank render is indistinguishable from a successful one in the logs, which is
how we first mis-diagnosed a mistyped path as a VOID result.

**This is five PRs against a merged total of two, both documentation fixes.** It is
offered as evidence of the practice, not as an adoption claim.

What exists is outbound and, honestly, unanswered: six villa issues are open from us and four have
zero comments, the oldest since August. We checked upstream and none has been resolved. We are not
filing more issues while that backlog stands.

The one substantive external exchange remains @Bullo27's reply on #1660, which correctly identified
that half of it duplicated #1588. We verified this month that the fix referenced there, PR #1619, was
closed unmerged and the problem persists.

---

## Field 3 — "What is released, and under what license?"

MIT, public on GitHub. ScrollGT reached **v0.3.2** this month and now has tagged releases
(`v0.1.0`, `v0.3.1`, `v0.3.2`) — previously it had none, so no specific release could be installed or
diffed. Its 206 tests pass; the documented quickstart is exercised by a test after a cold clone once
failed.

**It now ships a Docker image** (660 MB), which is the criteria's requested reproduction path:

```bash
docker build -t scrollgt . && docker run --rm --network none scrollgt pytest -q
```

The offline claim is demonstrated rather than asserted — **all 206 tests pass inside the container
with networking disabled**, in 8m02s, verified 2026-09-13. System requirements: any x86-64 host with Docker, no GPU, ~200 MB of disk.

New reusable tooling this month, all tested: patch-selection and radial-balance verification, a
radius/winding calibration, per-study verdict runners that refuse partial samples, and a checkpoint
pruner that refuses to delete any artifact a report cites.

All data needed to reproduce every published number ships in-repo. Scoring needs no GPU and no
network; the spiral work needs one consumer GPU and only published villa artifacts.

---

---

## Required disclosure — include this, do not trim it

Every pinned-tier number above was measured on villa-spiral `6847063f`, and villa has moved past it:
current villa recovers **67.6% more ink** through a byte-identical renderer and scorer. The four
decoupling studies and the r = −0.121 corpus correlation are therefore measurements of **superseded
code**. They stand as such — the arithmetic is unchanged and the registrations were honoured.

The re-measurement on current code **went against us**: the ink null reproduces (+0.28%, 95% CI
[−2.56%, +3.13%]) but the decoupling evidence does not. So this submission does **not** claim the
satisfaction guard fails to track ink on current villa. What it claims is narrower and defensible: it
failed to on `6847063f`, across four pre-registered studies and 24 fits; and on current code, removing
5,413 same-winding constraints does not measurably change reading.

A reviewer who checks will find that gap anyway. Finding it disclosed is different from finding it
hidden.

---

## Do not add any of these

* Not "the metrics are broken" — two measured disagreements, not a general property.
* Not "the avenue is refuted" — the current-code null bounds ±3%, the pinned-tier ones ~12%.
* Not any adoption claim. There is none.
* Not that these results describe current villa. They describe `6847063f`.
* **Not the ink-placement work.** It is exploratory, its mechanism is unexplained after two failed
  tests, and its forward prediction was still running when this was written. It does not go in a
  submission until it has survived that test.
