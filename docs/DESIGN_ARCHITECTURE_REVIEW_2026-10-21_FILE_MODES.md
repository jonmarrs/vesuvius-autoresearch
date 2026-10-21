# Design and architecture review — the file modes of atomically written outputs

Date: 2026-10-21. Baseline: `21292adb` (main after #169).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: every writer that builds a file under a temporary name and renames it into place.

On 2026-10-17 the owner fixed `save_checkpoint_atomic`, which renamed `mkstemp`'s 0600 file over its target as it
was (`a2199798`, #115). Every promoted `best_model.pt` and every `last_model.pt` could be read by their owner alone.
The loop's JSON writer kept an existing file's mode but gave a new one 0600, and the owner fixed it too. The
2026-10-18 review found no defect in that change. Nothing checked the repository's other writers of the same kind.

Main has not moved since #169. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches.

## What changed

- **Four more writers published a 0600 file.** `tempfile.mkstemp` and `NamedTemporaryFile` create their file 0600, and
  each of these renamed it into place as it was:
  - `atomic_file` in `src/vesuvius_autoresearch/fibers/provenance.py`, and `write_json` on it. `bench_cli`, their only
    user, writes through them:
    - each cube's cached probability volume and its cache record;
    - the cubes `bench_cli fetch` downloads;
    - its benchmark reports and saved instances;
  - `write_json` in `scripts/candidate_artifacts.py`. Its callers include:
    - `launch_mutex`'s training config and run markers;
    - the data catalogue and the plot manifest;
    - the `summary.json`, `handoff.json` and `split.json` written inside published directories;
  - `publish_new_file` in `scripts/labeling/label_artifacts.py`. What it publishes includes:
    - `export_for_production`'s exported checkpoint;
    - `generate_pseudo_labels`' label image;
    - `register_volumes`' transform JSON;
    - the Volume Cartographer benchmark and the fiber-miss diagnostic;
  - `fetch_obj` in `repro/sota_data/obj_geometry.py`, for its cached OBJ download.

  **Change:** each now gives its file the mode the owner's fix gives a checkpoint: that of the file it replaces, or
  0666 less the umask for a new one.
  - `atomic_file` and `write_json` take the mode before they create the temporary file.
  - `publish_new_file` and `fetch_obj` set it just before the rename, when the output cannot exist yet. So it holds
    however the caller wrote the file. `register_volumes`, for one, has another process write it.
  - No writer of these helpers writes a credential or token, so none of them needed 0600.
- **One helper.** The owner's `_umask` and `replacement_mode` move from `scripts/training/promotion.py` to
  `vesuvius_autoresearch.core.file_modes`. They are unchanged but for `_umask`'s name (`current_umask`) and the path's
  type (any path, not only `str`).
  - `promotion.save_checkpoint_atomic`, the loop's JSON writer and the writers above all take it from there.
  - The package should not import from `scripts/`, which is on the path only when run from the repository root.
  - `core/__init__.py` is empty, so importing the helper loads neither torch nor zarr. The loop controller still
    imports no training code.
- **Tests** (`tests/test_file_modes.py`, 11). They run under a 027 umask, so a mode that ignored the umask would show.
  They check that:
  - the umask is read without being changed, also without `/proc`;
  - `replacement_mode` gives a replaced file's mode, else the umask's;
  - `provenance.write_json`, `provenance.atomic_file` and `candidate_artifacts.write_json` give a new file the umask's
    mode and keep a replaced file's, leaving no temporary file;
  - a published label artifact gets the umask's mode, also when its caller replaced the staging file with a 0600 one;
  - a downloaded OBJ gets the umask's mode;
  - in every tracked module, any function that makes a `mkstemp` file, a `NamedTemporaryFile(delete=False)` or a
    `mkdtemp` directory also sets a mode (`replacement_mode`, `chmod` or `fchmod`). Otherwise the test must name the
    function and say why.
    - It reads each function's syntax tree, so it finds the call however it is spelled or imported.
    - A second writer added beside a fixed one is checked on its own.
    - A test of the scan covers aliased imports, a `delete=False` after other arguments, a nested function, and a
      `NamedTemporaryFile` that deletes itself.
    - It leaves out `tests/`, `villa/`, `repro/villa_preserved/` and the retired `scripts/archive/`.

  Each of these mutants fails them:
  - each writer's mode dropped;
  - the mode taken from the temporary file;
  - `publish_new_file`'s mode set when the staging file is made, not before the rename;
  - the umask ignored;
  - the fallback leaving the umask changed;
  - a writer's use of the helper removed;
  - an unprotected writer added to a module that already uses the helper.

  The owner's own tests of the checkpoint and the loop's JSON writer pass unchanged. The loop now imports
  `file_modes`, so `scripts/run_validation_tests.py` lists its tests, as `test_validation_suite_covers_the_loop`
  requires.

## Verified, no change needed

- **Directories staged in a temporary directory and moved out.** Each of these builds in a subdirectory it creates
  with `mkdir`, and that subdirectory, with the umask's mode, is what moves. The temporary directory around it is
  removed.
  - `candidate_artifacts.staged_directory`;
  - `export_fiber_targets`;
  - `repro/sota_data/fragment.py`;
  - `subsample_mesh`.
- **The other temporary directories are scratch, never moved into place.** These include `f1_noise_probe`'s TMPDIR,
  `tracer_rescore_analysis`'s scorer copy and `render_cli`'s scale probes.
- **Writers that open their temporary file with `open()`** (`<path>.tmp` and the like) get the umask's mode already.

## Observations for the owner (not changed)

- **Two scripts of the registered neural-tracer chains still publish owner-only outputs.**
  - `scripts/resample_cube_pitch.py` writes its resampled probability through `mkstemp` (0600). It builds its
    resampled CT in a `mkdtemp` directory, which is 0700 and renamed into place as it is.
  - `scripts/make_tracer_presence.py` renames its 0700 `mkdtemp` directory into place the same way.
  - The chains copy them into their work directories, and a resume refuses when the repository's copy differs:
    - `repro/fibers/run_neural_tracer_chain.sh` copies `make_tracer_presence.py`;
    - the pitch chain copies both;
    - the seeding chain copies `resample_cube_pitch.py`.

    So they are left for the owner, and the test names their functions.
- **Two outputs are made 0700 in place, not renamed.** `mktemp -d` makes:
  - `repro/spiral_render/run_snapshot.sh`'s `_driver_snapshot_*` directory;
  - the `outputs/pin-review.XXXXXX` directory that `scripts/review_villa_pin.py`'s documented smoke command
    makes.

  They are outside this round's scope.
- **Files written before this change keep 0600.** A replaced file keeps its mode, by the owner's design. So a cache
  record, a report or a config first written 0600 stays so when it is rewritten. `find <dir> -type f -perm 600`
  lists them, and `chmod` widens them.

## Verification

- `pytest tests/test_file_modes.py`: 11 passed. `tests/test_validation_suite_covers_the_loop.py`: 4 passed.
- The tests of the changed modules and their callers fail only as on main: villa's files and `s3fs` are missing in
  this container. This covers the loop's measurement tests and the bench, candidate, label, geometry-handoff and
  surface-render contracts.
- Ruff 0.9.10 (the project's pin) and ruff format are clean on the changed files, and so is mypy.
- **The standard suite** on the first commit (`1ae67490`) ran as on main: 2699 passed, with the same 42 failures and
  2 errors, all environmental. That is 9 more passes, this file's tests. The smoke test gave 9 of 11 passed and 2
  skipped, as on main.
- **Independent review** of the first commit found nothing blocking. It confirmed:
  - each writer takes the mode from its target, never from the temporary file;
  - no file descriptor leaks, and every failure path still removes the temporary;
  - no credential passes through these writers;
  - the import layering: no torch or zarr from `file_modes`;
  - the list of `bench_cli` outputs;
  - every temporary-file writer is fixed or named here;
  - the dates and commits.

  Its should-fix findings:
  - this document said no review had read the owner's change. The 2026-10-18 review had;
  - `register_volumes` publishes a transform, not a volume;
  - the scan's text match missed other spellings, and passed any file that named the helper;
  - no test showed why `publish_new_file` sets the mode before the rename.

  Its nits:
  - "five" writers for four;
  - the loop's JSON writer had already kept an existing file's mode;
  - `publish_new_file`'s list read as complete;
  - `render_cli` moves nothing;
  - the chains;
  - the ruff version;
  - `scripts/archive/`;
  - the 0700 directories made in place.

  All are addressed above. Not addressed: no test of a symlinked target, which the review checked by hand. The
  target's mode is kept, and the link is replaced by a file.
