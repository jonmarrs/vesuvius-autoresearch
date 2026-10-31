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

Check a saved generation without importing Torch, NumPy or image libraries:

```bash
python scripts/check_detector_report.py \
  reports/detector/PHercParis2Fr143_scorecard.json
```

The script also works from another working directory using its absolute path.
It prints JSON with integrity, completion status, creation time and artifact
names. It exits 0 for a consistent complete report, 1 for invalid/missing files
or an incomplete measurement, and 2 for usage errors. It reads files only; it does
not run inference or repair a report. A checksum check binds the observed output
bytes, not the source dataset, actual model weights or scientific validity. It
does not recompute metrics or establish which attempted run was most recent.

## Cross-scroll measurements

`measure` keeps `cross_scroll_measurement.md` and
`cross_scroll_measurement.json`, including the JSON's existing fragment-keyed
schema. It additionally publishes `cross_scroll_measurement_manifest.json` as
the completion marker, with checkpoint display text, both output hashes,
creation time and target/success/failure counts:

```bash
python scripts/check_detector_report.py \
  reports/detector/cross_scroll_measurement_manifest.json
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
report directory and output/checkpoint aliases are refused. Output path/type/size
checks run before expensive CLI evaluation or measurement inference. Names stay
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

**Serialize readers and writers.** Multiple flat filenames cannot be swapped in
one filesystem rename: files may temporarily be absent during replacement. The
marker and hashes detect incomplete/mixed sets when checked after the writer
finishes. There is no cross-process locking, concurrent-reader transaction,
filesystem-wide snapshot or power-loss durability guarantee. A killed process
can leave hidden staging/recovery files and no canonical completion marker.

No study measurements, checkpoints, training policy or historical reports are
changed by these checks. See the [design review](DESIGN_ARCHITECTURE_REVIEW_2026-10-31_DETECTOR_REPORTS.md)
for the tested cases and limits.
