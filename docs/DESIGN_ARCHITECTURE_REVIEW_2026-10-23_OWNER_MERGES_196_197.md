# Design and architecture review — the owner's #196 and #197

Date: 2026-10-23. Baseline: `b3c99def` (main after #198; the owner merged #196 and #197 before it).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 09:12, 10:13, 11:17 and 12:18 UTC firings.
- **#196** prepared a fix for villa #1482: a rejected native ink crop can trap a DataLoader worker
  in a retry cycle. It added:
  - the report and the PR draft;
  - the portable patch;
  - `repro/ink_native/check_retry_cycle.py`, a probe on a published mesh;
  - its before and after records and a validation transcript.
- **#197** audited the provenance of the published fiber references for villa #2264. It added:
  - `scripts/audit_fiber_reference_provenance.py`, its tests, and a downloader;
  - two audit JSONs and a snapshot record;
  - the report, an eight-line documentation patch and its PR draft.

## What changed

- **The retry probe had no test.**
  - The evidence for the fix is what the probe does with what villa returns. A cycle is a timeout
    and exits 1. A bounded retry is a RuntimeError after exactly the two patches, and exits 0.
  - It also refuses four things before writing:
    - a mesh that is not the published one;
    - a corner with surface in it;
    - a voxel read before the geometry rejects the patch;
    - an existing record.
  - `tests/test_check_retry_cycle.py` drives it in a subprocess on stand-in villa modules: config,
    types, tifxyz, and the dataset with villa's two retry loops. The mesh is a stand-in too, so
    neither villa nor the mesh is needed.
  - The stand-in stores its grid at half resolution, so a probe that read the shape before
    `use_full_resolution()` would misplace the second corner.
  - The tests also bind what the probe hands villa:
    - the two corner bounding boxes;
    - `full_3d`, the 17×64×64 patch and seed 17;
    - no augmentation;
    - the segment directory.
  - **20 mutants** of the probe each fail a test. They cover:
    - every refusal;
    - the bounded condition;
    - the exit code and the timer;
    - every recorded field;
    - every setting it passes.

    The first run left one alive: with the corner check gone, the voxel sentinel still stopped the
    probe. That test now uses a sample method that rejects everything, so only the corner check can
    stop it.
- **#196's report and draft are bound to the records, the patch and the transcript.**
  - **Probe records.** Both records carry the probe's own input hashes and source URL, and the
    corners of their mesh shape. Each was taken on a different `dataset.py`.
  - **Report and draft.** "7,358 attempts; watchdog after 2.009 s" and "2 attempts" are the records.
    So are the 50,600 by 36,400 grid and the download URL.
  - **The bounded error.** The after record's message is the patch's own `RuntimeError` text, filled
    in with two attempts, index 0 and dataset size 2.
  - **The patch and transcript.** These figures are the committed patch and the transcript:
    - +17 production lines, none removed;
    - the 64-patch budget;
    - nine new cases, each parametrization counted;
    - the baseline's five failures, each one of the new cases, and four passes;
    - the 13 selected and 40 deselected, so four existing cases;
    - the smoke's 8/11.
- **#197's report and draft are bound to the audits and the snapshot record**
  (`tests/test_fiber_reference_provenance_record.py`):
  - **The snapshot record** binds by SHA-256 the audit script, the downloader and both audits. Each
    hash is the committed file's. File counts and bytes are the audits' inputs, and the commands and
    the downloader's printed totals are the record's.
  - **Both tables.** The folder table is the span counts per folder. The frame table is each frame's
    `trace` share, to four places.
  - **Totals.** 620 and 233 files, 853 in all, and the 318,241,559 bytes.
  - **Missing frames.** The 1 and 228 files with no frame are exactly those with no source resolution.
  - **One `trace` configuration per folder**, covering every `trace` span: "beam width 8, lookahead
    2 and cone angle 25 degrees", in the report and the draft.
  - **The local-path manifest spans**, 912 and 1,181.
  - **The draft's figures:** 13,862 and 2,422 spans.
  - **The patch** is eight lines, all added.
  - **The test count** is the nine cases of `test_audit_fiber_reference_provenance.py`.
  - Editing either script now fails this test until a new snapshot or a note says what changed.
- **A perturbation probe:** each of 46 bound figures in the two reports and two drafts, changed by one
  digit, fails a test.

## Verified, no change needed

- **The villa patch's logic.** Each patch is tried at most once.
  - **The escape terminates.** The budget check comes before it, so fewer than `len(patches)` indices
    are taken when it runs.
  - **Negative indices.** A negative index is counted as its positive patch. Its first seeded draw
    can be that same patch, and the escape moves past it.
  - **Unchanged paths.** The single-patch error and flat sampling do not change.
- **#196's table row "4 passed, 40 deselected"** is derived: the transcript records one combined run,
  13 passed and 40 deselected, which is the nine new cases plus four existing ones. The report says
  so later in the same section.
- **The audit script** does not pool frames, counts missing metadata as unknown, and reads each span's
  mode from its starting point. Its own nine tests cover each of these.

## Observations for the owner (not changed)

- **The downloader can drop listed files without saying so.** `Listing` skips any `.json` href
  containing `/`, `\`, `:` or `%`. An autoindex lists a name with a space as `%20`, so such a file
  would be neither downloaded nor counted. The manifest would still say "all listed".
  - Replaying the parser on the captured listings, as the report did, checks only that accepted
    names match the manifest. It does not check that no name was rejected.
  - The captured listings are outside the repo, and this container cannot reach `dl.ash2txt.org`.
  - **Proposed fix:** count rejected `.json` hrefs and refuse when there are any. That changes the
    downloader's hash, so it needs a new snapshot or a note in the record.
- **The probe counts any RuntimeError after both patches as bounded.** A different error raised after
  the second attempt would pass. The after record's message is the patch's, and is bound, so the
  evidence is sound. A rerun on other code could mislead.
- **The probe's corner and pre-checks are bare `assert`s,** which `python -O` removes.
- **The probe hashes each mesh file with `read_bytes()`,** which loads it whole into memory.

## Verification

- **New tests:** 18 passed, and the owner's nine audit tests pass beside them. **20 of 20 mutants** of
  the probe fail a test. **46 of 46 perturbed figures** fail a test.
- **Ruff** 0.9.10 `check` and `format` are clean on the new test files.
- Pending: the ledger, doc guards, doc audit and the standard suite.
