# Cross-Scroll Distillation — Design

**Status:** Approved design (brainstorming; controlled-experiment shape chosen by recommendation
after user AFK — revisit at spec review). Third slice of the "rebase on SOTA capabilities" pivot,
following Phase 2 (`2026-07-01-sota-distillation-design.md`).

## Context & motivation

Phase 2 proved distillation works within one scroll: a student trained on 4 Scroll-1 regions
against the released canon predictions reaches held-out **agreement-with-teacher val_f1 0.662 /
lift 3.24** (baseline: chance). The project's measured central problem remains **cross-scroll
generalization** (legacy detector: lift 2.07 same-scroll → 1.29 cross-scroll).

Verified by discovery: the open bucket carries the identical layout (2.4 µm surface-volume zarr +
`new_canon_autoresearch_recipe` teacher tif per segment) for at least three scrolls —
**PHercParis4 / Scroll 1 (44 segments), PHerc0139 (38), PHerc1667 (20, the fully-read scroll)**.
So a *controlled* cross-scroll experiment is possible entirely within the existing distillation
pipeline.

## The experiment (one variable: training-scroll diversity)

Held-out evaluation target: **one PHerc 1667 region** (a scroll no arm trains on; echoes the
community's "train elsewhere → generalize to 1667" benchmark direction).

| Arm | Training data | Cost |
| --- | --- | --- |
| Baseline | legacy detector (`models/detector/detector_epoch=7.ckpt`), no distillation | infer only |
| A: single-scroll student | the **existing Phase-2 student** (best epoch, 4 Scroll-1 regions) — no new training | infer only |
| B: multi-scroll student | **4 regions total: 2 Scroll-1 + 2 PHerc-0139** (same budget as A; diversity is the only change) | one ~10 h train |

Secondary read-outs (infer-only): each student on its own training scrolls' held-out segments
(the Phase-2 held-out Scroll-1 region; a held-out PHerc-0139 region for arm B), to see whether
diversity costs same-scroll performance.

**Interpretation (any outcome is a finding):**
- B ≫ A on 1667 ⇒ training-scroll diversity drives generalization at fixed budget.
- B ≈ A ⇒ diversity alone is insufficient at this scale (volume or 1667's distinct preparation
  dominates).
- A ≫ baseline ⇒ even single-scroll distillation transfers across scrolls.

## Honesty framing (binding, unchanged from Phase 2)

All metrics are **agreement-with-teacher** (the released canon predictions) — never ground-truth
accuracy; report titles/columns/JSON keys carry the framing; teacher provenance (dtype/range,
binarize ≥128) persisted per scroll. No fabricated numbers where alignment is unverified.

## Goals / success criteria

1. `distill_run.py` generalized to multiple scrolls (config-driven bucket prefixes), tests for
   the new mapping; everything else (prep/baseline/train/measure, guards, NaN-safe selection)
   reused.
2. The three-arm measurement on the same held-out PHerc-1667 region, plus secondary same-scroll
   read-outs, in one committed report (`reports/detector/cross_scroll_distill.md` + `.json` +
   renders).
3. A stated verdict against the interpretation table above — either direction.

## Non-goals

- No ground-truth label registration (separate follow-up); no legibility claim.
- No more than one new training run (arm B); no >2 training scrolls.
- No loop integration (Sub-project C); no detector code changes.

## Architecture & components

All in `repro/sota_data/`, extending Phase 2's files.

### 1. Scroll registry (the one real code change)
`distill_run.py` replaces its hardcoded `PHercParis4` paths with a module-level registry:

```python
SCROLLS = {
    "scroll1": "PHercParis4",
    "pherc0139": "PHerc0139",
    "pherc1667": "PHerc1667",
}
```

`fetch_teacher(scroll_key, seg)` / `extract_region(scroll_key, seg, y0, x0)` take the scroll key
and build `{BUCKET}/{SCROLLS[scroll_key]}/segments/{seg}/...`. Fragment ids gain the scroll key
(`{scroll_key}_{seg}_y{y0}_x{x0}`) so multi-scroll fragments coexist under one `data_root`.
Teacher cache filenames likewise (`{scroll_key}_{seg}.tif`).

### 2. Experiment arms as data
The experiment definition is a dict of named arms:

```python
ARMS = {
    "armB_multiscroll": {
        "train": [("scroll1", SEG_S1_A, Y, X), ("scroll1", SEG_S1_B, Y, X),
                  ("pherc0139", SEG_139_A, Y, X), ("pherc0139", SEG_139_B, Y, X)],
        "model_dir": "models/detector_xscroll",
    },
}
HELD_OUT = ("pherc1667", SEG_1667, Y, X)      # measured by every arm
```

Segment ids and region offsets are chosen operationally at prep time (teacher-positive fraction
in the 0.02–0.4 sanity band; adjust offsets if degenerate — the Phase-2 rule). Arm A needs no
training entry: it is the existing checkpoint
`models/detector_sota_distill/detector_epoch=9.ckpt`.

### 3. Measurement
`measure` evaluates a list of `(label, checkpoint)` pairs — baseline (epoch-7 legacy), arm A
(Phase-2 best), arm B (best-of-12 by held-out-1667 agreement, NaN-safe as in Phase 2) — on the
held-out 1667 fragment, plus the secondary read-outs, writing one comparative report with
renders (each student + teacher, side by side).

### 4. Tests
- Registry path construction (`fetch_teacher`/`extract_region` build the right bucket prefixes
  for each scroll key; unknown key ⇒ `ValueError`).
- Fragment-id round-trip (`{scroll_key}_{seg}_y{y}_x{x}` produces loadable, collision-free
  fragment dirs — synthetic, via `prep_distill_fragment`).
- Everything already covered by Phase-2 suites (prep geometry, guards, to_uint8) is reused, not
  re-tested.

## Data flow

```
bucket/{PHercParis4,PHerc0139,PHerc1667}/segments/<seg>/{surface-volumes/*.zarr, ink-detection/<canon>.tif}
  prep (per arm + held-out): extract level-2 regions -> teacher crop -> detector-format fragments
  baseline + armA: infer existing checkpoints on held-out 1667 fragment  [no training]
  armB: detector.train on its 4 fragments (valid = held-out 1667 fragment), ~10 h
  measure: {baseline, armA, armB} x held-out-1667  (+ secondary same-scroll read-outs)
  -> reports/detector/cross_scroll_distill.{md,json} + renders
```

## Error handling & operations

Phase-2 rules carry over verbatim: loud `ValueError`s on shape/anisotropy/missing-files; ops
re-runnable; teacher provenance persisted; loop paused for GPU steps (`.loop_paused` +
`bash start.sh`); degenerate-region rule at prep. New: unknown scroll key ⇒ `ValueError`;
per-scroll teacher dtype/range recorded (1667/0139 teachers not yet inspected — the prep print +
provenance json covers them).

## Global constraints

- Metrics contract + agreement-with-teacher framing (as Phase 2). Student recipe unchanged
  (`detector.train`, config-only). Anonymous S3. Isolation: `repro/sota_data/` + `tests/` +
  `reports/detector/` + `local_data/` (git-ignored). No edits to `run_autoresearch_loop.py` /
  `scripts/training/train.py`. No AI-authorship markers.

## Follow-ups (out of scope)

- Ground-truth label registration onto the SOTA flattening (independent validation).
- Scaling beyond 3 scrolls / larger budgets (informed by this experiment's verdict).
- Sub-project C: loop over distillation configs.
- July filing refresh with this result (deadline 2026-07-31).
