# Scroll-Augmentation Library — Design

**Date:** 2026-06-11
**Status:** approved (pending spec review)
**Goal:** Turn our scroll-specific 3D augmentations into a clean, tested, documented, reusable library that the autoresearch loop actually uses — and fix a real bug along the way. First Tier-1 deliverable of the June "own-repo-as-prize-artifact" plan.

## Context

The repo has scroll-physics augmentations for ink-detection training (modeling beam scatter, sheet compression, missing layers, etc.) — directly relevant to open villa issue **#201, "Scroll specific 3d augmentations for model training."** But the code is duplicated and partly broken:

- **`scroll_augmentations.py` (root):** a clean, well-documented module of ~10 augmentations (decohesion with z-ghost, warping, squeeze, z-dropout, intensity-drift, sheet-compression, thick-slice, rician-noise, blank-rectangles) plus a config-driven dispatcher. Designed to be standalone ("pure functions on torch tensors — no train.py imports"). **Only used by helper scripts, not the production loop.**
- **`scripts/training/train.py` (inline, lines 718/751):** the loop's *actual* augmentation path implements only **4** augmentations (decohesion as simple blur, z-dropout, intensity-drift, squeeze).

**The bug:** the loop's bandit samples probabilities for all ~10 augmentation families (the live config has e.g. `aug_scroll_blank_rectangles_p: 0.25`), but train.py's inline dispatcher reads only 4 — so **5 augmentation tweaks (blank-rectangles, rician-noise, thick-slice, sheet-compression, warping) are silent no-ops**, and the bandit has been crediting/discrediting families that never ran. The complete implementations already exist in the unused root module.

**Why fix it now:** shipping a showcased library the loop doesn't use — while a silent bug wastes bandit cycles — undermines a prize submission. Unifying is both the honest move and the higher-value one.

## Design

Single source of truth: `scroll_augmentations.py` becomes *the* library; train.py imports it; the inline duplicate is deleted.

### Components

1. **`scroll_augmentations.py` — the library.** Keep the existing pure augmentation functions (already documented with scroll-physics rationale and shape contracts). Add a clean public API decoupled from `ExperimentConfig` so external users don't need our config object:
   - `apply_scroll_augmentations(x, target_ink, target_fiber, probs: ScrollAugProbs)` — explicit probabilities (a small dataclass with the 10 `*_p` fields), the reusable entry point.
   - Keep `apply_scroll_specific_3d_augmentations(x, ink, fiber, config)` as a thin **config adapter** that reads `aug_scroll_*_p` off the config and calls the explicit API — this is what the loop uses (backward-compatible name/signature).
   - Public `__all__` listing each augmentation + both entry points.

2. **`scripts/training/train.py` — consume the library.** Delete the inline `apply_scroll_specific_3d_augmentations` (line 751) and `_scroll_squeeze_warp` (line 718); `from scroll_augmentations import apply_scroll_specific_3d_augmentations`. `scroll_augmentations.py` is a top-level module at repo root, so this is a bare top-level import (repo root is on the loop's `PYTHONPATH=.`); the existing helper scripts already import it this way successfully. Confirm it resolves both when train.py runs as a subprocess and when imported as `scripts.training.train`. Call site at line 1063 is unchanged. Net effect: all sampled augmentations now actually apply.

3. **Tests** (`tests/test_scroll_specific_augmentations.py`, extend): for each augmentation — shape preserved, output finite and clamped to [0,1], seeded determinism, geometric augs (warping/squeeze/thick-slice) transform targets consistently with `x`, and each aug measurably changes its input. Plus a **no-op-bug regression guard**: with all `*_p = 1.0`, assert every augmentation family is exercised (the dispatcher must touch all 10, not 4).

4. **Visual demos** (`scripts/visualize_scroll_augmentations.py`, exists — verify/enhance): generate before/after montages for each augmentation on a real Fr47 patch, written to `reports/augmentation_demos/`, for the README and the prize filing.

5. **Library docs** (`docs/SCROLL_AUGMENTATIONS.md` + README section): what each augmentation models physically, parameter ranges, the explicit-probabilities API with a usage example, links to the demo images and villa issue #201.

### Data flow

`train.py` validation/training loop → `apply_scroll_specific_3d_augmentations(x, ink, fiber, config)` (adapter) → `apply_scroll_augmentations(x, ink, fiber, probs)` (library) → each augmentation fires with its sampled probability → clamped tensors returned. External users call the explicit API directly with their own `ScrollAugProbs`.

### Parallel-safety & risk

- Library work (explicit API, tests, demos, docs) touches only the root module + scripts → **parallel-safe while the loop runs**.
- Only the train.py unify edit is loop-critical: **pause the loop, swap, verify, restart** (per [[autoresearch-loop-autocommits]]).
- **Behavioral change:** decohesion gains a z-ghost component and 5 augmentations newly activate. This changes what models train on. Verify no NaN/instability and that the loop completes a cycle; the bandit re-learns family weights honestly from here.

## Verification

- `pytest tests/test_scroll_specific_augmentations.py` passes, including the no-op regression guard.
- `train.py --smoke` (default) and `--test` with augmentations enabled both pass with no NaN/instability.
- Loop runs one full cycle post-swap without error (check `autoresearch.out` + a history row).
- `scripts/visualize_scroll_augmentations.py` produces before/after montages in `reports/augmentation_demos/`.
- Diff is limited to: `scroll_augmentations.py`, `scripts/training/train.py` (deletions + import), tests, the demo script, and docs.

## Out of scope (later)

- Ablation quantifying the richer augmentations' effect on the train→val AUC gap (optional follow-up; uses GPU).
- A villa PR against #201 (deferred — own-repo-first per the June plan).
