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

The predictor uses the checkpoint's voxel size for image scale and both ink and
fiber exports. Single and ensemble inference require complete matching weights;
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

Artifact paths in metadata resolve relative to its directory. Existing paths
relative to the caller's working directory are accepted for older records when
no metadata-relative artifact exists. New prediction and evidence records write
absolute artifact paths; explicit CLI paths resolve from the caller's directory.

Optional ink/fiber VC3D exports are checked for a Zarr v2 group, a single uint8
slice, coherent dimensions and voxel size, z/y/x spatial axes in micrometers,
and a matching OME scale. A declared origin must match its physical translation.
Missing or malformed metadata in a provided export is a failure. Omitting an
export leaves a warning that export compatibility was not checked. Chunk
payloads are not scanned by this metadata validator.

Malformed JSON, geometry, masks, or exports produce a machine-readable failure
report and exit status 1. The output directory for `--out` is created as needed.

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
