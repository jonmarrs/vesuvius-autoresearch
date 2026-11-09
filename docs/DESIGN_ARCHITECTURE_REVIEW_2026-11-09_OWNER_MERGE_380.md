# Design and architecture review — the owner's #380

Date: 2026-11-09. Baseline: `c7395e15` (main after #380).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 02:12 UTC firing on 2026-11-09. At 01:12, main was still the merge of round #154's PR, so that
firing had nothing to review. #380 makes the fiber benchmark parse and hash one capture of its probability cache. It
carries the captured inference record into every report, and adds `--refresh-cache` and cache diagnostics.

## What changed

### The orientation driver read the cache twice (`scripts/analyze_orientation_field.py`)

#380 found that `bench_cli` hashed the cache file and then opened it again with `np.load`. A file replaced in between
was then used under the original's digest. `analyze_orientation_field.probability()` had the same two reads.

- It now uses #380's `read_probabilities` on the cube's shape, so the measured volume is the one its record attests.
- Its refusal messages are unchanged. A malformed or missing file is now refused with a message, not a traceback.
- The new test replaces the file both after it is captured and before `np.load` reads it. It fails on the old driver.
- The script is not registered. Its committed report is not regenerated.

### #380: seven guards no test reached (`tests/test_fiber_probability_cache.py`)

I made 26 mutants of #380's cache path. Its tests killed 18. Each new test passes as merged and fails with its guard
removed:

- **The 1 MiB manifest bound.** The existing case was a mebibyte of spaces, which is not JSON. That case was refused
  with or without the bound. The new manifest is valid JSON with trailing spaces.
- **A manifest without a digest is invalid.** With the string check loosened, the missing key raised an uncaught
  `KeyError`.
- **Refresh keeps the manifest's own mode.**
  - The existing case set 0o644, which is also the usual umask default, so dropping `permissions=` passed.
  - The new case uses 0o604.
- **Freshly computed probabilities are read-only.** Only a hit was checked.
- **The console line naming the cache outcome**, for a hit and for an explicit refresh.
- **A hit reports the manifest it validated.**
  - The new test replaces the manifest as soon as it is captured. Reading it again would report the replacement.
  - The existing test replaced it only after scoring.
- **A float64 cache larger than the header allowance still hits.**
  - On the existing 3×3×8 cube, the 10,012 header bytes hid a bound of four bytes a voxel.
  - The new cube is 16³, 32 KiB of float64.

The eighth survivor, `isinstance(record, dict)`, is equivalent. No other JSON value has `.get`, and that
`AttributeError` is already caught.

## Verified, no change needed

- **#380's two regressions fail on the code before it.** Run against `9156eb38`'s source:
  - the replaced cache gave the 0.125 field, not 0.75;
  - the replaced manifest gave the `ffff…` digest.
- **#380's counts.** The PR's seven curated modules give 247 passed, as it says.
- **The other 18 mutants** fail its tests. They cover:
  - the inference and digest comparisons;
  - the identity recheck on a hit, and the read-only hit;
  - `--refresh-cache` reaching the cache, the explicit-refresh reason and the missing-metadata reason;
  - removing the old manifest before publication;
  - the research interface's writable copy;
  - score's usage error;
  - both report keys and the all-cube refresh flag;
  - `read_probabilities`' finite, range and kind checks, and its digest.
- **Commands work on the read-only array.** #380's tests stub a writable array into `trace`. I ran `trace` plain, with
  `--relink` and with `--detect-block` on a read-only one; nothing writes into it.
- **The research interface is unchanged for its callers.** The registered `seed_heading_confirmation.py` still calls
  `_fiber_prob`, which returns its own writable float64 array as before.
- **Provenance is unchanged.** It is still the record's inference and digest, with the cache diagnostics outside it.
  So an all-cube refresh still carries a matching tracer row forward. #380's test covers that.

## Observations for the owner (not changed)

- **A hit computes the inference identity twice**, before and after validating the cache. Each computation hashes the
  three model files, including the checkpoint. That is the cost of the recheck #380 adds.
- **The diagnostics hold absolute paths.** `probability_cache` records the resolved cache and manifest paths, so two
  machines' reports differ there even when their provenance agrees. #380 keeps the diagnostics outside provenance.

## Verification

- **The touched modules pass.** The cache module gives 38 passed (31 and 7 new). The orientation driver's module
  gives 15 passed (14 and 1 new). Each new test fails with its guard removed, or on the old driver.
- **Ruff and mypy.** Ruff 0.9.10 `check` and `format` are clean on the three changed Python files. Mypy is clean over
  the whole repository: 927 files.
- **The standard suite.**
  - On `c7395e15`, the 187 modules give round #153's 70 failing ids. #380 added one module.
  - On this branch, before merging #375 (below), they give the same 70.
- **The test modules outside the suite.** Before merging #375, the 252 modules give 2,411 passed, 82 skipped, 13 failed
  and 21 errors. The failing ids are round #153's 34. The one extra pass over round #154's 2,410 is the driver's new
  test.
- **The doc audit**, run alone after merging #375, lists exactly round #154's unresolved references. It checks 2,222
  path and 820 commit references, against 2,220 and 816 then.

## A note on this round's work

- **The owner merged #375 at 02:21 UTC, after this round began.** It rewords finding 106's face crossings in the
  report and the villa draft, with tests. I merged main into this branch so it stays mergeable. Finding 106's five test
  modules, the November draft's and the suite guard give 58 passed after the merge. The next round reviews it.
- **The baseline suite ran in the main checkout while I committed this round's changes there.** pytest had already
  collected its modules, and that run gave the 70 ids.
