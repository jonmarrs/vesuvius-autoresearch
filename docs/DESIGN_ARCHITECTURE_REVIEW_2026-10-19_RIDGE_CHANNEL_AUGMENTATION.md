# Design and architecture review — what the augmentations do to the ridge channel

Date: 2026-10-19. Baseline: `3da545bb` (main after #141); merged with `1d3e4a1b` (#143).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scroll_augmentations.py`, which five review docs mention but none reviewed as a module, and what the training
augmentations do to an input with more than one channel.

The round also read the least-reviewed modules `train.py` imports. They need no change (below):
- `betti_loss_module`;
- `pixel_auc`;
- `cldice_loss`;
- `frangi_torch`;
- `inference_constants`.

## What changed

- **The ridge channel received the CT's intensity augmentations.**
  - Production trains with `use_ridges`. Channel 0 is the CT, scaled to [0, 1]. Channel 1 is the ridge filter's
    response to it (`vesuvius_loader.ridge_channel`). For the incumbent's inputs, the 2026-10-13 review put those
    values at around 1e-5 to 1e-3.
  - The Albumentations recipe concatenates both channels' slices into one `(H, W, D*C)` image, and ran every
    transform on it. Measured on the patch below, each transform at p=1:
    - `RandomBrightnessContrast` (production p 0.75) shifts by up to ±0.2, and albumentations 1.3.1 clips a float
      image to [0, 1]. It zeroed the ridge channel in 46% of samples and lifted it above its own maximum in 54%.
    - `GaussNoise` (in the `OneOf`, p 0.4, a third of the time) has std 0.1 to 0.17. The noisy ridge channel's
      correlation with the original is 0.00.
    - The two blurs keep its shape (correlation 0.99 to 1.00).

    So in about four of five training samples the ridge channel was zeroed, far past its range, or noise. At
    inference it is the filter's response to the scan.
  - The scroll intensity drift (production p 0.25) adds up to ±0.08, 73 times the ridge channel's maximum. The ridge
    channel of the drifted CT moves much less: its offset cancels, and at the steepest depth slope it still
    correlates 0.80 with the original (1.00 without a slope).
  - Two that production leaves at p 0 did the same:
    - Rician noise, which changed the ridge channel by up to 359 times its maximum on average;
    - blank rectangles, which filled each region with one mean over the batch and both channels. That put a share
      of the CT's values, up to 298 times the ridge maximum, into the ridge channel.
  - **Now:**
    - `_get_villa_aug` returns each transform as a stage of its own, in the same order, each with its own p.
      `_apply_recipe` runs the pixel-level stages (an `ImageOnlyTransform`, or a `OneOf` of them) on the CT's
      slices only. The spatial stages move both channels and the labels, as before.
    - Each stage runs with `force_apply`. That skips only the stage's own draw: a p=1 Compose, which always runs.
      For a CT-only image, the stages give bit for bit what one Compose of the same transforms gives.
    - `scroll_augmentations.apply_scroll_augmentations` takes `ct_channels`. Intensity drift and Rician noise apply
      to that many leading channels; the loop's adapter passes 1. The augmentations that move voxels, mix them along
      z or blank a region act on every channel, each in its own values. With the default, `None`, the library
      augments every channel, as before, for other callers.
    - Blank rectangles fill each sample's and channel's region with its own mean.
  - **Measured after.**
    - The ridge channel: 200 samples through the production recipe (the scroll augmentations off).
      - None moved its median past its range; 71 did before.
      - Its mean absolute change at the 90th percentile is 2e-4 (0.2 times its maximum), from geometry alone.
        Before, it was 0.12 (113 times).
    - The CT's augmentation is unchanged in distribution. 1500 samples went through main's recipe and 1500
      through this one. The CT's mean, std, roughness and zero fraction, and the ink label's mean, agree (KS p 0.31
      to 0.96). An independent check of the first commit found it exact. With Compose's own draw set aside, a
      CT-only input came out bit-identical to main's in 300 of 300 seeds; a two-channel input's CT differed only
      where `GaussNoise` drew its noise over fewer slices.
    - One change to the CT on purpose: with `aug_scroll_blank_rectangles_p` above 0 and more than one sample per
      batch, each sample's rectangle now takes that sample's mean. Production leaves it at 0.
  - **The patch.** 16 slices of 64 × 64. The CT is 0.35 plus N(0, 0.05²) noise, with bright Gaussian sheets
    (amplitude 0.3, variance 1) at slices 3, 8 and 13, tilted 0.04 slices per row, clipped to [0, 1]. Its ridge
    channel is `ridge_channel` at `ridge_sigma` 1.0, with a maximum of 1.1e-3.
- **Docstrings and docs**:
  - the module lists all nine augmentations and says which channels the intensity ones change;
  - `apply_augmentations` gives `x`'s channels;
  - `docs/SCROLL_AUGMENTATIONS.md` documents `ct_channels`.
- **Tests** (`tests/test_ridge_channel_augmentation.py`, added to the standard suite, 7 tests, 8 cases):
  - the recipe's stages, and which are CT-only;
  - for a CT-only image, the stages equal one Compose of the recipe bit for bit, with every transform it can hold,
    the labels included;
  - brightness, noise and blur leave the ridge channel and change every CT slice;
  - the spatial transforms still move it with the CT;
  - the scroll intensity drift and Rician noise leave it;
  - the library's default, and a CT-only input through the adapter;
  - blank rectangles' per-sample, per-channel mean, on an input that varies.

  Seven of the eight cases fail with main's code. The eighth, the library's default, is unchanged behaviour.

## Effect on the loop

- **Albumentations cycles** (`config.json`'s `aug_mode`, the incumbent's) augment the ridge channel only
  geometrically from the next cycle. Their CT augmentation is unchanged. Promotion compares val_f1 under the same
  validation protocol, which has no augmentation, so the incumbent stays comparable.
- **batchgeneratorsv2 cycles** are unchanged except their scroll drift and Rician noise, which are now CT-only.
  - `aug_mode` is a loop axis, `features` family, with both values. The committed sprint logs (2026-04-24 to
    07-08) record about 7,600 cycle configs with batchgeneratorsv2, so villa's pipeline is installed where the loop
    runs. Later logs are not committed.
  - That pipeline applies villa's own intensity transforms to every channel of its `image`, the ridge channel
    included. Villa is not installed in this container, so that path is neither changed nor tested here.
  - **The two arms of `aug_mode` now also differ in what they do to the ridge channel.** What the bandit learns
    about that axis includes the difference. The owner's choice:
    - pin `aug_mode`;
    - keep the ridge channel out of villa's intensity transforms, for example by passing it under a key that only
      its spatial transforms move;
    - or accept the confound and note it.
- **Seeds.** Seed-pinned runs no longer reproduce runs from before this change:
  - the stages draw their random numbers in a different order;
  - `GaussNoise` draws over the CT's slices only.

  `history.tsv` records no code version, so rows from before and after are told apart by their time.
- The 2026-10-13 review found that the incumbent "barely uses the channel". A channel that most training samples
  zero, shift or bury in noise may be part of the reason. Nothing here measures that on a trained model. The loop's
  cycles mix this change with each cycle's own tweak, so whether it helps would show cleanly only in a controlled
  pair of cycles: the same config, before and after. That is the owner's call.

## Verified, no change needed

- **`betti_loss_module`** is retired and raises. `use_betti_loss` is false in `config.json` and is not a loop axis,
  so it cannot crash a cycle.
- **`cldice_loss`'s** soft skeleton and clDice follow Shit et al. (2021): erosion, dilation, the iterated skeleton,
  and topology precision and sensitivity. It is off in `config.json` and is not a loop axis.
- **`pixel_auc`** returns 0.5 when one class is present, by design and tested. The curve probe that uses it
  (`periodic_pixel_auc_eval`) reads ink as the main validation does (`out[0]` of a tuple). `eval_every_steps` is 0
  in `config.json`.
- **`frangi_torch`**:
  - runs in float64;
  - takes eigenvalues in closed form;
  - pads with scipy's reflect;
  - is tested against skimage, patch by patch.
- **`inference_constants.depth_band_for`** validates the band and applies it only to the volumes the checkpoint
  recorded.
- **The owner's #141**: the October draft's citations, and a test that pins the epoch-boundary windows. The test
  skips where the sprint logs are absent.
- **The owner's #143** (the neural tracer at its training pitch) touches no file this change does.

## Observations for the owner (not changed)

- **The blurs are now CT-only**, because they are pixel-level transforms, although they keep the ridge channel's
  shape. The independent review measured that the ridge channel of a motion-blurred CT is closer to the blurred
  ridge channel (correlation 1.00) than to the clean one (0.97), so blurring it too would be marginally more
  faithful. For noise, CT-only is the closer
  choice. Either way the effect is small.
- **UA-MT's teacher noise** (std 0.01, `uamt_teacher`) is about ten times the ridge channel's range. The teacher
  sees a noisy ridge channel, the student a clean one. With resenc_unet's single teacher pass the effect is
  bounded, but it is the same mismatch.
- **Each scroll augmentation fires once per batch**, not per sample. At p 0.25 a quarter of the batches are all
  augmented and the rest not at all.
  - Thick slice, sheet compression and Rician noise draw one parameter per batch.
  - Blank rectangles share their positions across the batch.
  - Villa's, in batchgeneratorsv2 mode, run per sample.
- **Sheet compression** computes its displacement from the mean over channels, so the ridge channel takes part, if
  negligibly.
- **Rician noise's variance range**, (0, 0.1) as in villa's transform, is std up to 0.32 on CT scaled to [0, 1].
- **Decohesion pads its ghost and z-blur with zeros.** At alpha 0.45 a constant volume's first two slices come out
  at 0.71 and 0.77, and its last two at 0.95 and 0.89. It is off in production, and it is one of the ablation's
  conditions.
- **`scripts/train_with_new_augs.py`** swaps `train.apply_scroll_specific_3d_augmentations` for the function
  `train.py` already imports, so the swap is now a no-op.

## Verification

- `pytest tests/test_ridge_channel_augmentation.py`: 8 passed. With main's code, 7 fail.
- **Mutation check.** Each of these is killed:
  - pixel stages on every channel, or every stage CT-only;
  - a `OneOf` not looked into;
  - the pixel-level stages run before the spatial ones;
  - the ink mask, or the fiber, left unmoved;
  - the CT slice one short or one over, in `_apply_recipe` or in its caller;
  - the adapter without `ct_channels`, or `_on_ct` ignoring it;
  - Rician noise on every channel;
  - blank rectangles left unfilled, or filled with a mean over the batch, over the channels, or over two axes only.
- The spatial test's correlation threshold, 0.5, sits below its lowest value over seeds 0 to 499 (0.66).
- The existing augmentation tests pass: scroll-specific, the library, disable-augmentation and the training-step
  contracts.
- Ruff clean on the changed files. Mypy clean on them, the new test included.
- The standard suite on the first commit (`ee238650`): 2669 passed. The failures and errors are the same 42 and 2
  as on main, all environmental. The PR gives the final commit's.
- **Independent review** of the first commit found nothing blocking. Its should-fix findings:
  - batchgeneratorsv2 is a live loop axis, so "from the next cycle" overstated (above);
  - the tests did not pin the CT's augmentation or the labels;
  - the blank-rectangles test passed with no blanking at all;
  - the spatial test's threshold held only on its seeds.

  Its nits: the doc's numbers came from two patches, the wrong passing test was named, the CT claim needed the
  blank-rectangle qualifier, and the library doc and the suite list's order. All are addressed above.
