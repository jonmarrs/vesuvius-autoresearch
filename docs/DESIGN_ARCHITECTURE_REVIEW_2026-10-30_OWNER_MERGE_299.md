# Design and architecture review — the owner's #299 (fiber label generation)

Date: 2026-10-30. Baseline: `4d35d5a2` (main after #299).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 06:17–10:15 UTC firings; main did not move after #299. One read-only review ran beside
mine, and I checked each of its findings before acting on it.
- **#299** rewrites `scripts/labeling/generate_fiber_labels.py` and adds `scripts/labeling/fiber_candidates.py`.
  - Candidate mode reads exact CT windows and runs the repository's vendored vesselness filter on them. It
    publishes a new run directory only when every candidate and every recheck succeeds.
  - Skeleton mode checks bounds in XYZ before converting, keeps an empty mask empty, and queues one batch of
    trees at a time.

## What changed

- **#299 broke the live-document audit** (`tests/test_audit_doc_references.py`).
  - The usage guide cites the generator's new default run directory, `reports/fiber_labels_run`. The directory
    must not exist before a run, so the audit lists it as a stale path in a live document.
    `test_live_documents_stay_clean` therefore fails on a full checkout.
  - Neither of #299's runs could show this. The test is outside the standard suite, and in this checkout it
    already fails on the 20 Villa and model paths that are absent here.
  - The path is now exempt, with a comment, as REPRODUCE.md's default detector `data_root` already is. Without
    the entry the test lists it beside those 20; with it, only the 20 remain.
- **A killed run could leave a staged summary saying `"complete": true`** (`scripts/labeling/fiber_candidates.py`).
  - The summary was written before the TSV, filter and CT rechecks. A process killed during them (by SIGKILL,
    or by the default SIGTERM) runs no cleanup.
  - It leaves a hidden staging directory holding both TIFFs and a summary that claims completion and points
    at a run directory that was never published. The review reproduced this with SIGTERM.
  - The summary is now written after every recheck. The test records, at each source check, whether a summary
    is staged. It fails on #299's code.
- **A TSV from a pipe failed with a misleading error** (`fiber_candidates.py`).
  - `--candidates <(...)` resolved `/dev/fd/N` to a path that does not exist and failed with
    `[Errno 2] No such file or directory: '/proc/…/fd/pipe:[…]'`. The parent accepted a pipe.
  - #299 hashes the TSV again before publishing, so a pipe cannot work, but the error did not say why.
  - The TSV is now read through `Snapshot` (`scripts/text_snapshot.py`), the bounded regular-file reader that
    the patch and experiment tools share. It replaces #299's own size check, bounded read and decode.
  - A pipe or a missing file is refused with "input must be a regular file". The test fails on #299's code.
- **The guide** (`docs/FIBER_LABEL_GENERATION.md`) now says:
  - the TSV must be a regular file;
  - the duplicate check compares resolved paths, so a group and its level-0 array (`ct.zarr` and `ct.zarr/0`)
    pass as two sources;
  - the summary is written last;
  - a killed run leaves a hidden staging directory, to be removed by hand.
- **A stale comment.** `scripts/refine_labels_villa.py` said its Villa path injection mirrors
  `generate_fiber_labels.py`, which no longer injects one.

## Verified, no change needed

- **#299's tests and record.**
  - Its integration command (five test files) gives 214 passed, as recorded, and its 45 new cases pass.
  - The six measured source hashes in the public-CT smoke record are the hashes of the merged files. This
    round's change to `fiber_candidates.py` moves that file off its recorded hash.
  - On the parent, `--help` fails with `No module named 'tools'`, and an empty skeleton mask expands into 9
    corner voxels, as the record says.
- **The filter swap.** #299 replaced Villa's `tools.detect_vesselness` with the vendored
  `vesuvius_autoresearch.fibers` filter. The two agree within float tolerance:
  - on normalized uint8 CT, smoothed CT and an expanded skeleton mask, they differ by at most 2e-10 here;
  - the review found at most 1.5e-8 on its crops;
  - labels are identical at threshold 0.5 here, and at 0.05 and 0.1 in the review.
- **Geometry** (the review).
  - A window ending exactly at the volume's far corner succeeds; one voxel further fails with exit 1.
  - Axes are ZYX from the TSV through the read, the TIFFs, the metadata and the final content hash. The
    in-memory digest and the recheck's digest agree.
  - TIFFs of 9 shapes, with axes of 3 or 4 voxels, read back as ZYX and never as RGB.
- **Publication** (the review).
  - An existing output or symlink is refused and left untouched.
  - Failures leave neither an output nor a staging directory.
  - Dry runs write nothing and probe no CUDA.
  - Exit codes are 0, 1 and 2, as the guide says.
- **Skeleton mode** (the review).
  - The 500-cube default is refused at the default budget and planned with `--max-voxels 125000000`, as
    documented.
  - A non-finite skeleton coordinate hung the parent past 20 s; it now raises.
- **Callers.**
  - No script calls the generator or the functions #299 removed.
  - `scripts/cross_scroll_validation.py` reads the new `candidate.json` and label TIFF.
  - All 110 rows of `reports/scroll23_ranked_candidates.tsv` plan cleanly.

## Observations for the owner (not changed)

- **The duplicate-window check compares paths.**
  - `ct.zarr` and `ct.zarr/0` select the same array and pass as two candidates. The review produced two
    identical crops that differ only in `source_path`.
  - The committed TSV always uses the level-0 form. The guide now says this; keying the check on the opened
    array would need every CT opened before the check.
- **Untested guards.** With each guard removed in turn, the 45 new tests still pass for:
  - the TIFF readback (each of it and the finite check hides the other);
  - the [0, 1] range check;
  - the preflight-snapshot comparison;
  - the filter-source recheck;
  - "output appeared during processing", the only thing that stops the shared publisher from moving a
    concurrently created output aside and deleting it;
  - the TSV limits (top-n, size, headers, ragged rows, cohort identifiers);
  - the CT dtype check, without which complex CT would silently lose its imaginary part;
  - the skeleton coordinate, filename and size checks, and the skeleton readback.
- **Tests that pass for another reason.**
  - The `review_score` NaN case fails later, when the JSON is written, not at its own guard.
  - Three of the four overlap cases are refused as existing outputs before the overlap check.
  - The `width` case already passes on the parent.
  - The `src` bootstrap is unchecked because the virtual environment's editable install already puts this
    checkout's `src` on the path.
- **The smoke record cannot be repeated from what it records.**
  - It names a TIFF URL and hash, but the CLI reads Zarr, and the conversion (chunks, attributes) is not
    recorded.
  - Neither the TSV, its hash nor the CT content digest is recorded, and no committed script writes the record.
  - The host is not reachable from here, so the TIFF hashes and `labeled_voxels: 0` are unchecked.
- **Baseline count.** #299's record gives its baseline run as "28 failures". The merged test file gives 43
  failed and 2 passed on the parent.
- **The XYZ/ZYX bounds fix is not reachable from the CLI.** Skeleton cubes are cubic, so the parent's swapped
  comparison gave the same answer. The negative-fraction fix is reachable: interpolated points on edges that
  cross a lower face.

## Verification

- **The changed area.** `tests/test_fiber_label_generation.py` gives 47 passed. Both new tests fail on #299's
  `fiber_candidates.py`.
- **#299's integration command** gives 216 passed (its 214 and this round's 2).
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the changed Python files. Mypy is clean over
  the whole repository (845 files).
- **The standard suite** gives the same 43 failures as before, from `s3fs`, `numba`, `jsonschema` and Villa
  files absent here. The same 2 modules cannot be collected (`tensorstore`, `s3fs`).
- **The 230 test modules outside the standard suite** give 2,096 passed, 80 skipped, 13 failed and 21 collection
  errors: the same failures as round #134's run. `test_live_documents_stay_clean` lists the same 20 Villa and
  model paths as before.
- **The doc audit's** only new unresolved path is `reports/fiber_labels_run`: the default exempted above, also
  cited in #299's record and this one.
