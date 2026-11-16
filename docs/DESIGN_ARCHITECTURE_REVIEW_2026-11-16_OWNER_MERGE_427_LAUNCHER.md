# Design and architecture review — the owner's #427, finding 115 and the fit launcher

Date: 2026-11-16. Baseline: `2209c8d` (main after round #174's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 21:12 UTC firing on 2026-11-16. Main had not moved.

It takes **#427**, merged at 02:19 UTC on 11-16. #427 is finding 115: PHerc. 0826's band fitted again with villa's
outer winding set to 80 in place of 130, the change finding 114's consequence named. The decision is
`PARTLY_ON_SHEETS`, with P3 `HELPS`. #427 changed two scripts in `repro/first_letters/eligible_band/`:
- `band_fit_verdict.py` takes the two arms to read as arguments;
- `run_fit.sh`, the fit launcher, gains the `outerN` arms. A later commit (8b8b348, for finding 116) added the
  `outerN-otherhand` arms, which fit the same band with the spiral declared to turn the other way.

The launcher decides which fit each of findings 112 and 114 to 116 ran. This round recomputed finding 115 from its
record and tested the two scripts' new code.

## What changed

### The fit launcher's own blocks now run in tests (`tests/test_first_letters_eligible_band.py`)

Both scripts ran registered findings, so they are left as they are. #427's tests of the launcher matched its text.
This round made 25 mutants: 21 of the launcher and 4 of the verdict script's argument handling. The existing tests
killed 7. Six new test functions (18 cases) kill 17 of the other 18. The last swaps two entries of a dictionary
literal, which changes only their order, so no test can see it.

The new tests cut each block out of `run_fit.sh` and run it, in bash or in Python:
- **Each arm is read as the comment says.** `full`, `smoke`, `outer80`, `outer80-smoke`, `outer80-otherhand` and
  `outer80-otherhand-smoke` each give the right kind, outer winding, direction flag and step count. Before this
  round, a launcher that read `outer80-otherhand` as a smoke arm, or did not flip it, passed every test.
- **An arm it does not know is refused**: `outer0`, `outer80x`, `outer8-0-smoke` and a name that is no arm. So is a
  step count given to a full arm, and a smoke arm without one.
- **The settings villa is given are the recipe's**, and an outer arm adds exactly the two winding settings, N and
  N + 3. The z range and the step count are the ones passed in.
- **An `otherhand` arm fits a copy of the dataset turned the other way.** The copy's description differs from the
  published one only in `spiral_outward_sense`, in either direction. Its tracks link to the published ones, its
  umbilicus is a copy, and the published description is left as it was. An arm that does not flip fits the
  published dataset and makes no copy.
- **The verdict command takes both arms or neither.** One arm, or three, prints the usage and writes nothing.

No code changed.

## Verified, no change needed

- **The decision recomputes from the record.** `verdict(record["steps"], record["smoke"], record["full"])` gives
  the stored verdict, and both stored flags are what `holds` gives:
  - all three steps exited 0, and each fit has 70 scored windings against at least 60;
  - the floor, the 300-step fit's median excess, is 0.0003 against at most 0.03;
  - P1 fails on the share positive: 55 of 70 windings, 78.57% against 80%. One more would have held it;
  - P2 holds: a median excess of 0.1026 against at least 0.03, and 78.57% against at least 65%.
- **P3 recomputes.** Its line, 0.0925, is 0.01 above the baseline of 0.0825 that the registration fixed before
  the run. The median of 0.1026 is above it, so `HELPS`. #427's report test binds the line, the label and the
  margin.
- **The order of events.** The registration (49a5bc6, 21:31 PST on 11-14) precedes the results (32941ae, 06:23
  PST on 11-15). Nothing in `repro/first_letters/eligible_band/` changed between the two. The launcher changed
  nine minutes after the results, for finding 116; that change adds arms and leaves the `outer80` arms as they
  were, which the new tests confirm.
- **The report matches the record**: 0.103 against the line of 0.0925, 78.6% positive, 70 scored windings, and
  0.083 and 75.7% for the same 70 indices in finding 114's fit. It says the registered verdict was right and the
  P3 prediction wrong.

## Observations for the owner (not changed)

- **The fit launcher carries on when its settings snippet fails.** `FIT_SPIRAL_CONFIG_OVERRIDES=$(...)` has no
  `|| exit`, and the launcher does not use `set -e`. With `FL_Z_BEGIN=10250x`, the snippet raises a `ValueError`,
  the variable is empty, and the launcher goes on to start the fit. How villa reads an empty value was not
  checked, because this container has no villa checkout. The arm parsing rejects a bad outer winding first, so
  today only the z range and step count from the environment can reach this. The flip snippet just above it does
  end in `|| exit 2`.
- **The band verdict command still fails on a full fit with no scored winding.** Rounds #171, #173 and #174
  reported it. It is unchanged on `2209c8d`.

## Verification

- **The touched module.** `test_first_letters_eligible_band.py` gives 64 passed, against 46 on `2209c8d`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,020 files, with `--python-executable ./.venv/bin/python`.
- **The suite's guard against bare file names** in tests passes.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #174's run.
- **The test modules outside the suite.** The 262 modules give the same 23 failing ids as round #174's run, and
  2,670 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `2209c8d`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Finding 115 was checked from its record, not rerun.** The run needs the scan, villa's fit and a GPU.
- **The launcher's fit, timing and GPU trace were not run.** The tests run the blocks before the fit starts.
- **Not reviewed in #427:** the report below its score table and the edits to `docs/RESEARCH_STRATEGY.md`.
- **Still not reviewed:** #433, #434 (finding 116), #435, #436, #437 and #443, #422, #424 and #428, the rest of #390,
  #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the two scripts. Both touched test modules passed here before the mutants were
  run. The 18 survivors were run again against the new tests; the 7 that the existing tests killed were not.
