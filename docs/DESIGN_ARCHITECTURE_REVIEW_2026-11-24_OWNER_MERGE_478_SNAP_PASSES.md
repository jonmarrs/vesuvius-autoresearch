# Design and architecture review — the owner's #478, three snap passes at PHerc. 211

Date: 2026-11-24. Baseline: `ddac64e` (main after round #220's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 05:12 UTC firing on 2026-11-24. Main had not moved since round #220's merge.

It takes **#478**, finding 134: does a three-pass snap read better than one pass, where PHerc. 211's prize was won?
`repro/first_letters/pherc0211_control/run_snap_passes.sh` snaps finding 131's densified windings w033 to w036 three
times, carries them through finding 121's route, and reads them with Studio. `snap_passes_read.py compare` then scores
four arms as finding 131 scored its three, on the cells all four reach:
- finding 124's windings (`f124`);
- finding 131's re-run (`rerun`) and its densified windings snapped once (`dense2`);
- the same windings snapped three times (`dense2s3`).

The change that counts is finding 131's margin. The record's `consequence`, which finding 133 reads, is `three_passes`
if the three passes read better, or read the same and put more of each winding on the predicted sheet.

The scripts are under `repro/first_letters/`, so this round adds tests only.

## What changed

### The comparison and the run script's steps are run (`tests/test_first_letters_0211_snap_passes.py`)

#478's tests cover the verdict table, the consequence, the arms' names and the run script's text. This round made 36
mutants, 28 of `snap_passes_read.py` and 8 of `run_snap_passes.sh`, and #478's tests killed 5. Fourteen new test
functions, 20 cases, kill the other 31.
- **`compare_cmd` is run on round #217's stand-ins** for finding 110's side and transfer, now with four arms. Each
  arm lacks a different row of cells.
  - The arms are scored on the cells every arm reaches, and `f124` also on its own.
  - The share is of the mask's whole cells, and the transfer distances are taken over the common cells.
  - The noise and the change keep their signs.
  - The comparison runs only once finding 124's r is given again on `f124`'s own cells, and then it compares three
    passes against one, not the reverse.
- **The consequence.** With the verdict `SNAP3_READS_SAME`, it is `three_passes` when the sheet share gains and
  `one_pass` when it loses. The gain is taken from the distance field given. A render against the winner's normals
  stops the comparison at `one_pass`.
- **The edges.**
  - The verdict runs at exactly half the mask. It does not run without a share or without finding 124's r.
  - There is no geometry gain with no windings, or with a winding unmeasured after three passes.
  - An unreadable mask stops the comparison.
- **The command** writes its whole record, prints it without the described part, and exits 1 when it does not run.
- **The run script's own blocks**, each taken from the script's text and run with stand-in commands:
  - each winding is rendered flipped or kept as orient decided, and one without a decision stops the render;
  - the first pass is described as finding 131's snap only when all three coordinates are byte-identical;
  - the GPU peak is the largest sample, or null without one;
  - finding 131's windings, maps and densified windings are required before anything runs;
  - a failed step records its gate and stops the run;
  - Studio reads both orders of each winding's planes with the winner's command, and the planes are deleted.

No code changed. No defect was found.

## Verified, no change needed

- **The verdict is the registered table's.**
  - Every step exited 0, and every winding's normal cosine is between −0.996 and −0.999.
  - `f124` gave 0.8247 on its own 457,405 cells.
  - 435,420 of the 550,482 mask cells are common to all four arms (0.791), above the 0.5 line.
  - There, r is 0.8325 (`f124`), 0.8289 (`rerun`), 0.8188 (`dense2`) and 0.8217 (`dense2s3`).
  - The noise, −0.0036, keeps the margin at 0.02. The change, +0.0029, is inside it, so `SNAP3_READS_SAME`.
- **The consequence is the registered table's.** The three passes put more of every winding on the sheet: +0.0127,
  +0.0586, +0.0128 and +0.0599 for w033 to w036. Their median, +0.0357, is above 0, so `three_passes`.
- **The first of the three passes is finding 131's one-pass snap**, byte for byte, on all four windings. The script
  writes "no" for a missing file, so "yes" means each file was there.
- **A failed step leaves no record.** `step` stops the run before `compare`, so finding 133's wrapper finds no record
  and takes one pass: the consequence the registration gives a run whose step failed.

### Two corrections to round #220's record

**Finding 134's record.** Round #220's record says finding 134's record is not in the repository. It is: #478 added
it as `reports/first_letters_0211_snap_passes.json`, with the consequence `three_passes`. Finding 131's verdict
`DENSE_READS_SAME` leaves `FL_DENSIFY=2`, so `run_after_controls.sh` will set `FL_SNAP_PASSES=3` for finding 133's
read, with the skip and the denser snap. #534's description repeats the error; this record corrects both.

**The two `SIGHUP` failures of its first suite run** were not from load, as that record says. That run was started
under `nohup`, so its processes ignore `SIGHUP`, and `scripts/process_supervisor.py` leaves an ignored signal
ignored, as its docstring says. Under `nohup` the two cases fail every time, and without it they pass. This
round's first suite run was started the same way and failed them too. The run reported below was not.

## Observations for the owner (not changed)

- **Two cases of `tests/test_supervisor_startup.py` need `SIGHUP` handled when pytest starts.**
  `test_interrupt_between_spawn_and_registration_cleans_child[SIGHUP]` and
  `test_stop_is_not_lost_when_spawn_also_fails[SIGHUP]` fail when pytest runs under `nohup`. The supervisor is
  right to leave nohup's `SIGHUP` ignored; the two cases could set it to its default first. Not changed: it is
  outside this round's slice.

## Verification

- **The touched module.** `test_first_letters_0211_snap_passes.py` gives 38 passed, against 18 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #220's second run, started without
  `nohup`. It does not run the touched module.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #220's run.
  - 3,437 passed: round #220's 3,417 and the 20 new cases.
  - 4 xfailed, as in round #220.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `ddac64e`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`snap_passes_read.py` and `run_snap_passes.sh` are unchanged.** Their mutants were run in a worktree.
  - The tests replace finding 110's side and transfer, and the sheet share, with stand-ins through `monkeypatch`.
    The comparison's own code runs as written.
  - The run script's blocks run under `bash -u` with stand-in commands written under `tmp_path`.
- **Still not reviewed from the owner's merges since round #182:** #480, #483, #485, #488, #489, #493, #496, #505,
  #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 36 were run again with the new tests, and all 36 are killed.
