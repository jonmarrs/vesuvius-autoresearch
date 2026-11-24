# Design and architecture review — the owner's #476, the overlapped band read

Date: 2026-11-24. Baseline: `4184855` (main after round #218's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12 UTC firing on 2026-11-24. Main had not moved since round #218's merge.

It takes **#476**, which adds `FL_OVERLAP=1` to `repro/first_letters/eligible_band/run_studio_band.sh`. With it,
`render_and_read` renders the windings in the background, in order, while Studio reads each winding as soon as its
render is recorded. The commands, gates and logs are the serial read's; only when each runs changes. It is off by
default. PHerc. 0800's read, finding 133, is registered with it on.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### Four more rules of the overlap are tested (`tests/test_band_read_overlap.py`)

#476's tests run `render_and_read` with stand-ins for the render, Studio and the gate. They killed 7 of this round's
11 mutants. Four new test functions, on the same stand-ins, kill the other 4.
- **The done list is emptied first.** With a list left from before, Studio would read a winding whose render had
  not run. In the script this cannot arise, since the read refuses an existing output folder; the test checks the
  function on its own.
- **A winding waits for its own name, not for one it begins.** With w10 rendered before w1, w1 does not take w10's
  line.
- **A render recorded just as the renderer stops is still read.** In the test, the reader's check of the renderer
  waits until the renderer has rendered everything and gone, so only the last look at the done list finds the
  first winding.
- **The read waits for the renderer to finish before it reports.** With the renderer's own count slowed, its line
  still comes before the read's.

No code changed. No defect was found.

## Verified, no change needed

- **The overlap keeps the serial read's names.** #476's tests check that both reads log and gate each winding as
  `studio_render_wNNN` and `studio_studio_wNNN`, and that Studio never reads a winding before its render is done.
- **A bad value stops the read.** `FL_OVERLAP` other than 0 or 1 exits 2 before anything runs, and the serial read
  is the same two lines as before.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_band_read_overlap.py` gives 9 passed, against 5 before. Three runs in a row gave
  the same.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #218's run.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #218's run.
  - 3,412 passed: round #218's 3,408 and the 4 new cases.
  - 4 xfailed, as in round #218.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `4184855`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_studio_band.sh` is unchanged.** Its mutants were run in a worktree. Two new tests replace a shell command
  inside the test's own script only: `kill`, so that the reader waits for the renderer to go, and `awk`, so that the
  renderer's count is slow. Neither touches the script under test.
- **Still not reviewed from the owner's merges since round #182:** #477, #478, #480, #483, #485, #488, #489, #493,
  #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 11 were run again with the new tests, and all 11 are killed.
