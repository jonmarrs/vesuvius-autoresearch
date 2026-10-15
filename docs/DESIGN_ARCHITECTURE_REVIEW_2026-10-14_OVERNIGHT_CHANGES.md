# Design and architecture review — the 2026-10-13 overnight changes

Date: 2026-10-14. Baseline: `ba9bdfec` (main after #53–#58). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: everything merged since the previous review round (`2351651d..ba9bdfec`, 23 commits):

- #53: the depth band in the zarr's slice numbers, `[1, 27)`;
- #54: lasagna off, and `reevaluate_best_model.py --unwarped`;
- #55, #58: worktree development (`scripts/dev_worktree.sh`, `scripts/sibling_checkouts.py`, the test `PYTHONPATH`);
- #57: the repeatability probe (`scripts/f1_noise_probe.py`, `scripts/training/run_noise_probe.py`, strict warm starts);
- #56: finding 88 (`scripts/detector_on_loop_sample.py`, `scripts/loop_candidate_spread.py`).

The production paths come first. The probe and the finding 88 scripts were each reviewed in their own PRs; here
they were read for isolation from the loop and agreement with its scoring.

## What changed

- **The measurement tools apply a checkpoint's depth band only to its own volumes.** `predict.py` (without
  `--z`), `measure_ink_auc.py` and the active-learning sampler use the band on the labeled volumes the checkpoint
  recorded (`uri`/`uris`, `val_uri`). Any other volume gets the whole depth, as before bands existed, and the
  command says so. The AUC line and the sampler's queue name the band used. The rule lives in `depth_band_for`
  (`core/inference_constants.py`). Pseudo-labels keep the band everywhere: they are trained on again, and training
  bands every labeled fragment.
- **A guard that the banded volumes number their slices alike** (equal depth across `uris`, `val_uri` and
  labeled `unlabeled_uris`), in the depth-band test, now part of `scripts/run_validation_tests.py`.
- **Stale documentation corrected**: the loop's benchmark comment and its test, and `docs/CHECKPOINT_ANALYSIS.md`
  (sampler score, buffered depth, shallow volumes, the banded protocol name, `--unwarped`).

Nothing here changes training, validation, the protocol string or the incumbent's score. The loop's benchmark
reads its validation fragment, one of the checkpoint's own volumes, so it is unchanged.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The analysis tools applied a checkpoint's depth band to any volume.** A band names slices of the volumes it was set for. Finding 87 found that the training fragments' zarrs start at surface-volume layer 16, so `[1, 27)` there is layers 17–42. The AUC, pseudo-label and sampler commands, and `predict.py` without `--z`, passed `checkpoint["config"]["depth_band"]` to whatever volume they were given. On a volume built from layer 0 (a 65-layer surface volume), `[1, 27)` reads layers 0–30, beside the surface rather than around it, and nothing says so. On a shallower volume (the repository references 21-slice ones), the dataset refuses the band and the measurement fails. `predict.py` noted the limit and offered `--z`; the other three had no way around it. None of this has happened yet: the incumbent records no band, and the first banded checkpoint will be the loop's next promotion. | `depth_band_for(saved_config, volume_uri)` returns the band only when the volume is one of the checkpoint's recorded labeled volumes. Paths are compared after resolving them; recorded relative paths are resolved against the working directory or the checkout. A zarr group matches its level 0, and `file://` matches its path. Anything else gets the whole depth, with a line on stderr. The AUC line and the sampler's queue record the band used. Pseudo-labels keep the band, so a fragment is labeled from the slices training will read; the depth guard below covers that case. Tests cover recorded and unrecorded volumes for each command; on the old code, the measurement cases for unrecorded volumes fail. They also cover path spellings, URLs, a string `uris`, an empty band and a malformed one. |
| P3 | **Nothing checked that one band suits every configured volume.** `test_config_depth_band_fits_fragments.py` checked only that the band lies inside each volume. A fragment built from another first layer, with the same depth or more, would pass and train on other layers. The test was also missing from the validation list, so it never ran on the host that has the data. | It now also requires the banded volumes (`uris`, `val_uri`, and `unlabeled_uris` that have labels) to share one depth, the check available without layer metadata. It fails on a 33/65 pair and ignores a label-less 65-slice unlabeled volume (both checked on synthetic zarrs). It is now in `scripts/run_validation_tests.py`. Without the data it skips, as before. |
| P3 | **Stale text.** The loop's benchmark comment and its test docstring still reasoned in a 65-slice frame ("z=10 … below the 17-42 band"), which finding 87 showed does not apply to these fragments. `docs/CHECKPOINT_ANALYSIS.md` still described the sampler's 0.7/0.3 entropy-and-QC score (entropy only since 2026-10-13). It also said the sampler reads the exact checkpoint depth (ridge models read the buffered context) and that volumes too shallow for the context fail (the centre of what they hold is used). Its re-evaluation section gave the protocol as `seeded-sample-400-v2` (now `+z1-27`) and did not mention `--unwarped`. | Rewritten. |

