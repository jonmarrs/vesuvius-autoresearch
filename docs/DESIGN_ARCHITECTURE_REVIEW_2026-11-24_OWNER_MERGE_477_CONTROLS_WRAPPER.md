# Design and architecture review — the owner's #477, the band read's choices from the controls

Date: 2026-11-24. Baseline: `0d244f7` (main after round #219's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 04:12 UTC firing on 2026-11-24. Main had not moved since round #219's merge.

It finishes **#477**, the registration of finding 133, PHerc. 0800's band read. Its choices wait on findings 131, 132
and 134. `repro/first_letters/eligible_band/run_after_controls.sh` reads their records when the read starts, sets
three choices from them, prints the choices, and then runs the read:
- `STUDIO_SKIP_EMPTY=1` if finding 132's verdict is `SKIP_ADOPTED`, and 0 otherwise;
- `FL_DENSIFY=2` unless finding 131's verdict is `DENSE_READS_WORSE`, when it is left unset;
- `FL_SNAP_PASSES=3` if finding 134's consequence is `three_passes` and `FL_DENSIFY` is set, and 1 otherwise.

A missing or unreadable record leaves its choice at finding 129's. #477 also made `run_studio_band.sh` run Studio
through `studio_fast.py --skip-empty` when `STUDIO_SKIP_EMPTY=1`. Round #212 reviewed #477's other change,
`FL_SNAP_PASSES` in `run_snap.sh`, with #471.

The scripts are under `repro/first_letters/`, so this round adds tests only.

## What changed

### Three more rules of the wrapper are tested (`tests/test_band_read_after_controls.py`)

This round made 11 mutants: 8 of the wrapper and 3 of `run_studio_band.sh`'s choice of Studio. #477's tests killed
8. Three new test functions, 5 cases, kill the other 3.
- **Without a command, the wrapper stops.** It exits 2 with its usage line, and prints no choices.
- **The records are read under `FL_ROOT`, unless `FL_CONTROL_DIR` is given.** #477's tests always gave
  `FL_CONTROL_DIR`.
- **A record without its key counts as missing.** The choices line shows `missing`, not `None`, and the choice is
  finding 129's. Finding 134's record is read for its consequence, not its verdict.

No code changed. No defect was found.

## Verified, no change needed

- **The wrapper reads the records where the controls write them.**
  - `run_studio_fast.sh`, `run_dense_read.sh` and `run_snap_passes.sh` write `work/studio_fast.json`,
    `work/dense_read.json` and `work/snap_passes.json` under the same folder: `FL_CONTROL_DIR`, or else
    `$FL_ROOT/pherc0211_control`.
  - `studio_fast.py` and `dense_read.py` write `verdict`, and `snap_passes_read.py` writes `consequence`, whose
    values include `three_passes`.
- **The rule is the registration's.** #477's tests check each row of the registration's table and of its
  amendment 1, including a garbled record and the caller's own `FL_DENSIFY`.
- **`run_studio_band.sh` runs the winner's `inference.py` unless `STUDIO_SKIP_EMPTY=1`**, and stops on any other
  value. #477's tests check both command lines, word for word.
- **The verdicts in so far.** Rounds #217 and #218 found finding 131's record `DENSE_READS_SAME` and finding 132's
  `SKIP_ADOPTED`. So the read will run with the skip and `FL_DENSIFY=2`; finding 134's record is not in the
  repository.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_band_read_after_controls.py` gives 21 passed, against 16 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #219's run.
  - A first run, alongside mypy and the smoke test, also failed the two `SIGHUP` cases of
    `test_supervisor_startup.py`: a child was not gone within 5 seconds.
  - That module passed alone three times, and a second run of the suite alone gave the 278.
  - The suite does not run the touched module.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #219's run.
  - 3,417 passed: round #219's 3,412 and the 5 new cases.
  - 4 xfailed, as in round #219.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `0d244f7`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_after_controls.sh` and `run_studio_band.sh` are unchanged.** Their mutants were run in a worktree. The new
  tests run the wrapper with a command that prints the choices it was given. They never read the default folder on
  the owner's machine.
- **#477 is now reviewed**, in rounds #212 and #220.
- **Still not reviewed from the owner's merges since round #182:** #478, #480, #483, #485, #488, #489, #493, #496,
  #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 11 were run again with the new tests, and all 11 are killed.
