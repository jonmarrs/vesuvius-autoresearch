# Design and architecture review — the owner's #442, finding 118's reader control

Date: 2026-11-17. Baseline: `fa2e2a7` (main after round #178's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 01:12 UTC firing on 2026-11-17. Main had not moved.

It takes **#442**, merged at 00:12 UTC on 11-17. #442 is finding 118, the reader half of a positive control.
PHerc. 211's First Letters prize was awarded on 11-15, and the winner published the surface, the probability map
and the CT image. Finding 118 rendered that surface here, ran the recipe's four ink models on it, and compared
their map with the winner's. The decision is `READER_AGREES`. The script is
`repro/first_letters/pherc0211_control/compare.py`. #442 also changed `transfer_maps.py`, finding 110's
registered module.

## What changed

### Seven guards of the comparison are now tested (`tests/test_first_letters_0211_reader_control.py`)

The script is registered, so it is left as it is. This round made 28 mutants of it. #442's tests killed 21. Six new
test functions kill the other 7:
- **A shift of one pixel is aligned and a shift of two is not.**
- **The alignment searches 16 pixels each way**, and finds a shift of exactly 16.
- **The alignment compares only pixels with CT in every layer.** A layer that is the CT over the half where it has
  CT is chosen over a noisy copy that covers everything.
- **A shifted r leaves out what slid in from outside the mask.**
- **A rightward roll of cells blanks the columns it brings in.** #442's test covered a leftward roll.
- **The winner's map loses its broad background before it is compared.** Without that step a slope across the map
  would hide strokes that agree.

No code changed.

## Verified, no change needed

- **The decision recomputes from the record.** `verdict(record["registered"], record["cell_share"])` gives
  `READER_AGREES`:
  - the alignment found layer 33, the mesh layer, at no shift, with r 0.8128;
  - 550,480 of the mask's 550,482 cells were compared, against at least half;
  - r is 0.53, against at least 0.30, and 5.7 times the larger control: −0.0059 for the other side and 0.093 for
    the largest 64-pixel slide.
- **The change to finding 110's module does not change finding 110.** `transfer_maps.side` used to read the other
  side at depth +1 whatever depth it was given. It now reads it at the depth asked for, and #442 tests that at
  depths −2 and +1. Finding 110 reads the other side only through the published-side call, at the default depth of
  +1, where the old and new code read the same files.
- **The report states that defect and how it was handled.** In the first record, all six other-side entries of the
  depth table were the depth +1 value. `compare.py --recheck`, added for this, measured everything again. The
  registered numbers and the verdict came out identical. The committed record keeps the recheck's table, the
  first record's other-side values and the recheck's `registered_reproduces: true`, and #442's report test binds
  all three.
- **The order of events.** The registration (11ba1c4, 22:49 PST on 11-15) precedes the results (7d31857, 09:46 PST
  on 11-16). Between the two, `compare.py` gained the `--recheck` option and `transfer_maps.py` the depth fix.
  Neither changes how the registered numbers are computed. An hour later 69994a5 corrected one limit in the report:
  which of the four models could have seen PHerc. 211. It says that Hecate's training scrolls are not fully listed.

## Observations for the owner (not changed)

- **Finding 110's registered module was changed by a later finding.** The change is a correct fix with a test, and
  it does not touch finding 110's result, but the module is now not the code that ran finding 110. Finding 110's
  record names the scripts as run. A note in finding 110's report, or a copy of the module for finding 118, would
  keep "as run" exact. This round did not make either change, because both are the owner's records.
- **The fit launcher still carries on when its settings snippet fails** (round #175). It is unchanged on
  `fa2e2a7`.

## Verification

- **The touched module.** `test_first_letters_0211_reader_control.py` gives 16 passed, against 10 on `fa2e2a7`.
  With the report's module that is 23 passed, against 17.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,023 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #178's run.
- **The test modules outside the suite.** The 264 modules give the same 23 failing ids as round #178's run, and
  2,722 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `fa2e2a7`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Finding 118 was checked from its record, not rerun.** The run needs the winner's files, the scan, the four
  models and a GPU.
- **The report's reading of the images was not checked.** "Draws no readable letter" is the owner's judgement, and
  the report says what the image shows.
- **Not reviewed in #442:** `described`, `write_image`, the launchers and the fetch script, and the edits to
  `docs/RESEARCH_STRATEGY.md`.
- **Still not reviewed:** #433, #436 and #437, #422, #424 and #428, the rest of #390, #396 and #411, and the parts
  of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the script. Both of its test modules passed here before the mutants were run.
  The 7 survivors were run again against the new tests; the 21 that #442's tests killed were not.
