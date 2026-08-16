# Registered-GT training data is exhausted on Scroll-1

**Date:** 2026-08-15
**Status:** design, awaiting review
**Supersedes the plan in:** `docs/superpowers/specs/2026-07-07-ground-truth-finetune-design.md`

## Problem

The 2026-07-11 finding "GT fine-tuning worsens held-out reading" was retracted on 2026-08-07:
the model had been fine-tuned on a displaced label. The report
`reports/detector/registration_offset_2026-08-07.md` marked the experiment
**"void, needs retraining"** and made retraining conditional on fixing the residual offset.

Two things have since made that instruction unfollowable:

1. The residual was **closed as an irreducible floor**, not a bug. The 2023 and 2026
   segmentations describe genuinely different surfaces. Two candidate fixes were tested and
   falsified. So "retrain once the residual is fixed" can never be satisfied.
2. Three of the four configured training regions now **fail the placement gate** that was
   added on 2026-08-14. The fourth passes by 1.4 px on a 48 px gate whose own per-tile
   scatter is +/- 27 to 33 px, which is not a meaningful pass.

The user approved overriding condition (1) on 2026-08-15, treating the 0.31 mm floor as a
declared label-noise term under a pre-registered rule: a positive result would be
trustworthy (the noise works against it), a negative result would be inconclusive and must
be reported as such.

Under that override, the remaining question was condition (2): where does new registered
training GT come from? This spec records the answer and what to publish about it.

## What was measured

A survey of the candidate pool, run 2026-08-15. Two independent queries:

**Local:** which Scroll-1 segments carry a 2023 hand ink label
(`villa/ink-detection/train_scrolls/<seg>/<seg>_inklabels.png`). Result: six.

**Remote:** which segments exist in the open data at
`s3://vesuvius-challenge-open-data/PHercParis4/segments/`, and whether each resolves an
`ink-detection/` (canon teacher) and `surface-volumes/` (SOTA geometry) prefix. Result: 81
segments, of which 11 are 2023-era.

Intersecting them:

| segment | hand label | in open data | placement | usable as training GT |
|---|---|---|---|---|
| `20230702185753` y4000_x2500 | yes | yes | 46.6 px | no, retired non-scoring 2026-08-14 |
| `20230702185753` y7000_x4000 | yes | yes | 53.3 px | no, fails gate |
| `20231005123336` y4000_x2500 | yes | yes | 57.5 px | no, fails gate |
| `20231005123336` y7000_x4000 | yes | yes | drops at prep | no, periodicity 0.556, ink 0.0005 |
| `20231210121321` y4000_x2500 | yes | yes | 32.0 px | **passes, but spent as held-out eval** |
| `20230820203112` | yes | **no** | n/a | no, no SOTA geometry exists |
| `20230826170124` | yes | **no** | n/a | no, no SOTA geometry exists |
| `20230903193206` | yes | **no** | n/a | no, no SOTA geometry exists |

The three absent segments are not badly placed. They are not in the open data at all:
neither `ink-detection/` nor `surface-volumes/` resolves for any of them, so there is no
SOTA geometry to register a label onto.

The complement is also measured: **eight** 2023-era segments are re-flattened in the open
data but carry no hand label (`20230929220926`, `20231007101619`, `20231012184424`,
`20231016151002`, `20231022170901`, `20231031143852`, `20231106155351`, `20231221180251`).

## Finding

On Scroll-1, the intersection {has a 2023 hand label} and {has a SOTA re-flattening} and
{passes the placement gate} contains **exactly one segment**, and that segment is required
as the held-out evaluation target.

One segment cannot be both the training set and the held-out test. This is a pigeonhole, not
a budget or compute problem.

**Two independent blockers bind, and this matters for how it is reported.** Two segments fail
on registration quality (a property of the cross-scan surface disagreement). Three more fail
on data availability (a property of what has been published). Fixing registration would not
unblock the experiment, and neither would compute. Reporting only the first would imply the
second does not exist.

## Consequences

### 1. The GT fine-tune is unanswerable as posed

Not "does not help", which is the retracted claim and was false. **Not testable**, for lack
of a training set. The pre-registered rule's negative branch fires.

Note also that the experiment's original premise is void independently of the data question.
It asked whether GT supervision could read held-out ink where distillation could not, citing
arm C at ROC-AUC 0.558. Post-correction arm C reads that segment at ~0.746. The question
"unlock reading from chance" no longer describes anything real.

### 2. ScrollGT's pixel target family is n=1 and cannot be expanded

This is the more consequential half and the reason this work ships outward rather than
staying in the lab notebook.

ScrollGT already discloses n=1 (`README.md:126`, "One scoreable pixel target"). What it
currently says is that `20231210121321` is "**currently** the only pixel target we would
stand behind". The word *currently* implies the family grows with more effort. The survey
shows it does not: the candidate pool is exhausted, and expansion requires new upstream data
that does not exist yet.

A single-target pixel family cannot separate model quality from segment idiosyncrasy. A user
scoring against ScrollGT deserves to know that, especially given the 2026-08-14 `#robots`
post actively asking people to re-pull and re-score.

### 3. Two concrete unblock paths exist, both upstream