## Review of the PR, and what it changed

The first version was reviewed (code-review skill) before merging. Its findings, and what was done:

| Finding | Outcome |
| --- | --- |
| Recorded relative paths resolved only against the working directory, so a tool run from `scripts/` dropped the band on the checkpoint's own validation fragment. | Fixed: they also resolve against the checkout (where `config.json`'s paths point). Tested. |
| Every `unlabeled_uris` entry counted as banded, but training reads a label-less volume over its whole depth. | Fixed: only `uri`/`uris` and `val_uri` count. |
| `X/surface_volume.zarr` and `X/surface_volume.zarr/0` (one array to `FastVesuviusVolume`), and a `file://` URL and its path, did not match. | Fixed and tested. |
| Pseudo-labels for a new fragment got the whole depth, though training will read that fragment with the band. | Fixed: the pseudo-label command keeps the band everywhere, as before this PR; the depth guard covers the fragments it is applied to. |
| A malformed or empty recorded band crashed `predict.py`, where an empty one used to mean no band. | Fixed: an empty band is no band; a malformed one raises a named `ValueError`. |
| A `uris` recorded as one string was matched character by character. | Fixed and tested. |
| The depth guard ignored labeled `unlabeled_uris`, which UA-MT reads banded. | Fixed. |
| `CHECKPOINT_ANALYSIS.md` said shallow volumes give the centre of what they hold; the pseudo-label command requires the whole context. | Corrected. |
| The benchmark's band depends on `BENCHMARK_URI` matching `val_uri`. | Comment now says so. A changed `val_uri` drops the band with a logged line, not silently. |
| The AUC output did not say which band it used. | Fixed. |
| The docs left out the deprecated `uri` field. | Fixed. |
| Path identity stands in for "numbered alike". | Recorded under observations; the durable fix needs layer metadata. |
| The dataset tools' fallback (random depth) differs from `predict.py`'s (centred). | Unchanged; recorded under observations. It predates bands. |
| The helper sits in the import-light constants module and prints. | Kept: it imports only the standard library, and `predict.py` and the tools share it. Every caller wants the note. |
| `_volume_uri` computed twice in the AUC path. | Kept: a pure path check, and `measure_fragment` keeps its band parameter. |

## Observations for the owner (not changed)

- **Validation never shows slices 1–3 of the band.** A read is 24 slices, drawn from the band widened by
  `DEPTH_MARGIN`, clamped to the volume: for `[1, 27)` on 33 slices, from `[0, 31)`. Validation crops each read's
  centre, so its windows start at 4–11 and cover slices 4–26 (layers 20–42). Training's windows (offsets 0–7 into
  the read) start at 0–14 and cover slices 0–29. Any band start from 0 to 4 gives the same reads, so `+z1-27` and `+z4-27` would name one sample. Validating windows
  that start at 1–3 needs an off-centre crop at the volume's end, as inference's `depth_window` does. That is a
  protocol change and a re-score. Finding 87's table already shows the effect: no validation window contains
  Fr143's slice 3.
- **UA-MT applies the band only to unlabeled volumes that have labels.** Corrected on 2026-10-14
  (`DESIGN_ARCHITECTURE_REVIEW_2026-10-14_TRAINING_DATA_SOURCES.md`): when this was written, every unlabeled
  volume went through `VesuviusS3Dataset` over its whole depth, labeled or not, so `[Fr47]` was not banded. Now
  UA-MT bands an unlabeled volume when it is also a training volume, matched by path as `depth_band_for` matches,
  which covers `[Fr47]`, and reads any other over its whole depth. The depth test's check of labeled
  `unlabeled_uris` (the "Fixed" row above) was removed with it.
