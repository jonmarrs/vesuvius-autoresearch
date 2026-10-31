# Design and architecture review: raw SOTA downloads

Reviewed main `307a57d3` in an isolated checkout on October 31, 2026 (Pacific
time). Scope: the raw-segment downloader, its converter handoff and transfer
integrity. The existing surface/teacher algorithms and Villa pin are unchanged.

## Findings and fixes

1. **A failed transfer mixed generations.** The downloader wrote into existing
   outputs. A fresh in-memory bucket reproduction failed while fetching the label
   and left `new-layer` beside `old-label`. It now refuses existing destinations
   before remote access and publishes a staged directory only after all checks.
2. **Selection and costs were implicit.** `layers/` was recursively copied without
   file/byte limits, including any nested caches or volume stores. The planner now
   enumerates only direct objects, checks an unambiguous converter-compatible
   label/mask layout, caps files/bytes and offers an explicit centered-layer
   selection. Dry runs read metadata only and create no output.
3. **Remote identity and local integrity were unrecorded.** The new helper makes
   conditional, bounded S3 range requests, validates headers and body lengths,
   rechecks remote selection/identities and verifies all local hashes and paths.
   A completion record and tool-source captures support later inspection.
4. **SDK-level conditions needed explicit verification.** Supplying a known size
   to `s3fs.open` bypasses its automatic ETag condition; arbitrary open kwargs do
   not reliably become GetObject read conditions. The implementation uses the
   public `call_s3` API with explicit `Range` and `IfMatch`. Actual S3/aiobotocore
   stub tests validate those service parameters, fragmented bodies, invalid
   identity/range headers, short/long bodies and a 412 precondition failure.
5. **A downloaded directory was not evidence of conversion readiness.** The
   manifest explicitly leaves image geometry, label quality and training readiness
   false. Missing masks stay absent, and modern OME-Zarr-only layouts are not
   guessed or recursively downloaded as substitutes.

The shared `download_artifacts.py` owns source-key validation, remote plans,
range/body checks and completion checks. The CLI/API adapter keeps the existing
two positional arguments and `fetch_segment` return value, with new keyword
budgets and planning support. The existing converter ignores the added manifest
and tool-source directory. It does not implicitly revalidate the raw manifest
after later user edits; keep completed raw artifacts immutable.

## Verification and limits

Final integration: **138 passed in 19.50 seconds, no skips**, on Python 3.10.21
with CUDA hidden. Scope: `test_sota_download`, `test_sota_convert`,
`test_sota_qualitative`, `test_sota_distill_prep`,
`test_validation_suite_covers_the_loop` and `test_validation_runner` under `tests/`.
The required smoke check reported **8/11 passed, 3 skipped, 0 failed in 9.1s**;
skips were two absent local training datasets and the missing BGv2 augmentation
entry point. Ruff check/format, Mypy on five Python files and whitespace checks
passed. Tests cover metadata-only
planning, strict prefixes, ambiguous layouts, selection equivalence through the
actual converter, payload budgets, partial failures, remote/local mutation,
unexpected staged files, completion ordering, no-overwrite behavior, CLI output
and the actual SDK request boundary. SDK tests use service stubs rather than
live object transfers.

A live public metadata smoke additionally read a **3,450-byte `.zattrs` file**
through the conditional range reader; no image or CT chunks were read. The source
was under the public Scroll-1 segment's surface-volume metadata, with SHA-256
`1451b48a7263d5b8e84dd48a26cc9cf0093ff559ebe67e57121bc7715efba487`.
The [durable smoke record](../reports/evidence/sota_download_metadata_smoke_2026-10-31.json)
records its URI, identity and runtime versions. This validates transport on one
metadata object, not complete legacy-segment
availability, annotation quality or scientific release identity.

No live research checkout, study measurements or GPU jobs were used. Integration
inputs are synthetic. The required smoke check uses the tracked model in the
isolated checkout. No full-repository, large-download, speed, memory-peak,
concurrent-writer or power-loss guarantee is claimed. SDK listing buffers are
outside the accepted metadata cap; disk space is not reserved. See
[usage and migration](SOTA_SEGMENT_DOWNLOADS.md) for the exact limits.
