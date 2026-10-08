# Volumetric label workflows

Two local CLI workflows produce heuristic labels. CT-gated ink generation uses
an aligned model prediction and CT intensity. Segmentation curation selects
whole chunks of existing labels using the pinned VC Proofreader filter. Neither
workflow establishes ink material, sheet correctness, or ground truth. They are
separate workflows: ink pseudo-labels are not papyrus sheet instance labels.

## CT-gated ink pseudo-labels

```bash
.venv/bin/python scripts/labeling/generate_3d_ink_labels.py \
  --ct /data/ct.zarr --ink-pred /data/xy_prediction.zarr \
  --aligned-prediction --bbox 100 116 200 264 300 364 \
  --output /data/ink-run-001.zarr \
  --debug-png /data/ink-run-001.zarr/debug.png
```

The inclusive-exclusive bbox is in source voxel indices, in **z0/z1/y0/y1/x0/x1**
order. All bounds must be nonnegative integers and fit entirely in the source.
No bound is clipped. CT must be a nonempty real 3D `(z, y, x)` array or group
level `0`; every requested intensity must be finite after float32 conversion.
The existing uint8 conversion to `[0, 1]` is retained; other numeric intensities
retain their scale. No new CT normalization recipe is introduced.

Prediction pixels must match the bbox's CT XY columns exactly, with shape
`(height, width)` or `(1, height, width)`. Probabilities must be finite floats in
`[0, 1]` or uint8 values representing `[0, 255]`. Groups must contain array `0`;
the tool never guesses another child or takes the first of multiple planes.

`--aligned-prediction` declares a fully evaluated map with this XY alignment.
It does not compute registration. A flattened surface UV prediction cannot be
used directly, even if its dimensions match. Register/resample it separately
before declaring alignment. For a bare map without coordinate or run metadata,
alignment and complete prediction coverage are the caller's responsibility.

When producer `meta.json` exists, its CT source and XYZ origin must match the
requested bbox. The supported OME layout is the repository's single-level VC3D
export: one uint8 plane, z/y/x spatial axes in micrometers, isotropic scale, then
origin translation. The existing evidence validator checks its dimensions,
scale, axes, and translation. Other OME compositions or OME predictions missing
producer metadata fail; no mapping from an unfamiliar frame is guessed.

The conventional sibling `PRED_STEM_meta.json` is checked when present. Use
`--prediction-metadata /data/custom-run.json` for a custom run-metadata location.
Run metadata must identify the same source, prediction artifact, bbox origin,
and dimensions, and explicitly record `prediction_complete=true` and
`coverage_fraction=1`. Inference shards and contradictory metadata fail before
publication. Metadata checking is a provenance check, not a rescan of model
inference or a content attestation. Source paths should be recorded as absolute
paths; relocated artifacts need corrected, verified provenance.

The initial mask is the intersection of the 2D probability gate and CT gate:

- `--ink-threshold` is finite in `[0, 1]`, default `0.5`.
- `--ct-percentile` is finite in `[0, 100]`, default `85`. By default the quantile
  is computed across the z stack independently in each prediction-active column.
- `--global-ct-threshold` uses one quantile of all voxels in prediction-active
  columns, falling back to the whole bbox when none are active. This documents
  the existing recipe; inactive columns remain ineligible.
- `--surface-window N` restricts labels to within `N` z voxels of each column's
  CT maximum; `0` disables. This peak-depth heuristic is not a measured surface.
- `--close R` uses a cubic footprint with side `2*R+1`; `0` disables. Final labels
  are intersected with every original gate. Closing cannot add unsupported ink
  and may remove labels at the bbox border, where outside values are zero.
- `--min-component-voxels N` drops 26-connected components smaller than `N` when
  `N > 1`. Counts are `null` when filtering is disabled, rather than falsely zero.

Output is a **new** sparse uint8 Zarr array with the full CT shape. Only the
requested bbox is evaluated. Outside zeros are **unevaluated**, not verified
negative labels. `ink_label_completion` attributes record source paths and
metadata, axes, exact evaluated bbox, alignment basis, run metadata, settings,
and measured counts. Consumers must honor the evaluated region.

Optional `--debug-png` must name a direct `.png` child of the new output folder.
It is built with the labels before publication. Its cyan contour uses the actual
ink threshold, and slice titles use source z coordinates. Successful execution
publishes the labels, requested PNG, and completion metadata together.

## Segmentation chunk curation

```bash
.venv/bin/python scripts/labeling/curate_training_data.py \
  --input /data/sheet-instances.zarr --output /data/curated-run-001.zarr \
  --chunk-size 64 --min-percent 1 --max-percent 95 \
  --min-cc 1 --max-cc 5 --workers 4
```

Input is a nonempty integer or boolean 3D label array, or a group with array `0`.
IDs must be nonnegative. Retained chunks keep the original IDs and dtype.
Percentage bounds are finite in `[0, 100]`, component bounds are nonnegative
integers, and minimum bounds must not exceed maximum bounds. Workers and chunk
size are positive integers.

The pinned upstream tool evaluates only complete cubic chunks. The wrapper
requires the chunk size to divide **every** input dimension, preventing silent
edge loss or a zero-chunk run on small inputs. Choose an aligned chunk size or
make an explicit crop with recorded coordinates. The wrapper does not silently
change the scientific sampling grid.

Upstream considers **all nonzero voxels as one foreground mask**. Connected
component counts use 26-connectivity; they are not counts of distinct instance
IDs. Branch rejection uses the upstream per-Z-plane skeleton junction heuristic,
which can reject valid structures and does not prove folds or merges. It is
enabled by default; `--no-reject-branches` disables it. No filtering algorithm
is copied or changed in the villa submodule.

The output is a new sparse array of the same shape and dtype. The wrapper verifies
readable payloads and that each retained nonempty chunk equals its source chunk.
It reports chunks evaluated, nonempty chunks retained, zero chunks, and labeled
voxels, including a legitimate all-rejected result. `label_curation_completion`
records these counts, settings, upstream script, and source attributes/frame.
Zero chunks are rejected or originally empty; they are not independently verified
negative labels. Source validity regions remain relevant and must be respected
by downstream training. Review selected data independently before training.

## Publication and migration

Both tools reject existing output paths, source/output equality, ancestor/child
relationships, and resolved aliases. Build into an adjacent temporary directory
and publish by a same-filesystem rename only after success. Inputs remain
read-only. Ordinary read, processing, write, debug, or metadata failures leave
no final artifact, and the CLI exits nonzero without a success message.

Choose a new output path for every run or bbox. The previous implicit in-place
accumulation of ink windows is no longer supported: it could mix sources and
settings without provenance. Explicit merging of independently generated windows
is a separate operation and must preserve evaluated coverage. Existing marker-only
outputs have no current completion contract.

The closing option now means the advertised radius, rather than footprint side
length. It also obeys the original eligibility gates. Old refined outputs can
differ and need regeneration; no accuracy improvement is claimed. Debug PNGs
move inside their artifact to give one publication boundary.

These local tools require serialized writers and stable input data throughout
execution. A killed process may leave a hidden staging folder; output is not a
concurrent-write API. Generation materializes the requested bbox in memory.
Curation verification uses one evaluation chunk at a time, but upstream builds
its chunk/future worklist in memory. Underlying Zarr decompression may require
more memory than a requested slice. No whole-scroll performance, GPU inference,
registered surface lifting, or label-accuracy validation was performed by these
contract checks. See the [review report](DESIGN_ARCHITECTURE_REVIEW_2026-10-07_VOLUMETRIC_LABELS.md)
for verification evidence.
