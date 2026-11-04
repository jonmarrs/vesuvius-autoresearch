# Design and architecture review — S3 acquisition

Date: November 4, 2026 (Pacific). Baseline: `9f538308`.

This review covers the raw-segment downloader, its shared S3 transport, teacher
cache callers, and conversion handoff. The changes address acquisition failures;
they do not change model inputs, training, study decisions or research results.

## Findings and fixes

1. **SDK failures bypassed the CLI error boundary.** Connection failures from
   botocore and interrupted HTTP bodies from aiohttp are not necessarily
   `OSError` or `ValueError`. Both acquisition CLIs could raise a traceback even
   though their staged publisher correctly discarded incomplete output.
   The shared transport now converts known SDK/HTTP exceptions at listing and
   range-read boundaries into `RemoteAccessError`, a `ValueError` subtype.
   Diagnostics identify the operation, source key and exception class, with
   recovery advice. Opaque SDK endpoint/debug text stays in the chained cause
   for library callers rather than the CLI message. Unexpected programming
   errors and cancellation are not broadly caught.
2. **Folder markers were rejected as objects outside the listing.** A real
   `ListObjectsV2` result can include a zero-byte object naming the listed
   prefix with a trailing slash. The path normalization removed that slash,
   making the object appear to belong to its parent. The listing now keeps
   this marker under its empty relative name. It is excluded from payloads and
   teacher candidates while still counting toward entry budgets and ignored
   counts. Nonempty or malformed markers, duplicates and unrelated paths
   remain errors.

The transport remains shared by raw and teacher downloads. SDK imports stay
lazy, so help, local backends and cache reuse do not acquire an SDK dependency.
Range/ETag validation and completion-last publication retain their existing
contracts. The commands add no application-level retries or partial resume.

The SDK tests also stopped explicitly closing sessions already owned by s3fs's
registered finalizer. Double closing emitted unraisable aiobotocore errors at
test teardown. Response-body closure is still asserted directly.

## Verification

The first 12 regression cases produced **10 failed, 2 passed** on the baseline:
valid markers failed the prefix guard, and SDK failures escaped both CLIs.
A thirteenth case additionally checks teacher selection when the prefix itself
ends in `.tif`.

- **255 passed** across six curated modules: SOTA download, teacher contracts,
  conversion contracts, converter, distillation preparation and validation runner.
  The new tests exercise real s3fs/aiobotocore with stubbed SDK responses and
  injected SDK/HTTP exceptions. They cover initial listing, request, fragmented
  body and final-recheck failures, body closure, absent final output/staging,
  marker accounting and bounded CLI diagnostics.
- CPU smoke: **8 passed, 3 skipped, 0 failed**. The skips are two unavailable
  local data inputs and the legacy augmentation entry point.
- Ruff check/format pass on the three changed Python files. Mypy passes on
  those files with `--follow-imports=silent --explicit-package-bases`.

Validation used Python 3.10.21; the transport packages match the lockfile:
s3fs/fsspec 2026.9.0, aiobotocore 3.0.0, botocore 1.42.5, aiohttp 3.10.11.
The smoke used Torch 2.9.1 on CPU. Missing detector dependencies were installed
in the disposable validation environment before the final passing run.

## Limits

No live bucket outage, real scroll transfer, large-download benchmark, GPU
experiment or full repository suite was run. SDK stubs do not establish real
network throughput or reliability. A killed process can still leave hidden
staging; readers and writers must remain serialized. Existing completed caches
remain immutable. See the [raw downloader](SOTA_SEGMENT_DOWNLOADS.md) and
[teacher cache](SOTA_TEACHER_CACHE.md) guides for recovery and input limits.
