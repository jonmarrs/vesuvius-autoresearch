# Design and architecture review — the owner's #451, the sampler TIFF comparison

Date: 2026-11-22. Baseline: `9fa3524` (main after round #188's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 21:12 UTC firing on 2026-11-22. Main had not moved since round #188's merge.

It takes **#451**. #451 tightens `scripts/compare_sampler_tifs.py`, which compares two runs of the TIFF sampler slice
by slice and gives one of three verdicts: byte-identical, differing, or not comparable. It refuses empty and
non-grayscale slices, sample types other than uint8 and uint16, and two runs of different bit depth. It also takes
differences in `int32`, so a uint16 difference of 65,535 no longer wraps. It also reads #405's change to
`fibers/field_quality.py`.

## What changed

### Eight more paths of the comparison are tested (`tests/test_compare_sampler_tifs.py`)

This round made 23 mutants of the script. #451's tests killed 14, and one cannot be killed (below). Five new test
functions, 8 cases, kill the other eight:
- **Each slice's own sample type is checked.** A uint8 slice beside an int8 one is refused in either order.
- **The mean difference is over covered pixels only.** Pixels that are zero in both runs do not dilute it.
- **Constant or empty coverage gives no correlation and no warning.** This holds for a constant reference, a
  constant test and a pair of all-zero slices, with warnings raised as errors. An empty pair's mean difference
  is 0.
- **One differing slice makes the sampling differ**, even beside an identical one.
- **A slice present in only one run is reported, not skipped**, from either side. The verdict is "not comparable"
  and the slice names a `FileNotFoundError`.

The command-line test takes the script's path from the module the test already imports.

No code changed. No defect was found.

### One mutant no test can kill

**Requiring one covered pixel instead of two before a correlation.** A single covered pixel has no spread, so the
spread check already gives "no correlation".

## Verified, no change needed

- **#405's cycle walk gives the same chains as before.** `_chains` now walks the unclaimed edges in one sorted pass
  and skips any edge an earlier walk claimed. The old loop re-sorted the remaining edges after each cycle. Both start
  each cycle at its smallest unclaimed edge. #405's test covers several pure cycles and checks that every edge is
  used once. `test_field_quality.py` gives 43 passed.
- **A torn or missing slice cannot be skipped.** Every read error is recorded as that slice's reason, and any slice
  that is not comparable makes the verdict "not comparable".
- **The guide matches the code.** The script's docstring now names the accepted sample types, and the checks hold
  them.

## Observations for the owner (not changed)

- **The JSON report can hold `NaN`.** A slice with no correlation writes `"r_covered": NaN`, which Python reads back
  but strict JSON parsers refuse.
- **Only `*.tif` names are compared.** A run that wrote `.tiff` files would compare as empty and be reported as not
  comparable, never as identical, so the error is safe.

## Verification

- **The touched module.** `test_compare_sampler_tifs.py` gives 30 passed, against 22 on `9fa3524`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,104 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The same 269 failing ids as round #188's run.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,779 passed. That
  is round #188's 2,771 and this round's 8.
- **The doc audit**, run alone, lists the same unresolved references as on `9fa3524`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **The script is not part of the training loop**, and its own tests run outside the standard suite.
- **Still not reviewed from the owner's merges since round #182:** #398, #400, #416, #419, #438, #446, #447, #448,
  #450, #453, #456, #458, #461, #463, #465, #468 to #478, #480, #483, #485, #488 and #489.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 23 were run again with the new tests: 22 are killed and the one above survives.
