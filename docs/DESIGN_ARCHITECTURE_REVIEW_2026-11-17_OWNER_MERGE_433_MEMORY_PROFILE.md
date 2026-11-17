# Design and architecture review — the owner's #433, the regional memory profile

Date: 2026-11-17. Baseline: `021cd07` (main after round #180's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12 UTC firing on 2026-11-17. Main had not moved.

It takes one slice of **#433**, merged at 02:19 UTC on 11-16: `src/vesuvius_autoresearch/core/regional_memory.py`.
That is the opt-in memory profile that `scripts/inference/predict.py` and `ensemble_predict.py` write into a
prediction's metadata when `--profile-memory` is given. It records:
- the process's resident memory and its lifetime peak;
- on a CUDA device, the PyTorch allocator's current and peak bytes since the profile reset them.

It is not registered.

#433's other code is the experimental interfaces in `core/villa_inference.py`. Their 30 tests need villa's
test-time augmentation module and fail in this container, so that part is left for a container with villa.

## What changed

### Eight guards of the memory profile are now tested (`tests/test_regional_memory_profile.py`)

The module is correct, and no code changed. This round made 24 mutants of it. #433's tests killed 16. They fake the
CUDA calls, so both paths could be sampled here. Four new test functions (6 cases) kill the other 8:
- **A bare "cuda" device is the current device throughout.** The profile resolves it once. Every CUDA call,
  including the device properties, then names that device, and the report names it.
- **The CPU report names its device and claims no CUDA synchronisation**, and its schema version is 1.
- **A phase must be a nonempty string.** An empty name, `None` or a number is refused and adds no observation.
- **Elapsed time counts from the start of profiling.**

## Verified, no change needed

- **The lifetime peak is converted by platform.** Linux reports kibibytes and macOS bytes. Other platforms get
  `null` rather than a sampled value presented as a peak. #433's tests cover all three.
- **The CUDA counters are reset once, after a synchronisation, on the selected device.** Every sample synchronises
  first. #433's tests check the order of the calls and that no other device is named.
- **The CPU path never touches CUDA.** #433's test fails on any CUDA call.
- **The report says what it does not measure.** It records the whole device's peak as not measured and capacity as
  not guaranteed. The CPU peak's scope is the process lifetime, including work before profiling.
- **Profiling changes no prediction.** #433's tests run both commands with and without it and compare the outputs.

## Observations for the owner (not changed)

- **The report's observations share their inner dictionaries with the profile.** `report()` copies the list but
  not the dictionaries, so a caller that edited a returned observation would change the profile's own. The two
  commands only serialise the report, so nothing does this today.
- **One of #433's tests needs villa.** `test_profile_includes_successful_optional_exports_and_coherence` fails here
  because the coherence step needs villa's structure-tensor source. It was left out of the mutant runs.
- **The fit launcher still carries on when its settings snippet fails** (round #175). It is unchanged on `021cd07`.

## Verification

- **The touched module.** `test_regional_memory_profile.py` gives 18 passed and the one villa failure, against 12
  passed on `021cd07`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,023 files, with `--python-executable ./.venv/bin/python`. Its
    first run flagged a test lambda that returned the value of `list.append`. The lambda was replaced with a named
    function.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #179's run. That run was made
  before the lambda was replaced. The change does not alter what the test does, and the module was run again after
  it.
- **The test modules outside the suite.** The 264 modules give the same 23 failing ids as round #179's run, and
  2,722 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `021cd07`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Not reviewed in #433:** `core/villa_inference.py` and its tests (need villa), the changes to the two
  prediction commands beyond the profile's calls, `prototype_volumetric_ink.py`, the documents, the two review
  records and the owner's review.
- **Still not reviewed:** #437 (needs villa), #422, #424 and #428, the rest of #390, #396 and #411, and the parts of
  #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the module. #433's tests passed here before the mutants were run, apart from the
  one villa test. The 8 survivors were run again against the new tests; the 16 that #433's tests killed were not.
