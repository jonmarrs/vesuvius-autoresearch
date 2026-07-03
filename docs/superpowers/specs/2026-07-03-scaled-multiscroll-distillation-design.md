# Scaled Multi-Scroll Distillation (Arm C) — Design

**Status:** Approved design (brainstorming; scaled shape chosen by recommendation after user AFK —
revisit at spec review). Fourth slice of the SOTA-rebase pivot, following the cross-scroll
diversity experiment (`2026-07-02-cross-scroll-distillation-design.md`).

## Context & motivation

The diversity experiment's verdict: training-scroll diversity at fixed budget substantially
improves transfer to an unseen scroll (held-out PHerc-1667 region, vs teacher: arm B lift 2.12 /
roc_auc 0.689 vs legacy baseline 1.47 / 0.591; single-scroll arm A over-specializes at 1.22).
The obvious next lever is **more scrolls**.

**Data reality (verified by a full bucket sweep, 45 PHerc entries):** only **4 scrolls** have
segments with both surface volumes and canon teacher predictions — PHercParis4/Scroll 1 (81
segments), PHerc0139 (38), **PHerc0172 (53, new to us)**, PHerc1667 (20). The rest lack released
predictions (first-segment probe). So "scale" concretely means **3 training scrolls** (adding
PHerc0172), with PHerc1667 kept as the unseen held-out for comparability with the arm history.

## The run (capability, not controlled science)

**Arm C:** train the unchanged TimeSformer recipe on **6 regions — 2 each from Scroll 1,
PHerc 0139, and PHerc 0172** (the 4 existing arm-B regions + 2 new 0172 regions), ~1.5× arm B's
budget, ~15–20 h. Measure on the **same held-out PHerc-1667 region** as all prior arms.

| on held-out 1667 (vs teacher) | comparator |
| --- | --- |
| legacy baseline | lift 1.47 (no selection asymmetry — the anchor comparison) |
| arm A (1 scroll, 4 regions) | lift 1.22 |
| arm B (2 scrolls, 4 regions) | lift 2.12 |
| **arm C (3 scrolls, 6 regions)** | **the question** |

**Acknowledged confound:** C differs from B in both diversity (+PHerc0172) and volume (6 vs 4
regions) — this is a *capability* run (best model buildable from available teachers), not another
single-variable experiment; the report says so explicitly.

**Reading:** C > B ⇒ scaling scrolls+data keeps improving unseen-scroll transfer (July-filing
headline). C ≈ B ⇒ transfer saturates at this recipe/scale (equally honest; points at the recipe
or 1667's distinct preparation). Same-scroll costs tracked via secondaries.

## Honesty framing (binding, unchanged)

All metrics agreement-with-teacher; per-scroll teacher provenance persisted (0172's teachers
inspected on first download); the selection-set caveat stated with the baseline-anchored
comparison as primary; no ground-truth claims.

## Goals / success criteria

1. Registry gains `"pherc0172": "PHerc0172"` (test updated).
2. Arm-C machinery in `xscroll_run.py` with minimal churn to the reviewed arm-B path (the plan
   picks the mechanism — parameterization or parallel `*_c` subcommands).
3. The scaled run executed: prep (0172 regions chosen by the 0.02–0.4 sanity-band rule) → train
   (12 epochs) → measure → committed report `reports/detector/cross_scroll_scale.{md,json}` with
   the four-row held-out table, secondaries (incl. arm C on a held-out 0172 region), and renders.
4. A stated verdict against the reading above — either direction.

## Non-goals

- No more than one training run; no 4th training scroll (none has teachers); held-out stays the
  same 1667 region (comparability). No ground-truth registration; no loop integration; no
  detector-code changes.

## Architecture & components

1. **`distill_run.py`:** one registry line (`"pherc0172": "PHerc0172"`). Everything else reused.
2. **`xscroll_run.py`:** add `TRAIN_C` (6 targets: arm-B's 4 + 2 PHerc-0172 entries with
   prep-adjustable offsets), `SECONDARY_0172_HELD` (1 region, for C's same-scroll read-out),
   `MODEL_DIR_C = "models/detector_xscroll_c"`, and arm-C prep/train/measure paths. The measure
   step writes `cross_scroll_scale.{md,json}`: four-row held-out-1667 table (baseline/A/B/C —
   baseline+A+B values re-used from the committed `cross_scroll_distill.json` rather than
   re-inferred, cited as such) + secondaries (C on held 0172/0139/Scroll-1 regions; B's values
   cited) + renders (C + teacher on 1667).
3. **Tests:** registry test gains the 0172 entry; any new pure helper (e.g., arm selection)
   tested. Operational paths verified by running.

## Data flow

```
bucket/{PHercParis4,PHerc0139,PHerc0172}/segments -> prep 7 fragments (6 train + held-0172)
  [held-1667 + held-0139 + Phase-2 scroll1 fragments already on disk]
train arm C (12 epochs, ~15-20h, valid = held-1667 fragment)
measure: best epoch on held-1667; secondaries; four-row table citing committed A/B numbers
  -> reports/detector/cross_scroll_scale.{md,json} + renders
```

## Error handling & operations

Phase-2/XS rules verbatim: loud guards, re-runnable ops, provenance persisted, loop paused for
GPU steps, degenerate-region adjustment rule, NaN-safe best-epoch selection, empty-ckpt/missing-
prereq guards. New: measure requires the committed `cross_scroll_distill.json` (loud error if
missing).

## Global constraints

As the prior slice: agreement-with-teacher framing; unchanged `detector.train` config-only;
anonymous S3; isolation to `repro/sota_data/` + `tests/` + `reports/detector/` +
`local_data/` (git-ignored); no `run_autoresearch_loop.py`/`scripts/training/train.py` edits;
no AI-authorship markers.

## Follow-ups (out of scope)

- Re-sweep the bucket periodically: more scrolls gain canon predictions over time (the pool was
  4 of 45 at 2026-07-03) — each new teacher scroll extends this recipe directly.
- Ground-truth label registration; Sub-project C (loop over distillation configs); July filing
  refresh with the arm-C result (deadline 2026-07-31).
- Checkpoint pruning: `models/detector_sota_distill` + `models/detector_xscroll` (+ new
  `detector_xscroll_c`) each hold 12 ckpts (~4.5 GB each) — prunable to best epochs.
