# Design and architecture review: detector report integrity

Reviewed main `cee9f12d` in an isolated checkout on October 31, 2026 (UTC).
Scope: detector evaluation/measurement report publication, target selection,
fragment-name validation and saved-report inspection.
The final branch integrates main `7d494afc`, including upstream loop/dependency
changes; the scoped CPU environment includes pyasn1 0.6.5 and fpdf2 2.8.8.

## Findings and fixes

1. **A failed write mixed report generations.** A synthetic evaluation wrote a
   new threshold CSV, then a thumbnail failure left the old scorecard and image.
   Both evaluation and batch measurement now stage/read back the entire report
   before changing any canonical file, install a completion marker last, verify
   published bytes and restore prior files on caught publication failures.
2. **A fragment name escaped the report directory.** Passing `../outside` wrote
   the scorecard above the configured directory. Shared filename validation now
   guards evaluation, CLI selections, data loading and direct inference. Report
   path/type/size and checkpoint-alias checks also run before costly inference.
   PR review also reproduced a symlink directory hidden behind a missing parent
   and `..`. Parent paths are now resolved before checking the final directory
   entry, and a failing regression now passes without creating that parent. The
   checker uses that same canonical parent for its completion-marker path.
3. **Duplicate targets silently disappeared.** Two measurement targets with the
   same fragment ID became one dictionary row carrying only the second scroll
   label. Empty, duplicate and malformed plans now fail before model/data work
   or report writes. CLI selection errors use the parser's usage-error path.
4. **Saved files had no consistency check.** Evaluation scorecards now bind CSV
   and thumbnail hashes. Measurement keeps its fragment-keyed JSON schema and
   adds a separate completion manifest binding Markdown/JSON, counts and
   `COMPLETE`, `PARTIAL` or `FAILED` status. Both record UTC creation time. A new
   standard-library-only checker validates observed bytes and status fields;
   it refuses legacy reports without checksums rather than upgrading them.
5. **Failure recovery needed explicit evidence.** Tests inject each publication
   rename failure with full, partial and absent prior sets, an interruption after
   marker installation, staged/installed byte changes, and failure while rolling
   back. Previous bytes and modes are restored, or private recovery files are
   retained with an actionable path. Review additionally tightened checks after
   installing the marker so a late output rewrite is detected and rolled back.

The standard-library `core/report_artifacts.py` owns path preflight, accepted byte
limits, report completion schema, publication/rollback and verification.
`detector/eval.py` encodes its CSV/image and passes its existing scorecard fields;
`detector/measure.py` retains scoring/error handling and prepares its report set.
The lightweight `scripts/check_detector_report.py` imports no ML/image libraries.
Shared `prediction_stem`, path-collision checks and file-mode helpers are reused.
Scientific metric formulas, thresholds, model predictions, training policy and
checkpoint selection are unchanged. See [usage and recovery](DETECTOR_REPORTS.md).

## Verification and limits

Final curated selection after integrating main and fixing PR review findings:
**243 passed in 24.39s, no skips**, including **63 new report contract cases**.
Scope: 7/168 curated modules covering detector contracts,
prediction/conversion artifacts, metrics and validation runner/coverage checks.
The final selection covers the tightened completion readback and output preflight.

Additional integration: **30 passed in 282.35s**, across existing detector eval,
measurement, CLI, data, inference and both training smoke modules. Those checks
use synthetic fragments and real CPU models; the two short training smokes write
temporary checkpoints. The model tests started before the final report-only
readback/preflight refinements; the final curated selection checks those changes.
Warnings cover existing augmentation defaults/deprecations and Lightning's
logging, worker, pin-memory and checkpoint-directory notices.

The required smoke check after integrating main passed **8/11, 3 skipped, 0 failed in 10.0s**. Skips were
two missing local training datasets and the unavailable BGv2 augmentation entry
point. Host font-cache warnings did not fail checks. Ruff lint/format passed for
nine changed Python files; Mypy passed for eight implementation/test files. The
new checker also ran from another working directory without importing NumPy,
Torch, OpenCV or Pillow. Local documentation links and whitespace were checked.

No live study measurements, data or research checkout were used or updated;
there were no GPU jobs or checkpoint promotions. The required smoke uses the
tracked model in the isolated checkout; fixture training uses temporary data.
The full repository suite, real large reports, inference quality, prize-relevant
research gains, peak memory/throughput, concurrency and power-loss durability were
not tested. Byte limits apply to accepted report bytes, not earlier scoring/image
encoding allocations. Disk space is not reserved.

Multiple flat filenames require several renames, so callers must serialize
readers and writers. During publication the old marker is absent; caught failures
restore it after restoring old payloads. A hard kill can leave recovery data and
an unavailable canonical report. There is no cross-process locking or global
filesystem snapshot. Hashes bind observed outputs and do not authenticate input
datasets, actual model weights or scientific validity. A consistent prior report
can remain after a failed newer attempt; creation time and the caller's error
must be considered when interpreting recency.
