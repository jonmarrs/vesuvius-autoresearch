# Design and architecture review — the owner's #367, #368 and #376

Date: 2026-11-09. Baseline: `ca3e61cd` (main after #376).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 17:13 UTC firing on 2026-11-09. The firings from 04:12 to 16:12 found main unchanged. The
owner merged three PRs at about 16:21 UTC:
- **#367** keys the training loader's coordinate cache on the selection it was computed from, not on file timestamps.
- **#368** treats a damaged coordinate cache as a miss and publishes it atomically.
- **#376** converts NML physical scales to micrometers, with nanometers as the default when the unit is omitted.

## What changed

### #367 and #368: four coordinate-cache guards no test reached

I made 28 mutants of the cache key and the cache reader. The owner's tests killed 21. Four of the seven survivors
break a promise the code documents, and each now has a test that passes as merged and fails with its guard removed:

- **A boolean ratio is refused** (`tests/test_coordinate_cache_identity.py`). `bool` is a `numbers.Real`, so only the
  explicit check keeps `min_mask_ratio=True` from meaning 1. A boolean patch size was already tested.
- **The target's dtype is part of the key.** The same bytes are 255 as uint8 and −1 as int8, which a threshold can
  treat differently. With the dtype dropped from the recipe the two shared a key.
- **A cache with three columns is a miss** (`tests/test_coordinate_cache_publication.py`). It is two-dimensional, so
  only the column check refuses it; otherwise the first sample would fail in `__getitem__`.
- **A cache with x past the last patch start is a miss.** Only y was tested.

The other three are equivalent:
- the finder never reads the volume, so its URI cannot change the coordinates;
- the fallback thresholds are a constant in the recipe;
- an unclosed NPZ archive is collected anyway.

### #376: `skeleton_io.py` passes `ruff format` again

The file was formatted before #376. Its new error line was too long, so committing it would fail the repository's
pre-commit `ruff-format` hook. It is now formatted; the change is layout only.

## Verified, no change needed

- **#367's key is the finder's input.** The key's recipe matches the finder call's arguments exactly:
  - the target array (the labels when ink is required, else the mask, else the implicit ones);
  - the patch size;
  - `bbox_threshold` (always `min_mask_ratio`) and the label threshold;
  - the 0.01 fallback;
  - the label name (the volume URI).

  The CT's intensities are not hashed, as the docstring says. Every 64-row block of the target is hashed; a key from
  the first block alone fails the owner's test.
- **#368's reader.** It treats each of these as a miss and leaves the file in place:
  - the load failures it names (`EOFError`, `ValueError`, `BadZipFile`);
  - an NPZ archive, a pickle and a non-integer array;
  - an empty array, and negative or out-of-range coordinates.

  An operating-system error still propagates. Finding no patch raises, so an empty array is never written, which
  matches the reader's non-empty check.
- **#368's suite registrations.** The loader now imports `fibers.provenance` for `atomic_file`, so the suite guard
  counts tests importing provenance as tests of the loop. That is why #368 moved `test_analyze_orientation_field.py`
  and `test_export_fiber_targets_bench.py` into the suite.
- **#376 leaves the published files unchanged.**
  - The fiber-skeleton NML files declare `unit="micrometer"`, as the step-0 GT survey records, so their scale is
    unchanged.
  - The registered `seed_heading_confirmation.py` checks that scale against 7.91 µm, and its inputs are those files.
  - `scale_um` is metadata; scoring and lengths stay in voxels.
- **#376's mutants.** 7 of 9 fail its tests. The two survivors:
  - `.get(unit, 1.0)` is equivalent, because an unknown unit is refused one line earlier;
  - the parser-version constant is read only into provenance, and no test reads its value.

## Observations for the owner (not changed)

- **Unicode lookalikes.** #376 accepts the micro sign (U+00B5) in "µm" and the precomposed Å (U+00C5). The Greek mu
  (U+03BC) and the angstrom sign (U+212B) are refused, loudly rather than mislabelled.
- **Old caches accumulate.** Timestamp-named caches are ignored and preserved, as #367's docstring says, so cache
  directories keep them until someone deletes them.
- **Fourteen other files fail `ruff format --check`.** They predate this round, and the pre-commit hook will flag each
  when it is next committed.

## Verification

VERIFICATION

## A note on this round's work

- **The first loader mutation run was invalid.** villa is a gitlink, so the sparse worktree had no
  `find_valid_patches`. The loader tests failed on unmutated code, and all 28 loader mutants were reported killed. I
  linked the main checkout's villa source into the worktree (no git command inside villa), confirmed the unmutated
  tests pass (97 passed, 3 skipped) and reran all 28. The figures above are from the rerun. #376's mutants needed no
  villa; their unmutated runs passed.
- **I committed the new loader tests in the main checkout while the baseline suite ran there.** pytest had already
  collected its modules, and that run gave the 70 ids.
