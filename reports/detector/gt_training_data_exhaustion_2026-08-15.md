# Registered-GT training data is exhausted on Scroll-1

**2026-08-15.** Re-run the survey: `uv run python scripts/probe_labeled_segment_availability.py`
Survey data: [`labeled_segment_availability.json`](labeled_segment_availability.json)
Placement measurements: [`registration_offset_2026-08-07.md`](registration_offset_2026-08-07.md)

Every figure below cites one of those two files. Where a number is quoted from the 08-07
report, the line reference is given so it can be checked without reading the whole thing.

## Headline

On Scroll 1, the intersection of three requirements

- carries a 2023 hand ink label,
- has a SOTA re-flattening in the open data,
- is placed well enough to score against — which means clearing the 48 level-2 px placement
  gate **and** not having been retired non-scoring for local placement error,

contains **exactly one segment**. Two segments clear the gate; the third criterion is stated
with its second half because that half is what excludes one of them. The survivor is
`20231210121321`, measured at **32.0 px**
(`registration_offset_2026-08-07.md:318`, `:339`). That segment is already spent — it is the
held-out evaluation target, the only pixel target the 08-07 report is willing to stand behind
(`registration_offset_2026-08-07.md:345-347`).

One segment cannot be both the training set and the held-out test. The survey records this as
`"measured_passing": ["20231210121321"]` and `"exhausted": true`, where `exhausted` is defined
as fewer than two usable segments, two being the minimum a train/held-out split requires
(`labeled_segment_availability.json`; the definition lives in `classify()` in
`scripts/probe_labeled_segment_availability.py`). The same record carries `"status":
"exhausted_pending_measurement"`, which says *why* it is exhausted — see Limitations for what
moves when the upstream data changes, since `exhausted` alone will not move on its own.

This is a pigeonhole. It is not a budget problem, not a compute problem, and — as the next
section shows — not a problem a better registration would solve either.

## The availability table

Surveyed 2026-08-15. Six Scroll-1 segments carry a 2023 hand ink label; three of those are
present in the open data and three are absent; eleven segments in the open data are 2023-era,
of which eight carry no hand label (all five counts from
`labeled_segment_availability.json`: `labeled`, `present`, `absent`, `era_2023`,
`unlabeled_2023`).

**What the probe's bucket half does and does not establish.** `era_2023` and
`unlabeled_2023` are derived from a listing of `PHercParis4/segments/`, so they prove those
eight segments are *published*, not that each one resolves a `surface-volumes/` prefix and is
therefore usable geometry. That stronger claim was checked directly against the bucket on
**2026-08-15**, as a separate step outside the probe: all eight resolve both
`surface-volumes/` and `ink-detection/`, and the three absent segments do not appear under
`segments/` at all. Where this report says the geometry for those eight already exists, it
rests on that dated check, not on the probe — and re-running the probe alone will not
re-establish it.

| segment | hand label | in open data | placement | usable as training GT |
|---|---|---|---|---|
| `20230702185753` y4000_x2500 | yes | yes | 46.6 px | no, retired non-scoring 2026-08-14 |
| `20230702185753` y7000_x4000 | yes | yes | 53.3 px | no, fails gate |
| `20231005123336` y4000_x2500 | yes | yes | 55.1 px | no, fails gate |
| `20231005123336` y7000_x4000 | yes | yes | drops at prep | no, periodicity 0.556, ink 0.0005 |
| `20231210121321` y4000_x2500 | yes | yes | 32.0 px | **passes, but spent as held-out eval** |
| `20230820203112` | yes | **no** | n/a | no, no SOTA geometry exists |
| `20230826170124` | yes | **no** | n/a | no, no SOTA geometry exists |
| `20230903193206` | yes | **no** | n/a | no, no SOTA geometry exists |

Placement figures: 46.6 px and 53.3 px at `registration_offset_2026-08-07.md:282-283` and
`:337-338`; 55.1 px at `:267` and `:284`; the y7000_x4000 prep drop (periodicity 0.556,
registered ink fraction 0.0005) at `:273-274` and `:285`; 32.0 px at `:318` and `:339`. The
three absent segments and the six/three/three split are from
`labeled_segment_availability.json`.

One figure in the table is an acknowledged exception to the citation rule stated at the top:
the retirement **date**, 2026-08-14, appears in neither permitted source. The probe JSON
records the fact of the retirement (`retired: ["20230702185753"]`) but carries no date; the
date is at `../scrollgt/README.md:126` and at `scripts/probe_labeled_segment_availability.py:51-53`,
where the exclusion and its reason are kept together as data.

**Two disclosures about the table's provenance, so a reader does not have to reconcile it
against the probe by hand.**

