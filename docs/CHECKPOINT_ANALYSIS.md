# Checkpoint analysis and labeling

These tools consume autoresearch `model_state_dict` checkpoints. Fragment
detector Lightning checkpoints use the [detector workflow](DETECTOR_WORKFLOW.md).
Regional map exports use the [CT inference workflow](VOLUME_INFERENCE.md).

Analysis requires a recorded configuration containing `architecture`,
`patch_size`, `num_layers`, and `base_feat`, plus all model weights. Channel/head
settings and ridge sigma come from that checkpoint. Incomplete or incompatible
weights fail before dataset reads; partial warm starts remain a training concern.
Files without recorded input settings require verification of their training
configuration before use, rather than guesses from a current experiment.

## Masked patch AUC

```bash
uv run python scripts/measure_ink_auc.py \
  --checkpoint best_model.pt --fragments /path/to/fragment --n 30 --device cpu
```

Each fragment needs `inklabels.png`, `mask.png`, and CT in
`surface_volume.zarr` or its bare level-0 directory. Labels must be binary and
aligned with the volume; confidence-filtered pseudo-labels are not ground truth.
Only pixels inside the fragment mask enter AUC. Each accepted patch needs both
classes. `--n` is positive and exact: too few usable patches, missing inputs, or
invalid outputs fail the measurement. Other requested fragments are attempted;
any failed fragment makes the command exit nonzero.

This is a mean/median of patch AUCs from the label-conditioned catalog, not a
pooled whole-fragment measurement or an attestation of held-out independence.
The command no longer depends on a working-directory `config.json`; optional
`--cache-dir` controls coordinate caching.

## Confidence-filtered pseudo-labels

```bash
uv run python scripts/generate_pseudo_labels.py \
  --checkpoint best_model.pt --fragment /path/to/fragment \
  --region-mask /path/to/region.png --out generated/inklabels.png \
  --tau-low 0.15 --tau-high 0.65 --device cpu
```

Thresholds satisfy `0 <= tau_low < tau_high <= 1`. The output is 0 for background,
255 for ink, and 128 for ignore/uncertain. Pixels outside the requested region or
outside scored patches remain ignored. The region must align with the volume
and contain covered pixels. Invalid probabilities, shape mismatches, and read
errors fail before saving. The CLI retains its degenerate-ink-fraction check and
publishes a new, source-disjoint PNG only after completion. Masks must be binary
single-channel PNGs, with a default image/fragment bound of 4,194,304 pixels
(`--max-pixels` overrides it). `config.json` is unnecessary; `--cache-dir` is
optional, and omitted caches are temporary.

For manual-label merging, batch publication, and separate training requirements,
see [Pseudo-label handoff](PSEUDO_LABEL_HANDOFF.md). PNG 128 receives residual
confidence weight 1/255 in the existing loss; it is not an exact ignore mask.

The AUC and pseudo-label paths retain the buffered sampling recipe: request
checkpoint depth plus eight slices and use the central window after dropping
four slices at each end. For AUC, a volume without room for the whole context
gives the centre of what it holds, and one shallower than the checkpoint depth
fails; the pseudo-label command requires the whole context. Spatial
coordinates are unjittered. Ridge features are computed on that buffered
context using the checkpoint sigma.

A checkpoint's `depth_band` is in the slice numbers of the volumes it was set
for: the training fragments' zarrs start at surface-volume layer 16, so
`[1, 27)` is layers 17–42 there and other layers elsewhere (finding 87). The AUC
and review-queue commands apply it only to the labeled volumes the checkpoint
recorded (`uri`/`uris` and `val_uri`; relative paths resolve against the working
directory or the checkout, and a zarr group matches its level 0). Any other
volume is read over its whole depth, as before bands existed, and the command
says so on stderr; the AUC line names the band it used. Pseudo-labels keep the
band on every fragment, because training will read that fragment with the same
band; `tests/test_config_depth_band_fits_fragments.py` checks that the banded
fragments share one depth.

## Manual-review queue

```bash
uv run python -m scripts.active_learning_sampler \
  --checkpoint best_model.pt --volume /path/to/ct.zarr \
  --n_samples 20 --output reports/review_queue.json
```

The queue ranks patches by mean prediction entropy. Before 2026-10-13 it added
`0.3 * (1 - sigmoid(qc))`, but the QC head is trained on the patch's mean fiber
target, not on confidence. At most the requested positive count is returned. Dataset order and
`jitter=False` are required so returned y/x positions identify the scored patches.
Custom reordered batches and invalid ink logits are rejected. The CLI validates
catalog coordinates, passes checkpoint ridge sigma, and records applied model
settings. Optional `--patches_json` must exist and contain valid coordinates.
Catalogs larger than 5000 entries use reproducible seeded subsampling.