Because both sides of the intersection were measured, the report can state what would
actually unblock this rather than ending on a dead end:

- **Re-flatten** any of the three labeled-but-absent segments (`20230820203112`,
  `20230826170124`, `20230903193206`), or
- **Hand-label** any of the eight re-flattened-but-unlabeled 2023-era segments.

Either yields a second well-placed target, subject to that segment passing the placement
gate, which is not guaranteed (measured base rate so far is 1 of 3).

## Deliverables

### D1. Committed survey probe

`scripts/probe_labeled_segment_availability.py`.

The survey above was run ad hoc. Per the lesson recorded in the 2026-08-14 claim-vs-test
audit (failures were never in metric code, always in properties measured once and never
re-checked), a finding that gates a published benchmark must be re-runnable.

The probe reports, per Scroll-1 segment: has-label, in-open-data, has-teacher-prefix,
has-surface-volumes, and where a registration already exists, its placement offset. It emits
JSON alongside a human-readable table. Network-dependent, so it must degrade to a clear
error rather than a silent empty result when the bucket is unreachable.

### D2. Report

`reports/detector/gt_training_data_exhaustion_2026-08-15.md`.

Leads with the intersection finding, then its two consequences and the two unblock paths.
States both blockers explicitly. Cites the probe so any reader can re-run it.

### D3. ScrollGT disclosure

In the published repo (`../scrollgt`, separate git remote):

- `README.md`: replace "currently the only pixel target we would stand behind" with the
  exhaustion result, and state what would expand the family. Match the file's existing prose
  style, which uses em-dashes, rather than the no-dash house style used for Discord and prize
  drafts.
- `baselines/BASELINES.md`: same fact where the withheld fourth region is discussed, so a
  reader who lands there does not infer the pool is merely under-processed.

Framed as a limitation of the benchmark, not as a finding about anyone's model.

### D4. Record cleanup in vesuvius-autoresearch

- **Regenerate `reports/detector/gt_finetune_prep.json`.** The committed artifact predates
  the placement gate and records all four regions as `passed: true` with
  `placement_verified: null`. It currently tells a reader the retracted story. If it cannot
  be regenerated without a network fetch, replace it with an explicit superseded marker
  rather than leaving stale numbers in place.
- **Amend `reports/detector/registration_offset_2026-08-07.md`.** The line
  "Void, needs retraining ... should not be retrained until the residual is fixed" becomes
  "void, not retrainable: no training set exists", citing D2 and noting that the residual
  precondition was moot because the residual is closed as a floor.
- **Amend `repro/sota_data/gt_finetune.py`.** The `len(kept) < 2` guard message says the
  experiment "needs new training GT". Update it to say that no such GT exists on Scroll-1 in
  the current open data, and point at D2.

## Non-goals

- **No retraining.** The pre-registered rule's negative branch fired. Running the fine-tune
  on one marginal region anyway would reproduce the underpowered result being corrected.
- **No attempt to rescue the two failing segments.** Their placement error is the cross-scan
  floor, already closed after two falsified fix attempts.
- **The `PHercParis2Fr47`/`Fr143` fragment variant is out of scope.** Training on fragments
  and evaluating on Scroll-1 is cross-domain transfer, a different question from held-out
  Scroll-1 reading. It may be worth a future pre-registered experiment. Starting it inside
  this block would be salvaging a closed experiment, which is the motivated-reasoning pattern
  this work exists to correct.
- **No new outward announcement.** D3 corrects the published repo. Whether to post about it
  is a separate decision, deliberately not bundled here.

## Verification

- D1 runs clean and its output reproduces the table in this spec, specifically: six labeled
  segments, three present in the open data, three absent, eight re-flattened-and-unlabeled.
- A test pins the exhaustion claim so it cannot rot silently. It asserts the *local*,
  offline half (which segments carry labels, and which of those have a registration on disk)
  and is skipped rather than failed when the network is unavailable, so CI does not depend
  on the bucket.
- ScrollGT's existing test suite passes after the D3 edits.
- No claim in D2 restates a number without a cite to either the probe output or
  `registration_offset_2026-08-07.md`.

## Risks and limitations

- **The absence result is a point-in-time observation.** The open data changes; the three
  segments could be published later. D1 exists so the claim can be re-checked rather than
  trusted, and D2 must date-stamp it.
- **Placement verification is relative, not absolute.** `placement_peak` measures label
  agreement against the canon teacher crop, so it localises disagreement between two
  artifacts rather than establishing truth. This is a general caveat on every placement
  figure quoted here, and it does not single out any one segment.

  It is specifically *not* a caveat on `20231005123336`, and an earlier draft of this spec
  wrongly said it was. The chance-quality teacher there (enrichment ~1 across all four
  orientation candidates) was our own second hardcoded level-0 shape; re-registered with the
  fix, teacher-enrichment is **4.88** and the orientation is decisively determined
  (`../scrollgt/baselines/BASELINES.md:119-131`). Its 57.5 px placement is a properly
  measured failure, not a weakly determined one. That strengthens the finding rather than
  qualifying it.
- **The base rate for a new segment passing the gate is 1 of 3 measured.** The unblock paths
  in D2 should be stated as necessary, not sufficient.
