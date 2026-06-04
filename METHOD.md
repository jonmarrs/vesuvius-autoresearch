# Method

## Goal

Automate the search for good 3D ink-detection configurations on the Vesuvius
Challenge, with every result gated by reproducible evidence rather than ad-hoc
judgement.

## Search loop

Each cycle of `run_autoresearch_loop.py`:

1. **Sample a configuration.** A bandit-style sampler draws from a configuration
   space — architecture (gated UNet-transformer, TimeSformer, ResNet3D-101,
   Inception-I3D), loss terms, augmentation settings, and related hyperparameters.
   Families that have produced improvements are weighted up; duplicates are
   re-sampled for diversity.
2. **Preflight smoke check.** Before spending the training budget, the candidate is
   built and run through one forward/backward pass on a synthetic batch
   (`train.py --smoke`). A configuration that cannot build or run is skipped
   immediately rather than consuming a cycle.
3. **Train under a fixed budget.** The candidate trains for a fixed wall-clock
   budget (≈60 minutes) on the training fragment.
4. **Evaluate on held-out data.** The model is scored on a separate validation
   fragment it never trained on (train/predict non-overlap), producing `val_bpb`
   plus topological metrics.
5. **Keep only if better.** The new configuration is promoted only if it improves
   on the current baseline; otherwise it is reverted. The outcome of every cycle is
   appended to `results.tsv`.

## Evaluation metrics

- **`val_bpb`** — bits-per-byte on held-out cross-fragment validation (lower is
  better); the primary selection signal.
- **`centerline_dice`** and **`skeleton_distance_length`** — topological scores that
  reward correct fiber/stroke structure, not just pixel overlap. These are integrated
  from the Villa metrics suite (see `CREDITS.md`).

## Constraints honored

- **ML window ≤ 0.5×0.5 mm** — all outputs use `patch_size=64` (64×64 at 8 µm),
  within the Challenge's hallucination-mitigation cap.
- **No train/predict overlap** — training and validation use disjoint fragments.

## Honest scope

This is research tooling. On the included logged run the loop's selection mechanism
works as intended (monotonic `val_bpb` improvement under the keep-if-better rule),
but the absolute gains are small and topological scores show large remaining
headroom (see `SUBMISSION.md` → Results). The contribution offered here is the
reproducible, evidence-gated search process, not a state-of-the-art detector.
