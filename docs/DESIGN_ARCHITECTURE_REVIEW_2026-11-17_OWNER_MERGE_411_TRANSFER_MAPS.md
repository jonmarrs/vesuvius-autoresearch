# Design and architecture review — the owner's #411, `transfer_maps.py`

Date: 2026-11-17. Baseline: `a5551a1` (main after round #181's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 04:12 UTC firing on 2026-11-17. Main had not moved.

It takes a third slice of **#411**, finding 110: `repro/first_letters/pherc343/mesh_step/transfer_maps.py`. That is
the module that carries the ink maps of fitted windings into the published segment's frame and runs P3's
comparison. It is also the shared map reader: finding 111 reads its maps through `map_file`, `read_map` and
`render_valid`, and finding 118 through `side`. Rounds #172 and #173 covered the analysis module's decision path
and measurements. Round #179 checked #442's change to `side`.

## What changed

### Fourteen guards of the map reader and the comparison are now tested (`tests/test_first_letters_343_mesh_step.py`)

The module is registered, so it is left as it is. This round made 27 mutants of it. The tests of findings 110, 111
and 118 killed 13. Six new test functions kill the other 14:
- **A villa map is scaled as the recipe's `ensemble_maps.py` scales it**, 64 to 192 onto 0 to 1 and clipped.
  **A Hecate map is divided by 255.** Each test reads a written file whose blocks hold known grey levels.
- **A map that is not 8-bit is refused, and so is a villa map of another size than the render.**
- **A letter box covers every lattice cell it touches.** The start is rounded down and the end up, in x and y
  separately, and a box past the edge is cut to the lattice.
- **A median normal cosine of exactly zero is refused.** On its own a zero would let a winding through whose
  render may sample the wrong side.
- **A winding that gives no cells has no cosine and is not refused.** It contributes nothing to the comparison.
- **The record's counts are what they are named.**
  - The windings' cells sum to the accepted cells.
  - The accepted fraction is over the published cells with CT.
  - A letter box's per-box r is taken only over accepted cells: a box half over cells with an empty CT layer
    counts only its accepted cells.

No code changed.

## Verified, no change needed

- **The map names follow the recipe's launcher**: villa layers from `depth + 25` and Hecate centred on
  `32.5 + depth`, with `_reverse` for the reading side. The tests of findings 110 and 118 bind both, at depths −2
  and +1.
- **Blocks with an empty CT layer in any of the 66 layers take no part**, on both renders. The existing test covers
  the published side.
- **The script never picks a side from the ink.** It measures the normals from the meshes. It stops for a winding
  whose normals point against the published ones unless its render was flipped, and it stops for a flipped render
  whose normals agree. The existing tests cover both.
- **A comparison at another depth is marked as not the registered one.** The existing test covers it.

## Observations for the owner (not changed)

- **The module is shared by three findings and was changed by the third.** Round #179 recorded that #442's change
  to `side` leaves finding 110's result unchanged. The new tests bind the reader that all three findings use as it
  stands now.
- **The fit launcher still carries on when its settings snippet fails** (round #175). It is unchanged on
  `a5551a1`.

## Verification

- **The touched module.** `test_first_letters_343_mesh_step.py` gives 94 passed, against 88 on `a5551a1`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,023 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #181's run.
- **The test modules outside the suite.** The 264 modules give the same 23 failing ids as round #181's run, and
  2,728 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `a5551a1`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Finding 110 was not rerun.**
- **Still not reviewed in #411:** `snap_chunks.py`, `s3_fetch.py` and `s3_plan.py`, the launchers, the setup files
  and the README.
- **Still not reviewed:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of #390 and
  #396, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the module. The three findings' test modules passed here before the mutants were
  run. The 14 survivors were run again against the new tests; the 13 the existing tests killed were not.