Review queues are suggestions for manual inspection; uncertainty scores are not
an accuracy measurement. Queue sampling reads the buffered context for ridge
models (their ridge channel is computed over it, as in training) and the exact
checkpoint depth for CT-only models. The queue records the depth band it applied.

## Incumbent re-evaluation

```bash
uv run python scripts/reevaluate_best_model.py
# Explicitly replace stored scores after a valid measurement:
uv run python scripts/reevaluate_best_model.py --update-stored
# A checkpoint that records a lasagna warp that never ran (finding 86):
uv run python scripts/reevaluate_best_model.py --update-stored --unwarped
```

This command reads `best_model.pt` and `config.json` from the working directory.
`--update-stored` writes `best_model.pt`, so it holds that checkout's lock
(`autoresearch.lock`) until it has written. It refuses to start while the loop,
the noise probe or the augmentation ablation holds it (stop them with `./stop.sh`,
which also pauses the watchdog; restart with `./start.sh`), and the loop cannot
start while it runs. It also does not write if `best_model.pt` changed while it
was loaded or scored, or if a loop killed mid-cycle left a hold that the loop's
next start must settle.
The current config selects validation URI, cache, and batch size; saved model
settings determine reconstruction and input dimensions, with the checkpoint's
recorded `use_lasagna` setting (`--unwarped` scores without a recorded warp and,
with `--update-stored`, records `use_lasagna: false`, keeping the old value in
`reevaluation.overridden_input_settings`). The command uses the loop's protocol,
`seeded-sample-400-v2`, plus `+z<start>-<end>` when `config.json` sets a
`depth_band` (currently `seeded-sample-400-v2+z1-27`): up to 400 seeded catalogue
entries, measured per patch independently of batch size, with ink-free patches
excluded. It recomputes
the promotion F1, AP-prevalence lift and ROC AUC, plus legacy Dice/topology metrics.
It prints the all-ink F1 baseline and margins so a change in sample prevalence
does not appear to be a model improvement.

Missing usable data, failed reads or preprocessing, failed metrics, and nonfinite
metrics fail without updating the checkpoint. A successful explicit update
records the protocol, evaluation URI, settings, accepted/requested patch counts,
thresholds and the fingerprint of the validation inputs
(`validation_diag.inputs_sha256`: the protocol, the fragment, the volume's zarr
metadata, and the label file, mask and `patches.json` it read), then atomically
replaces the checkpoint. The
re-scored checkpoint's model weights, and its configuration apart from an
`--unwarped` correction, remain intact. When `config.json`'s inputs fingerprint
differently (a refined label file written beside the fragment, say), the loop
starts no cycle and no candidate is promoted until the incumbent is re-scored.
For an incumbent scored before fingerprints, the loop records the inputs it
finds at its first start in `best_model.pt.inputs.json` (tied to the checkpoint's
hash, ignored once it is replaced or re-scored) and holds it to them. A stored score from another
protocol blocks loop startup and promotion until explicitly re-scored.

Resolve the host's preprocessing and metric choices before migrating the
incumbent; [finding 86](../reports/loop_v2_constant_control.md) records the open
decisions. Re-evaluation measures the declared inputs and does not establish
prize readiness or decide those choices.

All four tools opt into strict labeled-dataset reads: source reads and requested
Lasagna flattening, ridge features and Frangi targets must succeed. In strict
mode an unavailable warp, failed feature computation, invalid transform result,
or a requested warp/ridge transform with fewer than three slices raises with
patch and backend context. A successful CPU ridge computation is a valid
fallback from a failed GPU implementation; fabricated zero features are not.
For example, `use_lasagna: true` on a host without the CUDA extension/toolkit
now fails validation instead of scoring an unwarped patch. The loop's validation
uses this same strict boundary and marks such samples incomplete. Permissive
training reads retain their warning-and-fallback behavior.
Scientific measurements were not regenerated; corrected masking, sample counts,
ridge settings, and coordinate handling can change future results. See the
[review report](DESIGN_ARCHITECTURE_REVIEW_2026-10-04_CHECKPOINT_TOOLS.md).
The [October 13 review](DESIGN_ARCHITECTURE_REVIEW_2026-10-13_PREPROCESSING.md)
documents strict preprocessing and concurrent native-module initialization.
