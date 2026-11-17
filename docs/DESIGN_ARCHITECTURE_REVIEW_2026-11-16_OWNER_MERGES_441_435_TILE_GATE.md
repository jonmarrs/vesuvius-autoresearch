# Design and architecture review — the owner's #441 and #435, the band verdict fix and the tile gate

Date: 2026-11-16. Baseline: `76f7001` (main after #441).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 23:12 UTC firing on 2026-11-16. Main moved before the round began, with #441.

It takes two of the owner's merges:
- **#441**, merged at 22:33 UTC on 11-16, changes `repro/first_letters/eligible_band/band_fit_verdict.py` so that
  a full fit with no scored winding is recorded as `DOES_NOT_RUN`. Rounds #171 and #173 to #176 reported that
  defect.
- **#435**, merged at 06:18 UTC on 11-16, is finding 117. It asks whether the sheet-following score, taken per
  tile of about 380 voxels, picks out the tiles of a fitted winding that lie on the published sheet. The question
  is measured on PHerc. 343, finding 110's fit. The decision is `LOCAL_GATE_WORKS`. The script is
  `repro/first_letters/pherc343/tile_gate/tile_gate.py`.

## What changed

### Twenty-three guards of the tile gate are now tested (`tests/test_first_letters_343_tile_gate.py`)

The tile gate is registered, so it is left as it is. This round made 38 mutants of it. #435's tests killed 14. Ten
new test functions (18 cases) kill 23 of the other 24. The last starts the floor's shifts at zero, which the
script already leaves out, because zero is a whole number of every winding's widths.

- **The registration states the tile and the lines the code uses**: 19 nodes, 2 voxels and 0.07.
- **The table holds at its bounds.** It covers 15 tiles of each label, and an AUC exactly on the floor, including a
  floor above 0.75. It covers an AUC of exactly 0.60 and exactly 0.75, and a share at the line exactly 0.15 above
  the share overall.
- **A tile half on the sheet is right, and a tile at the 0.07 line is counted.**
- **The floor slides each winding by its own width.** The test works a two-winding case by hand from the
  docstring: shifts 1 to 4, the two-tile winding sitting out shifts 2 and 4, a 95th percentile of 0.475 and a
  maximum of 0.5.
- **A tile is kept from 200 scored nodes and from half its valid nodes covered**, `within` counts the 2-voxel line
  and only covered nodes, and only whole tiles are read.
- **The distance to the published winding** counts a partner exactly 30 voxels sideways. It is the least over the
  nearest nodes that have a normal, not the distance to the single nearest node.
- **A node on the face of a sheet is inside it**, and a node needs all three readings to be scored.

No code changed.

## Verified, no change needed

- **#441 records a full fit with no scored winding.** It computes P1 and P2 only from a summary that scored
  windings, and `by_index` returns no parts when there are none. On `76f7001`, a full fit with no scored winding
  is recorded as `DOES_NOT_RUN` with both flags false. A smoke fit with none still records the full arm's reading,
  and a full fit with 30 scored windings does not run. #441's two tests kill each of three mutants of the fix.
- **Finding 117's decision recomputes from the record.** `verdict(record["raw"])` gives `LOCAL_GATE_WORKS`:
  - 53 right and 17 wrong tiles, against at least 15 of each;
  - an AUC of 0.8946, above the floor's 95th percentile of 0.7772 (a margin of 0.1174) and above 0.75;
  - all 32 tiles at 0.07 or above are right, against 75.71% of all tiles, a gain of 0.2429 against 0.15.
- **The script ran once, in 10 seconds, and exited 0.**
- **The order of events.** The registration was committed at 18:49:16 PST on 11-15 (381705e) and the results at
  18:53:30 (474017c). A minute later d57b316 corrected one figure in the report, the margin over the floor, from
  0.118 to 0.117. The record gives 0.1174.
- **The registration is explicit about what the result would allow.** It frames finding 117 as narrowing finding
  116's consequence. Under `LOCAL_GATE_WORKS`, a read of an eligible band may choose tiles by tile excess,
  registered separately. Whether to do so it leaves to the owner, after finding 116.

## Observations for the owner (not changed)

- **Finding 117 was measured on a fit that turns the published way.** Finding 116 found the score blind to the
  direction of the turns. Whether the high-excess tiles of a wrong-direction fit also lie on the right sheet was
  not measured. That matters for a scroll whose direction is not published, such as PHerc. 0125. The
  registration's limits name one scroll, two windings and one fit.
- **The registration was committed four minutes before the results.** The commit order is the only evidence that
  the registration came first. The script takes 10 seconds, and the registration says no tile had been scored or
  labelled when it was written.
- **The fit launcher still carries on when its settings snippet fails** (round #175). It is unchanged on
  `76f7001`.

## Verification

- **The touched module.** `test_first_letters_343_tile_gate.py` gives 24 passed, against 6 on `76f7001`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,020 files, with `--python-executable ./.venv/bin/python`.
- **The suite's guard against bare file names** in tests passes.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #176's run.
- **The test modules outside the suite.** The 262 modules give the same 23 failing ids as round #176's run, and
  2,699 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `76f7001`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Finding 117 was checked from its record, not rerun.** The run needs finding 110's windings and the distance
  field, which are on the owner's machine.
- **Not reviewed in #435:** `measure`, `main`, the snapped description, the report beyond its verdict and floor,
  and the edits to `docs/RESEARCH_STRATEGY.md`.
- **Still not reviewed:** #433, #436, #437 and #443, #422, #424 and #428, the rest of #390, #396 and #411, and the
  parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the tile gate. Its two test modules passed here before the mutants were run.
  The 24 survivors were run again against the new tests; the 14 that #435's tests killed were not.
