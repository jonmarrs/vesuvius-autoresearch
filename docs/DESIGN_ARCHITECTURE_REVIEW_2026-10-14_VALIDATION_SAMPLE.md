# Design and architecture review — what a promotion's two scores were measured on

Date: 2026-10-14. Baseline: `96d7554b` (main after #59). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how the validation sample that decides promotion is defined, drawn and compared:

- `scripts/training/promotion.py`: the protocol string, `validation_indices`, the incumbent reader;
- `build_validation_dataset`, `collect_validation_predictions` and `promotion_decision` in `scripts/training/train.py`;
- the loop's incumbent check (`run_autoresearch_loop.py`);
- the labeled dataset's catalogue and per-patch draw (`core/vesuvius_loader.py`);
- `scripts/reevaluate_best_model.py`, which re-scores the incumbent, and the repeatability probe's sample check.

Earlier reviews fixed the draw itself: a seeded sample independent of batch size (2026-10-12), strict reads and
the depth band (2026-10-13). This one asks whether two scores that share a protocol string were measured on the
same patches and targets.

## What changed

- **Each score records a fingerprint of its validation inputs**, `validation_diag["inputs_sha256"]`
  (`promotion.validation_inputs_fingerprint`). It covers the protocol, the fragment and volume names, the label
  file validation reads and its contents, the mask, and `patches.json`. It is computed from files, without torch.
  `build_validation_dataset` attaches it to the dataset, so training, re-scoring
  (`reevaluate_best_model.py --update-stored`) and the analysis scripts record the same value.
  `validation_label_path` is now the one definition of which label file validation reads.
- **The loop checks the incumbent's fingerprint against `config.json`'s inputs**, when it starts and before every
  cycle (`promotion.check_incumbent`). On a difference it stops before training, with the re-score command in the
  message and in the sprint log, as it already did for a protocol mismatch.
- **`promotion_decision` refuses a candidate whose fingerprint differs from the incumbent's.** It is the second
  line of defence, and it names a run that recorded no fingerprint separately.
- **The repeatability probe** compares trials' fingerprints along with their counts and prevalence.
- **Experiment checkpoints (`checkpoint_out`) record `validation_diag`**, as promoted ones already did.

The current incumbent has no fingerprint. It is compared on its protocol alone, and the loop says so when it
starts. The protection starts with the next promotion or re-score. Nothing in how a score is computed changes.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **Two scores with one protocol string could be measured on different targets or patches.** The protocol string (`seeded-sample-400-v2+z1-27`) names the sample size, seed and depth band. The sample also depends on things the string does not name. One is the label file: validation takes `inklabels_refined.png` over `inklabels_filled.png` over `inklabels.png`. Others are the mask, which decides the catalogue, `patches.json`, which replaces the catalogue, and `val_uri`. Something already in the repository changes the first of these: `scripts/refine_labels_villa.py` in in-place mode writes `inklabels_refined.png` beside every `*/inklabels.png` it finds. Run on `local_data/`, it would switch the validation targets for every later candidate. The incumbent's stored `val_f1` would still be accepted as comparable, so a candidate could be promoted, or held back, by the label change rather than by the model. | The inputs fingerprint, checked by the loop before each cycle and by `promotion_decision` (above). An incumbent without a fingerprint is compared on its protocol alone, and the loop prints that it is. A fingerprint stored with another protocol's diagnostic is refused as inconsistent. Tests: the fingerprint is unchanged by an absolute path, a trailing slash or an unrelated file. It changes with the depth band, a relabel, a refined label file appearing, `patches.json` and the mask. Every score records it, through the label file validation picks. Promotion is refused on a mismatch or a missing candidate fingerprint, and allowed on a match and for an incumbent without one. The loop stops before cycle 2 when a refined label file appears during cycle 1, and refuses to start on a changed mask. A re-score stores the fingerprint a candidate is compared on. The probe fails trials whose fingerprints differ. |

## Review of the change, and what it changed

The first version fingerprinted the scored targets themselves, hashed batch by batch, together with the read
geometry. A code review before the PR found:

| Finding | Outcome |
| --- | --- |
| A mismatch was found only after a full training budget, and the loop's startup check did not see it, so every cycle of a shift would train and then be refused. | Redesigned: the fingerprint is of the input files, cheap and torch-free, so the loop checks it before every cycle and stops. |
| An incumbent without a fingerprint, or with an inconsistent stored diagnostic, was silently accepted. | The legacy case is kept, transitionally, and the loop now says so at startup; requiring a fingerprint would stop the running loop until a GPU re-score. The inconsistent case now refuses. |
| The patch size and depth, which are model settings, were in the fingerprint, so a candidate with other values could never match even after a re-score. | Removed: the fingerprint covers data inputs only. The loop pins both, as noted in the docstring. |
| Experiment checkpoints recorded no `validation_diag`. | Fixed. |
| `json.dumps` of unconverted dataset attributes could raise after training. | Gone with the redesign: the record holds only strings and hashes. |
| `sample=None` was reported as a label change. | A missing candidate fingerprint now has its own reason. |
| The mocks had no geometry attributes, and there was no re-score round-trip test. | The tests now use real label, mask and `patches.json` files, and a round-trip test was added. |
| The noise probe compared trials by counts and prevalence only. | It compares fingerprints too; tested, and the test fails on the old probe. |
| Double target conversion per batch. | Gone with the redesign. |
| The `CHECKPOINT_ANALYSIS.md` wording ("Its model weights") became ambiguous. | Rewritten. |

## Observations for the owner (not changed)

- **The validation metrics pool pixels outside the fragment mask.** `pooled_segmentation_metrics` passes an
  all-true mask. The catalogue keeps a grid position when at least 5% of it is inside the mask
  (`min_mask_ratio=0.05`), and validation jitters each position by up to half a patch. Pixels off the papyrus are
  labeled background, so they count toward the prevalence and the all-ink F1, and toward AUC and AP as easy
  negatives. The detector's own metric uses the fragment mask. Finding 88 scored both models the same way, so its
  comparison stands. How many sampled pixels lie outside the mask needs the fragment; if it is material, a masked
  metric would be a new protocol.
- **Not fingerprinted:**
  - the CT, since a volume rebuilt in place under the same path keeps the fingerprint;
  - the catalogue code and its thresholds, which are visible in git;
  - the model's patch size and depth, which the loop pins.
- **The incumbent has no fingerprint until it is replaced or re-scored.** Re-running
  `reevaluate_best_model.py --update-stored --unwarped` on the GPU host would add one now. Nothing requires it.

## Reviewed and sound

- **`validation_indices`** is a seeded permutation of the catalogue, sorted, of at most 400 entries. It is the
  same for every candidate while the catalogue's size is unchanged.
- **Per-patch draws** seed a `RandomState(idx + seed)` per catalogue entry, so jitter and depth do not depend on
  batch size or read order.
- **`collect_validation_predictions`** counts ink-free patches one by one and marks the sample incomplete on any
  failed read. `probe_validation_read` fails a cycle before training when the first sampled patch cannot be read.
- **The coordinate cache** is keyed by the volume URI, patch size, mask and label modification times, and the
  catalogue thresholds, so a changed mask or label file rebuilds it.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #59's head, whose tree is `96d7554b`'s.

- Baseline: 42 failed, 2055 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2063 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the 8 extra passes are the new tests.
- Ruff (check and format) on the changed files and mypy on `promotion.py` and the loop: clean.

New tests:

- `tests/test_autoresearch_measurement.py`:
  - the fingerprint's inputs;
  - every score records it;
  - promotion refuses other inputs;
  - the loop stops before a cycle, refuses to start, and notes a legacy incumbent.
- `tests/test_checkpoint_tool_contracts.py`: a re-score stores the fingerprint a candidate is compared on.
- `tests/test_noise_probe_contracts.py`: changed inputs invalidate a repeatability estimate.

Not verified here: the fragments (the fingerprint of the real inputs) and the GPU host.
