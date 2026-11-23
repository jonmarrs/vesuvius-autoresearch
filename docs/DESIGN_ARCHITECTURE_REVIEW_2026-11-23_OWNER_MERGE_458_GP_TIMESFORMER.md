# Design and architecture review — the owner's #458, the Grand Prize TimeSformer comparison

Date: 2026-11-23. Baseline: `8b0987c` (main after round #200's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 09:12 UTC firing on 2026-11-23. Main had not moved since round #200's merge.

It finishes **#458**, finding 122. Round #200 took its pickle audit. This round takes
`repro/first_letters/pherc0211_control/gp_timesformer.py`, which has two steps:
- `segments` lays finding 118's 66-layer render out as the 2023 Grand Prize script reads a segment, in both layer
  orders. Each order holds only the 26 layers its window reads, chosen so that the surface sits where the model was
  trained to find it.
- `compare` scores the model's two predictions as finding 120 scored Reader V3: the reversed order is the reading
  side and the forward order its other side. Reader V3 is described beside it.

The script is registered, so this round adds tests only.

## What changed

### Sixteen more rules of the comparison are tested (`tests/test_first_letters_0211_gp_timesformer.py`)

This round made 18 mutants of `gp_timesformer.py`, and #458's tests killed none of them. Nine new test functions,
14 cases, kill 16. The other two are equivalent, below.

- **`segments` refuses a render of another depth or another type**: 65 layers, or 16-bit.
- **A prediction that cannot be read, or is short in either dimension, is refused.** The script pads its output to
  multiples of 256, and a prediction smaller than the render would mean a different input.
- **The alignment's three uses**, with finding 118's `alignment` stubbed:
  - a shift of 16 pixels, down, up or sideways, does not run;
  - a shift within tolerance is not applied;
  - a shift beyond it moves this model's maps and Reader V3's alike.

  The last case gives the model Reader V3's own pixels, so the two standardise to one map. Their numbers then agree
  only if both were moved.
- **A constant prediction on either side does not run**, and Reader V3 is still described. The code catches the
  refusal to standardise a constant map and records no score.
- **An unreadable mask stops the comparison.**
- **A winner's cell at exactly 0.5 is ink, and a cell share exactly at the line is measured.**
- **The described comparisons point the right way.** With the ensemble weakened, the bootstrap of this model's r
  minus the ensemble's lies above zero. This model's map also correlates more with Reader V3's than with the
  ensemble's.

No code changed. No defect was found.

### Two mutants are equivalent

- **Dropping the predictions from the finiteness mask** changes nothing. A prediction read from a PNG is finite
  everywhere on the render, and it is moved by the same shift as the other maps, which blanks the same cells.
- **Leaving out the division by 255** changes nothing. Each prediction is standardised before it is scored, and the
  overlap ranks cells, so the scale cancels.

## Verified, no change needed

- **The windows put the surface where the model was trained to find it.** The model read layers 17 to 42 of
  65-layer volumes with the surface at 32, so the surface was 15 layers into its window. The forward order starts at
  render layer 18, and the reversed order at reversed layer 17, which is render layer 48. Both put the render's
  surface layer 33 at window index 15. #458's test checks both.
- **The strategy matches the record.** The model gives r 0.237 against the ensemble's 0.53, a difference of −0.293.
  That is past the −0.10 margin, so `GP_FARTHER`. It clears its controls, at more than twice its largest, 0.0501.

## Observations for the owner (not changed)

- **The alignment, shift and cell selection are a second registered copy.** `compare_readers.py` and
  `gp_timesformer.py` each carry finding 118's alignment branch, shift and cell selection. Each registration
  freezes its own copy, which keeps each finding reproducible. A correction to one will not reach the other. Each
  copy now has its own tests: round #197's and this round's.

## Verification

- **The touched module.** `test_first_letters_0211_gp_timesformer.py` gives 49 passed and round #200's 2 strict
  xfails, against 35 passed before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #200's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #200's run, and 3,225 passed:
  round #200's 3,211 and the 14 new cases. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `8b0987c`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`gp_timesformer.py` is registered and unchanged.** Its mutants were run in a worktree.
- **Still not reviewed from the owner's merges since round #182:** #461, #465, #468 to #478, #480, #483, #485, #488,
  #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 18 were run again with the new tests: 16 are killed, and the two equivalent ones
  are not.
