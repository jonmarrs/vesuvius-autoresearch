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

## Legacy diagnostic re-evaluation

```bash
uv run python scripts/reevaluate_best_model.py
# Explicitly replace stored legacy diagnostic metrics after a valid measurement:
uv run python scripts/reevaluate_best_model.py --update-stored
```

This command reads `best_model.pt` and `config.json` from the working directory.
The current config selects validation URI, cache, and batch size; saved model
settings determine reconstruction and input dimensions. It retains the legacy
Dice/topology formulas and sampling schedule. It does not recompute the newer
F1/AP promotion contract or establish prize readiness.

Missing usable data, failed metrics, and nonfinite metrics fail without updating
the checkpoint. A successful explicit update records evaluation URI, settings,
accepted/requested batch counts, and thresholds, then atomically replaces the
checkpoint. Its original configuration and model weights remain intact.

All four tools opt into strict labeled-dataset reads: read/processing failures
raise with patch context. Training retains its existing fallback behavior.
Scientific measurements were not regenerated; corrected masking, sample counts,
ridge settings, and coordinate handling can change future results. See the
[review report](DESIGN_ARCHITECTURE_REVIEW_2026-10-04_CHECKPOINT_TOOLS.md).
