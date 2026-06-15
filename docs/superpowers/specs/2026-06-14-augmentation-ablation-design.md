# Augmentation Ablation (none vs full) — Design

**Date:** 2026-06-14
**Status:** approved
**Goal:** Decide whether the production training regime's heavy augmentation is
suppressing the learnable ink signal, by training a fresh resenc with
augmentation **fully off** vs **full production augmentation** and comparing
**train + val** pooled pixel AUC.

## Context

The overfit probe ([[overfit-probe-result]]) ruled out capacity and pipeline:
a fresh resenc memorizes 16 un-augmented Fr47 ink patches to pixel AUC 1.0 in 100
steps, yet under the production regime (full 7,345-patch set + heavy augmentation)
the same architecture reaches only ~0.58 train / ~0.52 val (Probe 0). The
bottleneck is therefore the training regime — most plausibly augmentation strong
enough to scramble the ink↔CT relationship the model otherwise fits trivially.
This ablation tests that hypothesis directly.

The honest metric is **pooled pixel AUC** on a fixed random sample of patches:
on **train** = Fr47 (the trained-on fragment) and on **val** = the held-out
Fr143 **V-region** (the spatially-disjoint region from the pseudo-label study).
val_bpb and per-patch AUC are artifact-saturated / noisy and are not the decision
axis.

## Key finding that shapes the design

Zeroing the config augmentation probabilities does **not** disable augmentation.
Three sites in `scripts/training/train.py` fire unconditionally (bare
`np.random`, not gated by config):

1. `apply_augmentations` — the "albumentations" path applies rot90 + flips every
   call regardless of `aug_*_p`.
2. Z-compression (~line 1532) — 20% per step.
3. mixup / cutmix (~lines 1588-1597) — 20% / 20% per step when batch > 1.

So a true "none" arm needs a **master kill-switch**, not config-prob zeroing.

## Architecture

One gated config flag, `disable_augmentation: bool = False` (default off → the
running loop is byte-identical). When `True` it short-circuits all three sites:
`apply_augmentations` returns its `(x, target_ink, target_fiber)` inputs
unchanged, and the z-compression and mixup/cutmix blocks are skipped. Two run
configs (full vs none) then train fresh and are compared.

## Components

- **`disable_augmentation` switch** (`scripts/training/train.py`):
  - new dataclass field `disable_augmentation: bool = False`.
  - `apply_augmentations(x, target_ink, target_fiber, step, max_steps, config=None)`
    returns `(x, target_ink, target_fiber)` immediately when
    `getattr(config, "disable_augmentation", False)` is set (before any transform).
  - in the training loop, wrap the z-compression block (the `if np.random.rand()
    > 0.8:` thinner-Z branch) and the mixup/cutmix block (`if x_orig.size(0) > 1:
    ... r = np.random.rand() ...`) so they are skipped when
    `config.disable_augmentation` is set. (The `z_start` jitter and the plain
    `x_orig = x_raw[:, :, z_start:z_start+num_layers]` central slice stay — they
    are the standard z-window selection, not augmentation; only the *random
    z-compression* branch is gated.)
- **`experiments/aug_ablation/cfg_aug_full.json`** — production resenc config,
  `uris=[Fr47]`, `val_uri=Fr143_Vregion`, fresh init (best_model aside),
  `time_budget≈7200` (~2h), `checkpoint_out=experiments/aug_ablation/full_model.pt`,
  `eval_every_steps=1000`, `eval_sample_patches=250`, `use_wandb=false`,
  `disable_augmentation=false`.
- **`experiments/aug_ablation/cfg_aug_none.json`** — identical but
  `disable_augmentation=true`, `checkpoint_out=.../none_model.pt`.
- **Post-hoc measurement** — for each arm's final checkpoint, pooled pixel AUC on
  Fr47 (train) and Fr143_Vregion (val), reusing the Probe-0 / `pooled_pixel_auc`
  pattern (fixed seeded 250-patch sample, `jitter=False`).
- **Classification** — fill the decision table from the four numbers
  (full train/val, none train/val).

## Decision rule

| Observation | Conclusion → next lever |
| --- | --- |
| none **val** > full val (meaningful margin) | augmentation was suppressing signal → de-augment / isolate the harmful family |
| none **train** ≫ full train but none val ≈ full val | pure generalization gap (memorizes, doesn't transfer) → regularization / data, or 64px limits generalization |
| none val ≈ full val (or worse) | augmentation is not the bottleneck / it aids regularization → keep aug, look elsewhere |

"Meaningful margin" = ≥ +0.03 pooled pixel AUC (above the ~±0.01 sampling noise
seen across prior measurements).

## Operational / safety

- Pause the loop (`.loop_paused` + kill PIDs), verify GPU free via `nvidia-smi`.
- Move `best_model.pt` aside for fresh init; restore after; keep a backup.
- All saves go through `checkpoint_out` to `experiments/aug_ablation/`; the loop's
  `best_model.pt`/`history.tsv` are never touched (verified by the smoke check
  used in the long-schedule plan).
- `disable_augmentation` defaults False → the loop's training is unchanged until a
  config opts in.

## Testing

- Unit test: `apply_augmentations` with a config where `disable_augmentation=True`
  returns the exact input tensors unchanged (identity), and with it False (and a
  fixed seed) returns something (smoke — does not assert specific transforms).
- The z-compression / mixup gating is validated by a short smoke run of
  `cfg_aug_none` (tiny budget): confirm it trains, writes a curve CSV, and leaves
  loop state untouched. (Hard to unit-test deep-loop gating; the smoke is the
  gate.)

## Out of scope

- Isolating *which* augmentation family hurts (the fast follow-up if "none" wins).
- A regularization axis (weight_decay/dropout) — deferred.
- Promoting any arm to production (separate decision if a clean win appears).
