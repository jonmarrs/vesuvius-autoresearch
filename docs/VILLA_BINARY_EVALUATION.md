# Bounded binary evaluation with Villa metrics

`scripts/evaluate_villa_metrics.py` compares an existing binary reference and
prediction on an explicitly declared common voxel grid. It runs no inference
or training. Matching shapes and successful metric computation do not establish
registration, reference quality, independent validation or prize eligibility.

## Plan, then evaluate

```bash
uv run python scripts/evaluate_villa_metrics.py \
  --gt /data/reference.zarr --pred /data/probability.zarr \
  --bbox 100 116 200 264 300 364 --out /data/eval-run-001 --dry-run

uv run python scripts/evaluate_villa_metrics.py \
  --gt /data/reference.zarr --pred /data/probability.zarr \
  --bbox 100 116 200 264 300 364 --out /data/eval-run-001 --aligned-inputs
```

The output must be a **new directory**, separate from both inputs and metric
sources. Existing outputs, symlinks and source/output ancestors or descendants
are refused. The old flat JSON-file destination and implicit shape cropping are
retired. Read `summary.json` inside the new bundle instead. Do not reuse an
input filename as `--out`.

Planning checks source headers, settings, selected bounds and metric source-file
availability. It imports no metric, probes no CUDA and creates no output. Values
and dependency availability remain unchecked. Planning can precede the alignment
declaration; execution requires `--aligned-inputs` after independently verifying
that the inputs use the same source voxel coordinates. No resampling or
registration is performed, and physical transforms in metadata are not verified.

Use the repository's pinned Villa submodule (`git submodule update --init villa`)
in an ordinary development checkout. The wrapper expects its legacy
`segmentation/evaluation/metrics/*.py` interface. `--villa-root /path/to/villa`
selects another explicit **trusted code source**; it executes those Python
files. It does not download code or substitute an installed `metrics` package.
Help and planning do not require metric dependencies. A missing source file is
an error, with no report published.

## Exact input contract

Both sources must have the same full 3D shape, even when evaluating a bbox.
The bbox uses **z0/z1/y0/y1/x0/x1**, inclusive-exclusive, in source voxel indices.
It must fit entirely in both sources; no extent is clipped. Without a bbox,
the entire volume is selected. Default `--max-voxels` is `128**3 = 2,097,152`.
For larger sources, use a bounded Zarr crop or explicitly raise the budget.

Accepted inputs are a local 3D Zarr array, a group with explicit array `0`, or
one scalar TIFF stack with ZYX/QYX/IYX axes. Other group levels are not guessed.
2D, RGB/channel, complex/object and multiple-series TIFFs fail. Zarr reads only
the selected region. When root/array `axes`, `_ARRAY_DIMENSIONS` or a single
multiscale frame declares named axes, they must be spatial Z/Y/X in that order;
channel/time axes and contradictory ordering fail. Unnamed 3D arrays retain the
caller-declared ZYX interpretation. Physical transforms remain unverified.
A TIFF's **entire decoded stack** must fit the voxel budget;
large TIFFs should be converted to a bounded TIFF or chunked Zarr first. Encoded
TIFF bytes are limited to `16 * max_voxels + 1 MiB`, captured once, then hashed
and decoded from that capture. The budgets do not cap codec temporaries or total
RAM. Readers, normalized probabilities and topology algorithms allocate more.

The reference uses binary 0/1 or 0/255 values. Multiclass, orientation and ignore
IDs such as 2 or 128 fail instead of becoming foreground. All selected voxels
are evaluated: there is no ignore mask. Choose a fully reviewed region. Unknown
or unevaluated zeros in a sparse label export must not be treated as known
negative labels. This tool does not certify the reference's annotation coverage.

| `--prediction-encoding` | Meaning |
| --- | --- |
| `probability` (default) | Finite real values in [0,1]; binary 0/1 also works |
| `uint8` | Require uint8 and divide values by 255 |
| `binary` | Require binary 0/1 or 0/255, then normalize to 0/1 |

Logits and arbitrary integer class IDs are unsupported. Every hard metric uses
one mask, **probability >= threshold**, with a finite `--threshold` in [0,1].
Threshold zero includes zero probabilities. This replaces the old disagreement:
Dice used its own default 0.5 while topology used `--threshold` with strict `>`.

