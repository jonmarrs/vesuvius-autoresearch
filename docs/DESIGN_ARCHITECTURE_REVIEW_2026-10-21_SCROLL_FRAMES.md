# Design and architecture review — the scroll-frames tool

Date: 2026-10-21. Baseline: `c2f53c18` (main after #171).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `tools/scroll_frames/`, which no review had read. `scrollframes list <scroll>/<segment>` lists a segment's
`.tifxyz` meshes with each one's scan and voxel size, and flags a collision. A collision is meshes whose metadata
declares the same `scale` while their voxel sizes differ. It exits 1 on a collision, so a pipeline can gate on it.

The directory is a `git subtree` of the public `jonmarrs/scroll-frames` repository (`tools/EXTRACTION.md`). A change
here reaches that repository only when the owner runs the subtree push.

Main has not moved since #171. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches. This round covers the 09:13 and 10:14 UTC firings.

## What changed

- **A failure exited 1, which means a collision.**
  - A segment given without its scroll raised `SystemExit` with a message, which exits 1.
  - So did any uncaught error:
    - from the lookup: no `s3fs`, no network, or no such segment;
    - from a malformed `meta.json`: a scalar or non-numeric `scale`, a `grid` that is not two numbers, or a meta
      that is not an object;
    - from the report, which indexed an empty list when no scale had been read (below).
  - A script told by the README to gate on the exit status could not tell "these frames collide" from "nothing was
    checked".
  - **Change:**
    - a malformed segment is an argparse usage error, which exits 2;
    - a failed lookup prints its reason, with the exception's type, to stderr and exits 2;
    - only a missing `s3fs` gets the install hint (`pip install s3fs`). Another import error, such as a broken
      `botocore`, is reported as it is;
    - a malformed `scale` or `grid`, or a meta that is not an object, is left out as if absent, as a malformed
      `bbox` already was. So the report uses the filenames and whatever metadata is sound.

    A failure still exits non-zero, so a caller that gates on any non-zero status still stops. The README states the
    three exit codes.
- **The text report crashed, or said "all", when scales were missing.**
  - `_fetch` skips any `meta.json` it cannot read, and a mesh's meta may have no `scale`.
  - With no scale read, `collision()` still reports a collision: the filenames alone show the spread, as the tool
    intends. `render()` then named "all N meshes declare scale" from the first declared scale, and raised an
    `IndexError` on the empty list.
  - With some scales read, it said "all N meshes declare scale" when only those had.
  - **Change:**
    - with no scale, the report says the voxel sizes differ and no `meta.json` gave a scale;
    - with some, it says how many meshes declare one (singular or plural), and for how many none was read;
    - `collision()` reports the count as `n_declaring_scale`, which `--json` carries too. It now gives that key and
      `n_frames` for fewer than two frames as well.
- **"No collision: frames are distinguishable from their metadata" was printed when nothing was compared.**
  - It was printed for a single mesh, and for meshes sharing one voxel size.
  - **Change:** those now say "Nothing to compare" and "the meshes share one voxel size".
  - `.tifxyz` names off the `-on-<scan>-<um>um` convention are still skipped, not guessed. `main()` now lists them on
    stderr, and `--json` lists them under `skipped`.
- **A malformed voxel size raised instead of being skipped.**
  - The name pattern took any run of digits and dots, so `-1.2.3um` or `-.um` reached `float()` and raised.
  - `-0um` parsed as 0, and `collision()` and `render()` then divided by it.
  - The tool's contract, and its test, is that a name off the convention is skipped.
  - **Change:** the voxel size must be a positive decimal number, or the mesh is skipped. `-8.um` is now skipped too.
- **The docs.**
  - The module docstring's example output was not what the code prints. It listed the meshes coarsest first and
    marked 2.4 µm as finest, so its "rel. scale" column was relative to 2.4 µm. The code sorts finest first: here
    1.129 µm. The example is now the README's, which matches the code.
  - The README and docstring said "83% of segments in the open data". The denominator, 311, counts segments with a
    mesh directory, and they now say "of the segments with meshes".
  - The tool's CI installed `.[test,images]`, and there is no `images` extra. It installs `.[test]`.
- **Tests** (`tools/scroll_frames/test_scroll_frames.py`, 12 → 36). They check:
  - the three malformed voxel sizes are skipped;
  - eight malformed metas are left out, not raised, and a whole-number grid is kept;
  - the report:
    - with no scale read;
    - with one or two of four scales read;
    - for one frame, and for one shared voxel size;
  - `collision()`'s keys for fewer than two frames;
  - `main()`, with the lookup stubbed:
    - exit 1 on a collision and 0 without one;
    - the `--json` report, with a skipped name;
    - a skipped name listed on stderr;
    - exit 2 with nothing on stdout, for:
      - a missing `s3fs`, with the hint;
      - another import error, without it;
      - a missing segment, with its reason;
    - exit 2 on a segment without its scroll, with the usage message on stderr.

  Run against the original code, 22 of the 24 new tests fail. Each of these mutants fails them:
  - the hint dropped, or given for any import error;
  - the reason dropped;
  - "declares" for one mesh broken;
  - a malformed or NaN scale, a one-number grid, or a list-shaped meta let through;
  - skipped names not reported;
  - the single-frame message dropped;
  - `collision()`'s early keys dropped.

## Verified, no change needed

- **The collision rule.**
  - Declared scales are compared with a 1e-6 tolerance, so the catalogue's float32 and float64 spellings of 0.05 match.
  - Two meshes at the same voxel size are not a collision (spread ≤ 1.001).
  - A single mesh is never one.
- **The filenames alone expose a collision**, as `frames_for` says. With no metadata read the frames still count as
  indistinguishable, which is the tool's design.
- **`frames_for`** looks a mesh's meta up by its directory name or the full path, sorts finest first, and skips names
  off the convention. The voxel-size pattern accepts `-8um`, `-.5um`, full S3 paths and trailing slashes.
- **Nothing in this repository** calls `scrollframes` or depends on its exit status or output. The subtree's CI runs
  only `scrollframes --help`.
- **The README's figures** agree with each other: 257 of 311 segments is 83%, 204 of 257 is 79%, and 45.532 / 1.129
  is 40.33. They were measured against the live bucket on 2026-08-18. This round does not fetch the bucket, so it does
  not re-measure them.
- **Compatibility.** Both files still parse as Python 3.9, the oldest version `pyproject.toml` allows, and the
  standard-library calls used exist in 3.9. The tool stays standard-library only.
- **Ctrl-C** is not caught by the lookup's error handling: `KeyboardInterrupt` is not an `Exception`.

## Observations for the owner (not changed)

- **This repository never runs the tool's tests.**
  - `pytest`'s `testpaths` is `tests/`, and `scripts/run_validation_tests.py` lists only `tests/` files.
  - So `tools/scroll_frames/test_scroll_frames.py`, and `placement_check`'s own tests, run only in their public
    repositories' CI. That CI is not checked here.
  - `tests/test_placement_impl_parity.py` is the one test here that reaches into `tools/`.
- **The public `scroll-frames` repository lacks these fixes until the subtree is pushed:**
  `git subtree push --prefix=tools/scroll_frames https://github.com/jonmarrs/scroll-frames.git main`
  (`tools/EXTRACTION.md`).
  - The version is still 0.1.0.
  - A caller that tests for status 1 specifically would now see 2 where a failure used to exit 1, which may call for
    a version bump or a release note.
- **`placement_check` has the same two meanings for 1.**
  - Its help says it exits 1 when the offset exceeds `--max-offset`. A missing file or a missing Pillow also exits 1,
    through `SystemExit` with a message, and so do a shape mismatch or a peak on the search bound, through an
    uncaught `ValueError`.
  - Every one of these fails closed, which suits a gate, but a caller cannot tell a misplaced label from a check that
    did not run.
  - It was reviewed in the warp-alignment round and is left as it is: whether the two tools should agree is the
    owner's call.
- **`docs/VILLA_ISSUE_DRAFT_frame_metadata.md` calls the tool "stdlib+numpy".** It is standard-library only. The draft
  is the record of an issue already filed, so it is left as it is.

## Verification

- `pytest tools/scroll_frames/test_scroll_frames.py`: 36 passed.
- Ruff 0.9.10 and ruff format are clean on the changed files.
- **The standard suite** on the first commit (`b7e1acb2`) ran as on main: 2701 passed, with the same 42 failures and
  2 errors, all environmental. It does not run the tool's tests (above). The smoke test gave 9 of 11 passed and 2
  skipped, as on main.
- **Independent review** of the first commit found nothing blocking. It confirmed:
  - the pattern's accepted and rejected names, and that `float()` can no longer raise;
  - the exit codes;
  - that nothing in this repository depends on the tool's exit status;
  - Python 3.9 syntax;
  - the test counts and the README's arithmetic.

  Its should-fix findings:
  - a malformed `meta.json` still crashed outside the new error handling, and so exited 1;
  - the import-error branch caught any import error, hid its cause, and gave a PyPI install hint for a tool installed
    from git.

  Its nits:
  - the exception type missing from the message;
  - surviving mutants, and loose assertions in the exit tests;
  - a regression test's docstring that the test, which stubs the lookup, could not show;
  - "No collision" for one frame;
  - `--json`'s keys for fewer than two frames;
  - the report's wording for one mesh, and for a meta read without a scale;
  - this document's account of `placement_check`;
  - the README's denominator;
  - the CI's `images` extra;
  - the villa draft's "stdlib+numpy";
  - a release note for the exit-code change.

  All are addressed above, the last two as observations.
