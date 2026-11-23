# Design and architecture review — the owner's #500, required training images

Date: 2026-11-23. Baseline: `c1c6056` (main after #500, which followed round #192's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 01:12 UTC firing on 2026-11-23. Main had moved once since round #192's merge, with the owner's
#500.

It takes **#500**, which makes supervised training open the label and mask files it selected. Before #500, a
selected file that disappeared before loading was silently left out, and the trainer passed `mask.png` only when the
path existed. Now:
- `VesuviusLabeledDataset` takes `require_input_images`, refuses an empty label path, and opens each selected image
  even if it has gone;
- the trainer passes `mask.png` only when no `patches.json` places the patches;
- it passes the mask when the path is a link at all, so a dangling link is reported rather than skipped.

The guide states all three.

It also reads #419, which stops the test harness probing for CUDA when the shell has masked it.

## What changed

### #500's checks are now tested without patch discovery (`tests/test_training_data_sources.py`)

#500's own tests of these checks build datasets by patch discovery, which needs villa's patch finder. Here none of
them runs, and none of six mutants of the checks was killed. Three new test functions, five cases, kill all six.
They give the volumes explicit patch catalogs:
- **A supervised dataset needs a label path.**
- **A selected label or mask that is gone is an error only when images are required**, and the error names the
  file. Without the requirement it is left out, as before.
- **The trainer opens a dangling `mask.png` only when the mask would place the patches.**
  - With a catalog beside the volume, the mask is not opened, and the run reaches the loader.
  - Without one, the broken link is reported by name before any patch is discovered.

No code changed. No defect was found.

## Verified, no change needed

- **Skipping the mask beside a catalog changes nothing the model sees.** The dataset uses the mask only to place
  patches: its shape check already skips a mask when a catalog is given, and `__getitem__` never reads it.
- **Validation is unchanged.** It already reads both images through the digest check that #481 added.
- **#419's early return is the whole change.** When the shell's `CUDA_VISIBLE_DEVICES` is empty,
  `gpu_available_ambiently` returns False without starting the probe. #419's tests cover:
  - the masked case under three process settings;
  - the unmasked probe's environment;
  - failed probes;
  - the cache.

## Observations for the owner (not changed)

- **The required-image error differs by kind.** A missing label or mask surfaces as Pillow's `FileNotFoundError`
  naming the path, while an empty label path is a `ValueError`. Both stop training.
- **#500's own trainer-level tests need villa here.** The new tests reach the same checks with catalogs and can run
  where villa is absent.

## Verification

- **The touched module.** `test_training_data_sources.py` gives 38 passed and 12 failed, against 33 and 12 on
  `c1c6056`. The twelve need villa's patch finder: #487's three trainer-level cases and #500's nine.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,106 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** 278 failing ids. These are round #192's 269 and #500's nine new cases:
  - `test_selected_training_images_cannot_disappear_before_loading`, six cases;
  - `test_training_checks_the_mask_only_when_it_guides_discovery`, three cases.

  The nine fail on `c1c6056` as well.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,782 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `c1c6056`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`train.py` is in `scripts/training/`**, where only tests may be added. Its #500 lines were mutated in a worktree.
- **Still not reviewed from the owner's merges since round #182:** #398, #416, #447, #448, #450, #453, #456, #458,
  #461, #463, #465, #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All six were run again with the new tests, and all six are killed.
