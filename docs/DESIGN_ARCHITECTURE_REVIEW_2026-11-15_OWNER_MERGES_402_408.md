# Design and architecture review — the owner's #402 and #408

Date: 2026-11-15. Baseline: `c0eeecc` (main after round #168's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the firings from 15:12 to 18:12 UTC on 2026-11-15. It takes two of the seven PRs the owner merged
while the session was down:
- **#402** (merged 00:35 UTC on 11-14) is finding 109: the generator's two seam changes, the trim and the cross-block
  duplicate suppression, on ten cubes of Scrolls 1 and 5 that findings 106 to 108 never used. The decision is
  `CONFIRMED`.
- **#408** (merged 19:57 UTC on 11-13) makes the sampler in `scripts/neural_tracer_offref_location.py` read a voxel
  on the far face as itself.

The other five, #411, #421, #422, #423 and #424, are left to later rounds. So is #428, which the owner merged at
16:04 UTC during this round; it is merged into this branch.

## What changed

### Three guards are now tested

Both scripts are left as they are: finding 109's is registered, and the other is the owner's exploratory analysis.
This round made 27 mutants, 20 of finding 109's decision rule and 7 of #408's sampler. The PRs' own tests killed 23.
Two new tests kill three of the four survivors:

- **An ERLpen that did not move is not higher** (`tests/test_afv_generator_seam_confirmation.py`). P1 and P4 count
  the cubes whose ERLpen is above the other arm's. With three cubes exactly equal to main, P1 is 7 of 10 and the
  decision is `NOT_CONFIRMED`. With four cubes exactly equal to the trim, P4 is 6 of 10 and the decision is
  `TRIM_ONLY`. #402's test sets its losing cubes 1% below, so counting an equal cube as higher passed it.
- **The sampler does not cast a non-finite coordinate** (`tests/test_neural_tracer_offref_location.py`). #408
  replaces a NaN or an infinity before it floors the coordinates. Without that step the result is still NaN, but
  NumPy warns on the cast. The new test turns warnings into errors.

The fourth survivor changes P2 from "at least 0.10" to "above 0.10". #402's test has a case named for that bound,
but a ratio of two ERLpens minus one does not land on exactly 0.10, so no input reaches it.

## Verified, no change needed

- **Finding 109's decision recomputes.** `verdict(record["cubes"])` equals the stored verdict, no cube has an
  identity problem, and every margin is wide:
  - P1: ERLpen at tolerance 4 above main's on 10 of 10, against at least 8;
  - P2: median gain 0.3115 (0.0753 to 0.9028), against at least 0.10;
  - P3: merges at tolerance 2 from 325 to 297, against a limit of 341.25;
  - P4: above the trim alone on 10 of 10 (0.0320 to 0.1853, median 0.1019), against at least 7;
  - P5: median duplicated share from 0.4089 to 0.0425, against a limit of 0.2045.
- **The order of events.** The registration (9f3bf4f, 18:18 PST on 11-09) precedes the results (c443f40, 15:02 PST
  on 11-10). The script and its launcher are unchanged from the registration to the results and since, and the
  record is unchanged since the results.
- **The decision rule applies its rows in the table's order.** A P1 or P3 miss gives `NOT_CONFIRMED`, then a P4
  miss gives `TRIM_ONLY`, then a P2 or P5 miss gives `PARTIAL`. A missing cube or an identity problem gives no
  verdict. #402's tests kill a mutant of each, and of each of the five thresholds.
- **#408 changes values only on and past the far face.** Against the version before it, on 4,000 random points:
  - inside the volume the two are identical;
  - on the far face and past it the old one mixed in a thousandth of the voxel before, which moved a
    unit-variance volume's samples by up to 0.0034.
- **#408 keeps the script's own rule for a point outside the volume**: it is held on the boundary, where the other
  samplers reviewed this week return NaN. The docstring says so.

## Observations for the owner (not changed)

- **Finding 109's P2 case does not test its bound.** `d(both=0.10) == "CONFIRMED"` passes because 30 × 1.1 / 30 − 1
  is a hair above 0.10 in floating point, as it would with the bound made strict.
- **The off-reference analysis's record predates #408.** Its evidence file is dated 11-05. Samples on the far face
  can differ in the third decimal from what the script would compute now. The analysis is not registered and says
  it decides nothing.

## Verification

- **The touched modules.** Finding 109's two modules and the off-reference module give 61 passed, against 59 on
  `c0eeecc`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    two changed test files.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 221 modules give the same 173 failing ids as round #168's run.
- **The test modules outside the suite.** The 257 modules give the same 23 failing ids as round #168's run, and
  2,516 passed against 2,514: the two new tests.
- **The doc audit**, run alone, lists the same unresolved references as on `c0eeecc`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The baseline is round #168's branch run. `c0eeecc` differs from the tree that run used by one passing test case and
that round's record. Both sets of failing ids are this container's: it has no villa checkout.

## A note on this round's work

- **Finding 109 was checked from its record, not rerun.** The ten cubes and the model are on the owner's machine.
- **Its report and the documents that quote it were not checked line by line.** #402's report test binds the
  report to the record, and this round did not sample it.
- **The full runs were made before #428 was merged in.** After the merge I reran the three touched modules, ruff,
  mypy, the smoke test and the doc audit. #428 changes the dependency lock, and this container's environment was
  built from the earlier lock, so the CPU workflow is the check that uses the new one.
- **The usage limit interrupted the round once**, after the full runs.
- **Still not reviewed:** #411, #421, #422, #423, #424 and #428, the rest of #390 and the rest of #396.
