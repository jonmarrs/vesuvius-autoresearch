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
four slices at each end. Volumes too shallow to provide that context fail;
there is no silent shortened input. Spatial coordinates are unjittered. Ridge
features are computed on that buffered context using the checkpoint sigma.

## Manual-review queue

```bash
uv run python -m scripts.active_learning_sampler \
  --checkpoint best_model.pt --volume /path/to/ct.zarr \
  --n_samples 20 --output reports/review_queue.json
```

The queue ranks mean ink entropy and QC uncertainty using the existing 0.7/0.3
recipe. At most the requested positive count is returned. Dataset order and
`jitter=False` are required so returned y/x positions identify the scored patches.
Custom reordered batches and invalid heads are rejected. The CLI validates
catalog coordinates, passes checkpoint ridge sigma, and records applied model
settings. Optional `--patches_json` must exist and contain valid coordinates.
Catalogs larger than 5000 entries use reproducible seeded subsampling.

Review queues are suggestions for manual inspection; uncertainty scores are not
an accuracy measurement. Queue sampling uses the exact checkpoint depth, while
the AUC/pseudo-label commands retain their buffered depth recipe.

## Incumbent re-evaluation

```bash
uv run python scripts/reevaluate_best_model.py
# Explicitly replace stored scores after a valid measurement:
uv run python scripts/reevaluate_best_model.py --update-stored
```

This command reads `best_model.pt` and `config.json` from the working directory.
The current config selects validation URI, cache, and batch size; saved model
settings determine reconstruction and input dimensions, with the checkpoint's
recorded `use_lasagna` setting. The command uses the loop's
`seeded-sample-400-v2` protocol: up to 400 seeded catalogue entries, measured per
patch independently of batch size, with ink-free patches excluded. It recomputes
the promotion F1, AP-prevalence lift and ROC AUC, plus legacy Dice/topology metrics.
It prints the all-ink F1 baseline and margins so a change in sample prevalence
does not appear to be a model improvement.

Missing usable data, failed reads or preprocessing, failed metrics, and nonfinite
metrics fail without updating the checkpoint. A successful explicit update
records the protocol, evaluation URI, settings, accepted/requested patch counts,
and thresholds, then atomically replaces the checkpoint. Its original
configuration and model weights remain intact. A stored score from another
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
