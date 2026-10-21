# Design and architecture review — the file modes of atomically written outputs

Date: 2026-10-21. Baseline: `21292adb` (main after #169).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: every writer that builds a file under a temporary name and renames it into place. On 2026-10-17 the owner
found that `save_checkpoint_atomic` and the loop's JSON writer published `mkstemp`'s 0600 file as it was, so every
promoted `best_model.pt`, every `last_model.pt` and the loop's state could be read by their owner alone
(`a2199798`). No review had read that change, and nothing checked the repository's other writers of the same kind.

Main has not moved since #169. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches.

## What changed

- **Five more writers published a 0600 file.** `tempfile.mkstemp` and `NamedTemporaryFile` create their file 0600, and
  each of these renamed it into place as it was:
  - `atomic_file` in `src/vesuvius_autoresearch/fibers/provenance.py`, and `write_json` on it. `bench_cli` writes
    through them:
    - each cube's cached probability volume and its cache record;
    - the cubes `bench_cli fetch` downloads;
    - its benchmark reports and saved instances;
  - `write_json` in `scripts/candidate_artifacts.py`. Its callers include:
    - `launch_mutex`'s training config and run markers;
    - the data catalogue and the plot manifest;
    - the `summary.json`, `handoff.json` and `split.json` written inside published directories;
  - `publish_new_file` in `scripts/labeling/label_artifacts.py`. It publishes:
    - `export_for_production`'s exported checkpoint;
    - `generate_pseudo_labels`'s label image;
    - `register_volumes`' registered volume;
    - the Volume Cartographer benchmark and the fiber-miss diagnostic;
  - `fetch_obj` in `repro/sota_data/obj_geometry.py`, for its cached OBJ download.

  **Change:** each now gives its file the mode the owner's fix gives a checkpoint: that of the file it replaces, or
  0666 less the umask for a new one. `publish_new_file` sets it just before the rename, so it holds however its
  caller wrote the file. `register_volumes`' caller, for one, has another process write it.
- **One helper.** The owner's `_umask` and `replacement_mode` move from `scripts/training/promotion.py` to
  `vesuvius_autoresearch.core.file_modes`, unchanged but for `_umask`'s name (`current_umask`) and the path's type
  (any path, not only `str`).
  - `promotion.save_checkpoint_atomic`, the loop's JSON writer and the writers above all take it from there.
  - The package should not import from `scripts/`, which is on the path only when run from the repository root.
  - `core/__init__.py` imports nothing, so the loop controller still imports no training code.
- **Tests** (`tests/test_file_modes.py`, 9). They run under a 027 umask, so a mode that ignored the umask would show.
  They check that:
  - the umask is read without being changed, also without `/proc`;
  - `replacement_mode` gives a replaced file's mode, else the umask's;
  - `provenance.write_json`, `provenance.atomic_file` and `candidate_artifacts.write_json` give a new file the umask's
    mode and keep a replaced file's, leaving no temporary file;
  - a published label artifact and a downloaded OBJ get the umask's mode;
  - every tracked writer that renames a `mkstemp` or `NamedTemporaryFile(delete=False)` file uses `replacement_mode`,
    unless the test names it and why.

  Each of these mutants fails them:
  - each writer's mode dropped;
  - the umask ignored;
  - the fallback leaving the umask changed;
  - a writer's use of the helper removed.

  The owner's own tests of the checkpoint and the loop's JSON writer pass unchanged. The loop now imports
  `file_modes`, so `scripts/run_validation_tests.py` lists its tests, as `test_validation_suite_covers_the_loop`
  requires.

## Verified, no change needed

- **Directories staged in a temporary directory and renamed out.** `candidate_artifacts.staged_directory`,
  `export_fiber_targets`, `repro/sota_data/fragment.py`, `render_cli` and `subsample_mesh` each build in a
  subdirectory they create with `mkdir`. That subdirectory is what moves, and it has the umask's mode. The 0700
  temporary directory around it is removed.
- **Writers that open their temporary file with `open()`** (`<path>.tmp` and the like) get the umask's mode already.

## Observations for the owner (not changed)

- **Two scripts of the registered neural-tracer chains still publish owner-only outputs.**
  - `scripts/resample_cube_pitch.py` writes its resampled probability through `mkstemp` (0600). It builds its
    resampled CT in a `mkdtemp` directory, which is 0700 and renamed into place as it is.
  - `scripts/make_tracer_presence.py` renames its 0700 `mkdtemp` directory into place the same way.
  - Both are copied into the chains' work directories (`repro/fibers/run_neural_tracer_*_chain.sh`). A resume
    refuses when the repository's copy differs, so they are left for the owner. The test names the one that uses
    `mkstemp`.
- **Files written before this change keep 0600.** A replaced file keeps its mode, by the owner's design. So a cache
  record, a report or a config first written 0600 stays so when it is rewritten. `find <dir> -type f -perm 600`
  lists them, and `chmod` widens them.

## Verification

- `pytest tests/test_file_modes.py`: 9 passed.
- PLACEHOLDER: affected test files.
- Ruff, ruff format and mypy are clean on the changed files. `run_autoresearch_loop.py` was not ruff-formatted, so
  only its import line changed.
- PLACEHOLDER: standard suite and smoke.
- PLACEHOLDER: independent review.
