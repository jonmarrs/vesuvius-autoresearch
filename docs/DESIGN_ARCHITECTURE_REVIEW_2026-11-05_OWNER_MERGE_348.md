# Design and architecture review — the owner's #348

Date: 2026-11-05. Baseline: `da4d1e82` (main after #348).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 15:13 UTC firing. Main had not moved from `07b5dd6c` in the seven firings before it.
- **#348 refuses aliased backing files before streaming fiber filtering.**
  - `streaming.filter_into` already refused input and output that share memory. Two separate maps of one file pass
    that test, so writing the response could change CT blocks still to be read.
  - `_mapped_storage` now walks an array's `.base` chain (ndarray views, memoryviews and NumPy's `DummyArray`) to
    the `mmap` and the memmap's filename.
  - `_validate_backing_files` then requires two mapped arrays to have accessible, identifiable and different files
    by `os.path.samefile`. The comparison is conservative: disjoint regions and copy-on-write maps of one file are
    refused too.
  - Its 76 tests are in the suite.

This round changes no library code. It adds one test.

## What changed

- **`_mapped_storage`'s cycle guard had no test** (`tests/test_fiber_streaming_storage.py`).
  - Of eight mutants of the new checks, seven fail #348's tests. Removing the guard did not.
  - NumPy never builds a cyclic base chain, so the guard is defensive. Without it, though, a cyclic chain would loop
    forever.
  - The new test passes an object whose `.base` is itself. Its property raises after 100 hops, so a missing guard
    fails the test instead of hanging it.
  - It passes as merged and fails with the guard removed.

## Verified, no change needed

- **The other seven mutants fail #348's tests:**
  - the call in `filter_into` removed;
  - the memoryview hop removed;
  - the memmap filename not recorded;
  - the check run when only one side is mapped;
  - an unidentifiable path accepted;
  - an inaccessible path read as a different file;
  - `samefile` replaced by path-string equality, which a symlink or hard link would pass.
- **A copy is not refused.** `memmap.copy()` has no `.base` and no `mmap`, so `_mapped_storage` reports it as unmapped
  and an in-memory copy stays valid output, as the doc says.
- **The CLI already writes elsewhere.** `fibers/cli.py` calls `filter_artifacts.validate_paths` and writes the
  response into `filter_artifacts.staged_file(args.output)`, a separate temporary file, before publishing. So the CLI
  never passes `filter_into` two maps of one file.

## Observations for the owner (not changed)

- **The check compares paths at one moment.** A path replaced between the check and the two filtering passes would
  not be noticed. #348's doc and docstring both say so: keep backing paths stable, with no concurrent writers.

## Verification

- **The touched module**, `test_fiber_streaming_storage`, gives 77 passed with the added test.
- **Ruff and mypy.**
- **The standard suite.**
- **The test modules outside the suite.**
- **The doc audit**, run alone.
