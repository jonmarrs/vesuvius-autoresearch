# Fragment detector workflow

This CLI consumes converted fragments and detector Lightning checkpoints.
Research-loop `best_model.pt` files belong to the separate CT-volume predictor
described in the README.

## Configuration and commands

Use a JSON object after each subcommand's `--config` option. Keep the model and
input layer interval consistent with training; changing the target fragment or
data location does not require changing the architecture. Minimal example:

```json
{"data_root": "/path/to/converted_fragments", "architecture": "timesformer"}
```

```sh
uv run python -m vesuvius_autoresearch.detector.cli train --config detector_config.json

uv run python -m vesuvius_autoresearch.detector.cli infer \
  --config detector_config.json --checkpoint /path/to/detector.ckpt \
  --fragment PHercParis2Fr143 --output predictions/fragment.npy

uv run python -m vesuvius_autoresearch.detector.cli eval \
  --config detector_config.json --checkpoint /path/to/detector.ckpt \
  --fragment PHercParis2Fr143

uv run python -m vesuvius_autoresearch.detector.cli measure \
  --config detector_config.json --checkpoint /path/to/detector.ckpt \
  --same PHercParis2Fr143 --cross 20230702185753
```

Inference needs depth layers and a fragment mask. Training, evaluation, and
measurement also need exactly one readable ink-label image. All images for a
fragment must share dimensions. Inference retains the existing full-window mask
rule and stride: uncovered pixels are zero, and no usable windows is an error.
This guide makes no claim that every masked pixel receives a prediction.

## Prediction coverage and export

Inference warns when valid fragment pixels have no usable window and prints a
coverage count after a successful CLI export. A 64×100 fragment at stride 32,
for example, leaves its rightmost four columns uncovered even with a full mask.
An internal mask hole can exclude entire windows as well. These pixels retain
the existing recipe's zero fill; a zero alone does not show whether the model
predicted background or never visited that pixel.

Use an NPZ bundle to save the distinction in one file:

```sh
uv run python -m vesuvius_autoresearch.detector.cli infer \
  --config detector_config.json --checkpoint /path/to/detector.ckpt \
  --fragment PHercParis2Fr143 --output predictions/fragment.npz \
  --output-format npz
```

Load it with `np.load(path, allow_pickle=False)`. Schema version 1 contains:

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | scalar uint8 | 1 |
| `probability` | float32, H×W | Existing blended probability map, including zero fill |
| `coverage` | bool, H×W | At least one usable inference window predicted this pixel |
| `fragment_mask` | bool, H×W | Nonzero original fragment mask, without loader padding |

All maps have the original layer dimensions. Coverage concerns the fragment
mask, not ink labels or confidence. The bundle does not hash inputs or attest
checkpoint provenance. `--output-format npy` remains the default probability-only
format. Both formats use the exact `--output` path without appending a suffix.

Add `--require-full-coverage` to refuse any unpredicted fragment pixels before
replacing the output. This checks the completed inference; it does not add edge
windows or change mask rules. Padding and pixels outside the fragment do not
count as missing. A fragment with no usable windows remains an error.

Python callers retain the probability-array return from `infer(...)`. Pass
`return_details=True` to receive an `InferenceResult` with `probability`,
`coverage`, `fragment_mask`, and a `summary` dictionary (`valid_pixels`,
`predicted_pixels`, `uncovered_pixels`, `coverage_fraction`). The Python API also
accepts `require_full_coverage=True`.

The CLI refuses outputs that overlap its checkpoint, configuration, or fragment
input tree, including symlink and hard-link aliases to the input files. The
output itself must not be a symlink or a nonregular file. It checks paths before
inference and again before publication, then replaces the output by renaming a
fully serialized sibling temporary file. Save failures retain the previous
complete output; replacements retain its permission bits and new files honor
the umask. Use stable input paths and serialize writers; these checks do not
lock inputs or coordinate concurrent inference commands.

Evaluation and measurement still score the original fragment mask, including
uncovered zero-filled pixels. They now receive the inference warning but their
metric formulas, scorecard schema and denominator remain unchanged. This
feature does not revise published results or establish an accuracy improvement.

## Checkpoint compatibility

New checkpoints save the full configuration in `detector_config` with version 1.
Loading checks architecture, lateral size, depth count, and start/end layer indices;
ResEnc checkpoints also check stages and feature count. A same-shaped weight file
cannot silently select a different layer interval or lateral window. Target names,
data paths, tiling settings, training hyperparameters, and TTA can change without
failing that input check. This record does not prove which training data was used.

Legacy checkpoints without a configuration still load using the caller's
configuration and emit a warning. Their input settings cannot be verified from
weights alone. Malformed or unsupported recorded configurations fail loading.
The existing checkpoint loading uses `weights_only=False`; use trusted checkpoints.

## Effective training settings

| Setting | Default | Effect |
|---|---|---|
| `weight_decay` | 0.01 | AdamW weight decay for both architectures |
| `max_grad_norm` | 1.0 | Lightning's gradient norm clipping threshold |
| `warmup_factor` | 1.0 | Warmup scheduler multiplier, followed by the existing cosine schedule |
| `use_tta` | false | Prediction only: average four spatial mirror views when true |

The first three fields previously advertised 1e-6, 100, and 10, while execution
used AdamW's 0.01 default, clipping at 1.0, and multiplier 1.0. Defaults now describe
the executed recipe. An existing JSON file that explicitly supplies the older
advertised values will now apply those values; use the table to retain the old
execution behavior. No published measurement was rerun under those overrides.

Configuration rejects noninteger dimensions/indices, invalid loss and optimizer
settings, nonfinite or nonpositive calibration, invalid fragment lists, and
nonboolean TTA. Invalid JSON configuration is a CLI usage error before work starts.

## Prediction and measurement failures

With TTA enabled, inference evaluates the original, horizontal, vertical, and
combined mirror views, returns each probability map to the original orientation,
then averages them. With TTA disabled, the original one-forward path is retained.
No depth reversal is used. Invalid batch/channel dimensions or nonfinite logits
fail before the CLI writes the prediction map. TTA is optional and has no new
accuracy claim attached to it.

Evaluation requires finite 2D probability/label arrays in [0, 1], a finite
nonnegative mask of the same shape, and selected pixels containing both ink and
background. Invalid input fails before replacing scorecard, threshold CSV, or
thumbnail files. An older scorecard is retained as a previous result; command
failure means that it is not the result of the attempted evaluation.

Cross-scroll measurement continues after a target fails, records its error in the
partial report, and exits nonzero. Reports contain standard JSON without NaN/Inf.
The shared scientific metric formulas, thresholds, and mask denominator are
unchanged. The low-level metric function still returns NaN diagnostics for a
degenerate sample; command-level evaluation does not report it as a valid score.
The reproduction AUC gate also remains active when Python runs with `-O`.
