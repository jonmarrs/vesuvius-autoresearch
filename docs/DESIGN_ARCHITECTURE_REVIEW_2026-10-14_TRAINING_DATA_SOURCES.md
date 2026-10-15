# Design and architecture review — which files and slices a training run reads

Date: 2026-10-14. Baseline: `f3794ea7` (main after #63). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `train.train` turns `config.json`'s data fields into readers:
- `uris`, `pseudo_label_dir` and `use_confidence_weight` for the supervised loss;
- `unlabeled_uris` and `depth_band` for UA-MT's consistency loss;
- `ExperimentConfig`'s guards on them.

The production config trains `resenc_unet` on Fr47 and validates on Fr143.
- **Depth:** `num_layers` 16, so reads are 24 slices with the 4-slice margin; `depth_band` is `[1, 27)` on 33-slice volumes.
- **UA-MT:** on, with `unlabeled_uris: [Fr47]`.
- **Pseudo-labels:** `pseudo_label_dir: local_data/pseudo_labels`, with `use_confidence_weight: false`.

## What changed

- **UA-MT reads a training volume inside the depth band** (`train.unlabeled_dataset`), as the labeled readers do.
  An unlabeled volume counts when it is also a training volume, matched by path as `depth_band_for` matches a
  checkpoint's volumes for inference. Any other unlabeled volume is still read over its whole depth. Both readers
  take the read range from one helper, `vesuvius_loader.band_read_range`. Without a band the draws are exactly as
  before.
- **Each training volume's label file is resolved first** (`train.resolve_training_labels`, through
  `training_label_path`), in `train()` and in the loop's `--smoke` preflight:
  - it is printed;
  - it is recorded as `training_labels` in `run_result.json` and in the checkpoints;
  - a pseudo-label from `pseudo_label_dir` without `use_confidence_weight` is refused;
  - a training volume without a label file is refused, naming the files looked for.

  These are file checks only, so a refusal comes in seconds, before the validation catalogue or the model is
  built.
- **Corrected statements:** the 2026-10-14 overnight review's observation and the depth-band test, both of which
  took UA-MT to read in the band. The `depth_band_for` docstring, the pseudo-label handoff doc and the loop's
  comment on the removed `pseudo_label_dir` axis now describe the new behavior.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **UA-MT read the training volume over its whole depth, outside the band the rest of training and validation use.** Every `unlabeled_uris` entry has gone through `VesuviusS3Dataset` since UA-MT was added (2026-05-10). That reader draws a read's start over the whole volume and takes no band. It did not matter until `depth_band` entered `config.json` on 2026-10-13. The overnight review on 2026-10-14 recorded the opposite ("Today `unlabeled_uris` is `[Fr47]`, which is labeled, so it is banded"), and the depth-band test's check that banded volumes share a depth relied on it. In production the labeled reads start at slices 0–7 (the band widened by the margin, `[0, 31)`); UA-MT's started at 0–9. The model sees a 16-slice window at a random offset (0–7) inside each read, so about 4% of UA-MT's windows (3 of 80 start and offset pairs) started past any labeled window (slice 14). A fifth of its reads (starts 8 and 9) put slices 31–32 into the ridge channel, which is computed and min-max normalized over the whole read. The effect is small at 33 slices; on a deeper volume most UA-MT reads would fall outside the band. | `unlabeled_dataset` takes the band from `depth_band_for`, so it applies when the unlabeled volume is one of the training volumes. `band_read_range` and `_read_start` replace the labeled reader's inline code and serve both readers. Tests: on the production layout, the training volume's reads start at 0–7 under two spellings of its path; another volume (label-less, labeled, or a labeled 21-slice volume the band would not fit) is read over its whole depth; with no band the draws equal the old formula; and through `train.train`, UA-MT's reader receives the band. |