AP now receives probabilities by default; `--ap-input binary` explicitly selects
thresholded AP. The legacy `--soft_pred` flag is accepted as a probability-AP
alias and conflicts with `--ap-input binary`. Negative voxels remain part of AP;
the upstream `ignore_index=0` excludes the background *class* from averaging,
not negative examples from the foreground ranking. AP without positive
reference voxels is recorded as undefined rather than a measured zero.

`--num_classes` / `--num-classes` remains accepted only with value 2. This wrapper
does not implement multiclass evaluation. Use an appropriate upstream workflow
for class/instance scoring instead of collapsing IDs.

## Metrics, resources and failures

Defaults are `dice`, `centerline_dice`, `connected_components` and `mean_ap`.
Repeat `--metric NAME` to select a different set. Optional names are
`dice_multiclass` (foreground Dice on this binary input),
`skeleton_distance_length` and `critical_components_multiclass` (binary inputs,
two classes). These names identify the pinned functions; they are not new
metric definitions. Each function receives independent copies of the hard masks.

CPU is the default. The CLI hides CUDA before importing PyTorch or metric code.
`--device cuda` explicitly requires a usable CUDA device and never falls back
to CPU after failure. Critical-components evaluation requires that explicit
choice. Native CUDA was not tested in this review. Run the CLI in a fresh
process; it sets process environment variables and is not a concurrent library
evaluation API.

Skeleton evaluation is opt-in. Its module-local Kimimaro call is capped to
**one worker**, replacing the pinned function's `parallel=0` request for all
CPUs. Its optional tracking reference is disabled without starting a global
WandB run or modifying the shared Kimimaro package. Source captures and adapter
settings record these changes. Successful histograms must be readable PNGs,
at most 16 MiB; corrupt or failed-metric histograms are discarded.
The old `--hist_dir` is retired: histograms now belong to the new report bundle.

Villa's centerline score is an asymmetric tolerance statistic, **not a bounded
Dice score**. Reference-empty slices can count predicted skeletons as hits, and
longer prediction skeletons within tolerance can also push it above one. The
wrapper preserves the upstream value, counts predicted reference-empty slices,
and warns about that empty-slice route or a centerline score above one. It does
not change the upstream formula or certify topology accuracy. `--tolerance` is a finite, nonnegative voxel
radius, default 3. Connected components uses 26-connectivity and ignores the
background class.

| Metric status | Interpretation |
| --- | --- |
| `OK` | Finite numeric result from the selected function |
| `WARNING` | Result retained with an explicit interpretation warning |
| `UNAVAILABLE` | Optional metric dependency could not be imported |
| `UNDEFINED` | No finite numeric result, empty result, or AP without positives |
| `FAILED` | Metric execution or artifact validation raised an error |

A selected core metric (Dice, centerline or components) that cannot import stops
before input values are loaded. Runtime failures and optional dependency
failures remain visible alongside other results. No metric is silently omitted,
replaced by zero, or serialized as JSON NaN/Infinity.
The pinned AP implementation catches its own backend exceptions, logs an error,
and returns zero; that reported internal-error path is recorded as `FAILED`.

Exit 0 publishes a `COMPLETE` report with every selected metric `OK`. Exit 2
publishes a `PARTIAL` report containing warning/unavailable/undefined/failed
records. Exit 1 publishes no report after input, core-import, source-stability or
publication failure. Argparse errors use exit 2 without publishing. Stdout is a
JSON plan or completion summary; fatal errors go to stderr. Metric logs are
captured with an 8 KiB tail and truncation marker in the JSON report.

## Report bundle and provenance

```text
eval-run-001/
  summary.json
  summary.md
  sources/
    evaluate_villa_metrics.py
    evaluation_artifacts.py
    villa_dice.py
    ...selected metric sources...
  artifacts/skeleton/...png          # only for a successful skeleton metric
```

The JSON records threshold/encoding/alignment declarations, source shape/dtype,
selected bbox, available Zarr attributes, decoded-region hashes, TIFF byte hashes,
metric source hashes/copies, adapter hashes/copies, package versions, per-metric
results/statuses and verified artifact hashes. It is a bounded measurement
record, not an entire environment or dataset snapshot.

Captured metric sources load under private, fresh module paths. They cannot
resolve to an ambient `metrics` package or reuse an earlier run's metric globals.
Input contents/metadata, original and captured source code, and histogram hashes
are rechecked after writing the report, before publishing the new directory.
Failure leaves no final report and preserves existing files. Keep inputs and
code stable and serialize writers; publication does not promise concurrent
writer safety or power-loss durability.