- **The band belongs to the volumes, not the model.** A durable form would record each zarr's first surface layer
  (for example in its attributes) and keep the band in layer numbers. The scoping above is the conservative
  interim: correct where the band was defined, unchanged elsewhere. Path identity stands in for "numbered alike",
  so a copy of a training fragment at another path is treated as foreign (whole depth, with a note), and a
  recorded path whose zarr was rebuilt differently is trusted.
- **On an unrecorded volume, the dataset tools draw depths at random over the whole volume while `predict.py`
  centres its window in the volume.** That is how both behaved before bands, and how they treat the unbanded
  incumbent today. A centred fallback for the AUC and sampler would be a separate change to how they measure.

## Reviewed and sound

- **`--unwarped`** scores without a recorded warp that never ran. It records `use_lasagna: false` only with
  `--update-stored`, and keeps the old value in `reevaluation.overridden_input_settings`. Weights are untouched.
- **Strict warm starts** (`load_required_starting_checkpoint`) share `WARM_START_FIELDS` with the loop's lenient
  path, require every field to be recorded, and load with `strict=True`. Only the probe's runner opts in.
- **Probe isolation.** Each trial sets `checkpoint_out`, so `train.py` writes its candidate there and never writes
  `best_model.pt`, `history.tsv`, `results.tsv` or `prize_readiness.tsv`. The trial runs in its own directory with
  absolute data paths and private caches. The probe holds `autoresearch.lock`, so the watchdog will not start the
  loop beside it, and `stop.sh` can stop it (`loop_control` accepts the probe as the lock's owner).
- **Finding 88's scoring** builds the incumbent's sample through the loop's own `build_validation_dataset` and
  `collect_validation_predictions`, and checks that its patch coordinates reproduce the loop's targets before the
  detector is scored. *Corrected 2026-10-14:* it checked the targets, not the coordinates. The detector was read at
  the pre-jitter `valid_coords`, a median 16 px from the targets. `9acb865a` reads it at `patch_origin` and checks
  the labels there against every target (`check_origins`); finding 88's readings stand (its Correction section).
- **Worktrees.** `main_checkout` follows a linked worktree's `commondir` and returns a submodule's own directory
  unchanged. The test `PYTHONPATH` puts this checkout's `src/` first for pytest and its subprocesses.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is a
worktree of `ba9bdfec` with `PYTHONPATH` set to its own `src/`, asserted before the run. Both trees run the full
`scripts/run_validation_tests.py` list.

- Baseline: 42 failed, 2047 passed, 12 skipped, 1 xfailed, 2 errors. These are the same environmental failures
  as the previous rounds (no scroll data, no CUDA, no villa data files).
- Branch, after the review fixes: 42 failed, 2055 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline. The 8 extra passes are the new tests. The 3 extra skips are the
  depth-band test file, newly in the list, which skips without `local_data/`. With `main`'s versions of the three
  measurement tools, 4 of the new tests fail: the AUC and `predict.py` cases on an unrecorded volume, and both
  sampler cases, because the queue did not record the band.
- Ruff (check and format) on the changed files: clean.

New and changed tests:

- `tests/test_checkpoint_tool_contracts.py`: the AUC and sampler commands apply a band only on the checkpoint's own
  volumes, and pseudo-labels keep it everywhere. The sampler's queue records the band.
- `tests/test_volume_inference_contracts.py`:
  - `predict.py` without `--z` uses the band on a recorded volume and the volume's centre on another;
  - a recorded volume shallower than the band falls back to the volume's centre;
  - `depth_band_for`: path spellings, a zarr group against its level 0, `file://`, URLs, a string `uris`,
    `unlabeled_uris` excluded, empty and malformed bands, and resolution against the checkout from `scripts/`.
- `tests/test_config_depth_band_fits_fragments.py`: the banded volumes (labeled `unlabeled_uris` included) share
  one depth.

Not verified here: the fragments themselves (the depth tests skip without `local_data/`), and the GPU host.
