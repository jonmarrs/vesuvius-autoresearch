# Design and architecture review — the owner's #388 and #389

Date: 2026-11-10. Baseline: `e3be7258` (main after round #159's merge, which carried #388 and #389).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:12 UTC firing on 2026-11-10. The owner merged both PRs during round #159, which merged them
into its branch and left their review to this round:
- **#388** (23:23 UTC on 11-09) is version 2 of the confidence-and-ink-agreement analysis. It requires complete
  paired evidence for each arm, sums probabilities only at the re-score's saved ink pixels, and moves the input checks
  into `scripts/confidence_inputs.py`.
- **#389** (23:54 UTC) adds `repro/sota_data/pyramid_depth.py`. It checks an OME-Zarr ink pyramid's levels for depth
  silently truncated by successive halving, from the headers alone or, with `--compare`, from the pixels of one window.

## What changed

### #389: a damaged chunk is refused, not a traceback (`repro/sota_data/pyramid_depth.py`)

`--compare` checked only that each chunk in the window exists. A zero-byte or cut-short chunk, which is what an
interrupted download leaves, made the codec raise an exception `main()` does not catch:
- RuntimeError for Blosc (zarr's default) and Zstd;
- `zlib.error` for Zlib;
- EOFError for GZip;
- `LZMAError` for LZMA.

The result was a traceback and exit status 1, the status the tool uses for "the pyramid failed the check".
`_read_window` now turns those four into ValueError, so the command refuses with exit 2 and names the level and the
cause. The new test damages one chunk for each of the five codecs. All five cases fail on the merged code and pass
with the fix, and dropping any one of the four exception types fails the test.

The tool is not part of a registered finding: no registration mentions it, and nothing runs it but its tests.

### #389: 34 guards no test reached (`tests/test_ink_pyramid_depth.py`)

This round made 70 mutants of the tool. #389's tests killed 27. New tests kill 34 of the 43 survivors, and each passes
on the tool (with the fix) and fails with its mutant:
- **Malformed headers** are refused with exit 2: a zero or four-dimensional shape, a non-finite or boolean scale, two
  scale transforms, two multiscales entries, `zarr_format` 3.
- **The classification rules.**
  - The depth-pool tolerance is one voxel or 8%, whichever is larger.
  - A z scale rounded through float32 still counts as unchanged.
  - Unequal or fractional XY ratios are refused as a pooling factor.
  - Level `0` is the reference wherever it is listed.
  - A truncated level's reason names ceil-halving only when its depth matches it.
- **The window comparison.**
  - Scales in physical units are normalised by level 0's.
  - A window away from the origin is read at the matching coarse origin.
  - A coarse window deeper than level 0 is scored on the shared slices.
  - A middling correlation, or two high ones, is not a verdict.
  - A full-depth level whose pixels are ambiguous fails.
- **The command line.**
  - An inconsistent level fails.
  - The text report explains a truncated level.
  - A compare it cannot honour is refused: the level itself, an unknown level, an unaligned origin, a voxel cap
    over either window, a zero cap, or `--compare` without both `--origin` and `--size`.

The other nine survivors:
- six are equivalent: another check still refuses the same input, or the branch is unreachable;
- three are not worth a test:
  - a level path like `01` changes only informational fields;
  - an empty path cannot reach the code from the command line;
  - row order changes only for non-numeric paths.

### #388: 36 guards no test reached (`tests/test_confidence_analysis_contracts.py`)

This round made 90 mutants: 41 of `confidence_inputs.py` and 49 of the measure script. #388's tests killed 34. 29 new
cases kill 36 of the 56 survivors. Each passes as merged and fails with its mutant:
- **Inputs.**
  - A second probability map is ambiguous wherever it sorts.
  - Unrelated or mixed mask tiles are refused.
  - 0/1 masks count the same ink as 0/255.
  - A missing inkless final tile is refused although the counts agree.
  - The probability map must match the grid's width as well as its height.
- **Resource limits.** The grid-cell, block-pixel and mask-tile limits are enforced, and the guide states each
  constant's value.
- **Metrics.**
  - Counts must be consistent integers.
  - The 0.1% gate is a share of the original count.
  - A 0.1125% drift is refused.
- **Paths and the report.**
  - Arm names cannot carry path syntax.
  - A symlinked report path is refused, not replaced.
  - The report records every input, seed 0 and the untested claims.
  - Its shared axis is the first arm's valid-coordinate mean.
- **The statistics.**
  - Each cohort needs thirty bins.
  - Two-arm bins are neither unanimous nor lone.
  - Differences within rounding tie in the shuffle.
  - The shuffle test is two-sided.

The other 20 survivors:
- **Thirteen fail closed anyway.** Another check refuses the same input, with a different message.
- **Two are equivalent by logic.**
- **Five are not worth a test**, for example a float128 probability map, or checks on the internal inputs that the
  command line always builds valid.

## Verified, no change needed

- **The measure script and `confidence_inputs.py` are registered.** Version 1 implemented the 2026-09-13
  registration, and the owner's correction appended to it describes version 2. Nothing in them needed changing.
- **#388's account of version 1.**
  - With `--arms s s s`, version 1 printed the table header and then "CONFIDENCE PREDICTS REPRODUCIBILITY" with no
    rows, and returned 0.
  - #388's two regression tests also fail against version 1.
  - Version 1 called the result OPPOSITE when only one binning was negative. It never used `INK_TOLERANCE`, and wrote
    its report with a truncating `write_text`.
- **Version 2 against version 1 on a synthetic three-arm study.**
  - With probability constant inside each cell, both give the same cohort counts and means, so the shared axis is
    "as before" and only p changes (0.0 to 1/1001).
  - With background varying inside cells, the differences diverge, which is #388's background-contamination point.
- **The plus-one p-value changes no decision.** Version 1 called a result significant when fewer than 50 of 1,000
  shuffles reached it. (count + 1)/1001 < 0.05 makes the same cut. The historical 0.0 becomes 0.000999, still below
  0.001.
- **The historical table matches its JSON**, which #388 did not touch: 0.6696/0.5375/+0.1321, 0.6820/0.5315/+0.1505
  and 0.6998/0.5406/+0.1591.
- **The new bounds fit the real strip.**
  - 4,490 × 89,820 is 403,291,800 pixels, the committed `total_pixels`.
  - The grid is 4,032,918 cells, under the 16,777,216 limit.
  - A 1,868-column block is 8,387,320 pixels, under 8,388,608.
  - A 4,490 × 16,384 mask tile is 73,564,160 pixels, under 134,217,728.
- **#388's 0.1% gate passes exactly at its boundary**, as documented.
- **#389's header classification works as its docstring says.**
  - On a 65-slice level 0, ceil-halving gives 33, 17, 9, 5 and 3.
  - A 17-slice level at z scale 1 is `truncated`, with a reason that cites halving. At z scale 4 it is
    `depth_pooled`.
- **#389's refusals, each probed:**
  - a missing root, `.zattrs` or `.zarray`;
  - non-integer shapes, NaN, boolean or zero scales;
  - axes other than z, y, x;
  - a symlink that escapes the group;
  - a missing chunk, or a window over the voxel cap.

  Exit codes are 0 (usable), 1 (a level unusable, or pixels that disagree or are ambiguous) and 2 (refused).

## Observations for the owner (not changed)

- **#389 ignores the XY scales in the header check.** A level whose scale is written in x, y, z order gives the
  17-of-65 level `[4, 4, 1]`. The tool reads a z ratio of 4, calls it `depth_pooled` and exits 0, even though the
  declared x ratio of 1 contradicts the 4× smaller x shape. `--compare` refuses it. Catching it from headers alone
  needs a cross-check of scale ratios against shape ratios.
- **#389's pixel check takes the XY factor as the depth-pool width.** On a correct anisotropic pyramid (level 2 at
  scale `[2, 4, 4]`), the headers say `depth_pooled` but the pixels come out `ambiguous` and it exits 1. This is a false
  alarm, not a silent pass.
- **The 8% depth tolerance is loose.** Rounding alone stays within one voxel. A 200-slice volume's level at z ratio 2
  with 93 slices instead of 100 counts as usable.
- **Gaps in #389's documentation.**
  - The window's origin must also divide by the XY factor; the docstring names only its height and width. An unaligned
    origin is refused cleanly.
  - The exit codes are not documented.
  - The commit message says the check runs before a pyramid "is used as a training input", but no training or data
    code calls it.
- **#389 refuses sparse arrays.** Arrays whose writer omitted all-fill chunks are refused as having a missing chunk.
- **A truncated chunk can still decode.** A cut-short Blosc chunk that was stored uncompressed decoded to a full chunk
  of the wrong bytes, with no error. This is outside the tool's reach.
- **Real CT has not met `--compare`.** Adjacent slices correlate in real scans, so real windows may come out
  `ambiguous` more often than the synthetic tests do.
- **Three of #388's tests pass for a reason other than the one they name.**
  - The "ambiguous" case's extra map sorts first and fails mask pairing.
  - The "mask_short" case is refused by the count gate.
  - The "boolean" case is refused because summary and strip disagree.
  - The new tests reach each named guard directly.
  - The duplicate-arms test patches `binned_maps`, which version 2's `main()` no longer calls.
- **The guide's account of version 1 → 2 is incomplete.** `docs/CONFIDENCE_REPRODUCIBILITY.md` does not say that ink
  and agreement labels now come from the re-score's saved masks rather than the published `ink_metric` masks. The
  historical counts show the two differ slightly (−0.0009% to +0.0005%).
- **The guide names `*_flat_prob.npy`; the code counts any `*_prob.npy`.** The code is the stricter of the two.
- **Two of #388's checks have never met a real re-score.** These are the exact match between the re-score's
  foreground count and its saved mask pixels, and a 1 MiB limit on `metrics.json` that the guide does not mention.
  Both fail closed.
- **Not reproducible here:** #388's "108 passed across 7 modules" (the six obvious modules give 95) and its mypy file
  count and package versions, which describe a different environment.

## Verification

- **The touched modules pass.**
  - `test_ink_pyramid_depth.py` gives 71 passed, against 28 as merged: 43 new cases from 18 new test functions.
  - With the suite guard, that is 78 passed.
  - #388's three test modules and the suite guard give 102 passed, against 73 as merged: 29 new cases from 18 new
    test functions. The doc-reference audit's standing whole-repository failure was left out of both runs.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` and `format` are clean on the three changed Python files.
  - Mypy is clean over the whole repository: 939 files, with `--python-executable ./.venv/bin/python` as the hook runs
    it. #389 added two files.
- **The standard suite.**
  - On `e3be7258`, the 196 modules give round #153's 70 failing ids. #389 added one module.
  - On this branch they give the same 70.
- **The test modules outside the suite.** The 250 modules give 2,387 passed, 86 skipped, 13 failed and 21 errors, as
  in round #159. The failing ids are round #153's 34. All of this round's new tests are in suite modules.
- **The doc audit**, run alone, lists exactly round #159's unresolved references. It checks 2,243 path and 833
  commit references, against 2,238 and 832 then.

## A note on this round's work

- **The disk filled during this round.** Earlier rounds' pytest temp directories had used up the session's disk.
  - The first baseline run failed one test with "No space left on device".
  - I deleted the old temp directories and reran it. It gave round #153's 70 ids.
  - The #389 helper's first mutant sweeps overlapped the full disk. It discarded them and reran both with bytecode
    writing off. The #388 helper found no disk error in its runs.
- **Helper agents made the mutants and wrote the tests.** I reran 18 of the kills myself, nine for each PR, including
  the reverted fix. Each new test passed as merged and failed with its mutant.
- **The #389 commit message is slightly loose.** It says the nine remaining mutants are "equivalent or change only
  informational output". One of them, an empty level path, cannot reach the code from the command line.
