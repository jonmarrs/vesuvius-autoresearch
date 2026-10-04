# CT-volume inference

The autoresearch loop's checkpoints consume CT volumes. Fragment-detector
Lightning checkpoints use the separate [detector workflow](DETECTOR_WORKFLOW.md).
This guide covers `scripts/inference/predict.py`,
`scripts/inference/ensemble_predict.py`, and `scripts/production_predict.py`.

## Choose an inference recipe

The batched production command exports ink probabilities using `sigmoid(ink)`.
It uses positive Hann blending, without QC gating or test-time augmentation:

```bash
uv run python -m scripts.production_predict \
  --checkpoint best_model.pt --uri /path/to/ct.zarr \
  --x 0 --y 0 --z 0 --width 1024 --height 1024 \
  --batch-size 16 --out-dir predictions/production
```

The regional commands export ink, fiber context, and a three-panel CT overlay.
Their existing probability recipe is `sigmoid(ink) * sigmoid(qc / 0.1)` for
ink and `sigmoid(mean(fiber, z))` for fiber. They average probabilities across
four spatial views (unchanged, x mirror, y mirror, both), undoing each output
mirror first. Use `--disable_tta` for one forward per model and tile.

```bash
uv run python -m scripts.inference.predict \
  --checkpoint best_model.pt --uri /path/to/ct.zarr \
  --x 0 --y 0 --z 0 --width 1024 --height 1024 \
  --skip_active_learning --output_img predictions/region.png

uv run python -m scripts.inference.ensemble_predict \
  --uri /path/to/ct.zarr --x 0 --y 0 --z 0 \
  --width 1024 --height 1024 \
  --checkpoints best_model.pt /path/to/second_model.pt \
  --output_img predictions/ensemble.png
```

The ensemble averages each member's probabilities, after that member's QC gate
and optional mirror averaging. Every requested checkpoint must exist and load
all its weights. An empty list, a missing member, incompatible weights, and an
unknown architecture fail explicitly.

These recipes are different, so production and regional outputs need not agree.
For `GenericMultiTaskWrapper` backbones with dummy heads, QC logits are zero
(giving a 0.5 gate) and fiber output reuses ink logits. That output is not an
independently learned fiber measurement. The adapter behavior is unchanged;
use checkpoint configuration and model implementation to interpret the heads.
Ensembling or QC gating does not establish accuracy or hallucination absence.

## Geometry and input compatibility

Positions are source voxel indices in x/y/z order. The loader reads z/y/x and
supplies normalized CT, plus a ridge channel when configured. Model inputs have
shape `(batch, channels, depth, height, width)` even for CT-only ensembles.

Checkpoint patch size, depth, channels, and `ridge_sigma` determine the input.
Voxel size comes from `voxel_size_um`, then legacy `voxelsize`, with the CLI
providing a fallback (7.91 µm by default). The regional option is
`--voxel_size_um`; production uses `--voxel-size-um`.

Regional width and height default to one checkpoint patch. Explicit dimensions
must be positive and at least that patch size. Stride defaults to half the patch
when width or height is supplied, otherwise one patch; a supplied stride must be
positive and no larger than the patch. Production defaults to a 1024×1024 region
and half-patch stride. Every command rejects negative coordinates and regions
extending past the volume, including the full depth interval.

The tile grid includes the final legal tile at each boundary, even when the
region size is not a multiple of stride. Blending divides by actual positive
weights; complete predictions require every pixel to receive a contribution.
Regional blending defaults to Gaussian. `--gaussian_blend` explicitly enables
it; `--no-gaussian_blend` selects positive Hann weights. Before the October 4
review, the positive flag accidentally disabled Gaussian blending. Update
commands that depended on that inversion.

Ensemble members must share patch size and voxel size. Ridge-enabled members
must share `ridge_sigma` and use the maximum ensemble depth: ridge filtering on
a longer patch can change a shorter patch's features. CT-only members may use
different depths, taking a prefix starting at the same source z. Incompatible
members fail before opening the source volume, without spatial resizing or
cropping to reinterpret their context.

## Outputs and provenance

Regional commands save float32 ink/fiber NPY maps, grayscale PNG maps, uint8
OME-Zarr groups, a CT overlay, and JSON metadata. Artifacts and default metadata
are placed beside `--output_img`, or under `predictions` when it is omitted. A
bare image filename uses the current directory. `--metadata_out` selects an
explicit metadata path and creates its parent directories.

OME axes are z/y/x in micrometers. Scale and translation use the same calibrated
voxel size as the fitted overlay scale bar. Both ink and fiber exports record
the source URI and region origin. Metadata records dimensions, calibration,
output paths, configuration, inference recipe, and completeness. Single-model
and production records include the checkpoint path. Ensembles record all
checkpoint paths/configurations and maximum loaded depth; the legacy
`model_config` field identifies the first member.

Input tensors and output logits must be finite floating-point arrays of the
expected dimensions. Invalid data or heads fail before output export. JSON
serialization rejects NaN and infinity. Checkpoint paths and recorded
configuration provide traceability; they do not attest to training history or
independent scientific validity.

## Partial shards

Regional `--num_parts N --part_id K` assigns every Nth tile to part K. N must be
positive and K must be in `[0, N)`; an empty shard is rejected. Any N greater
than one is a partial inference result, even when overlap gives its pixels full
coverage.

Each shard saves normalized ink/fiber maps and a float32 weight map. Unprocessed
pixels stay zero. Metadata includes `prediction_complete=false`, shard identity,
coverage fraction, tile counts, and `blend_weight_path`. The completion message
identifies the partial result. Submission validation rejects these records.

No automatic shard merger is supplied. Maps cannot be merged by averaging their
PNG values. A deliberate merger must verify common source, origin, dimensions,
members, and recipe, combine float maps using their saved weights, require all
tiles/coverage, and write a new complete result with provenance. Until then,
run without sharding for complete-region evidence. See
[Submission evidence](SUBMISSION_EVIDENCE.md) for the remaining evidence gates.

Boundary coverage and normalization were corrected in the October 4 review.
Future regional predictions can therefore differ numerically at boundaries;
existing measurements and published predictions were not regenerated. The
[review report](DESIGN_ARCHITECTURE_REVIEW_2026-10-04_VOLUME.md) lists repairs,
tests, and verification limits.
