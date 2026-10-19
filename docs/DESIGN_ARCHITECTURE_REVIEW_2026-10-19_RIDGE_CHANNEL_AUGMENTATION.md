# Design and architecture review — what the augmentations do to the ridge channel

Date: 2026-10-19. Baseline: `3da545bb` (main after #141).
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
    transform on it. Measured on a two-channel patch, each transform at p=1:
    - `RandomBrightnessContrast` (production p 0.75) shifts by up to ±0.2, and albumentations 1.3.1 clips a float
      image to [0, 1]. It zeroed the ridge channel in 49% of samples and lifted it above its own maximum in 50%.
    - `GaussNoise` (in the `OneOf`, p 0.4, a third of the time) has std 0.1 to 0.17. The noisy ridge channel's
      correlation with the original is 0.00.
    - The two blurs keep its shape (correlation 1.00).

    So in about four of five training samples the ridge channel was zeroed, far past its range, or noise. At
    inference it is the filter's response to the scan.
  - The scroll intensity drift (production p 0.25) adds up to ±0.08, 29 times the ridge channel's maximum on that
    patch. The ridge channel of the drifted CT itself barely moves (correlation 0.96 to 1.00): the filter normalizes
    the block it is given, so gain and offset cancel.
  - Two that production leaves at p 0 did the same:
    - Rician noise, about 100 times the ridge channel's maximum;
    - blank rectangles, which filled each region with one mean over the batch and both channels. That put a share
      of the CT's values, up to 87 times the ridge maximum, into the ridge channel.
  - **Now:**
    - `_get_villa_aug` returns each transform as a stage of its own, in the same order, each with its own p.
      `apply_augmentations` runs the pixel-level stages (an `ImageOnlyTransform`, or a `OneOf` of them) on the CT's
      slices only. The spatial stages move both channels and the labels, as before.
    - `scroll_augmentations.apply_scroll_augmentations` takes `ct_channels`. Intensity drift and Rician noise apply
      to that many leading channels; the loop's adapter passes 1. The augmentations that move voxels, mix them along
      z or blank a region act on every channel, each in its own values. With the default, `None`, the library
      augments every channel, as before, for other callers.
    - Blank rectangles fill each sample's and channel's region with its own mean.
  - **Measured after.**
    - The ridge channel: 200 samples through the production recipe (the scroll augmentations off).
      - None moved its median past its range; 70 did before.
      - Its mean change is 0.2 times its maximum at the 90th percentile, from geometry alone. Before, it was 110.
    - The CT's augmentation is unchanged in distribution. 1500 samples went through main's recipe and 1500
      through this one. The CT's mean, std, roughness and zero fraction, and the ink label's mean, agree (KS p 0.31
      to 0.96).
- **Docstrings**:
  - the module lists all nine augmentations and says which channels the intensity ones change;
  - `apply_augmentations` gives `x`'s channels.
- **Tests** (`tests/test_ridge_channel_augmentation.py`, added to the standard suite, 6 tests, 7 cases):
  - the recipe's stages, and which are CT-only;
  - brightness, noise and blur leave the ridge channel;
  - the spatial transforms still move it with the CT;
  - the scroll intensity drift and Rician noise leave it;
  - the library's default, and a CT-only input through the adapter;
  - blank rectangles' per-sample, per-channel mean.

  Six of the seven cases fail with main's code. The seventh, that geometry still moves the ridge channel, guards
  the fix.

## Effect on the loop

From the next cycle, the ridge channel is augmented only geometrically. The CT's augmentation is unchanged.
Promotion compares val_f1 under the same validation protocol, which has no augmentation, so the incumbent stays
comparable.

The 2026-10-13 review found that the incumbent "barely uses the channel". A channel that most training samples
zero, shift or bury in noise may be part of the reason. Nothing here measures that on a trained model; the loop's
cycles will show whether a model fine-tuned with a clean ridge channel scores differently.

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

## Observations for the owner (not changed)

- **batchgeneratorsv2 mode** (not production): villa's pipeline applies its own intensity transforms to every
  channel of `image`, the ridge channel included. Villa is not installed in this container, so that path is not
  changed or tested here. One way would be to pass the ridge channel under a key that only its spatial transforms
  move.
- **UA-MT's teacher noise** (std 0.01, `uamt_teacher`) is about ten times the ridge channel's range. The teacher
  sees a noisy ridge channel, the student a clean one. With resenc_unet's single teacher pass the effect is
  bounded, but it is the same mismatch.
- **Each scroll augmentation fires once per batch**, not per sample. At p 0.25 a quarter of the batches are all
  augmented and the rest not at all.
  - Thick slice, sheet compression and Rician noise draw one parameter per batch.
  - Blank rectangles share their positions across the batch.
  - Villa's, in batchgeneratorsv2 mode, run per sample.
- **Rician noise's variance range**, (0, 0.1) as in villa's transform, is std up to 0.32 on CT scaled to [0, 1].
- **Decohesion pads its ghost and z-blur with zeros.** At alpha 0.45 a constant volume's first two slices come out
  at 0.71 and 0.77, and its last two at 0.95 and 0.89. It is off in production, and it is one of the ablation's
  conditions.
- **`scripts/train_with_new_augs.py`** swaps `train.apply_scroll_specific_3d_augmentations` for the function
  `train.py` already imports, so the swap is now a no-op.

## Verification

- `pytest tests/test_ridge_channel_augmentation.py`: 7 passed. With main's code, 6 fail.
- **Mutation check.** Each of these is killed:
  - pixel stages on every channel;
  - every stage CT-only;
  - a `OneOf` not looked into;
  - the CT slice off by one;
  - the adapter without `ct_channels`;
  - `_on_ct` ignoring it;
  - Rician noise on every channel;
  - blank rectangles' mean over channels, or over the batch.
- The existing augmentation tests pass: scroll-specific, the library, disable-augmentation and the training-step
  contracts.
- Ruff clean on the changed files. Mypy clean on them, the new test included.
- The standard suite: see the PR.
