# Design and architecture review — the owner's #471, the band-and-read chain

Date: 2026-11-23. Baseline: `7f0bdc1` (main after the owner's #522).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 19:12 UTC firing on 2026-11-23. Main had moved since round #210's merge. The owner's #522 marks
the UAMT strategy item's launcher as archived in `docs/VILLA_STRATEGY.md`, a one-line change. It is listed below for a
later round.

It takes more of **#471**, finding 126: `repro/first_letters/eligible_band/run_band_and_read.sh`, the chain that
fitted PHerc. 0358's band and read it. Each step runs only if the one before exited 0, and each writes its exit and
time to `R/work/gate_chain/`:
- fetch the band's public inputs and make villa's dataset;
- build the distance field;
- fit 300 steps, then the registered 30,000;
- score each raw winding's sheet-following excess, and select the windings above zero;
- with `FL_DENSIFY`, subdivide the selected windings into arm `fulldense`;
- read the selected windings with Studio.

The script is under `repro/first_letters/`, so this round adds tests only. Round #204 reviewed `studio_band.py`, with
the select and stacked steps #471 added. Round #209 reviewed `band_record.py`, and round #210 `outer_sheets.py`.

## What changed

### The chain is run, not only read (`tests/test_first_letters_0358_band.py`)

#471's test of the chain reads its text: the steps' order, the fit's arguments, the winding list passed to the read,
and that it uploads nothing. That killed 2 of this round's 14 mutants. Five new test functions run a copy of the
chain beside a copy of `env.sh`, with every step and the Python a stub that logs its call. They kill all 14.
- **The steps run once each, in order, each with its gate.** The read takes the selected windings of arm `full`.
- **The first failing step stops the chain with its own exit**, and no later step runs or is gated.
- **With `FL_DENSIFY`, each selected winding of the fit is subdivided by that factor into arm `fulldense`**, which
  is then read.
- **A densify that fails on one winding, or that finds its arm already there, stops the chain** before the read.
- **A band already fitted is refused** before any step.

No code changed. No defect was found.

## Verified, no change needed

- **Finding 126's costs are its record's.** The chain's gates in `reports/first_letters_0358_studio_band.json` give
  each row of the report's cost table:
  - the volumes 2,198 s (36 min 38 s), the tracks 418 s, the distance field 898 s;
  - the 300-step fit 402 s, the 30,000-step fit 11,690 s (3 h 14 min 50 s);
  - the quality 441 s, and the read 48,489 s (13 h 28 min 9 s).

  Together they come to 64,561 s, the report's 17 h 56 min, 2.2 times the registered 8 hours. The read's steps
  (2 h 10 min 9 s, 4 h 7 min 39 s, 6 h 44 min 40 s, 9 min 55 s) are its record's too.
- **Per winding the read took 7.3 minutes.** That is 48,489 s over 111 windings. Finding 125's took 7.5, its 31,678 s
  over 70, as the report says.
- **A selected list is read whole.** `studio_band.py select` ends every name with a newline, so the densify loop's
  `read` reaches the last winding.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_first_letters_0358_band.py` gives 16 passed, against 11 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,109 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #210's run.
- **The 309 test modules outside the suite** give the same 24 failing ids as round #210's run.
  - 3,328 passed: round #210's 3,323 and the 5 new cases.
  - 4 xfailed, as in round #210.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `7f0bdc1`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_band_and_read.sh` is unchanged.** Its mutants were run in a worktree. The tests copy it and `env.sh` into
  `tmp_path` byte for byte, and stub only the steps it calls.
- **Still not reviewed from the owner's merges since round #182:** the rest of #471 (the snap's batches and the read's
  winding list and tiling in `run_studio_band.sh`), #472 to #478, #480, #483, #485, #488, #489, #493, #496, #505 and
  #522.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 14 were run again with the new tests, and all 14 are killed.
