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

- **The text report crashed when no `meta.json` declared a scale.**
  - `_fetch` skips any `meta.json` it cannot read, and a mesh's meta may have no `scale`.
  - With no scale read, `collision()` still reports a collision: the filenames alone show the spread, as the tool
    intends. `render()` then named "all N meshes declare scale" from the first declared scale, so it raised an
    `IndexError` on the empty list.
  - **Change:** that case now says the voxel sizes differ and no `meta.json` could be read for a scale.
- **With some scales unread, the report said "all N meshes declare scale".** Only those whose scale was read had.
  **Change:** it says how many declare one, and that no scale was read for the others. `collision()` reports the
  count (`n_declaring_scale`), which `--json` carries too.
- **A failure exited 1, which means a collision.**
  - A segment given without its scroll raised `SystemExit` with a message, which exits 1.
  - So did an uncaught error from the lookup: no `s3fs`, no network, or no such segment.
  - A script told by the README to gate on the exit status could not tell "these frames collide" from "nothing was
    checked".
  - **Change:**
    - a malformed segment is an argparse usage error, which exits 2;
    - a failed lookup prints its reason to stderr and exits 2;
    - a missing `s3fs` names the extra that installs it.

    Both still exit non-zero, so a caller that gates on any non-zero status still stops. The README states the three
    exit codes.
- **A malformed voxel size raised instead of being skipped.**
  - The name pattern took any run of digits and dots, so `-1.2.3um` or `-.um` reached `float()` and raised.
  - `-0um` parsed as 0, and `collision()` then divided by it.
  - The tool's contract, and its test, is that a name off the convention is skipped, not guessed.
  - **Change:** the voxel size must be a positive decimal number, or the mesh is skipped.
- **The module docstring's example output was not what the code prints.** It listed the meshes coarsest first and
  marked 2.4 µm as finest, so its "rel. scale" column was relative to 2.4 µm. The code sorts finest first: here
  1.129 µm. The example is now the README's, which matches the code.
- **Tests** (`tools/scroll_frames/test_scroll_frames.py`, 12 → 22). They check:
  - the three malformed voxel sizes are skipped;
  - the report with no scale read, and with some unread;
  - `main()`, with the lookup stubbed:
    - exit 1 on a collision and 0 without one;
    - the `--json` report;
    - exit 2 on a missing `s3fs` or a missing segment, with nothing on stdout;
    - exit 2 on a segment without its scroll.

  Run against the original code, 9 of the new tests fail.

## Verified, no change needed

- **The collision rule.**
  - Declared scales are compared with a 1e-6 tolerance, so the catalogue's float32 and float64 spellings of 0.05 match.
  - Two meshes at the same voxel size are not a collision (spread ≤ 1.001).
  - A single mesh is never one.
- **The filenames alone expose a collision**, as `frames_for` says. With no metadata read the frames still count as
  indistinguishable, which is the tool's design.
- **`frames_for`** looks a mesh's meta up by its directory name or the full path, sorts finest first, and skips names
  off the convention.
- **The README's figures** agree with each other: 257 of 311 segments is 83%, 204 of 257 is 79%, and 45.532 / 1.129
  is 40.33. They were measured against the live bucket on 2026-08-18. This round does not fetch the bucket, so it does
  not re-measure them.
- **Compatibility.** Both files still parse as Python 3.9, the oldest version `pyproject.toml` allows. The tool stays
  standard-library only.

## Observations for the owner (not changed)

- **This repository never runs the tool's tests.**
  - `pytest`'s `testpaths` is `tests/`, and `scripts/run_validation_tests.py` lists only `tests/` files.
  - So `tools/scroll_frames/test_scroll_frames.py`, and `placement_check`'s own tests, run only in their public
    repositories' CI. That CI is not checked here.
  - `tests/test_placement_impl_parity.py` is the one test here that reaches into `tools/`.
- **The public `scroll-frames` repository lacks these fixes until the subtree is pushed:**
  `git subtree push --prefix=tools/scroll_frames https://github.com/jonmarrs/scroll-frames.git main`
  (`tools/EXTRACTION.md`). The version is still 0.1.0, so bumping it is the owner's call.
- **`placement_check` also exits non-zero on a failure** (`SystemExit` with a message, so 1). It is a gate, and its
  README promises only "non-zero", so failing closed there is consistent. It is left as it is.

## Verification

- `pytest tools/scroll_frames/test_scroll_frames.py`: 22 passed.
- Ruff 0.9.10 and ruff format are clean on the changed files.
- PLACEHOLDER: standard suite and smoke.
- PLACEHOLDER: independent review.
