# Design and architecture review — the owner's #305, #309, #311 and #313–#318

Date: 2026-11-01. Baseline: `83f7ea9e` (main after #318).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the firings from 18:12 UTC on October 31 to 03:12 UTC on November 1. Four read-only reviews ran
beside mine, one each for #314–#317. A usage limit stopped two of them, and both were resumed. I checked each of
their findings before acting on it.
- **#305 and #309** bump fpdf2 from 2.8.7 to 2.8.8 and pyasn1 from 0.6.4 to 0.6.5.
- **#311** stops the loop sampling lr 1e-5.
- **#313** floors the replicate rule's SD at the field's, as a registered amendment.
- **#314** plans and downloads raw SOTA segments as bounded, staged generations.
- **#315** converts raw segments with one float scale and a decoded-volume budget.
- **#316** makes teacher caches immutable bundles bound to their source.
- **#317** publishes detector reports with hashes and rollback, and adds a checker.
- **#318** records the second October filing.

## What changed

- **The teacher pixel cap refused every teacher the runners recorded** (#316,
  `repro/sota_data/teacher_artifacts.py`).
  - `MAX_PIXELS` was a fixed 512 Mi (536,870,912) pixels, with no flag to raise it.
  - The distillation record's teachers are 50600 × 36400, 34880 × 97280 and 51000 × 39980: 1.84 to 3.39 G pixels.
    The cross-scroll records add 41600 × 79600 and three PHerc0139 teachers of 0.75 to 0.82 G. Of the cross-scroll
    runner's nine teachers, only the three PHerc0172 ones fit.
  - The objects themselves are 167 to 325 MB encoded in the public bucket, inside the 2 GiB default download budget.
  - The cap is now 4 Gi (4,294,967,296) pixels. The test reads headers that claim three recorded shapes, and fails on
    #316's code.
  - The owner's pixel-budget test claimed `MAX_PIXELS + 1` rows, which no longer fits a TIFF tag. It now claims one
    row more than four columns allow.
- **A file that is not a TIFF escaped as a traceback** (#316).
  - tifffile's `TiffFileError` is an `Exception`, not a `ValueError`. The cache reader, the cache CLI and
    `read_teacher` catch only the latter.
  - An HTML error page as the remote object, or a zero-filled cache of the right size, therefore stopped with a
    traceback. Both are now input errors.
  - The tests fail on #316's code.
- **The same two escapes in the raw converter** (#315, `repro/sota_data/conversion_artifacts.py`).
  - A layer that is not a TIFF raised `TiffFileError`.
  - A label over Pillow's limit raised `DecompressionBombError`, which is not an `OSError`. Segment 20231022170901's
    6656 × 35840 label is one.
  - Both are now input errors, so the CLI exits 1 with its message. The tests fail on #315's code.
  - The label test pins Pillow's default limit. Importing `core/vesuvius_loader.py` sets it to `None` for the whole
    process, so in the full suite the label opens.
- **Layer files not in `download.json` moved the depth window** (#315).
  - The centered window is taken over every local layer, but only the selected layers were checked against the
    record.
  - Adding two layers, or deleting an unselected one, moved the window. The output still recorded
    `download_consumed_hashes_verified: true`.
  - #315 had closed this for the label and mask. Now the local layer files must be exactly the recorded ones.
  - The tests, one for an added layer and one for a deleted layer, fail on #315's code.
- **A hidden file in `layers/` failed the whole download plan** (#314, `repro/sota_data/download_artifacts.py`).
  - A macOS `._00.tif` was refused as a malformed layer name, though the converter skips hidden files.
  - It is now ignored and counted with the ignored entries. The test fails on #314's code.
- **`detector reproduce` checked its report directory only after training** (#317's preflight,
  `src/vesuvius_autoresearch/detector/cli.py`).
  - `eval` and `measure` check the report targets before inference. `reproduce` reached that check only after
    conversion and training, so a bad `reports_dir` failed hours in.
  - It now checks before conversion. The test fails on the code before.
- **Guards no test reached.** Each new test fails with its guard removed.
  - #317:
    - The rollback's hiding of a new marker. The existing test failed before the marker was installed.
    - The measurement status and count checks.
    - The UTC creation time and contract version.
    - The payload and marker budgets.
  - #316:
    - A re-pixelled bundle (the hash against the completion record).
    - A same-name replacement during download. The existing listing-change test is refused as ambiguous first.
  - #314: the combined listing budget, and one file that is both the label and the mask.
- **Docs.** The teacher cache, conversion, download and detector report guides give the changes above.

## Verified, no change needed

- **#305 and #309.**
  - The locked wheel and sdist hashes match PyPI.
  - The daily report's tests give 106 passed under fpdf2 2.8.8.
  - pyasn1 reaches the repository only through google-auth.
- **#311.**
  - Nothing else reads the lr values.
  - The current lr, 5e-4, is skipped as unchanged, so the loop samples 1e-3, 1e-4 and 5e-5.
- **#313.**
  - The floored scores equal the brute-force recomputation in its tests.
  - The floor only lowers positive scores, so every floored promotion is a live one at the same cycle.
  - The record regenerates exactly: the replayed windows, both nulls (1,000 shuffles each) and the power simulation
    (2,000 windows at each of three effects).
  - `decide()` is called only by the loop, which records the unfloored score beside it.
- **#314** (the review).
  - Against a local fake S3, run with the real s3fs, aiobotocore and aiohttp, each request carries `Range` and
    `IfMatch`, and the body is closed.
  - Existing outputs are refused before remote access, and a dry run creates nothing.
  - Failures leave no partial output or staging.
  - The converter accepts its layout. Its scope collects the 139 tests its record gives.
- **#315** (the review).
  - The depth rule and the single float scale behave as documented, and big-endian uint16 keeps the high byte.
  - The `download.json` fields match what the downloader writes.
  - Callers are compatible.
  - Its 55 contract cases and the record's 331 tests collect as stated.
- **#316** (the review).
  - Interrupted transfers leave no cache, and legacy caches are refused before remote access.
  - Callers match the new signatures.
  - The bugs its record fixes reproduce on the parent.
- **#317** (the review).
  - No limit refuses the default fragment's report: Fr143's 1188 × 1853 thumbnail is 2.2 MB even when incompressible.
  - Metric formulas are unchanged.
  - Rollback holds at every rename step.
  - The checker imports no image or ML package.
  - Its 63 tests pass, and the curated registry has 168 modules.
- **#318.**
  - The Villa merges, at 21:04:45 and 21:37:35 UTC on October 30, are 2:04 and 2:37 p.m. Pacific, as written.
  - The receipt, at 20:58:08 UTC, is 1:58:08 p.m. Pacific, before the 06:59 UTC deadline.
  - The 335-word count and both answer hashes hold. Its 10 tests pass with the first record's.
  - The Villa merge times were not checked against Villa here.

## Observations for the owner (not changed)

- **#314:**
  - **SDK transport errors are tracebacks.** An offline `EndpointConnectionError` or a cut-off body's aiohttp
    `ClientPayloadError` escapes the CLI. Exit status is still 1 and staging is removed.
    - The record's short- and long-body claims rest on a `BytesIO` stub. A real short body fails in aiohttp before
      the "short S3 body" check.
  - **S3 folder markers.** A zero-byte `prefix/` object lists as the prefix itself, which the plan refuses as outside
    its prefix. None of the bucket listings I checked has one.
  - **Untested guards:** the key and identifier length caps, the entry and body-part type checks, and the layout's
    symlink check.
- **#315:**
  - **No full legacy segment can be converted.** The whole selected volume is held in its source dtype. The voxel
    ceiling (512 Mi; default 128 Mi) allows at most three Fr143-size planes, against the default 26.
    - None of the 278 segments I listed under nine scrolls in the public bucket uses the legacy `layers/` layout. This
      affects local legacy data.
  - **Smaller limits:**
    - The fixed 512 MiB per-file limit is below the downloader's 2 GiB maximum.
    - Bad option values exit 1, where the guide reserves 2 for usage errors.
  - **Pillow's limit depends on what the process imported.** The detector loader lifts it at import, so the
    converter refuses an oversized label in its own process but reads it in one that imported the loader.
  - **Two-step centering.** Downloading 27 layers and then converting 26 can select one plane off from centering 26
    directly.
  - **Untested guards:**
    - the multiframe-label check, the only guard for that case;
    - the label mode check;
    - the TIFF layout and dtype checks before decoding;
    - output outside the source;
    - argument validation;
    - the readbacks.
- **#316:**
  - **The runner cannot reuse a bundle fetched with a larger budget.** `distill_run` reuses bundles at the 2 GiB
    default, so a bundle fetched with a larger `--max-bytes` is refused.
  - **Untested guards:** the cached-candidate prefix check, the payload key, size and header rechecks,
    `teacher_provenance`'s pixel mismatch, and `distill_prep`'s 3D and empty-crop checks.
- **#317:**
  - **A marker nested 5,000 deep** makes `json.loads` raise `RecursionError`. The checker prints a traceback, with
    exit status 1. Only a hand-built marker does this.
  - **The scorecard's own fields are not hashed.** A hand-edited `val_f1` still passes. The guide says the checker
    does not recompute metrics; the README's wording reads wider.
  - **A check that cannot trigger.** The 64 MiB total-payload check never fires: there are two payloads of at most
    32 MiB each.
  - **The guide's example.** It names the tracked legacy scorecard, which fails on its `NaN` before reaching the
    regeneration message.
  - **Report-path errors from `eval` and `infer`** escape the CLI as `ValueError` tracebacks. This predates #317.
- **#311's commit message** lists 1e-3, 1e-4 and 5e-5 as kept. 5e-4 is kept too; it is the current setting.
- **#318:** neither prize record's test is in the standard suite.
- **The SDK tests need s3fs and aiobotocore,** which this environment does not install. They are the standard suite's
  14 new failures here.

## Verification

- **The changed areas.**
  - Conversion, convert and download tests: 136 passed (the SDK cases deselected).
  - Teacher tests: 46 passed (6 need s3fs).
  - Detector report tests: 70 passed.
- **Each fix and new guard test checked against its code.** Ten mutants in `repro/sota_data` and eight in the
  detector reports and CLI were each caught by the intended new test. Reverting each fix fails its test.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the changed Python files. Mypy is clean over
  the whole repository (869 files).
- **The standard suite** SUITE
- **The 231 test modules outside the suite** give 2,107 passed, 80 skipped, 13 failed and 21 collection errors: the
  same failures as round #139. #318 added the one new module, whose 6 tests pass.
- **The doc audit** AUDIT
