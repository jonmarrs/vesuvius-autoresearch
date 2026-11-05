# Verify saved detector reports

Evaluation keeps its existing filenames under `DetectorConfig.reports_dir`:

- `<fragment>_metrics_by_threshold.csv`
- `<fragment>_pred_thumb.png`
- `<fragment>_scorecard.json`

The scorecard is now the completion marker. It retains existing metrics and the
`pixel_auc` / `threshold` aliases, and adds `artifact_contract: 1`, report kind,
`report_status: COMPLETE`, a UTC creation timestamp and byte counts/SHA-256 hashes
for the CSV and thumbnail. Metric formulas, thresholds, masks and blending are
unchanged.

Check a newly generated report without importing Torch, NumPy or image libraries.
Set `REPORT_DIR` to the report directory from that evaluation; the repository's
tracked legacy scorecard lacks this completion contract and needs regeneration.

```bash
python scripts/check_detector_report.py \
  "$REPORT_DIR/PHercParis2Fr143_scorecard.json"
```

The script also works from another working directory using its absolute path.
It prints JSON with integrity, completion status, creation time and artifact
names. It exits 0 for a consistent complete report, 1 for invalid/missing files
or an incomplete measurement, and 2 for usage errors. It reads files only; it does
not run inference or repair a report. A checksum check binds the observed output
bytes, not the source dataset, actual model weights or scientific validity. It
does not recompute metrics or establish which attempted run was most recent.

## Pin a recorded report

The default check validates the payload bytes declared by the current marker.
It cannot detect an edit confined to the marker's metric fields or checkpoint
display text. When a report is produced and trusted, record its marker's SHA-256
separately, for example in the run ledger:

```bash
sha256sum "$REPORT_DIR/PHercParis2Fr143_scorecard.json"
```

For a later check, set `RECORDED_SHA256` to that saved 64-character hash:

```bash
python scripts/check_detector_report.py \
  "$REPORT_DIR/PHercParis2Fr143_scorecard.json" \
  --expected-sha256 "$RECORDED_SHA256"
```

The hash comparison uses the same captured bytes that are parsed. Matching it
still requires valid marker contents, unchanged payload hashes and the normal
completion checks. On success, JSON output also includes `marker_sha256`, in
lowercase; uppercase input is accepted. A mismatch or malformed hash exits 1
without modifying files. A partial measurement still exits 1 when its pin matches.
Python callers can pass `check_report(path, expected_sha256=recorded_hash)`.

The pin covers exact marker bytes, including metrics, timestamp, formatting and
declared payload identities. Keep the expected hash independently of the mutable
report. Computing a new expected hash from the file being inspected would not
detect an earlier edit. A hash does not establish dataset/model identity,
scientific correctness or authorship.

## Cross-scroll measurements

`measure` keeps `cross_scroll_measurement.md` and
`cross_scroll_measurement.json`, including the JSON's existing fragment-keyed
schema. It additionally publishes `cross_scroll_measurement_manifest.json` as
the completion marker, with checkpoint display text, both output hashes,
creation time and target/success/failure counts:

```bash
python scripts/check_detector_report.py \
  "$REPORT_DIR/cross_scroll_measurement_manifest.json"
```

| Status | Meaning | Checker exit |
|---|---|---:|
| `COMPLETE` | Every requested target was scored | 0 |
| `PARTIAL` | Some targets were scored; others recorded errors | 1 |
| `FAILED` | Every target recorded an error | 1 |

A partial/failed measurement can have valid file integrity. The checker reports
both facts and prints the counts. The detector CLI still exits nonzero when any
target fails. Per-target errors remain in the JSON and Markdown; successful
targets remain usable for inspection.

Target IDs must be unique, nonempty filename components, and each target needs a
nonempty scroll label. Empty plans, duplicates, path components and control
characters fail before any model/data work or report writes. CLI `--same` and
`--cross` must be distinct. Invalid CLI selections produce a usage error instead
of silently overwriting a dictionary row. Public data/inference entry points also
refuse unsafe fragment IDs.

## Coverage and scoring inputs

CLI evaluation and cross-scroll measurement now request inference details and
load only the ink-label image afterward. The full CT layers and fragment mask
are decoded once per target; scoring uses that captured mask. Labels must match
the original prediction dimensions. Training's `read_image_mask` API continues
to load the volume, labels and mask together.

Successful CLI scorecards and measurement rows add `prediction_coverage`:

| Field | Meaning |
|---|---|
| `valid_pixels` | Nonzero pixels in the captured fragment mask |
| `predicted_pixels` | Valid pixels visited by at least one inference window |
| `uncovered_pixels` | Valid pixels with the existing zero fill |
| `coverage_fraction` | Predicted / valid pixels |

