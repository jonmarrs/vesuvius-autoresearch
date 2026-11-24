# Design and architecture review — the owner's #475, Studio without its empty windows

Date: 2026-11-24. Baseline: `a54148f` (main after round #217's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 02:12 UTC firing on 2026-11-24. Main had not moved since round #217's merge.

It takes **#475**, finding 132: does Studio give the same map, faster, without the windows whose crop holds no CT?
`repro/first_letters/pherc0211_control/studio_fast.py`:
- copies the loop of the winner's `inference.py`, using that file's own crop, Hann kernel and model loader;
- with `--skip-empty`, does not run a window whose 128-pixel crop has no pixel with CT;
- compares each map with its reference over the pixels with CT, and requires the skip to take at most 0.8 of the
  full loop's time on each band winding.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### Twenty-three more rules of the skip are tested (`tests/test_studio_fast.py`)

This round made 25 mutants of `studio_fast.py`, and #475's tests killed 2. Nine new test functions, 20 cases, kill the
other 23.
- **A window's crop reaches 16 pixels beyond it on each side.** Each side is pinned on both sides of the CT's edge:
  CT only in the 16 rows of context above a window, or only in the last 16 rows or columns of its crop. CT in any
  one of the 16 planes counts.
- **`predict` refuses 15 planes, 16-bit input and an empty batch.**
- **`predict` counts the winner's window starts.** With Hann blending, the last window lies flush with the bottom
  and right edges: 8 × 9 windows on a 400 × 500 input at stride 64, against 5 × 6 at 96 without blending.
- **The lines.** A map exactly at each line is the same map. The verdict needs pairs and ratios, and takes a ratio
  exactly at 0.8.
- **A pair is compared over the pixels any plane gives CT**, and is exact there even where it differs elsewhere.
- **The compare command** divides the skip's time by the full loop's, honours the steps' outcome, and runs once.
- **`run` checks first, before it looks for CUDA**: that the code it imported is the given `inference.py`, that its
  output does not exist, and that a stride other than 96 comes with Hann blending.

No code changed. No defect was found.

## Verified, no change needed

- **The crop rule matches the winner's crop, as #475's test copies it.** That crop takes rows y − 16 to y + 111,
  clipped to the image, and pads the rest by reflection from inside it. So a window whose clipped crop has no CT
  reads no CT, and it writes only to its central 96 pixels, which then have no CT either. The loop sets those pixels
  to 0 at the end.
- **The verdict is the registered table's.**
  - Every full map is identical to its reference over the CT.
  - Every skip map is the same map, with r 1.0, p99 0.0 and all pixels on the same side of 0.5. The largest
    difference is 0.00075, from the GPU's rounding in other batches, as the docstring expects.
  - The skip took 158.3 of 267.5 s on w062 (0.5918), and 168.1 of 290.8 s on w065 (0.5781).
  - So `SKIP_ADOPTED`, and the report's "0.58 to 0.59 of the time".
- **The skip ran fewer windows.** On w062 it ran 6,994 of 11,842 windows, and on w065 7,411 of 13,002.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_studio_fast.py` gives 31 passed and 1 skipped, against 11 passed and 1 skipped
  before. The skipped test compares the copied loop with the winner's own file, which is on the owner's machine only.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #217's run.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #217's run.
  - 3,408 passed: round #217's 3,388 and the 20 new cases.
  - 4 xfailed, as in round #217.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `a54148f`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`studio_fast.py` is unchanged.** Its mutants were run in a worktree. The loop runs on the CPU with #475's toy
  model and crop. `run`'s checks run up to its CUDA check, which this container would fail; nothing tests past it.
- **Still not reviewed from the owner's merges since round #182:** #476 to #478, #480, #483, #485, #488, #489, #493,
  #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 25 were run again with the new tests, and all 25 are killed.
