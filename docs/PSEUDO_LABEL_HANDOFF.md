# Pseudo-label preparation and training handoff

`scripts/iterative_pseudo_labeling.py` prepares **one label batch from one
recorded teacher**. Its default is a validated dry run; `--execute` runs actual
inference. The previous interface simulated retraining and called an incompatible
generator. It is retired, including `--scrolls`, `--rounds`, and `--threshold`.
A subsequent round requires a separately trained, recorded teacher checkpoint.
No training, experiment promotion, or accuracy claim follows from preparation.

## Declare inputs

Use a trusted local autoresearch checkpoint with recorded model configuration
and complete finite weights. See [checkpoint analysis](CHECKPOINT_ANALYSIS.md).
Generation uses the declared region for label-free sampling; unrelated fragment
`inklabels.png` files are not read. Manual labels enter only through the manifest.
Each fragment contains a local nonempty ZYX CT array in `surface_volume.zarr`
(bare array or explicit level `0`) or a bare `0` directory. The existing local
reader supplies patches. Checkpoint depth plus eight buffered slices and a full
spatial patch must fit. Inputs must remain stable while the command runs.

Create a JSON manifest; paths resolve relative to its containing directory:

```json
{
  "regions": [
    {
      "fragment": "fragments/segment_a",
      "region_mask": "masks/segment_a_requested.png",
      "manual_labels": "labels/segment_a.png",
      "manual_mask": "masks/segment_a_known.png",
      "holdout_mask": "masks/segment_a_heldout.png"
    }
  ]
}
```

`fragment` and `region_mask` are required. `manual_labels` and `manual_mask` are
optional together. An explicit known-pixel mask distinguishes manual background
from unlabeled pixels. Where that mask is positive, both manual background and
manual ink override pseudo-labels. Known manual pixels can extend beyond the
requested pseudo-label region. Optional `holdout_mask` must not overlap either
requested pixels or known manual pixels. These checks concern supplied masks;
they do not establish the teacher's training history or held-out independence.

Masks and manual labels must be aligned, single-channel binary PNGs using 0/1
or 0/255. RGB, other grayscale values, empty requested regions, shape mismatch,
and duplicate fields or unknown manifest keys are rejected. Pseudo-label PNGs
use exactly uint8 0/128/255. Fragment basenames must be unique because the trainer
looks up `<segment>_pseudo.png`; two paths ending in `div_100` would collide.
Duplicate canonical volume sources are rejected too.

The default bound is **4,194,304 pixels per fragment/image**. `--max-pixels` can
explicitly raise it. Probability mosaics, masks, and merged labels occupy memory
proportional to H×W; CT is read by patch. Prefer explicit bounded crops for large
fragments. Volume content is not hashed or scientifically validated.

## Validate and prepare

```bash
uv run python scripts/iterative_pseudo_labeling.py \
  --checkpoint /path/to/teacher.pt --manifest /path/to/regions.json \
  --out /path/to/new_batch --device cpu

uv run python scripts/iterative_pseudo_labeling.py \
  --checkpoint /path/to/teacher.pt --manifest /path/to/regions.json \
  --out /path/to/new_batch --device cpu --execute --timeout 3600
```

A dry run validates weights, metadata, masks, and destinations, prints prospective
commands, and creates no outputs. It cannot prove patch coverage or predictions
without inference. Thresholds satisfy `0 <= tau_low < tau_high <= 1`, with
strict comparisons; defaults remain 0.15 and 0.65. The existing producer's
degenerate-ink check remains defined over the full image: ink fraction below
0.0001 or above 0.99 fails. It is a workflow guard, not a quality measurement.

Execution uses the active interpreter, the actual producer CLI, source-disjoint
staged outputs, and per-segment caches. `--timeout` is a positive finite number
of seconds per child. Nonzero exits, timeout, interruption, malformed PNGs,
confident pixels outside the requested region, missing confident coverage, or
changed checkpoint/manifest/mask/label hashes prevent batch publication. The
process supervisor stops the child's process group. The final output must be
new and separate from every declared source. Serialize writers; this is not a
concurrent publication API. Keep CT content stable; only its identity and shape
are rechecked, not every voxel.

A successful batch contains:

- `raw/<segment>_pseudo.png`: the actual teacher's confidence-filtered labels.
- `labels/<segment>_pseudo.png`: the merged labels the trainer can consume.
- `cache/<segment>/`: coordinate catalogs used during generation.
- `handoff.json`: source and output hashes, model settings, thresholds, coverage
  counts, executed commands, and requirements for a separate training run.

`status: PREPARED` and `scope: pseudo_label_preparation` describe completion of
label preparation. `training_executed`, `accuracy_verified`, and
`teacher_lineage_verified` remain false; `submittable` remains null. Executed
commands retain the real temporary staging paths for provenance; use the final
artifact paths in the manifest to locate the published files.

## Training requirements and ignore encoding

Review the handoff's `training_requirements` before a separate recorded training
run. Set `uris` to the listed source volumes, `pseudo_label_dir` to the published
`labels` directory, and **`use_confidence_weight: true`**. The trainer gives an
existing pseudo-label file precedence over its fragment's manual file, making
this explicit merge necessary. Fragment sampling masks, validation data, spatial
separation, teacher lineage, and the rest of the experiment config remain the
operator's responsibility. No full training config is generated or executed.

The existing loader normalizes PNG 128 to **128/255**, not exactly 0.5. Existing
confidence weighting therefore gives these pixels residual weight **1/255**,
not zero. Without confidence weighting they are ordinary soft labels. Exact
ignore-mask enforcement is not implemented in the existing loss, and these
artifacts cannot promise that held-out pixels receive no training gradient.
Training loss, normalization, buffered sampling, model math, and evaluation
formulas are unchanged. Do not use confidence-filtered labels as ground truth.

For local directory merging through `combine_labels`, put `<segment>.png` and
`<segment>_mask.png` in the manual directory and `<segment>_pseudo.png` in the
pseudo directory. Manual-only and pseudo-only segments are retained; unknown
manual-only pixels become 128. The destination must be new and source-disjoint.
The legacy `scripts/labeling/generate_pseudo_labels.py` entry point now delegates
to the region-mask producer; old architecture-guessing flags fail with usage.

## Measure agreement

```bash
uv run python scripts/pseudo_label_quality_report.py \
  --pseudo /path/to/new_batch/raw/segment_a_pseudo.png \
  --true /path/to/independent_ground_truth.png \
  --region-mask /path/to/evaluation_region.png
```

Output is finite JSON. Coverage is confident pixels divided by **requested
region pixels**; precision and recall use that confident subset. `auc` is
**hard-label ROC-AUC**, not ROC-AUC of teacher probabilities. Selection by
confidence can bias these metrics; compare coverage and independently measured
teacher probabilities before drawing conclusions.

Undefined precision/recall, no confident predictions, and one-class ground truth
produce JSON nulls with `status: INDETERMINATE` and a nonzero exit. They do not
manufacture zero scores or chance AUC. Malformed inputs also exit nonzero.
`MEASURED` means these subset metrics are defined, not that the model is accurate
or independently validated. Review [FINDINGS](../FINDINGS.md) before proposing
self-training: preparation correctness does not establish a quality gain.
