# Design and architecture review — the owner's #471, the snap's batches and passes

Date: 2026-11-23. Baseline: `5b8f4eb` (main after round #211's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 20:12 UTC firing on 2026-11-23. Main had not moved since round #211's merge, which took in the
owner's #517 (finding 129, PHerc. 0813's band read). #517 is listed below for a later round.

It takes more of **#471**: `repro/first_letters/eligible_band/run_snap.sh`, which snaps an arm's raw windings with
the recipe's `snap_meshes.py`. #471 made it snap the windings in batches of `SNAP_BATCH` (12 by default) into one
folder, so that a denser grid's samples fit in memory. Finding 134's amendment (`21c0943`) later added
`FL_SNAP_PASSES`, which snaps each pass's output again. Before each pass the script fetches the surface prediction's
chunks the windings can touch, and checks offline that none is missing. After the last pass it checks that every
winding was written.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### The snap is run, not only read (`tests/test_first_letters_0358_band.py`)

#471's test of the batches reads the script's `split` line and simulates it. That killed 1 of this round's 15
mutants. Four new test functions, 6 cases, run a copy of the script beside a copy of `env.sh`. The recipe's snap and
the chunk check are logging stubs. They kill all 15.
- **The chunks are checked online, then offline, and the windings are snapped in batches into one folder.** With 25
  windings and batches of 12, that is three runs of 12, 12 and 1, and every winding is written.
- **With `FL_SNAP_PASSES=3`, each pass snaps the one before, with its own chunk manifest.** The passes write
  `snap_a.pass1` and `snap_a.pass2`, with manifests `snap_chunks_a.json`, `snap_chunks_a.pass2.json` and
  `snap_chunks_a.pass3.json`, and the last pass writes `snap_a`.
- **A failed batch, a failed pass, or a winding left unwritten stops the snap with a failed gate.** No later batch or
  pass runs.
- **An empty list, passes outside 1 to 5, and an earlier output or pass folder are refused** before anything runs.

No code changed. No defect was found.

## Verified, no change needed

- **One pass runs the snap as before the passes were added.** With `FL_SNAP_PASSES` unset, the chunk manifest is
  `snap_chunks_ARM.json` and the output `snap_ARM`, read from the fit's meshes, as the script's header says.
- **A failure leaves the arm refused.** A snap that stops partway leaves `snap_ARM` behind, and the next run refuses
  it, as "a step is run once per arm" intends.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_first_letters_0358_band.py` gives 22 passed, against 16 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, now 1,110 files with #517's test module, with
    `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #211's run.
- **The 310 test modules outside the suite**, round #211's 309 and #517's new one, give the same 24 failing ids as
  round #211's run.
  - 3,348 passed: round #211's 3,328, #517's 14 and this round's 6.
  - 4 xfailed, as in round #211.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `5b8f4eb`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_snap.sh` is unchanged.** Its mutants were run in a worktree.
  - This container has no GNU time, which the script runs as `/usr/bin/time -v`. The tests' copy points that one
    path at a stub that drops `-v`, and checks that it occurs once. Nothing else in the copy changes.
  - The header's claim that batches give byte-identical output rests on the owner's check of two of PHerc. 0826's
    windings. It could not be rerun here, because the recipe's snap is not in this container.
- **Still not reviewed from the owner's merges since round #182:** the rest of #471 (the read's winding list and
  tiling in `run_studio_band.sh`), #472 to #478, #480, #483, #485, #488, #489, #493, #496, #505, #517 and #522.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 15 were run again with the new tests, and all 15 are killed.
