# Design and architecture review — the owner's #384

Date: 2026-11-09. Baseline: `d56ce121` (main after #384).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 20:13 UTC firing on 2026-11-09. The 18:13 and 19:12 firings found main unchanged.

#384 changes how `bench_cli fetch` downloads the fiber-skeletons dataset:
- it plans the whole download before transferring anything;
- it picks each cube's highest numeric annotation version;
- it refuses unsafe destinations;
- it adds `--dry-run` and `--refresh`.

## What changed

### Six of #384's guards no test reached (`tests/test_fiber_fetch.py`)

I made 26 mutants of the planner (`dataset_fetch.py`) and the fetch command. #384's tests killed 17. Six of the nine
survivors break something #384's review or usage document states, and each now has a test that passes as merged and
fails with its guard removed:

- **A multi-digit scroll can be requested.** The review says multi-digit scroll identities now match the request
  validator, but no test requested one. With the validator back to one digit, `s12_…` was refused.
- **A bare `<a href>` is not a source.** Without the empty-value check, the planner passed `None` to the filename
  pattern and raised `TypeError`.
- **The 2 MiB listing cap.** The existing oversized listing had no annotation link, so it failed as an empty listing
  whether or not the cap was checked. The new listing has a valid link and is one byte over.
- **An empty download with no `Content-Length` is refused.** The existing empty case also declared 100 bytes, so the
  length check refused it either way.
- **An existing empty file is replaced, not reused.** Only nonempty files are reusable, as the usage document says.
- **A reused file swapped for a symlink after an earlier transfer is refused.**
  - Once transfers have begun, the loop's recheck is the only one a reused file gets.
  - Without it, the swapped link was silently accepted, which #384's review counts as a defect when it happens before
    the run.

The other three survivors need no test:
- `create()`'s own validation repeats the loop's first recheck, with nothing in between;
- the recheck after opening a response is backed by the one before publication, which still refuses;
- the planner reads hrefs only from anchors, and nothing promises that.

## Verified, no change needed

- **#384's counts.** The PR's eight curated modules give 297 at the merge: 303 in the checkout with the six tests
  above. #384's own module holds 23 of them, as it says.
- **Version choice.** The highest numeric version wins, independent of link order. String comparison would pick `v2`
  over `v10`, and #384's test fails with it.
- **Other selection rules.**
  - A tie between different filenames at that version is refused.
  - The `s1a` alias maps to `s1`.
  - Cubes are planned in sorted order.
- **The listing.** It is checked against a supplied `Content-Length`, and a listing with no recognized annotation
  fails before any write.
- **Destinations.** `--dry-run` requests only the listing and creates no directory. `--refresh` replaces each
  selected file and keeps its mode.
- **Transfers.** A short or interrupted transfer leaves the previous file and no temporary.

## Observations for the owner (not changed)

- **Reuse cannot tell versions apart.** A nonempty file is reused whatever annotation version it holds. #384 prints
  that its source and content are unverified, and `--refresh` is the remedy. A re-run after the server publishes a
  newer version keeps the old one unless `--refresh` is given.
- **Publication is per file**, as #384 says. A failure partway through a cube can leave its NML new and its labels
  old.
- **The live preview** (11 cubes, 33 downloads) was not rerun here; this round made no network request to the
  dataset.

## Verification

- **The touched module passes.** `tests/test_fiber_fetch.py` gives 29 passed: 23 of #384's and 6 new. Each new test
  fails with its guard removed.
- **Ruff and mypy.** Ruff 0.9.10 `check` and `format` are clean on the changed test file. Mypy is clean over the whole
  repository: 931 files.
- **The standard suite.** The 192 modules give round #153's 70 failing ids. #384 added one module.
- **The test modules outside the suite.** The 250 modules give 2,366 passed, 82 skipped, 13 failed and 21 errors, as
  in round #157. The failing ids are round #153's 34.
- **The doc audit**, run alone, lists exactly round #157's unresolved references. It checks 2,226 path and 825 commit
  references, against 2,225 and 822 then.

## A note on this round's work

- **The fetch tests' commit message miscounts.** It says #384's tests killed 16 mutants and that three of "the other
  four" are equivalent. The run gave 17 killed and 9 survivors: the six tested above and three that need no test. The
  figures in this record are the run's.
- **#384's selection in a sparse worktree** failed the two checks that scan the whole checkout, because
  `v3_training/` is not checked out there. In the main checkout all 303 pass.