A 32×36 full fragment mask at size/stride 16, for example, has 1,152 valid pixels,
1,024 predicted pixels and 128 uncovered pixels. Default scoring still includes
all 1,152 valid pixels; counts do not silently change the denominator. Measurement
Markdown also displays predicted and uncovered counts. A `COMPLETE` report means
all requested targets were scored, not that every pixel was predicted.

Pass `--require-full-coverage` to `eval` or `measure` to reject uncovered targets.
Evaluation preserves the previous report on refusal. Measurement records a target
error, continues and writes a partial/failed report with a nonzero CLI exit. A
fully covered target remains scoreable alongside a failed one. These options
retain the inference grid, mask rules, metric formulas and zero-fill convention;
they do not introduce a covered-only scoring mode.

Python `measure(..., require_full_coverage=True)` supports the same policy.
The array-level `evaluate(..., coverage=boolean_map)` API optionally records the
same counts after checking shape/type; callers omitting coverage retain the
previous metric-only behavior. Absent coverage metadata means unknown coverage,
not full coverage. The report checker verifies the recorded report bytes, not
the missing full-resolution coverage maps or model accuracy.

CLI report preflight also protects the supplied configuration, selected converted
fragment trees, CT layers, fragment masks and discovered ink-label files, in
addition to the checkpoint. Reports inside a selected input tree or aliasing
these files are refused before inference; `reproduce` checks its configuration
and selected converted fragments before conversion/training. Publication rechecks
the supplied input paths, including aliases created after inference.

Python `measure` callers can supply `config_path=...` for configuration protection.
Array-level `evaluate` callers can supply extra filesystem `inputs=(...)`; arrays
alone do not identify their source paths. These checks do not hash or snapshot
datasets/configurations/checkpoints, verify a scientific split or lock out other
writers. Keep inputs and paths stable. No historical report is upgraded.

## Publication and failure behavior

Previously, a thumbnail error after CSV writing left new CSV values beside an
old scorecard. The report was a mixture of attempts. Both report writers now:

1. Encode all payloads and metadata, validate target paths and byte limits, and
   stage/read back every file before touching the previous set.
2. Recheck the existing files, then move the old completion marker to a private
   recovery directory before replacing its payloads.
3. Install and verify payloads, install the new marker last, and recheck every
   published byte sequence before returning success.

Caught publication errors restore the previous files, their permission modes and
previously absent files' absence. An interrupted write before publication leaves
all previous reports intact. Existing symlink/special-file targets, a symlink
report directory and output/input aliases are refused. Output path/type/size
checks run before expensive CLI evaluation or measurement inference, and
`reproduce` runs them before conversion and training. Names stay
inside the selected local report directory. Unrelated files are preserved.

If rollback also fails, the error names a retained `.detector-report-*` recovery
directory. Its `previous/` subdirectory holds prior files that were not restored;
already restored prior files may be back at their canonical paths. The new marker
is hidden before restoring old payloads. Inspect the retained files and complete
recovery deliberately, with the prior marker restored last. Do not delete the
recovery directory before accounting for every previous file. A fresh report
root can be used while recovery is pending.

A failed new attempt can leave a consistent **previous** report. The raised
error and old creation timestamp identify that outcome; integrity alone does not
mean the latest attempted evaluation succeeded. Reports written before this
contract remain readable as historical JSON/CSV/images, but the checker cannot
verify their missing hashes. Re-evaluate deliberately into an appropriate report
root to create a verified generation; no historical report is automatically
rewritten or upgraded.

## Bounds and operational limits

Payloads are at most 32 MiB each and 64 MiB in total; new completion markers are
at most 64 KiB. Existing targets must also fit the per-file limit. Budgets bound
accepted report bytes, not inference memory, array scoring, thumbnail encoding
allocations, filesystem buffers or disk space. Those earlier operations can
allocate before the encoded report size is known.

Marker JSON refuses duplicate members at every object level, nonfinite values
(including exponent overflow such as `1e999`), and more than 64 nested containers,
counting the root object. Parser/encoder recursion failures become ordinary input
errors. Publication applies the same rules to encoded metadata before creating
staging or replacing any prior report, so it cannot publish a marker its own
checker would reject for these reasons. Historical files are never repaired.

**Serialize readers and writers.** Multiple flat filenames cannot be swapped in
one filesystem rename: files may temporarily be absent during replacement. The
marker and hashes detect incomplete/mixed sets when checked after the writer
finishes. There is no cross-process locking, concurrent-reader transaction,
filesystem-wide snapshot or power-loss durability guarantee. A killed process
can leave hidden staging/recovery files and no canonical completion marker.

No study measurements, checkpoints, training policy or historical reports are
changed by these checks. See the [design review](DESIGN_ARCHITECTURE_REVIEW_2026-10-31_DETECTOR_REPORTS.md)
for the tested cases and limits.
