# Checkpoint export and inference handoff

These commands export a research checkpoint envelope and validate its local
weight contract. An exported file is separate from proof that an upstream
inference runtime can load it or that its predictions are eligible for submission.

## Export a local checkpoint

```sh
.venv/bin/python scripts/export_for_production.py \
  --input best_model.pt \
  --output outputs/checkpoint-review/model.pt
```

Use a new output path. Existing files, directories, symlinks, source aliases,
and overlapping paths are refused. The command works outside the checkout when
invoked by absolute script path; supplied relative paths refer to the caller's
working directory. Only read trusted checkpoints: the existing PyTorch loading
contract uses `weights_only=False`.

The checkpoint must contain its recorded `config` and one nonempty weight mapping:
`model_state_dict`, or the legacy `state_dict` key. Both keys together are
ambiguous and are refused. Architecture is read from configuration rather than
guessed from the first key; the ResNet decoder and TimeSformer wrappers both use
`backbone.*` keys, so that prefix cannot identify their architecture.

For local inference architectures, export reuses the shared checkpoint-model
constructor. Required recorded dimensions and settings are validated and
`load_state_dict(strict=True)` must accept every weight. Finite real dense
tensors are required. This is a CPU model-load check without volume access,
training, evaluation, preprocessing changes, or a performance measurement.
Unsupported architecture names and missing/mismatched weights fail before
publication. The local canonical factory's supported models determine support;
an upstream model name such as `resnet3d-50` does not imply a local converter.

The envelope contains `model_state_dict`, the original configuration, recorded
scalar metrics, and `metadata`. It preserves tensor values and dtypes. It omits
optimizer/scheduler/training state and is therefore not a training-resume file.
Missing metrics remain absent; `metadata.val_bpb` is null when not recorded.
No measurement is rerun. Recorded metrics are not new accuracy evidence.

Metadata records the canonical source checkpoint path, its SHA-256, architecture,
and weight-validation scope. `inference_verified` is false and `submittable` is
null. Pretrain/config paths and hashes are copied only when recorded in this
checkpoint's configuration. No ambient launcher marker or current external file
is used to manufacture lineage. Such recorded lineage is explicitly unverified.

The source hash is checked again after model validation. A saved envelope is
read back and validated in a same-directory staging file before rename publishes
it. Failures clean up staging. Keep source files stable and writers serialized;
a concurrent writer after the last check is outside this publication contract.

## Validate the envelope and record handoff limits

```sh
.venv/bin/python scripts/smoke_test_villa_optimized_inference.py \
  --input best_model.pt \
  --output outputs/checkpoint-handoff/model.pt \
  --report outputs/checkpoint-handoff/report.json \
  --command-out outputs/checkpoint-handoff/command-template.sh
```

All destinations must be new, mutually separate, and source-disjoint. Preflight
checks them before any export. Malformed/missing inputs produce a finite JSON
`FAIL` report and a nonzero CLI exit when the requested report path is safe.
Invalid output paths are refused without rewriting an earlier report.

`PASS` has the explicit scope **checkpoint envelope validation only**. For local
models, the report covers strict local weight loading; it does not certify
upstream inference, prediction accuracy, or eligibility. A complete envelope
may remain if a later command/archive/report stage fails; the report states the
overall outcome. Use new paths for retries.

For architectures with a corresponding villa registry model type, the command
file can contain a clearly labeled Docker template. `MODEL` selects the registry
model; the template does not mount or load the exported file. Its layer range
and tile/stride settings are validated, but it is separate from checkpoint
verification. `--execute-docker` is refused before export/execution and records
`FAIL`, because running a different model cannot verify this checkpoint. Running
an upstream registry workflow separately requires its own input/model context
and independent validation of the model being used.

## Legacy Primus archives

A `primus_lejepa` envelope requires a recorded positive scalar patch size and
finite tensor weights including `shared_encoder.*`. It receives
`STRUCTURE_ONLY` validation: there is no complete local Primus constructor or
verified upstream conversion in this exporter.

Optionally supply `--submission-package-dir` with a new directory to archive
such an envelope. The legacy function/flag and `submission_manifest.json` names
remain, but the package scope is **checkpoint archive only**. It copies the
checkpoint byte-for-byte, records its digest and declarations, and writes
`predict_manifest.json` with `command: null`, `inference_verified: false`, and
the blocking reason. No native inference command or submission readiness is
claimed. Existing archive directories are refused; copy failures do not publish
an incomplete archive.

The pinned villa `train_py` loader selects weights from `model` (or the configured
EMA set), and builds its network from `model_config` and normalization metadata.
The legacy envelope has `model_state_dict` and a local `config`; renaming a flag
or weight key does not supply the missing architecture/normalization contract.
Retain native villa training checkpoints for their intended runtime rather than
discarding these fields through this exporter. Native checkpoints are not
converted here.

## Migration

The prior exporter overwrote destinations, inferred architecture by key prefix,
defaulted missing `val_bpb` to zero, and read a CWD-relative fine-tuning marker.
Exports now require recorded settings, preserve existing metrics, and use new
artifact paths. The smoke CLI requires explicit output/report/command paths and
does not execute the registry Docker template. Primus packaging is an optional
archive with explicit missing compatibility evidence. Historical reports remain
records of their original runs and are not upgraded by envelope validation.
