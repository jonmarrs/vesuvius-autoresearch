# Design and architecture review — the owner's #421

Date: 2026-11-16. Baseline: `6ef70b7` (main after round #169's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the hourly firings from 20:12 to 23:12 UTC on 2026-11-15. Main had not moved. It takes one of the
PRs the owner merged while the session was down: **#421**, merged at 00:05 UTC on 11-14.

#421 is finding 111. It ran the First Letters recipe's render and its four released ink models on three published,
labelled segments of PHerc. 0841, a scroll with known ink that is not prize-eligible. The decision is
`BLOB_LEVEL_SIGNAL`: the models find the labelled ink, but not at the level registered as letter level. The result
decides what a blank or a dark image on an eligible scroll would mean, so this round recomputed it from its record
and tested the script that produced it.

The other merges, #411, #422, #423, #424 and #428, are left to later rounds.

## What changed

### Forty guards of the registered script are now tested (`tests/test_first_letters_0841_surface_control.py`)

`repro/first_letters/pherc0841/surface_control.py` is registered, so it is left as it is. This round made 62 mutants
of it. #421's tests killed 22. They cover the score, the choice of depth and the table, but none of them runs a
command of the script or reads a held-out segment. Fifteen new test functions (24 cases) kill the other 40:

- **The registered lines are "at least".** An AUC of exactly 0.60 holds P1, a reading exactly 0.05 above its floor
  holds it, and exactly 0.75 holds P2. #421's table cases all sit clear of the lines.
- **The cell classes are the registration's.** A cell is supervised from 99%, ink from a labelled share of one
  half, and bare only at zero. The registration's sentence is now bound to the three constants.
- **A slide moves the map its own way and scores only the cells it covers**, in each of the four directions. Cells
  that wrapped round the edge, and cells whose slid value came from an unrendered cell, are left out. #421's test
  checked the wrap of the downward slide only.
- **The floor is the largest of the four slides.** A slide is scored only on 1,000 cells of each class, and when no
  slide can be scored there is no floor.
- **A segment is scorable from 1,000 scored cells of each class.**
- **A held-out reading scores the chosen side on the scored cells**, takes its floor on the same cells, reports
  the other side, and sets P1 and P2 from those.
- **`sweep` scores every depth of the range on both sides** and refuses a segment with too few scored cells.
- **`confirm` reads each held-out segment at the chosen depth and side.** It reads nothing, and returns
  `DOES_NOT_RUN`, when the sweep chose nothing, a step exited non-zero or a step left no record. #421 tested that
  row of the table on `verdict` alone.
- **An output that exists is refused and left as it was.** #421's test of this reads the script's text for the
  message.
- **The instrument carries the 2.4 µm mesh with the published transform** and reads the two mesh files it names.
  It uses only valid nodes of either mesh, gives the offset along the normal with its sign and the offset across it
  without the normal part, and passes only when every segment is within both limits on either side of the surface.

No code changed.

## Verified, no change needed

- **The decision recomputes from the record.** `verdict(record["steps"], record["held_out"])` equals the stored
  verdict, and the stored P1 and P2 flags are what `p1_holds` and `p2_holds` give:
  - P1: AUC 0.7478 and 0.7194, against at least 0.60, and 0.2215 and 0.1904 above the floors of 0.5263 and 0.5290,
    against at least 0.05;
  - P2: the same two AUCs against at least 0.75, short by 0.0022 and 0.0306;
  - all six steps exited 0, each floor is the largest of its four slides, and the smallest class on any segment
    has 18,119 cells against the minimum of 1,000.
- **The choice recomputes.** `choose` on the 34 rows of the sweep gives depth −2 on the `_reverse` side at 0.7641.
  The next rows are 0.7577 and 0.7554, so no tie-break was used.
- **The report's account of the sweep matches the table**: 0.645 at depth −8, 0.764 at −2 and 0.578 at +8 on the
  `_reverse` side, within 0.01 of the peak from −3 to 0, and 0.490 to 0.558 on the forward side.
- **The order of events.** The registration (3e3487f, 12:30 PST on 11-13) precedes the results (0eee777, 15:38 PST
  on 11-13). The script and its launchers are unchanged from the registration to the results and since, and the
  record is unchanged since the results. The results commit added `describe.py`, which computes the report's
  unregistered figures.
- **The report states how thin P2's margin is.** It says that 0.748 against 0.75 is thin, that 0.75 lies inside the
  resampling spread on both held-out segments, that the line was a judgement, and that a better-aligned position
  would read 0.756 and was not used. The verdict does not rest on the thin one: P2 must hold on both segments, and
  the second is 0.031 short.
- **The lines are applied to the rounded values the record stores**, so the record alone reproduces the verdict.

## Observations for the owner (not changed)

- **The margin rule can fail at exact equality.** P1 asks for an AUC "at least 0.05 above" the floor, and the
  script tests `value >= floor + 0.05` on values rounded to four places. In floating point 0.55 + 0.05 is a hair
  above 0.60, so an AUC of 0.6000 over a floor of 0.5500 fails P1. Of the 4,500 four-place floors from 0.5000 to
  0.9499, a reading exactly 0.05 above fails for 1,798. This record's margins are 0.19 and 0.22, so it is not
  affected. A later registration with a margin could compare in ten-thousandths.
- **`confirm` does not ask whether a held-out segment is scorable.** `sweep` refuses a development segment with
  fewer than 1,000 cells of either class. `confirm` has no such check. A held-out segment with no ink cells has no
  AUC, fails P1 and gives `NO_SIGNAL`, and so does one whose floor no slide could score. "Could not be measured"
  is nearer to `DOES_NOT_RUN`. It did not arise here.
- **Two step times in the report differ from the record by a second.** The cost table gives 17 min 32 s and
  16 min 10 s for the held-out ink steps. The record gives 1,051 s and 969 s, which are 17 min 31 s and
  16 min 9 s. The table's GPU peaks are the record's MiB divided by 1,000: 3,426 MiB is given as 3.4 GB. #421's
  report test does not cover the cost table.

## Verification

- **The touched module.** `test_first_letters_0841_surface_control.py` gives 42 passed, against 18 on `6ef70b7`.
  With the report's module that is 48 passed, against 24.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 222 modules give the same 173 failing ids as round #169's run.
- **The test modules outside the suite.** The 257 modules give the same 23 failing ids as round #169's run, and
  2,540 passed against 2,516.
- **The doc audit**, run alone, lists the same unresolved references as on `6ef70b7`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

`6ef70b7` itself was not rerun. It differs from the tree of round #169's run by #428, which adds one module to the
suite, and from this branch by one test module that has no failing id. Both sets of failing ids are this
container's: it has no villa checkout.

## A note on this round's work

- **Finding 111 was checked from its record, not rerun.** The run needs the scan, the four models and a GPU.
- **The two figures and the report's reading of them were not checked.** "No labelled letter can be read from the
  map alone" is the owner's judgement, and the report says so.
- **Not reviewed in #421:** the launchers, `describe.py` and the edits to `docs/RESEARCH_STRATEGY.md`. A later
  merge added `surface_control_v2.py` beside the registered script, and it was not reviewed either.
- **Still not reviewed:** #411, #422, #423, #424 and #428, the rest of #390, and the rest of #396.
- **The mutants are a sample** of the script's checks. Both of #421's test modules passed here before the mutants
  were run. The 40 survivors were run again against the new tests; the 22 that #421's tests killed were not.
- **The session was interrupted** by the usage limit and by worker restarts between 20:12 UTC on 11-15 and
  00:11 UTC on 11-16.
