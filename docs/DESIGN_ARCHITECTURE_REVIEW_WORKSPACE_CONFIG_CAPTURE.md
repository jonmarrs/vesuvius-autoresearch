# Design and architecture review — workspace config capture

Baseline: `07b5dd6c`. Scope: the read-only workspace diagnostic, its configuration
identity, and the shared UTF-8 source reader used by reports and command planners.

## Findings and changes

1. **The setup diagnostic could block or read an unbounded config.** It called
   `Path.read_text()` without a byte budget or regular-file check. A FIFO config
   waited indefinitely for a writer. It now uses the existing `Snapshot` reader,
   with a 1 MiB default and an explicit `--max-config-bytes` limit up to 16 MiB.
   Invalid budgets fail before process/config reads.
2. **The shared reader's path check did not protect its actual open.** A regular
   file could be replaced by a FIFO after `is_file()`, causing the reader to
   wait. POSIX opens are now nonblocking, and the opened descriptor must describe
   a regular file before bytes are read. Its size is checked before reading;
   the bounded read and post-read length check still catch growth. Nonpositive
   or noninteger limits fail before path access, preventing negative read sizes
   from turning a bounded capture into an unbounded one.
3. **Some diagnostic errors escaped instead of producing a report.** A looping
   repository path raised during normalization, and deeply nested config JSON
   raised a recursion error. These now become structured `blocked` checks.
4. **The inspected config had no recorded identity.** JSON output now includes
   `config_byte_limit` and, after a UTF-8 capture, `config_source` with resolved
   path, byte count and SHA-256. Human output prints the fingerprint. The parser
   and fingerprint consume the same bytes, even if another writer replaces the
   file during parsing. The hash identifies raw bytes before normalization.

The shared reader keeps its existing dataclass, text, provenance, verify and
copy APIs. File symlinks still resolve to their regular targets. Workspace data
paths remain relative to the selected repository. The diagnostic deliberately
retains the config loader's rejection of a UTF-8 BOM; source planners retain
their existing BOM-aware text decoding.

The command remains standard-library-only and read-only. It does not inspect
checkpoint contents, arrays, labels or study measurements, initialize a GPU,
reserve resources or launch research work. Training readiness remains unassessed.

## Verification

- Before implementation, the two focused modules produced **16 failed, 17
  passed**, including five-second timeouts on both FIFO reproductions. Two
  additional growth/symlink cases were added afterward; there are **20 new
  cases** in the final modules.
- Initial compatibility selection: **388 passed** across 9/172 curated modules: workspace status,
  source capture, validation runner, patch datasets, report time/selection,
  experiment reports, ranked inference planning, label edits and SOTA downloads.
  This exercises existing callers of the changed shared reader.
- After incorporating current main at `da4d1e82`, the final expanded selection
  passed **464 tests** across 10/173 modules. It also includes the upstream
  streaming-storage guards, and verifies that both registry additions coexist.
- CPU smoke: **8 passed, 3 skipped, 0 failed**. The skips are two absent local
  data inputs and the unavailable legacy augmentation entry point.
- Ruff check/format and scoped Mypy pass on the five changed Python files.
- The new source-reader module is registered in the curated runner. The
  existing status subprocess test still forbids ML imports and checks unchanged
  file contents/mtimes.

Validation used Python 3.10.21 and Torch 2.9.1 on CPU. The initial caller suite
could not collect PDF-report tests until fpdf2 was installed in the disposable
environment; the final selected run passed. Exact commands and captured output
are in the PR test report.

## Limits

This is selected validation, not the full suite or a repository-wide document
audit. FIFO behavior was tested on POSIX; Windows named-pipe behavior was not.
The byte budget bounds captured config data, not total memory or filesystem
wall-clock time. The fingerprint does not certify normalized settings, model
compatibility or later file contents, and the diagnostic is not a global
filesystem snapshot. No live study, training settings or historical measurement
was changed. See the [workspace guide](WORKSPACE_STATUS.md) for usage and scope.
