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

- **UA-MT reads a labeled unlabeled volume inside the depth band** (`train.unlabeled_dataset`), as the labeled
  readers do. A label-less volume is still read over its whole depth. Both readers take the read range from one
  helper, `vesuvius_loader.band_read_range`. Without a band, the draws are exactly as before.
- **Which label file each training volume uses is decided in one place** (`train.training_label_path`):
  - it is printed;
  - it is recorded as `training_labels` in `run_result.json` and in the checkpoints;
  - a pseudo-label without `use_confidence_weight` is refused.
- **A training volume without a label file is refused** when its reader is built, with the files looked for.
- **Two statements corrected:** the 2026-10-14 overnight review's observation and the depth-band test's comment
  both said UA-MT already read in the band.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **UA-MT read its unlabeled volume over the whole depth, outside the band the rest of training and validation use.** Since 2026-05-29, every `unlabeled_uris` entry has gone through `VesuviusS3Dataset`, which draws a read's start over the whole volume and takes no band. The overnight review on 2026-10-14 recorded the opposite ("Today `unlabeled_uris` is `[Fr47]`, which is labeled, so it is banded"). The depth-band test's check that banded volumes share a depth relied on it too. In production the labeled reads start at slices 0–7 (the band widened by the margin, `[0, 31)`). UA-MT's started at 0–9, so a fifth of its reads (starts 8 and 9) reached slices 31–32, which training is never scored on and inference never reads. The band exists because windows away from the inked surface carry little signal; the consistency loss was trained on them. The effect is small at 33 slices; on a deeper volume most UA-MT reads would fall outside the band. | `unlabeled_dataset` passes the band when the volume has a label file: the rule the depth test and the overnight review state. `band_read_range` and `_read_start` replace the labeled reader's inline code and serve both readers. Tests: on the production layout, the reads start at 0–7 with labels and 0–9 without; with no band the draws equal the old formula; and through `train.train`, UA-MT's reader receives the band. |
| P3 | **A pseudo-label replaced a training fragment's labels without a trace, and could do so in production.** A `<segment>_pseudo.png` in `pseudo_label_dir` takes precedence over the fragment's own labels. Nothing printed or recorded which file was used. `config.json` has carried `pseudo_label_dir: local_data/pseudo_labels` since a 2026-05-03 cycle promoted it, while it changed nothing. The 2026-05-17 audit removed the axis but left the value. The pseudo-label handoff (`docs/PSEUDO_LABEL_HANDOFF.md`) publishes `<segment>_pseudo.png` files and requires `use_confidence_weight: true`, because their uncertain band (PNG 128) is otherwise an ink target of 0.5. Production has it off. A `PHercParis2Fr47_pseudo.png` copied into that directory would therefore switch every later cycle to pseudo-labels, train the uncertain band as ink 0.5, and leave no record. | `training_label_path` refuses a pseudo-label without `use_confidence_weight`, naming the file and the handoff doc. Every training volume's label file is printed and recorded (`training_labels`). Tests: the fragment's own labels without a pseudo-label; refusal without weighting; the pseudo-label with it. |
| P3 | **A training volume without labels failed late and obscurely.** A `uris` entry with no label file fell back to the unlabeled reader. Its two-item `(patch, zeros)` samples then failed to unpack at the first training step, after the validation catalogue had been built and probed and the model built. | Refused when the reader is built: `no label file for training volume … (looked for inklabels_refined.png, inklabels_filled.png, inklabels.png beside it)`. Tested. |

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
- Branch: 42 failed, 2103 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the 6 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loader: clean.

New tests in `tests/test_training_data_sources.py`, now in `scripts/run_validation_tests.py`:
- a labeled unlabeled volume is read inside the band (starts 0–7 on the production layout);
- a label-less one over its whole depth (starts 0–9);
- without a band the unlabeled draws equal the old formula;
- through `train.train`, UA-MT's reader receives the band, and each training volume's label file is printed;
- a pseudo-label needs confidence weighting, and is used with it;
- a training volume without labels is refused.

`tests/test_noise_probe_contracts.py` stubbed the removed fallback (a training volume without labels read by the
unlabeled reader); it now stubs the labeled reader.

Not verified here: a training cycle on the GPU host.
