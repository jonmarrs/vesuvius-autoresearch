# Design and architecture review — detector report markers

Date: November 4, 2026 (Pacific). Baseline: `c5ab81b6`.

Scope: report publication, saved-report verification, the standalone checker,
and their detector evaluation/measurement callers. No study results, model
weights, scoring formulas or training settings are changed.

## Findings and changes

1. **A small marker could crash the checker.** JSON containing 5,000 nested
   arrays fits the 64 KiB marker budget but raises `RecursionError`, bypassing
   the CLI's ordinary input-error handling. Parsed markers now allow at most
   64 nested containers, including the root. Decoder and encoder recursion
   errors become `ValueError`; failed checks remain read-only.
2. **Ambiguous or overflowing JSON was accepted.** Duplicate members were
   resolved by silently keeping the last value. `parse_constant` rejected
   literal `NaN`/`Infinity` but did not catch `1e999`, which decodes to infinity.
   A shared decoder now rejects duplicate members at every object level and
   nonfinite floating-point values, including exponent overflow. Publication
   validates its encoded metadata with that decoder before creating staging or
   touching old files. This also catches Python dictionary keys that collide
   after JSON string conversion.
3. **Previously recorded marker identity could not be checked.** Payload hashes
   alone cannot detect an edit confined to scorecard metrics, checkpoint display
   text or creation time. `check_report(..., expected_sha256=...)` and the CLI's
   `--expected-sha256` now optionally compare a separately recorded SHA-256 with
   the same captured bytes that are parsed. The expected value is validated
   before file reads. Matching it still requires all existing status, schema,
   payload and marker-readback checks. Uppercase hashes are accepted.

The existing on-disk contract and unpinned return values remain compatible for
ordinary valid reports. Pinned CLI results additionally report `marker_sha256`.
A partial measurement retains its nonzero exit even when its pin matches.
The checker continues to import only the standard library.

The guide now starts from a newly produced report rather than the repository's
unverifiable historical scorecard. It explains when to record a hash, where to
keep it and what it does not prove. The README links that workflow without an
unquoted angle-bracket filename that a shell could interpret as redirection.

## Verification

Before implementation, a 20-case selection produced **18 failed, 2 passed**:
the new pin API was absent, duplicate/overflowing JSON was accepted, and deep
JSON escaped as recursion errors. One additional readback-race case was added
after that baseline run. There are **20 new cases** in the final module.

- **193 passed** across five curated modules: detector contracts, report
  artifacts, prediction artifacts, metrics and file modes. Tests include real
  CPU checkpoint/prediction integration, publication rollback and the new pin,
  parser, byte/depth-boundary and read-only failure cases.
- CPU smoke: **8 passed, 3 skipped, 0 failed**. Skips are two absent local data
  inputs and the unavailable legacy augmentation entry point.
- Changed-file Ruff check/format and scoped Mypy pass.
- The checker runs from another working directory without NumPy, Torch, OpenCV
  or Pillow imports, both with and without a pin.

Validation used Python 3.10.21 and Torch 2.9.1 on CPU. The commands and captured
summaries are in the PR test report. This is selected validation, not the full
repository suite or a repository-wide reference audit.

## Limits

An unpinned check still cannot establish earlier marker identity. Record the
expected hash independently when the report is trusted; deriving a new pin from
the file under inspection would not detect earlier edits. A matching hash binds
exact bytes, including whitespace. It does not authenticate authorship or
validate model weights, source data or scientific correctness.

Readers and writers must remain serialized. Pinning adds no lock, concurrent
snapshot, power-loss durability or automatic migration. No historical report is
rewritten. See the [report guide](DETECTOR_REPORTS.md) for usage and recovery.