*The probe reports `20231005123336` as unmeasured, not as failing.* It reads placement only
from committed `*_validation.json` gate blocks, and no such file carries a placement for that
segment, so the probe leaves it `null` — by design it never reports an unmeasured segment as
fine (see the probe's docstring: "it does not judge placement for segments it has no committed
measurement for"). The 55.1 px figure in the table comes from the 08-07 report. Both routes
exclude the segment; they differ only in whether the exclusion is recorded as a measured
failure or as an absence of measurement, and the stricter of the two is the one in the table.

*The probe is segment-level; the table is region-level.* The probe reports one placement per
segment (46.6 px for `20230702185753`, from that segment's y4000_x2500 validation record),
while the 08-07 report measured both of that segment's regions and found the second at 53.3 px
(`:283`, `:338`). The finer split is shown here because it is the one that matters for a
training set: `20230702185753` is poorly placed segment-wide, not in one region
(`registration_offset_2026-08-07.md:341-347`).

## Two blockers, named separately, and they bind independently

**Blocker 1 — registration quality. Two segments.** `20230702185753` and `20231005123336`
both fail on where their labels land. This is the cross-scan surface disagreement, and on
2026-08-07 it was closed as an **irreducible floor rather than a pending bug**
(`registration_offset_2026-08-07.md:206-216`). Two candidate fixes were tested and falsified
before that call was made: the same-normalised-UV bridge between the 7.91 µm and 2.4 µm
flattenings left a median residual of **2137 voxels, 4.6% of the surface's 46,474-voxel
extent** (`:175-181`), and the unpaired 3D similarity into the old scan frame left a median
residual of **81 old-scan voxels** against the existing obj bridge's **7.95** — worse than
what is already shipped (`:186-193`). Only 32% of paired points land within 25 voxels and 17%
are beyond 200 (`:196-204`). The 2023 and 2026 segmentations are materially different
surfaces; no rigid or similarity transform bridges them tightly.

**Blocker 2 — data availability. Three segments.** `20230820203112`, `20230826170124` and
`20230903193206` carry hand labels and are **absent from the open data entirely**: neither an
`ink-detection/` nor a `surface-volumes/` prefix resolves for any of them
(`labeled_segment_availability.json`, `absent`). These segments are not badly placed. There is
nothing to place a label onto.

**Stated plainly, because reporting only the first blocker would imply the second does not
exist:** a perfect registration would not unblock this experiment. Even if the cross-scan
floor were solved tomorrow and both failing segments came inside the gate, the three absent
segments would still be absent. And compute would not unblock it either — no amount of
training time creates a second correctly-placed labelled segment. The two blockers have
different causes (one is a property of the data's geometry, the other of what has been
published upstream) and neither is downstream of the other.

## Consequence 1: the GT fine-tune is unanswerable as posed

The correct statement is **not testable, for want of a training set**.

It is specifically *not* "GT fine-tuning does not help". That was the 2026-07-11 claim, it was
published, and it was retracted on 2026-08-07. The reason it was retracted *that day* is
narrower than the reason we would give now, and the two should not be run together. What was
known on 08-07 is that the **evaluation** label was displaced: the 08-07 report states that
every conclusion resting on the held-out misregistration inherits the doubt, the GT fine-tune
negative included, because a model scored against displaced labels degrades toward the trivial
predictor — which is exactly what had been observed
(`registration_offset_2026-08-07.md:77-81`).

A week later the account got worse rather than different. On **2026-08-14** a second copy of
the same hardcoded constant was found, in `gt_register.py`, having survived the first fix
because nobody grepped for other copies (`registration_offset_2026-08-07.md:218-222`). That
put the fine-tune's **training** labels in the same condition as its evaluation label: two of
its four regions carried a 167% x-scale error, and the other two sat on the segment now known
to be the worse-placed one. The 08-07 report calls this "very likely the whole of" the
negative, and says in the same breath that the result "was already retracted on weaker
grounds" (`registration_offset_2026-08-07.md:224-235`) — the retraction did not wait on this
discovery, and did not depend on it.

Replacing a false negative with a stronger negative pointed the same direction would repeat
the original error with more confidence. The honest replacement is narrower: the experiment
cannot be run, and here is precisely which resource is missing.

All four of the fine-tune's configured training regions are now measured, and at best one
marginal region survives (`registration_offset_2026-08-07.md:278-290`). That is the same
arithmetic as the headline, seen from the experiment's side.

**Where the retracted record lives.** The published report of that result,
[`gt_finetune_heldout.md`](gt_finetune_heldout.md), is kept rather than deleted, with a
retraction banner at the top marking both its headline and its "4/4 regions passed" claim as
void; its companion `gt_finetune_heldout.json` and the prep artifact `gt_finetune_prep.json`
carry `superseded` blocks saying the same in machine-readable form, and
`repro.sota_data.gt_finetune finetune` refuses to run at all. A retraction that leaves the
original text readable is deliberate: the point is that no record keeps *asserting* the
retracted claim, not that the claim disappears from the history.

**The experiment's original premise is void independently of the data question.** It asked
whether human GT supervision could unlock held-out reading where distillation could not,
citing arm C — the 3-scroll student, identified as such at
`docs/PRIZE_FILING_2026-07_SUBMIT.md:19`, since the 08-07 report gives the two students'
figures without naming which is which — at ROC-AUC **0.558** as the bar to beat. That number
was produced against the
misregistered label. Post-correction, the 08-07 report records the two clean held-out students
going **0.553/0.558 → 0.731/0.746**, and the canon teacher **0.563 → 0.753**, against an
all-positive floor of 0.518 (`registration_offset_2026-08-07.md:8-10`). The figure the
premise quoted, 0.558, now reads ~0.746. "Unlock reading from chance" no longer describes
anything real: the models were already reading held-out ink, and the chance result was an
artifact of our own constant.

So even with a training set in hand, the question would have to be re-posed before it was
worth asking.

## Consequence 2: ScrollGT's pixel target family is n=1 and cannot be expanded today

This is the half that reaches users, and it is the reason this finding ships outward rather
than staying in the lab notebook.

ScrollGT already discloses that the pixel family has one scoreable target — `README.md:126`,
"One scoreable pixel target, plus a documented contrast" — and explains why the two
`20230702185753` regions were marked non-scoring on 2026-08-14: local placement error there
reaches roughly 1.9× the 512 µm prize analysis window, so within one window a model can be
scored against ground truth from a different part of the sheet. The underlying measurement is
in the 08-07 report, and it is two figures rather than one: per-tile, that segment's worst
768 px tile is **~102 px** against ~50 px on the held-out target
(`registration_offset_2026-08-07.md:337-339`), and the disclosure paragraph puts the same
worst case at **~100 px, ~0.96 mm** (`:360`). Globally the segment reports 46.6 px, which is
the number that understates it. (ScrollGT used to state 0.98 mm for that tile, a rounding
difference against the 08-07 report's 0.96 mm; corrected by ScrollGT commit `6123e5a`
2026-08-15, and `../scrollgt/README.md:142` now reads "worst tile ~0.96 mm = 1.9 windows".)

The README also did not say that the family is *closed*. Its disclosure was qualified —
`20231210121321` was "**currently** the only pixel target we would stand behind" — and
*currently* implies the family grows with more processing effort on our side. This survey
rules that out: the candidate pool is exhausted at n=1, and expansion requires new upstream
data that does not exist today. A reader who took "currently" at face value would plan around
a benchmark that was about to get broader, and it is not. The same ScrollGT commit `6123e5a`
dropped the word (`README.md:149-150`) and added the exhaustion paragraph — "And the pool is
exhausted, not merely unprocessed" (`README.md:152-159`) — which carries the six/three/three
split, the two blockers, and a pointer to the re-runnable probe. Both corrections are made;
what follows is why they matter to a reader, not an outstanding action.

This matters for interpretation, not just for bookkeeping. A single-target pixel family cannot
separate model quality from segment idiosyncrasy — any score is a score on one sheet, and
nothing in the benchmark distinguishes a model that reads ink from a model that suits
`20231210121321`. Anyone re-pulling and re-scoring against ScrollGT deserves that stated
alongside the number, which `6123e5a` also does — `README.md:161`, "What this costs you as a
user".

## Two unblock paths, both upstream

Because both sides of the intersection were measured, this ends on something actionable rather
than a dead end. Either path would yield a second candidate:

1. **Re-flatten** any of the three labelled-but-absent segments — `20230820203112`,
   `20230826170124`, `20230903193206` (`labeled_segment_availability.json`, `absent`). The
   hand labels already exist; the geometry does not.
2. **Hand-label** any of the eight published 2023-era segments that carry no label —
   `20230929220926`, `20231007101619`, `20231012184424`, `20231016151002`, `20231022170901`,
   `20231031143852`, `20231106155351`, `20231221180251`
   (`labeled_segment_availability.json`, `unlabeled_2023`; all eight confirmed to resolve
   `surface-volumes/` by the direct bucket check dated 2026-08-15 above, which the probe does
   not perform). The geometry already exists; the labels do not.

**Each is necessary but not sufficient.** A new segment still has to be placed well enough to
use, and that is not a formality. Two base rates, kept apart because conflating them is the
error this project has already had to fix once in ScrollGT:

- **gate-pass, 2 of 3** (`in_gate`): of the three labelled segments present in the open data,
  `20231210121321` passes at 32.0 px and `20230702185753` at 46.6 px, while `20231005123336`
  fails at 55.1 px.
- **usable, 1 of 3** (`measured_passing`): `20230702185753` clears the threshold by 1.4 px
  and is retired non-scoring anyway.

(`registration_offset_2026-08-07.md:318-320`, `:267`; `labeled_segment_availability.json`,
`in_gate` vs `retired` vs `measured_passing`.) That last case is worth dwelling on:
**clearing the gate is necessary but not sufficient.** The survey keeps `in_gate` and
`measured_passing` as separate fields for exactly this reason, so the exclusion is visible in
the data rather than buried inside a single count.

## Limitations

**This is a point-in-time observation, established 2026-08-15.** The open data changes. The
three absent segments could be published next month — but publication alone would **not** end
the exhaustion, for the same reason stated in the unblock paths above: a new segment still has
to be placed well enough to use, and that is measured here, not upstream. Publication is
necessary and not sufficient.

So be specific about what a re-run would show, rather than watching the headline. On
publication, `absent` shrinks and `present` grows immediately, and the newly published segment
appears in `unmeasured` — present, not retired, and carrying no committed placement. `status`
reads `exhausted_pending_measurement` whenever such a candidate exists, against
`exhausted_no_candidate` when none does. `exhausted` itself flips only after someone registers
that segment here and its placement lands inside the gate; it cannot be flipped by upstream
alone, and the probe is built that way deliberately — it never reports an unmeasured segment
as fine. `20231005123336` sits in `unmeasured` today for exactly that reason (see the
provenance disclosure above): the probe declines to call it a failure on a measurement it does
not hold, even though the 08-07 report has one.

That is why the survey is a committed probe rather than a constant in a document:
`scripts/probe_labeled_segment_availability.py` re-runs both halves — the local label scan and
the live bucket listing — and rewrites `labeled_segment_availability.json`, stamping the run
date and whether the run was live or `--offline` (a reused listing carries the date it was
listed, so a stale availability claim cannot wear a fresh stamp). Anyone acting on this report
should re-run it rather than trust the date. The probe treats an unreachable bucket as a hard
error rather than an empty result, precisely so that a network failure cannot manufacture the
exhaustion finding.

**Placement verification is relative, not absolute.** `placement_peak` measures where GT-vs-
prediction agreement is maximised against the canon teacher's own region crop
(`registration_offset_2026-08-07.md:39-47`). It therefore localises *disagreement between two
artifacts* — a registered label and a model prediction — rather than establishing truth about
where the ink is. This is a general caveat on **every** placement figure in this report, the
32.0 px pass as much as the 55.1 px failure. It does not single out any one segment, and it is
not a reason to discount a specific inconvenient number.

**In particular, it is not a caveat on `20231005123336`.** The record used to say the canon
teacher was chance-quality there (enrichment ≈ 1, 0.79–1.02 across all four orientation
candidates), which would have made that segment's label orientation unverifiable. That is now
known to be false: the enrichment collapse was our own second hardcoded level-0 shape — the
segment's true level-0 is 34880×97280 against the assumed 50600×36400, a 167% x-scale error
that scattered the label, and a scattered label enriches at ≈1 against any teacher.
Re-registered with the fix, **teacher-enrichment is 4.88** with residual 8.10 and periodicity
0.865, and the orientation is decisively determined
(`registration_offset_2026-08-07.md:257-271`; also `../scrollgt/baselines/BASELINES.md:119-131`).
Its 55.1 px placement is a **properly measured failure**, not a weakly determined one. That
strengthens this finding rather than qualifying it.

The same correction retires a claim in the 2026-07-11 orientation addendum
(`orientation_probe_2026-07-11.md:51-52`): that if the orientation prior were wrong on that
segment, half the fine-tune's training labels may have been geometric noise. The labels were
fine. The registration was broken. That distinction is the whole lesson of the 08-07
correction, recorded there as a third instance of the same pattern — an instrument disagreed
with us and we explained it away instead of believing it
(`registration_offset_2026-08-07.md:292-305`).

**Regions and segments are not interchangeable.** The gate is measured per region, but
`20230702185753`'s failure is segment-wide: both of its regions are poorly placed, which is a
property of that segment's 2023-vs-2026 surface disagreement rather than of either region
(`registration_offset_2026-08-07.md:341-347`). Counting regions instead of segments would
overstate how many independent candidates exist.
