# Design and architecture review — the owner's #302, #308, #310 and #312

Date: 2026-10-31. Baseline: `307a57d3` (main after #312).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 17:13 UTC firing. Two read-only reviews ran beside mine, one of #310 and one of #312, and I
checked each of their findings before acting on it. The owner's later merges (#305, #309, #311, #313–#317) are left
for the next round.
- **#302** reads out the registered unchanged-control comparison: `BEATS_UNCHANGED`, with a post hoc audit.
- **#308** restores `CUDA_VISIBLE_DEVICES` and `MPLBACKEND` after each Villa evaluation test.
- **#310** converts detector fragments as complete generations with a completion manifest. It also makes
  `detector reproduce` reuse a fragment only after its images pass checks.
- **#312** replaces label filling with bounded review proposals, written to a new directory.

## What changed

- **The pixel cap refused the detector's default held-out fragment** (#310,
  `src/vesuvius_autoresearch/core/fragment_conversion.py`).
  - #310 capped every image at 64 Mi (67,108,864) pixels, and `--max-pixels` can only lower that.
    `PHercParis2Fr143`, `DetectorConfig`'s held-out fragment, is 14830 × 9506: 140,973,980 pixels.
  - Conversion refused it, and a converted copy read as `NEEDS_CONVERSION`, so `detector reproduce` stopped on its
    default fragment. The previous converter had set Pillow's limit off globally and converted it.
  - The cap is now 160 Mi pixels (167,772,160). That is below Pillow's own refusal (twice
    `Image.MAX_IMAGE_PIXELS`, 178,956,970), and Pillow's lower warning is ignored inside the explicit budget.
  - The test converts and checks one full-size layer. It fails on #310's code.
