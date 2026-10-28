# Submission evidence

The submission tools check local file and metadata contracts. A `PASS` means the
provided artifacts satisfy those checks. It does not establish scientific
accuracy, prove that masks describe the full training history, verify the drawn
scale bar by image analysis, or certify current prize eligibility.

## Predict and retain provenance

Generate ranked inference commands from the repository root:

```sh
uv run python -m scripts.inference.run_ranked_inference \
  --ranked reports/scroll23_ranked_candidates.tsv \
  --manifest /tmp/scroll23_inference_commands.sh
```

The default writes commands. `--execute` runs them serially. Generated commands
use the existing prediction launcher, and candidate geometry must contain
nonnegative integer coordinates and a region at least as large as its ML patch.

The predictor uses the checkpoint's recorded voxel size, else the candidate's
`voxel_um` (passed as `--voxel_size_um`), for image scale and the ink and fiber
exports. Single and ensemble inference require complete matching weights;
partial warm starts cannot generate prediction evidence. Its four-mirror TTA runs once, and Gaussian blending works without
optional upstream model imports. `--disable_tta` requests one forward pass.

A small image uses a bar that fits its field of view; for example, a 64-pixel
crop at 7.91 µm uses a 100 µm bar. Such a crop does not satisfy this validator's
1 cm declaration gate. A larger output region can still use small ML windows.
Review the physical calibration of the final figure before submission.

## Supply overlap evidence

Provide two nonempty, finite 2D numeric arrays in the same coordinate frame,
using NumPy `.npy` files or grayscale images. Positive values select pixels.
The arrays must have matching shapes; the prediction mask must select at least
one pixel. A training mask with no selected pixels is accepted when supplied by
the operator, since a held-out scroll may have no training region in that frame.
The validator cannot infer this from a checkpoint or invent the mask.

Validate prediction metadata with actual masks:

```sh
uv run python scripts/validate_prize_artifact.py \
  --metadata /absolute/prediction_meta.json \
  --train-mask /absolute/train_mask.npy \
  --predict-mask /absolute/predict_mask.npy \
  --out /tmp/prediction_readiness.json
```

Masks can also be referenced by `train_mask_path` and `predict_mask_path` in the
metadata. A readable static image is required via `output_image_path` or
`source_image_path`. Geometry must be positive and finite, with three x/y/z
voxel indices. Placeholder or illustrative evidence fails even when its numeric
overlap is zero. The existing 64-pixel or 0.5 mm window rule is retained.

The metadata must record a complete prediction (`prediction_complete: true`)
whose ink map is `sigmoid(ink)` (`inference_recipe.ink_probability`): shards,
records without completeness, QC-gated maps from before 2026-10-13 and maps
without a recorded recipe fail. A declared 1 cm scale bar must fit the region:
`width_px × voxel_size_um` must be at least 10 mm, so a 64-pixel region at
7.91 µm (0.51 mm) cannot pass, whatever it declares. `predict.py` declares the
bar only when it fits 80% of the width, from 1581 pixels at 7.91 µm.

Artifact paths in metadata resolve relative to its directory. Existing paths
relative to the caller's working directory are accepted for older records when
no metadata-relative artifact exists. New prediction and evidence records write
absolute artifact paths; explicit CLI paths resolve from the caller's directory.
Metadata artifact references also accept local `file://` URIs; nonlocal file
authorities are rejected.

Optional ink/fiber VC3D exports are checked for a Zarr v2 group, a single uint8
slice, coherent dimensions and voxel size, z/y/x spatial axes in micrometers,
and a matching OME scale. A declared origin must match its physical translation.
Missing or malformed metadata in a provided export is a failure. Omitting an
export leaves a warning that export compatibility was not checked. Chunk
payloads are not scanned by this metadata validator.

Malformed JSON, geometry, masks, or exports produce a machine-readable failure
report and exit status 1. The output directory for `--out` is created as needed.
JSON inputs are bounded to 2 MiB and reject duplicate fields, nonstandard
nonfinite constants and excessive nesting. Masks and static discovery images
must be regular files. Invalid numeric ranges produce a failure report.

Validation captures metadata once and records its canonical path, SHA-256 and
byte size as `metadata_source`. Relative artifact paths use that capture's
directory, including when the requested metadata path is a symlink. Changes to
the captured source fail validation and abort CLI report publication. This binds
the metadata bytes; referenced image, mask, export and checkpoint contents are
not frozen or comprehensively fingerprinted.

