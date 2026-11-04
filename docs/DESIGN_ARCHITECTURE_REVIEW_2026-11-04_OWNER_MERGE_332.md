# Design and architecture review — the owner's #332

Date: 2026-11-04. Baseline: `c5ab81b6` (main after #332).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 23:12 UTC firing; main had not moved since #329 at the firings before it.
- **#332** turns S3 SDK and HTTP failures into bounded CLI errors and accepts S3 folder markers in listings. It
  takes up two observations from the review of #314 (`DESIGN_ARCHITECTURE_REVIEW_2026-11-01_OWNER_MERGES_305_318.md`):
  SDK transport errors escaped as tracebacks, and a zero-byte `prefix/` marker was refused as outside its prefix.

## What changed

- **The SDK error mapping made a suite test need botocore** (`repro/sota_data/download_artifacts.py`).
  - `_remote_errors` imported `botocore` and `aiohttp` for any filesystem that declares an S3 protocol, before the
    listing.
  - `test_invalid_listing_metadata_cannot_form_a_plan[missing_etag_s3]`, in the standard suite, declares S3 on a
    memory filesystem. Here, with `aiohttp` but no `botocore`, it stopped with `ModuleNotFoundError` instead of the
    downloader's missing-ETag refusal, and it joined the suite's failures.
    - #332's record says local backends need no SDK; this test double now did.
  - The mapping now imports only the classes that exist. s3fs always brings both, so a real S3 transfer maps the same
    errors.
  - The new test blocks both packages; it fails on #332's code even with the SDK installed.
- **The teacher CLI still raised a traceback without the SDK** (`repro/sota_data/teacher_cache.py`).
  - Without `s3fs`, `fetch.py` prints `Download failed: No module named 's3fs'` and exits 1. `teacher_cache.py`
    caught only `OSError` and `ValueError`, so the same `ImportError` escaped as a traceback.
  - It now reports `teacher cache failed: No module named 's3fs'` and exits 1, as the raw downloader does. The test
    fails on #332's code.
- **Two folder-marker guards no test reached** (`tests/test_sota_download.py`).
  - A marker must be a file named with the listing's own path plus the trailing slash. With either the name check
    or the file-type check removed, all 136 tests of the two acquisition modules passed.
  - The new test lists a zero-byte entry naming the listing without the slash, and one typed as a directory. Both
    must stay "outside its direct prefix". Each case fails with its guard removed; both pass on #332's parent too,
    which refused every such entry.

## Verified, no change needed

- **The error boundary.**
  - Every remote call in the two acquisition paths goes through `_listing` (list and its final recheck) or
    `_read_range` (each conditional `GetObject` and its body read), and both are wrapped.
  - `RemoteAccessError` is a `ValueError`, which both CLIs map to exit 1. The message names the operation, the
    `s3://` key and the exception class only.
  - SDK imports stay inside the wrapper and only for an S3 filesystem, so local backends need no SDK.
- **#332's tests** run here with the locked transport packages (s3fs and fsspec 2026.9.0, aiobotocore 3.0.0,
  botocore 1.42.5, aiohttp 3.10.11), installed outside the repository.
  - The two acquisition modules give 136 passed, also with unraisable-exception warnings made errors. That covers
    the fixture's dropped `close_session`.
  - On #332's parent, the 13 new cases give 11 failed and 2 passed. That is the record's 12 regression cases
    (10 failed, 2 passed) plus the teacher case, which fails too.
- **Each guard is reached.** With the marker's zero size, its `int` size type or its empty relative name removed, a
  test fails; so does catching no aiohttp error, or printing the exception's text instead of its class.
- **The guides** state the marker accounting and the diagnostics as the code implements them.

## Observations for the owner (not changed)

- **The botocore `ClientError` arm cannot be reached through s3fs.** s3fs translates `ClientError` into `OSError`
  subclasses before it returns, which is why the 412 test still expects `OSError`. Removing the arm passes every
  test. Those translated errors keep the earlier `OSError` path and s3fs's message, not the new diagnostic.
- **The doc audit can misreport under load.** A timed-out `git merge-base` reads as "this repo, not on main"
  (above). This predates #332.
- **The new SDK cases fail in this environment's standard suite.** It has no `s3fs`, so the 11 new cases that use
  the real SDK join the 14 earlier ones.

## Verification

- **The changed modules:**
  - With the locked SDK packages, the two acquisition modules give 140 passed. That includes running with
    unraisable-exception warnings made errors.
  - Of the six modules #332's record names, the five other than the validation runner give 229 passed. That run
    preceded the SDK-import fix and its test.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the four changed Python files. Mypy is clean over
  the whole repository (880 files).
- **The standard suite** gives round #142's 59 failures, plus #332's 11 new SDK cases, which stop at `import s3fs`:
  - the 43 standing failures;
  - the 14 earlier SDK cases that need `s3fs`;
  - the 2 modules that cannot be collected.
  - `missing_etag_s3` passes again; before the SDK-import fix it failed too.
- **The 237 test modules outside the suite** give 2,231 passed, 80 skipped, 13 failed and 21 collection errors: the
  same failures as round #142.
- **The doc audit** finds no new unresolved reference.
  - A first run beside the test runs listed `17739f03` in `reports/SPIRAL_FINDINGS_SUMMARY.md` as off main.
  - It is an ancestor of main. `_is_ancestor` reads any failure, including its 30 s timeout under load, as "not an
    ancestor". The rerun alone is clean.
