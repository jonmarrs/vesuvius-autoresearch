# Design and architecture review — the owner's #488, the run script for Studio on our own fit

Date: 2026-11-24. Baseline: `cbbfd25` (main after the owner's #545).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 11:12 UTC firing on 2026-11-24. Since round #226's merge, the owner merged #519, #527, #535 and
#545. They are listed below for later rounds. They add four test modules, which this round's outside run includes.

It finishes **#488**, finding 136, with `repro/first_letters/pherc343/run_studio_343_own.sh`, which round #226 left.
Nothing is fitted, snapped, flattened or rendered: the windings and renders are finding 110's. Its steps, each run
only if the one before exited 0:
- **check** the weights and the winner's `inference.py` against their SHA-256 values;
- **planes**: layers 41 down to 26 of w047's and w048's 66-layer renders, in both orders;
- **infer**: the winner's command on all four, with a GPU sampler;
- **compare**: `studio_343_own.py compare`, against finding 127's map of the published surface.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### The run script's blocks are run (`tests/test_studio_343_own.py`)

No test ran or read `run_studio_343_own.sh`, and all 17 of this round's mutants of it survived. Six new test
functions, 12 cases, take each block from the script's own text and run it under `bash -u` with stand-in commands,
as rounds #221 and #225 ran their run scripts. They kill all 17.
- **The up-front checks.** An existing output folder, a missing Studio environment, a missing render or mesh of
  either winding, or a missing map of finding 127's stops the run, before anything runs.
- **A failed step** writes its gate with its exit code, and stops the run.
- **The planes** are each winding's layers in both orders, the second with `--reverse`. A failure stops them.
- **Studio** reads all four sets of planes with the winner's command, in order, and deletes each set once read.
  - The GPU peak is the largest sample.
  - A failed read stops Studio and fails the step.
  - The sampler is stopped either way, and the peak is still written.
- **`compare`** gives each winding its own mesh, render, map and reversed map, and the published surface its reversed
  map.

No code changed. No defect was found.

## Verified, no change needed

- **The record's steps all exited 0.** Making the planes took 27 s and Studio 335 s on the four sets. The GPU peak
  was 14,487 MiB over all processes.
- **The script's paths are the ones the comparison and finding 127 use.**
  - `studio_e2e.py planes` writes `wNNN.npy` and `wNNN_reversed.npy`, and Studio's maps take the same names.
  - The published maps are `studio_343/maps/forward.npy` and `reversed.npy`, which `run_studio_343.sh` writes.
- **This script's sampler is stopped on failure**, unlike `run_depth_sweep.sh`'s (round #225). It lives inside
  `infer`, which stops it whether Studio succeeds or not.
- **Round #214's observation on #524's filing draft is half resolved.**
  - Of the two commits the draft cites from unmerged branches, `dc232051` is now on main, through the owner's #527.
  - The other, on `research/studio-band-triage`, is named in the draft as a run still going.
  - The doc audit lists one unresolved reference fewer for it.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_studio_343_own.py` gives 27 passed, against 15 before. Three runs in a row gave the
  same.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,118 files with the owner's new ones, with
    `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives 282 failing ids. They are round #226's 280, and 2 cases the owner's
  #543 added to `test_training_data_sources.py`. Like #541's two, those need a villa checkout. The suite does not run
  the touched module.
- **The 314 test modules outside the suite**, with the owner's four new ones, give the same 24 failing ids as
  round #226's run.
  - 3,583 passed: round #226's 3,494, this round's 12 new cases, and 77 from the owner's new and changed modules.
  - 3 xfailed: round #226's 5, less two strict xfails in `test_first_letters_0211_gp_timesformer.py` that the
    owner's #519 fixed and removed.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `cbbfd25`. That is one fewer than round
  #226's run, as above.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_studio_343_own.sh` is unchanged.** Its mutants were run in a worktree.
  - The tests write their stand-ins under `tmp_path`: Python, Studio's interpreter and `nvidia-smi`.
  - The stand-in sampler is always killed after its test.
- **#488 is now reviewed**, in rounds #226 and #227.
- **Still not reviewed from the owner's merges since round #182:** #489, #493, #496, #505, #517, #519, #524, #527,
  #535, #541, #543 and #545.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 17 were run again with the new tests, and all 17 are killed.
