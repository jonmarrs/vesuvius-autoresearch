# Ground-Truth Fine-Tuning (POC) — Design

**Status:** Approved design (brainstorming; fine-tune mode chosen by recommendation after user
AFK — revisit at spec review). Seventh slice of the SOTA-rebase pivot, following the held-out
ground-truth result (`2026-07-07-heldout-gt-registration-design.md`).

## Context & motivation

The held-out ground-truth test settled the distillation question with a negative: on a segment no
student trained on, scored against human labels, the distilled students read **near chance**
(ROC-AUC ~0.55) — distillation-from-canon reproduces the teacher faithfully, including its
failures, not independent reading. The direct response the negative points at: **stop training on
the teacher's predictions; train on the human labels we can now register onto SOTA geometry.**

This slice is the proof-of-concept for that: does ground-truth supervision read a held-out
segment better than distillation-from-canon?

## Feasibility (verified by sweep)

Only **3 of 7** hand-labeled Scroll-1 segments have all registration inputs (hand label +
`original.obj` + canon teacher + surface zarr): `20230702185753`, `20231005123336`,
`20231210121321`. This forces a clean design:
- **Train** on GT-registered labels of `20230702185753` + `20231005123336` (the 2 segments the
  students distilled on — same data, real labels instead of teacher predictions).
- **Test** on the held-out `20231210121321` GT (already registered; distilled students read
  0.55–0.56 there).

Data is thin (2 segments), so the experiment **fine-tunes the existing best distilled model
(arm C)** rather than training from scratch — a clean before/after on the same model that needs
far less data. arm C never trained or selected on `20231210121321`, so it stays genuine held-out
for the fine-tuned model too.

## The experiment

| model | held-out `20231210121321` vs GT (already measured / to measure) |
| --- | --- |
| arm C (distilled, baseline) | ROC-AUC 0.558 / lift 1.17 (committed) |
| **arm C + GT fine-tune** | **the question** |

**Reading:** fine-tuned ≫ 0.558 ⇒ ground-truth supervision reads held-out ink where
distillation-from-canon could not — the genuine positive the project has been chasing.
fine-tuned ≈ 0.558 ⇒ GT training on this little data doesn't beat distillation (honest, but
confounded by data thinness — a scale limitation, not necessarily a GT-vs-teacher verdict).
Either is a clean, reportable result on the same before/after axis.

## Honesty framing (binding)

- Every GT-training fragment's label comes from a **registration that passed the teacher-free
  alignment gate** for its own region (residual + periodicity); regions that fail are dropped,
  not used (the standing "no training/scoring on a misaligned label" discipline). Per-region
  alignment stats are recorded.
- The result is framed as **before/after fine-tuning arm C** (the init is the distilled model);
  we do not claim a from-scratch GT detector. The 2-segment data-thinness caveat is stated.
- The held-out score reuses the validated slice-6 registration of `20231210121321`.

## Architecture & components

All in `repro/sota_data/`, reusing `register.py` + the detector subpackage.

1. **`gt_prep.py`** — for each (segment, region) in the training set: `warp_obj`-register the hand
   label onto that region's SOTA surface, run the teacher-free alignment gate (residual +
   `label_line_periodicity`), and — if it passes — write a detector-format training fragment whose
   `inklabels.png` is the **registered GT** (reusing the already-prepped SOTA surface layers;
   only the label changes). Returns which regions passed + their stats. Unit-tested on the
   geometry/label-swap (synthetic); operational registration verified by running.
2. **`gt_finetune.py`** (operational) — load the arm C checkpoint as init, fine-tune on the
   passing GT fragments for a few epochs at a low LR (exact resume mechanism confirmed against
   `detector.train`/`DetectorModel` in the plan — if `detector.train` can't init-from-checkpoint,
   a thin Lightning `fit(ckpt_path=...)`-style loader), save to `models/detector_gt_finetune/`.
3. **Scoring** — extend the held-out registration's `score` (or a small runner) to add the
   fine-tuned checkpoint as a row against the committed `20231210121321` GT, producing
   `reports/detector/gt_finetune_heldout.{md,json}` with the arm-C-before / arm-C+GT-after
   comparison.

## Non-goals

- No from-scratch GT training (data too thin; the pure A/B is a deferred follow-up).
- No new scrolls / cross-scroll GT (blocked on released human labels).
- No detector-architecture changes (same TimeSformer; fine-tune only).
- Not a labels-at-scale pipeline — a 2-segment POC.

## Success criteria

1. GT-training fragments produced only from alignment-gate-passing registrations (or an honest
   "too few regions registered" stop).
2. A fine-tuned checkpoint + a committed before/after report on the held-out `20231210121321` GT.
3. A stated verdict on the before/after axis, with the data-thinness caveat.

## Global constraints

Isolation (`repro/sota_data/` + `tests/` + `reports/detector/` + git-ignored `local_data/` +
`models/`); anonymous S3; no detector-architecture changes; loop paused for GPU (fine-tune +
score); no AI-authorship markers.

## Follow-ups (out of scope)

- From-scratch GT training (pure supervision-signal A/B) if fine-tune is promising.
- Registering hand labels for the segments currently lacking SOTA bridge inputs, if the core team
  publishes their re-flattened surfaces.
- July filing refresh with the before/after result (deadline 2026-07-31).