| P3 | **A pseudo-label replaced a training fragment's labels without a trace, and could do so in production.** A `<segment>_pseudo.png` in `pseudo_label_dir` takes precedence over the fragment's own labels, and nothing printed or recorded which file was used. `config.json` has carried `pseudo_label_dir: local_data/pseudo_labels` since a 2026-05-03 cycle promoted it while it changed nothing; the 2026-05-17 audit removed the axis but left the value. The pseudo-label handoff (`docs/PSEUDO_LABEL_HANDOFF.md`) publishes `<segment>_pseudo.png` files and requires `use_confidence_weight: true`, because their uncertain band (PNG 128, read as 128/255) is otherwise an ink target. Production has it off. A `PHercParis2Fr47_pseudo.png` copied into that directory would therefore switch every later cycle to pseudo-labels, train the uncertain band as ink 128/255, and leave no record. | `training_label_path` refuses a pseudo-label from `pseudo_label_dir` without `use_confidence_weight`, naming the file and the handoff doc. Every training volume's label file is printed and recorded (`training_labels`). Tests: the fragment's own labels without a pseudo-label; the refusal; the pseudo-label with weighting; the refusal through `train.train`, before anything is built. |
| P3 | **A training volume without labels failed late and obscurely.** A `uris` entry with no label file fell back to the unlabeled reader. Its two-item `(patch, zeros)` samples then failed to unpack at the first training step, after the validation catalogue had been built and probed and the model built. The loop's preflight builds only the model, so it passed. | Refused at the start of `train()` and of the `--smoke` preflight: `no label file for training volume … (looked for inklabels_refined.png, inklabels_filled.png, inklabels.png beside it)`. Tested directly and through `train.train`, with the validation catalogue, the model and both readers stubbed to fail if built. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| "Has a label file" was the wrong test for banding an unlabeled volume. A label says nothing about how a volume numbers its slices. Inference matches a checkpoint's volumes by path. A labeled 21-slice unlabeled volume would have crashed training at the unlabeled reader, and a labeled 65-slice one would have been banded on the wrong layers. | Fixed: the band comes from `depth_band_for`, so it applies to the training volumes only. Tested with a labeled 21-slice volume. The depth test's check of labeled `unlabeled_uris` was removed with the rule it encoded. |
| The doc dated the routing to 2026-05-29, the date of a reformat. | Corrected: UA-MT was added on 2026-05-10, and the band mismatch dates from 2026-10-13. |
| The doc said a fifth of UA-MT's reads trained on slices 31–32. | Corrected: about 4% of windows, and a fifth of reads' ridge context. |
| No test covered the refusal at the reader, and none covered `training_labels` reaching the payloads. | The refusal moved to the start of `train()` and is tested through it. The payloads are not covered by a test; no test runs `train()` to its end. |
| The refusal still came after validation and the model were built, and the preflight did not see it. | Fixed: labels are resolved first in `train()` and in `--smoke`. |
| The loop's comment on re-adding the `pseudo_label_dir` axis, the handoff doc and `depth_band_for`'s docstring were stale. | Updated. |
| The refusal checks only `pseudo_label_dir`, and refuses an all-binary pseudo-label too. | Recorded below. |
| `training_labels` records paths, not contents. | Recorded below. |
| The depth test hard-coded the label file names. | The block that did so was removed. |

## Observations for the owner (not changed)

- **UA-MT has no unlabeled data of its own in production.**
  - **How it happened:** the default `unlabeled_uris` was `[Fr143, Fr47]`. `ExperimentConfig` drops `val_uri`
    from it so the consistency loss cannot see validation patches. That leaves Fr47, the supervised training
    fragment.
  - **What it adds:** the consistency loss covers what the supervised loss already sees, except Fr47's area
    outside its mask and catalogue. The unlabeled reader samples a grid over the whole volume and ignores the mask.
  - **The 2026-07-11 promotion of `use_uamt: true`** (val_f1 0.468) therefore measured consistency regularization
    on the training fragment, not semi-supervised learning on new data.
  - **To change it:** adding a fragment that is neither trained nor validated on is a data choice.
- **`pseudo_label_dir` is still set in `config.json`.** With the refusal it can no longer switch labels silently.
  Setting it to `null` would remove the dependency on the directory's contents altogether.
- **The refusal covers pseudo-labels in `pseudo_label_dir` only.** The 2026-06-13 self-training plan installs
  0/128/255 pseudo-labels as a fragment's own `inklabels.png`, which is read like any label file. The refusal
  also applies to a pseudo-label with no uncertain band; checking the pixels (any 128) would distinguish them.
- **`training_labels` records paths, not contents.** A label file regenerated in place is recorded identically.
  Validation hashes its inputs; recording a SHA-256 next to each training path would do the same here.
- **The unlabeled reader's draws are fixed per position.** Its seed is `None`, so each grid position always gets
  the same depth, as the labeled reader's index-deterministic jitter does (left unchanged on 2026-10-12).

## Reviewed and sound

- **Validation never reads pseudo-labels.** `build_validation_dataset` takes its label file from
  `validation_input_paths`, which the fingerprint hashes, so `pseudo_label_dir` cannot reach the score.
- **The val/unlabeled leak guard** removes `val_uri` from `unlabeled_uris`. It compares strings, which is enough
  for the configs the loop writes (it never changes the data fields).
- **The labeled training reader** gets the band and margin (2026-10-13), and a pseudo-label is read through the
  same reader as the fragment's own labels, with its mask and catalogue.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #63's head, whose tree is `f3794ea7`'s.

- Baseline: 42 failed, 2097 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, after the PR review's fixes: 42 failed, 2108 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 11 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loader: clean.

New tests in `tests/test_training_data_sources.py`, now in `scripts/run_validation_tests.py`:
- the training volume, read by UA-MT, is read inside the band (starts 0–7 on the production layout), under two
  spellings of its path;
- any other unlabeled volume (label-less, labeled, or a labeled 21-slice one) is read over its whole depth;
- without a band the unlabeled draws equal the old formula;
- through `train.train`, UA-MT's reader receives the band, and each training volume's label file is printed;
- a pseudo-label needs confidence weighting, and is used with it;
- a training volume without labels is refused;
- through `train.train`, both refusals come before the validation catalogue, the model or a reader is built;
- `resolve_training_labels` returns and prints each volume's file.

Two tests stubbed what moved:
- `tests/test_noise_probe_contracts.py` stubbed the removed fallback (a training volume without labels read by
  the unlabeled reader); it now stubs the labeled reader and the label check.
- `tests/test_training_step_contracts.py`'s probe-order test runs on the default config, whose label files are
  not in this checkout; it stubs the label check, which now runs first.

Not verified here: a training cycle on the GPU host; that `training_labels` reaches `run_result.json` and the
checkpoints (no test runs `train()` to its end).