- **An undecodable image crashed the check** (#310).
  - Pillow reports some damaged files as `SyntaxError` or `TypeError`, and a JPEG has no `n_frames`. These escaped
    the status check, so `--check` and `reproduce` stopped with a traceback instead of rebuilding.
  - Decoding failures are now a `ValueError`, so such a fragment reads as `NEEDS_CONVERSION`. A frame count is read
    only where the format has one.
  - The converter's command line also reports a rollback failure without a traceback.
  - The tests (a broken PNG chunk, a legacy JPEG label) fail on #310's code.
- **An interrupted run of the old converter blocked every rebuild** (#310).
  - The previous converter wrote each file through a hidden `.<name>.part`. #310 counts those as user files and
    refuses to replace the fragment. The default destination is inside the Villa checkout.
  - The label search also matched hidden files, which the loader's `glob.glob` does not. A leftover
    `.<id>_inklabels.png.part` therefore made a usable fragment read as unusable.
  - Those leftovers are now managed files, replaced with the rest of the generation, and hidden files are not
    labels. The test fails on #310's code.
- **An interruption between the two publishing renames skipped the rollback** (#310).
  - The first rename (old generation to `-previous`) sat outside the rollback's `try`. An interruption just after
    it left no fragment at the published path.
  - Both renames are now inside it. The test interrupts after the first rename, and fails on #310's code.
- **#310's documentation.**
  - The guide gives the new cap, the replaceable leftovers, and that an undecodable image needs conversion.
  - `README.md` had the new data-preparation paragraph between the `--config` sentence and "The JSON object
    overrides…", which then referred to nothing. The paragraph now follows the example.
  - `REPRODUCE.md` said a fragment is reconverted when a file is missing. It now says: missing, or failing its
    checks.
- **A damaged PNG escaped the shared PNG reader** (#312, `scripts/data_catalogue.py`).
  - `captured_binary_png` turns decoding errors into "invalid binary PNG", but Pillow's `SyntaxError` for a broken
    chunk passed through. Both label proposals and the training atlas then stopped with a traceback.
  - It is now converted too. The test fails on the code before.
- **The output-outside-source-folders rule was untested** (#312, `tests/test_label_edit_proposals.py`).
  - Its only case used a `.png` name, which the image-name rule refuses first. With the folder rule removed, all 56
    tests passed.
  - Two cases now use a review directory inside the source folder and inside the region mask's folder. Both fail
    with the rule removed.
- **Smaller corrections.**
  - Two comments in `tests/test_autoresearch_measurement.py` still described `refine_labels_villa.py --in-place`,
    which #312 retired.
  - The proposal guide and the lab notebook said "89–97% overfilled". The June specification they cite says the
    filled masks were 89–97% ink, against 0.057–0.079 for `inklabels.png`.

## Verified, no change needed

- **#302's readout.**
  - Every figure in `reports/loop_unchanged_control_readout_2026-10-30.md` matches its JSON records:
    - the three differences, standard errors, t and p values against their registered thresholds;
    - the step-gap shares (6%, 27%, 41%) and the remainders, which pass their thresholds;
    - the comparisons against the other tweaks;
    - the audit's drift, time-matched, Mann–Whitney and leave-one-out values.
  - Its tests pass.
- **#308.** The fixture restores both variables, whether they were set or unset.
- **#310.**
  - Publication rolls back on rename errors.
  - A failed rollback keeps the named backup.
  - Permissions are preserved.
  - `--check` writes nothing and imports no Torch.
  - The manifest's hashes bind the outputs.
  - Its 64 tests pass, and the new contract file cannot be collected on the parent.
- **#312.**
  - Proposals never write to a source.
  - Background touching the edge is never filled.
  - Size and pixel limits fail before any write.
  - Publication is one rename, and a failure leaves nothing.
  - Neither wrapper imports from Villa, and no caller uses the removed flags.
  - The record's pin and blob id (`daee6a9e…`) match the pinned file. Its 56 tests pass; none pass on the parent.

## Observations for the owner (not changed)

- **#310:**
  - **The shared publisher is duplicated.** `fragment_conversion.py` re-implements `staged_directory` and
    `separate_paths` from `scripts/candidate_artifacts.py`. The read-only-generation fix went only into the copy:
    run without root's override, `staged_directory` still fails on a 0o555 output.
  - **The read-only tests prove nothing as root.** Run as root, the usual case in containers, they pass on the code
    before the fix too.
  - **Mutations several guards survive:** the first-publish `chmod`, the pre-publication `_replaceable` recheck,
    the nested-overlap checks, the byte limit, the manifest's `fragment_id` check, the symlink checks and the
    readbacks.
  - **Reuse decodes with Pillow, the loader with OpenCV.** A legacy ZSTD- or LZMA-compressed layer can read
    `READY` and still fail in `cv2.imread`. 1-bit, LA and RGB labels and masks, which the old converter
    accepted, are refused; the guide says so, the record and README do not.
- **#312:**
  - **A symlink loop in an output path escapes as `RuntimeError` (exit 1).**
  - **Exit codes.** The guide says usage errors exit 2, but an out-of-range limit such as
    `--max-hole-pixels 0` exits 1.
  - **Untested guards.** Removing any of these still leaves the tests passing: the PNG readback, the re-read hash
    check, the source-copy check, the dry run's recheck, and the inclusive limits. The standalone help test blocks
    only Torch-era packages, not cv2 or numpy.
  - **The record's wording.**
    - It says the old wrapper picked its fallback backend "silently"; it logged a warning, but did not record the
      backend in its outputs.
    - It repeats "89–97% overfilled"; it is dated and unchanged here.
- **#302:**
  - **The audit test is outside the standard suite.** `tests/test_loop_unchanged_control_audit.py` runs only with
    the other modules outside it.
  - **The readout cannot be re-run from the repository.** It reads a copy of the loop's `cycles.jsonl` that is not
    committed.
- **The doc audit** lists #312's record's blob id `daee6a9e…` as unresolved. It is a Git blob id, not a commit;
  the id is right.

## Verification

- **The conversion tests:** 69 passed. Each of the five new tests fails on #310's code.
- **The label proposal, data catalogue and measurement tests:** 315 passed. The new cases fail on the code before.
- **#302's and #308's tests:** 99 passed and 3 skipped (the pinned-source cases).
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the changed Python files. Mypy is clean over the
  whole repository (854 files at the baseline).
- **The standard suite at the baseline** gives the same 43 failures as before, from `s3fs`, `numba`,
  `jsonschema` and Villa files absent here. The same 2 modules cannot be collected (`tensorstore`, `s3fs`).
- **The 230 test modules outside the suite at the baseline** give 2,101 passed, 80 skipped, 13 failed and 21
  collection errors: the same failures as before.
- **The doc audit** finds no new unresolved reference except that blob id.
