# Recorded experiment charts and PDF reports

These tools describe the recorded diagnostics in an experiment TSV. The loop
promotes threshold-swept F1 improvements gated by AP-prevalence-lift. The frozen
`results.tsv` schema does not contain those promotion metrics. Its `val_bpb`
field records auxiliary validation 1-Dice; its throughput field records a
training-rate proxy. Neither chart establishes a scientific optimization
frontier, an inference benchmark, a Pareto ranking, or comparable evaluation
across configurations and validation regimes.

## Commands

From the checkout, with an existing results file:

```bash
uv run python scripts/plot_results.py --results results.tsv --out reports/my_experiment_charts
uv run python scripts/generate_daily_report.py --results results.tsv --notebook docs/LAB_NOTEBOOK.md --out reports/my_experiment_report
```

Each `--out` is a **new directory**. Existing files, directories, symlinks, and
source aliases are rejected. If omitted, the tools choose a new directory under
`reports/` using a UTC timestamp with microseconds. A timestamp collision fails
instead of replacing a previous report. Invocations from another directory need
absolute script/input paths; input defaults are relative to the working directory.

The PDF notebook defaults to `docs/LAB_NOTEBOOK.md`, the actual repository path.
To deliberately report diagnostics without notebook commentary:

```bash
uv run python scripts/generate_daily_report.py --results results.tsv --no-notebook --out reports/my_metrics_report
```

A missing or invalid requested notebook fails. It is not silently omitted.
Successful commands exit 0; invalid input, rendering, verification, and
publication failures exit 1 with an error. Invalid arguments exit 2.

## Contents and interpretation

The chart bundle contains `recorded_diagnostics.png`/`.svg`,
`hardware_observations.png`/`.svg`, `report.json`, and `sources/results.tsv`.
The PDF bundle contains `report.pdf`, those four charts under `charts/`,
`report.json`, and exact source copies under `sources/`. An included notebook is
copied as `sources/notebook.md`. Source copies retain original bytes and all TSV
columns, including the configuration-last column.

`report.json` records the source paths, SHA-256 hashes, byte sizes, row count,
column names, timestamp interpretation, ordered numeric records, scope, and each
output's hash/size. Rows retain original TSV line numbers and timestamp strings;
normalized timestamps support ordering. PNG metadata also identifies the captured
TSV and report scope. Hashes bind the report to supplied bytes; they do not verify
training outcomes or scientific eligibility.

The timeline uses separate scatter plots for auxiliary loss and training
throughput. It does not join different regimes into an improvement curve. Loss
and color scales are linear, so a legitimate zero loss remains visible. The
hardware chart shows observations without computing a frontier or ranking.

The PDF lists the five most recent recorded rows, newest first. It does not
select the lowest auxiliary loss or label rows discoveries. For tied timestamps,
later source rows appear first; the manifest's ascending order is stable. The
PDF displays whole seconds, while the manifest and source copy preserve full
timestamp precision and recorded offsets.

Notebook selection uses the greatest date among level-two headings beginning
with an ISO date, including the repository's bracketed date syntax. For equal
dates it chooses the later section in the file. Undated headings, introductions,
and the future-entry template are not selected. The excerpt stops at the next
level-two heading, is capped at 2,000 characters, and marks truncation explicitly.
It is labeled dated intent and commentary, rather than current measured results.
Bundled DejaVu fonts support the notebook's punctuation and Greek characters.
Unsupported glyphs fail explicitly instead of disappearing from the PDF.

## Input and publication contracts

The reader accepts the unchanged configuration-last schema and tables containing
at least `timestamp`, `val_bpb`, `throughput_Mvps`, and `num_params_M`. Every data
row must match its header width; duplicate/empty headers, missing fields, invalid
UTF-8, empty tables, and malformed TSV are rejected. Other columns are preserved
in the source copy but not interpreted.

Required metrics must be finite numbers: loss in [0, 1], throughput nonnegative,
and parameter count positive. No row is silently dropped, imputed, or repaired.
Dates must include a valid ISO date and time down to seconds. Offset-qualified
dates are normalized to UTC; unqualified dates retain recorded wall time with
the timezone explicitly unknown. Mixing qualified and unqualified dates fails.
Inputs are bounded to 16 MiB and 10,000 rows for TSV, and 2 MiB for notebook.

Each input is captured once. Charts and the PDF use that capture, and the source
bytes are checked again immediately before publication. All outputs are staged
and verified, then published together using the existing directory publisher.
Failures remove the staging directory and preserve prior files. The publisher
assumes serialized writers and stable input paths; it is not a concurrent-writer
or live-log tailing API. Use a stable copy if the training loop is appending.

## Migration and limits

The old fixed chart names, same-day PDF destination, silent missing-input success,
loss-ranked discovery table, and lexicographic training-sample selection are
retired. The PDF builds its own charts from the selected TSV. It does not embed
legacy cached plots or unrelated training images. Historical committed reports
remain historical artifacts.

Python callers can use `plot_results(results, output)` to obtain the published
directory, or `generate_pdf(results, notebook, output)` to obtain its PDF path.
Pass `notebook=None` for explicit omission.

No training, promotion, evaluation harness, metric computation, or TSV schema
changes are included. This workflow cannot reconstruct F1/AP rankings or certify
comparability without a separately designed metric/provenance migration.
