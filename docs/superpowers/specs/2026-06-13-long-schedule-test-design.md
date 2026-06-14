# Longer From-Scratch Schedule Test — Design

**Date:** 2026-06-13
**Status:** approved
**Goal:** Determine whether the ink detector's pixel-level AUC ceiling (~0.557,
reached only by the production model after days of fragmented, warm-started
training) is a **budget** limit or a **capacity/window** limit, by running one
clean fresh-init resenc training for ~12h and tracking pooled V-region pixel AUC
as a learning curve.

## Context

Three Tier-3 experiments (TimeSformer@64px, LeJEPA, same-scroll pseudo-label
self-training) have failed to lift detection. The pseudo-label study established
that the bottleneck is the detector's pixel-level non-discrimination, not data:
a fresh 2.5h model floors at pooled pixel AUC ~0.49–0.50; even 13.5k patches of
true same-scroll labels (oracle) gave no lift; the production model reaches only
~0.557 even after days of training. See [[pseudo-label-self-training-blocked]],
[[model-barely-discriminates-ink]].

A confound remains: the production model's training was fragmented (many short
bandit cycles, warm-started, varied configs), and the fresh comparison runs were
only 2.5h. So "the detector can't discriminate" is entangled with "we never ran
one long clean schedule from scratch." This test removes that confound: one
continuous from-scratch run, fixed production recipe, ~12h, with a pixel-AUC
learning curve.

The honest metric is **pooled pixel AUC** on the held-out Fr143 **V-region** (the
same disjoint region built for the pseudo-label study). val_bpb (≈0.2627, the
predict-constant artifact floor) and per-patch AUC (noisy, reflects within-ink
ranking) are recorded for continuity but are not the decision axis.

## Decision rule

- Curve climbs past ~0.557 and is **still rising at 12h** → **budget-limited**:
  longer training / a better long schedule is a genuine lever. The final
  checkpoint becomes a promotion candidate (separate decision).
- Curve **plateaus at/near ~0.50–0.557** well before 12h → **capacity/window
  ceiling**: training longer won't fix detection; the bottleneck is the resenc
  architecture or the 64px hallucination window itself. A publishable negative
  finding that redirects strategy toward architecture/window changes.

## Architecture

One continuous training run reusing the exact production training path
(`scripts/training/train.py`). The only new behavior is a **gated periodic
evaluation hook**: every `eval_every_steps` steps the run saves a step-tagged
checkpoint and appends a pooled-pixel-AUC measurement to a curve CSV. The hook is
off by default (`eval_every_steps=0`), so the running loop is byte-identical.

train.py's existing budget-aware scheduler already stretches warmup + LR decay
across `time_budget`, so a single `time_budget≈43200` run is one clean long
schedule — no schedule changes needed.

## Components

- **`scripts/pixel_auc.py`** (new) — `pooled_pixel_auc(prob_arrays, label_arrays)`:
  a pure function concatenating per-patch probability/label arrays and returning
  `roc_auc_score` over all pixels, with a single-class guard returning 0.5. Lives
  in its own module (not `measure_ink_auc.py`, which imports `train` and would
  cause a circular import). Unit-tested.
- **train.py periodic-eval hook** — a new config field `eval_every_steps: int = 0`
  and, inside the training step loop, a gated block: when `eval_every_steps > 0`
  and `step > 0` and `step % eval_every_steps == 0`, run the model (eval mode) on
  a fixed random sample of `eval_sample_patches` (default 250) validation patches,
  collect sigmoid probabilities + binarized labels, call `pooled_pixel_auc`, save
  `{checkpoint_out}.step{step}.pt`, and append a `step,elapsed_s,pixel_auc` row
  to a curve CSV (`{checkpoint_out}.curve.csv`), then restore train mode. The
  sample indices are drawn once (seeded) so every evaluation scores the same
  patches — a comparable curve. Default `0` disables the hook entirely.
- **`experiments/long_schedule/cfg_long.json`** (new) — production resenc config,
  `uris=[Fr47]`, `val_uri=Fr143_Vregion`, fresh init (run with `best_model.pt`
  moved aside), `time_budget=43200`, `checkpoint_out=experiments/long_schedule/long_model.pt`,
  `eval_every_steps` set to ≈ max_steps/12 (~hourly; ~18000 for a 12h run, refined
  after reading the run's reported `max_steps`), `use_wandb=false`.
- **Curve analysis** — after the run, read `long_model.pt.curve.csv`, report the
  AUC trajectory (per-hour), the max, and whether it is still rising in the final
  third; write the verdict (budget vs capacity) into FINDINGS.md.

## Data flow

train loop → every N steps → sample fixed val patches → model forward (eval) →
`pooled_pixel_auc` → append row to curve CSV + save step checkpoint → resume
training. At the end: curve CSV → analysis → FINDINGS + memory.

## Isolation / safety

- `checkpoint_out` (already built) routes all saves to `experiments/long_schedule/`
  and skips loop bookkeeping; the step checkpoints use the same prefix.
- Move `best_model.pt` aside before the run (fresh init) and restore after.
- Pause the loop (`.loop_paused` + kill PIDs), verify GPU free, restart after.
- `eval_every_steps` defaults to 0 → the loop's cycles are unaffected by this code.

## Error handling

- The eval hook wraps inference in `try/except`; a failed evaluation logs a NaN
  row and continues training (a mid-run eval glitch must not kill a 12h run).
- The single-class AUC guard prevents a `roc_auc_score` crash if a sample is
  degenerate.
- A non-finite training loss already triggers train.py's existing guards; the
  hook adds no new failure path to the optimizer.

## Testing

- `pooled_pixel_auc`: unit tests for a perfect separation (AUC 1.0), random
  (≈0.5), and single-class guard (0.5).
- The hook is integration-validated by a short smoke run (`eval_every_steps`
  small, tiny budget): confirm the curve CSV gains rows, step checkpoints appear,
  and `best_model.pt`/`history.tsv` stay untouched.

## Out of scope

- Varying architecture, patch/window size, or LR schedule (those are the
  follow-ups *if* this test says "capacity/window-limited").
- Promoting the resulting model to production (a separate decision if the curve
  shows a real, sustained gain over 0.557).
- Multi-fragment or cross-scroll training (orthogonal; see
  [[cross-scroll-gap-quantified]]).
