# Design and architecture review — the owner's #469, the band read's record

Date: 2026-11-23. Baseline: `9666b6f` (main after round #208's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 17:12 UTC firing on 2026-11-23. Main had not moved since round #208's merge.

It finishes **#469** with `repro/first_letters/eligible_band/band_record.py`, which assembles a band read's record
from its run directory after the read. It changes nothing in the run, and it reads:
- each stage's and each winding's step gates;
- the render orientation, Studio's ink numbers and the reading turns;
- the fit's excess;
- the stacking and geometry records, if they were made;
- the GPU memory log, if one was sampled;
- a chained read's gates and the fit's verdict;
- each render's canvas, and the disk the renders and maps take.

Findings 125 and 126 were recorded with it. The script is under `repro/first_letters/`, so this round adds tests
only. Rounds #207 and #208 took #469's other two tools.

## What changed

### Twenty more rules of the record are tested (`tests/test_first_letters_band_record.py`)

This round made 27 mutants of `band_record.py`, and the existing tests killed 3. Six new test functions kill 20 of
the other 24. The last four are equivalent, below.
- **A stage or step that never ran has no numbers.** A missing stage gate is `None`, and a step with no gate has no
  median or maximum time, rather than an error.
- **Times and spreads are medians**, and failed and kept windings are listed in name order, whatever order the
  windings file and the orientation record give them in.
- **A read without a GPU log, a geometry record or a stacking record** records `None` for each, and carries no
  geometry per winding.
- **A canvas is given to four decimals.**
- **A winding with nothing rendered**, which has no ink share, is left out of the shares and the inspection order.
- **The reading turns are counted by kind**: both, upside down only and mirrored only. The inspection order stops at
  ten.

No code changed. No defect was found.

### Four mutants are equivalent

- **The no-tile list and the inspection order** are built from the summary's windings already sorted by name, so
  dropping their own sort or the name tie-break changes nothing.
- **Dropping the empty-canvas guard** changes nothing, because the spread of no values is already `None`.
- **Dropping the missing-folder guard on the disk size** changes nothing on this Python (3.10), where `rglob` on a
  missing folder yields nothing.

## Verified, no change needed

- **Finding 125's costs match its record.**
  - The flatten took 5,619 s (1 h 33 min 39 s), the renders 9,585 s (2 h 39 min 45 s), and Studio 15,866 s
    (4 h 24 min 26 s).
  - With the snap, orient and summarise, the stages add up to 31,678 s, the report's 8 h 48 min.
  - The renders take 102,387,820,838 bytes and Studio's maps 9,307,207,360 bytes: the report's 102.4 GB and 9.3 GB.
  - The canvases' median is 37.2614 million pixels (3.2568 to 60.816).
- **Finding 126's disk matches its record.** Its renders take 171.4 GB and its maps 15.4 GB.
- **The inspection order is the page's.** For the windings with a scored tile, it sorts by the largest tile's ink
  share, largest first, then by name. `band_index.order` sorts them the same way and puts the rest last.

## Observations for the owner (not changed)

- **The GPU log the record reads is not written by any script in the repository.** `run_fit.sh` and
  `run_flatten.sh` sample `nvidia-smi` themselves. `logs/studio_ARM_gpu_mib.log` comes from a sampler started by
  hand, so its window depends on when it was started.
  - Finding 126's report says so: its sampler covered only the last 22 windings' reads.
  - Its "10:34" is 18:34 UTC by the record's first epoch, so the report's clock is eight hours behind UTC.

  A sampler started by `run_studio_band.sh` would cover every read and date its window in one zone.

## Verification

- **The touched module.** `test_first_letters_band_record.py` gives 16 passed, against 10 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,109 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #208's run.
- **The 309 test modules outside the suite** give the same 24 failing ids as round #208's run.
  - 3,320 passed: round #208's 3,314 and the 6 new cases.
  - 4 xfailed, as in round #208.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `9666b6f`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`band_record.py` is unchanged.** Its mutants were run in a worktree.
- **#469 is now reviewed.** Rounds #207 to #209 took `band_index.py`, `band_geometry.py` and `band_record.py`. Round
  #204 had already compared finding 125's stacked pairs with its record.
- **Still not reviewed from the owner's merges since round #182:** #471 to #478, #480, #483, #485, #488, #489, #493,
  #496 and #505.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 27 were run again with the new tests: 23 are killed, and the four equivalent ones
  are not.
