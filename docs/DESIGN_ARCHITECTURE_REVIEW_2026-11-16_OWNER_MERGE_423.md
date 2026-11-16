# Design and architecture review — the owner's #423

Date: 2026-11-16. Baseline: `643450f` (main after round #170's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:12 UTC firing on 2026-11-16. Main had not moved. It takes another of the PRs the owner
merged while the session was down: **#423**, merged at 15:25 UTC on 11-14.

#423 is finding 112, the First Letters campaign's first step on a prize-eligible scroll. It ran the PHerc. 343
recipe's spiral fit, unchanged, on one band of PHerc. 0211 and asked whether the windings it writes follow
predicted sheets. The decision is `ON_SHEETS`. Two scripts produce it, both in
`repro/first_letters/eligible_band/`:
- `band_fit_quality.py` scores each raw winding against the distance field of the surface prediction;
- `band_fit_verdict.py` applies the registered table to the two fits' scores.

This round recomputed the decision from its record and tested both scripts. The last section lists what of #423
it did not review.

## What changed

### Forty-eight guards of the two scripts are now tested (`tests/test_first_letters_eligible_band.py`)

Both scripts ran finding 112, so they are left as they are. This round made 62 mutants: 29 of the verdict script
and 33 of the score script. #423's tests killed 14. Thirteen new test functions (20 cases) kill the other 48:

- **The distance field is read at (x, y, z) points in working voxels.** #423's tests score windings against a
  stand-in field, so nothing read the class that opens the real one. The new tests build a small field and check
  the axis order, the cell size of group 1 and of group 2, the nearest cell, the offset and the unit, the cell
  that holds no value, and a point one cell outside either face.
- **A winding is scored from 1,000 nodes**, and a node only where it and both displaced copies have a value.
- **A node on the face of a sheet is inside it**, for the node and for its displaced copies, and the two copies
  are averaged.
- **An invalid node is not scored**, even when its neighbours are valid.
- **The summary's two percentiles and its median share are what they are named**, and a winding at exactly zero is
  not positive.
- **The score command reads raw windings once.** It skips spliced twins and folders that hold no mesh, opens
  group 1 unless told otherwise, and refuses an output that exists.
- **The table's rows apply in the registered order and at their bounds.** One failed step among several, a missing
  smoke score, 60 against 59 scored windings in either fit, a floor of exactly 0.03, and a run that did not run
  with a floor that would also fail.
- **The verdict command reads the three gates and both arms.** A gate that is missing or failed, for each of the
  three steps, gives `DOES_NOT_RUN`, and so does a missing full arm.
- **The thirds round their size up**, count a winding at exactly 0.07, and take the median of an odd and of an
  even part.

No code changed.

## Verified, no change needed

- **The decision recomputes from the record.** `verdict(record["steps"], record["smoke"], record["full"])` equals
  the stored verdict, and both stored flags are what `holds` gives:
  - all three steps exited 0, and each fit has 120 scored windings against at least 60;
  - the floor, the 300-step fit's median excess, is 0.0004 against at most 0.03;
  - P1: a median excess of 0.0862 against at least 0.07, and 88.33% of windings positive against at least 80%.
- **The thirds add up to the whole.** Their positive windings are 32, 39 and 35, which is the 106 of 120 that the
  summary's share gives. Their windings at 0.07 or above are 24, 26 and 19, the report's 69.
- **The code's table is the registration's**, row for row, and #423's test binds its six constants to the
  registration's text.
- **The score script is unchanged since the registration** (4a2a6f8, 17:26 PST on 11-13), and so is the fit's
  launcher. Nothing in the directory has changed since the results (846ecbd, 23:17 PST on 11-13), nor has the
  record or the registration.
- **The report's top table and its thirds match the record**, and its "62% of PHerc. 343's" is 0.0862 over 0.1396.

## Observations for the owner (not changed)

- **The verdict command fails on a full fit with no scored winding.** `verdict` returns `DOES_NOT_RUN` for it,
  as the table says. `main` does not get that far: it asks `holds` for P1 on a summary that has no median, raises
  `KeyError: 'excess_median'` and writes no record. `by_index` would fail next, on a part size of zero. A fit that
  wrote no windings, or a wrong mesh folder, is the case the first row exists for. Finding 112 had 120 scored
  windings, so its record is not affected. For the next band: compute the two flags only when windings were
  scored, and return no parts when none were.
- **Two launcher files changed, and the verdict script was added, between the registration and the results.**
  - At 19:33 PST the search for a fit's mesh folder moved from `run_quality.sh` into a function in `env.sh`. The
    loop is the same.
  - At 21:42 PST the verdict script was added. That is 4 h 16 min after the registration. The three steps take
    3 h 36 min, so the fit may have finished before the script was committed. The record does not say.
  What the script encodes is the registration's table, so this does not change the decision.
- **"Fewer than 60 windings are scored" does not say in which fit.** The script asks for 60 in both. The report
  states both counts.
- **The verdict command replaces an output that exists.** The score command refuses one. The verdict is a function
  of the run directory alone, so running it twice gives the same record.

## Verification

- **The touched module.** `test_first_letters_eligible_band.py` gives 29 passed, against 9 on `643450f`. With the
  report's module that is 35 passed, against 15.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 222 modules give the same 173 failing ids as round #170's run.
- **The test modules outside the suite.** The 257 modules give the same 23 failing ids as round #170's run, and
  2,560 passed against 2,540.
- **The doc audit**, run alone, lists the same unresolved references as on `643450f`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The baseline is round #170's branch run, whose tree is `643450f`'s. Both sets of failing ids are this container's:
it has no villa checkout.

## A note on this round's work

- **Finding 112 was checked from its record, not rerun.** The run needs the scan's surface prediction, villa's
  fit and a GPU. The windings and the score of each winding are on the owner's machine only.
- **The new tests bind the score script to the convention it states**, not to villa. Whether `make_surf_sdt`
  writes its offset, unit and scale as the script reads them was not checked: this container has no villa
  checkout. The report's profile along the normal, with one peak at zero displacement, is the evidence that the
  reading is right.
- **Not reviewed in #423:** the fit, distance-field, sense, snap, flatten and render launchers, the three setup
  scripts, the November filing draft, the edits to `docs/RESEARCH_STRATEGY.md`, and the report below its second
  table.
- **Still not reviewed:** #411, #422, #424 and #428, the rest of #390, the rest of #396, and the parts of #421
  that round #170 listed.
- **The mutants are a sample** of the two scripts' checks. Both of #423's test modules passed here before the
  mutants were run. The 48 survivors were run again against the new tests; the 14 that #423's tests killed were
  not.
