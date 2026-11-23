# Design and architecture review — the owner's #448, Reader V3 against the winning PHerc. 211 map

Date: 2026-11-23. Baseline: `06eb6df` (main after round #196's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 05:13 UTC firing on 2026-11-23. Main had not moved since round #196's merge.

It takes **#448**, finding 120. It measures whether Reader V3, a released MIT reader, puts ink where the winning
PHerc. 211 reader put it, more closely than the PHerc. 343 recipe's four-model ensemble. Two scripts in
`repro/first_letters/pherc0211_control/` carry it:
- `compare_readers.py` scores both readers on finding 118's render, cells and alignment: Pearson r against the
  winner's map, and the overlap of the winner's ink cells with as many of the reader's strongest cells. Each number
  has a wrong-side and a slid control.
- `check_checkpoint.py` loads the downloaded checkpoint with Torch's weights-only unpickler. Villa's loader uses
  `weights_only=False`, so the checkpoint is handed to villa only after it loads this way.

`fetch_reader_v3.sh` pins the checkpoint's revision and SHA-256 and runs the check, and `run_reader_v3.sh` makes
the maps. All four are registered, so this round adds tests only.

## What changed

### The checkpoint check now runs, and 29 more rules are tested (`tests/test_first_letters_0211_reader_v3.py`)

This round made 40 mutants of the two scripts, and #448's tests killed 10. Fifteen new test functions, 21 cases,
kill 29 of the other 30. The last is equivalent, below.

**`check_checkpoint.py` ran in no test.** #448's test checks only that `fetch_reader_v3.sh` names it. None of its
eight mutants was killed, including one that loads with `weights_only=False`. The new cases run it on real Torch
checkpoints, and are skipped where Torch is absent:
- **A checkpoint of tensors loads, and its configuration is described.** The keys come back sorted, and the model
  type is read from a nested `model` section.
- **A checkpoint whose pickle would call `os.makedirs` is refused.** The check exits 1 and says `REFUSED`, and the
  directory is never made.
- **Any argument count but one exits 2**, with the usage text.
- **`describe` reads flat and nested configurations.** It falls back to the top-level model type and to
  `crop_size`, and leaves out a configuration that is not a dictionary.

**`compare_readers.py`:**
- **The verdict at its other edges.** A cell share exactly at the line is measured, and a reader exactly twice its
  controls clears them. A missing control fails the controls, and a missing r or overlap on either side does not
  run.
- **A constant map is refused** rather than standardised.
- **The strongest cells keep their order among 1,000 ties.** NumPy's default sort reorders that many equal values,
  so `kind="stable"` is what makes the choice reproducible. #448's test had four values, where both sorts agree.
- **The overlap counts only the winner's ink among the compared cells.**
- **Every slide leaves out the cells that wrapped round.** #448's test covered sliding up only. Down, left and
  right are the same case turned.
- **The largest slid overlap passes over a slide that leaves no ink to compare.**
- **The described bootstrap** leaves out a block holding one cell, and measures Reader V3 minus the ensemble, not
  the reverse.
- **The alignment's three uses in `main`**, with `compare.alignment` stubbed:
  - a shift of 16 pixels, down, up or sideways, does not run;
  - a shift within tolerance is not applied;
  - a shift beyond it is applied to every described depth as well as the registered one.
- **A winner's cell at exactly 0.5 is ink.**

No code changed. No defect was found.

### One mutant is equivalent

Dropping Reader V3's maps from the finiteness mask changes nothing here. A Reader V3 map must match the render's
canvas exactly and is clipped to `[0, 1]`, so it is finite wherever it is read. It is then moved by the same shift
as the ensemble's maps, which blanks the same cells.

## Verified, no change needed

- **The registered numbers give the verdict.** Reader V3's r is 0.6271 against the ensemble's 0.53, a difference
  of 0.0971, short of the 0.10 margin. Its overlap is 0.1019 higher, past the 0.05 margin. Its r is more than twice
  each control, 0.0194 and 0.1531 in absolute value. So `V3_NO_CLOSER`, as `docs/RESEARCH_STRATEGY.md` states.
- **The ensemble's numbers are finding 118's.** #448's test runs `compare.py` and `compare_readers.py` on the same
  inputs and finds the same r and controls.
- **The registered lines are the preregistration's.** #448's test reads them from the registration and from
  `fetch_reader_v3.sh`.

## Observations for the owner (not changed)

- **`run_reader_v3.sh` checks only that the checkpoint file exists.** `fetch_reader_v3.sh` ends with the
  weights-only check and exits 1 if it refuses. But nothing records that the check passed, and `run_reader_v3.sh`
  hands the file to villa's `weights_only=False` loader whenever it is present. The SHA-256 pin fixes which bytes
  that is, and the report lists the check as run. The record has no entry for it: its `steps` holds only the
  maps' run. A run that skipped or ignored the fetch step's exit status would look the same.

## Verification

- **The touched module.** `test_first_letters_0211_reader_v3.py` gives 31 passed, against 10 before. The four
  checkpoint cases ran on the installed Torch 2.9.1.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #196's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #196's run, and 3,183 passed:
  round #196's 3,162 and the 21 new cases. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `06eb6df`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **The four scripts are registered and unchanged.** Their mutants were run in a worktree.
- **The out-of-suite list is rebuilt each round,** as from round #196. It is unchanged at 308 modules.
- **Still not reviewed from the owner's merges since round #182:** #450, #453, #456, #458, #461, #465, #468 to
  #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 40 were run again with the new tests: 39 are killed, and the equivalent one is
  not.