Report outputs are checked against metadata, declared images/masks/exports and
checkpoint paths, explicit input overrides, and the research lock. Direct,
ancestor, symlink and existing hardlink aliases are rejected. A safe report path
is written by staged replacement; serialization or publication failure retains
the previous report. Unsafe destinations receive an error without an output
write. Path checks assume stable inputs and serialized writers.

## Check prerequisites before inference

```sh
uv run python scripts/run_villa_prize_evidence_chain.py \
  --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 0 \
  --out-dir /absolute/candidate_000 --checkpoint best_model.pt \
  --preflight --execute --preflight-report /tmp/candidate_prerequisites.json
```

With `--preflight`, `--execute` selects the inference prerequisite checks and
starts no processing. Without `--execute`, preflight checks existing prediction
files instead. Optional `--train-mask` and `--predict-mask` paths are forwarded
and checked for readable, nonempty files. Their contents, alignment and overlap
remain for artifact validation. Existing-artifact mode also checks masks declared
in that metadata; fresh inference does not inherit masks from an earlier run.
Missing unspecified masks are explicitly
`NOT_CHECKED` and may still block later artifact validation.

The JSON retains `status`, `failures` and `warnings`, and adds named `checks`
with `PASS`/`FAIL`/`NOT_CHECKED`, `next_actions`, and
`prize_eligibility: not_assessed`. Candidate geometry uses the same strict
command builder as prediction. Checkpoints must be readable, nonempty regular
files; model weights/compatibility, volume contents/bounds and full artifact
validation remain `NOT_CHECKED`. A preflight `PASS` has this prerequisite scope.
The window check identifies the retained local artifact contract explicitly.

`--preflight-report` requires `--preflight`. Its destination may be a separate
report beside the evidence, but cannot replace managed evidence files or files
under `predictions/`. This protects the final readiness report from being
replaced with a prerequisite-only report.

## Assemble an evidence directory

The chain expects the candidate's prediction image and original metadata under
the output directory's `predictions` subdirectory. Use `--execute` to create them
through inference, or supply existing prediction artifacts:

```sh
uv run python scripts/run_villa_prize_evidence_chain.py \
  --ranked reports/scroll23_ranked_candidates.tsv \
  --candidate-index 0 --out-dir /absolute/candidate_000 \
  --train-mask /absolute/train_mask.npy \
  --predict-mask /absolute/predict_mask.npy
```

The chain writes `candidate.json`, `predict_command.sh`, `evidence_metadata.json`,
`manifest.json`, and `PRIZE_READINESS_REPORT.json`. The original prediction
metadata is retained. The separate evidence record carries supplied mask paths
and candidate context; validation rejects disagreement in source, coordinates,
region size, ML patch, voxel size, or image identity. Placeholder and dry-run
flags remain in force. The review manifest validates the evidence record.

A failed execution cannot leave an earlier report marked `PASS`. Successful
execution must also refresh both image and metadata; a zero exit without new
artifacts cannot reuse old evidence. `--preflight` checks inference prerequisites
and identifies that scope explicitly. It does not certify submission readiness.
Before changing any evidence, the chain checks all managed writes and requested
prediction artifacts against the ranked input, checkpoint, source volumes,
supplied masks and declared input artifacts. Existing prediction metadata is
preserved in artifact-validation mode. An unsafe path is rejected before the
attempt begins. After safe preflight, an atomic `FAIL` marker begins the attempt;
if that marker cannot be published, previous evidence remains intact and no
processing starts. Subsequent failed runs leave the marker in force. JSON
records use the shared staged writer. Serialize writers; the whole evidence
directory is not one crash-transactional publication.

## Preview a package

```sh
uv run python scripts/generate_submission_package.py --out-dir /tmp/submission_preview
```

This command creates an illustrative layout and deliberately exits 1 with a
`FAIL` readiness report. Its masks are marked illustrative and its metadata is
always marked dry-run, including when a real source image or scroll ID is given.
The generated mitigation note lists the evidence still needed; it does not claim
that an ensemble eliminates hallucinations or revive the withdrawn skeleton
distance gate. A centimeter bar is only drawn when it fits the preview image.
