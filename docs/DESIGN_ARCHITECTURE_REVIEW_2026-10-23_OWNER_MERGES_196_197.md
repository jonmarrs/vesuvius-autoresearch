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
  - The evidence for the fix is what the probe does with what villa returns:
    - a cycle is a timeout and exits 1;
    - a bounded retry is a RuntimeError after exactly the two patches, and exits 0;
    - anything else is not bounded.
  - It also refuses five things before writing:
    - a mesh file that is not the published one;
    - a corner with surface in it;
    - a patch villa does not reject;
    - a voxel read before the geometry rejects the patch;
    - an existing record.
  - `tests/test_check_retry_cycle.py` drives it in a subprocess on stand-in villa modules (config,
    types, tifxyz and the dataset) and a stand-in mesh, so neither villa nor the mesh is needed.
  - **The dataset's retry loop has eight variants:**
    - a cycle like villa's before the fix;
    - a bounded loop;
    - five that are not bounded: a sample returned, a stop after one patch, the same patch twice,
      a fix that counts attempts but does not remember them, and both patches then a return;
    - both patches then a different exception, which the probe must not classify.
  - The stand-in surface reports half its shape until `use_full_resolution()` is called. So a probe
    that read the shape first would misplace the second corner.
  - **Each mesh file's hash and each corner** is refused on its own.
  - **The tests also bind what the probe hands villa:**
    - the whole data mapping, including `volume_scale` 0, the full-resolution grid the report
      describes;
    - every segment field;
    - the two corner bounding boxes;
    - no augmentation.
  - **The record's scope and source URL** are the committed records'. The watchdog fires between 2 and
    5 s.
  - **43 mutants** of the probe each fail a test. They cover:
    - every refusal, including a check of only one hash or one corner, and a missing pre-check;
    - four weakenings of the bounded condition, and catching every exception;
    - the exit code and the timer;
    - every recorded field;
    - every setting and segment field it passes.

    The independent review found 15 of these surviving the first version of the tests. They are all
    caught now.
- **#196's report and draft are bound to the records, the patch and the transcript.**
  - **Probe records.** Both records carry the probe's own input hashes and source URL, and the
    corners of their mesh shape.
  - **`dataset.py` hashes.** The before record's is villa `e2254ebe`'s `dataset.py`, and the after
    record's is that file with the committed patch applied. That was checked against the villa clone
    here; the test, which cannot rely on villa, checks only that the two differ.
  - **Report and draft.** "7,358 attempts; watchdog after 2.009 s" and "2 attempts" are the records.
    So are the 50,600 by 36,400 grid and the download URL.
  - **The bounded error.** The after record's message is the patch's own `RuntimeError` text, filled
    in with two attempts, index 0 and dataset size 2.
  - **The patch and transcript.** These figures are the committed patch and the transcript:
    - +17 production lines, none removed;
    - the 64-patch budget, in the report and in both places in the draft;
    - nine new cases, each parametrization counted;
    - the baseline's five failures, each one of the new cases, and four passes;
    - the 13 selected and 40 deselected, so four existing cases;
    - the smoke's 8/11.
- **#197's report and draft are bound to the audits and the snapshot record**
  (`tests/test_fiber_reference_provenance_record.py`):
  - **The snapshot record** binds both audits by SHA-256, and each hash is the committed audit's.
  - **The two scripts** are bound too: each hash is a version of the script this repository has
    committed. So a later fix to either script does not falsify the snapshot it made.
  - **Counts and commands.** File counts and bytes are the audits' inputs. The commands and the
    downloader's printed totals are the record's.
  - **The record's Python version and villa base.**
  - **Both tables.** The folder table is the span counts per folder. The frame table is each frame's
    `trace` share, to four places.
  - **Totals.** 620 and 233 files, 853 in all, and the 318,241,559 bytes.
  - **Missing frames.** As many files lack a source resolution as lack a frame: 1 and 228. The audits
    hold counts, not per-file metadata, so they do not show these are the same files.
  - **One `trace` configuration per folder**, covering every `trace` span: "beam width 8, lookahead
    2 and cone angle 25 degrees", in the report and the draft.
  - **The local-path manifest spans**, 912 and 1,181. Every manifest is a public URL or an absolute
    local path.
  - **The draft's figures:** 13,862 and 2,422 spans.
  - **The patch** is eight lines, all added.
  - **The native retry run** it quotes, 13 passed and 40 deselected, is #196's transcript.
  - **The test count** is the nine cases of `test_audit_fiber_reference_provenance.py`, as the
    report's own commit held the file.
- **A perturbation probe:** each of 46 bound figures in the two reports and two drafts, changed by one
  digit, fails a test.

## Verified, no change needed

- **The villa patch's logic.** Each patch is tried at most once.
  - **The escape terminates.** The budget check comes before it, so fewer than `len(patches)` indices
    are taken when it runs.
  - **Negative indices.** A negative index is counted as its positive patch. Its first seeded draw
    can be that same patch, and the escape moves past it.
  - **Unchanged paths.** The single-patch error and flat sampling do not change.
  - **Fuzzing.** The independent review ran the patched loop, extracted verbatim, over 4,000 random
    cases: 2 to 1,000 patches, with negative indices. There were no revisits, no budget overruns and
    no false failures.
- **#196's table row "4 passed, 40 deselected"** is derived: the transcript records one combined run,
  13 passed and 40 deselected, which is the nine new cases plus four existing ones. The report says
  so later in the same section.
- **The audit script** does not pool frames, counts missing metadata as unknown, and reads each span's
  mode from its starting point. Its own nine tests cover each of these.

## Observations for the owner (not changed)

- **The downloader can drop listed files without saying so.** `Listing` skips any `.json` href
  containing `/`, `\`, `:` or `%`. An autoindex lists a name with a space as `%20`, so such a file
  would be neither downloaded nor counted. The downloader would still print "Downloaded all N listed
  JSON files".
  - Replaying the parser on the captured listings, as the report did, checks only that accepted
    names match the manifest. It does not check that no name was rejected.
  - The captured listings are outside the repo, and this container cannot reach `dl.ash2txt.org`.
  - **Proposed fix:**
    - decode the href before validating it, and download a `%20` name under its decoded name;
    - keep refusing names that point outside the folder (the owner's tests feed `../outside.json`);
    - record any `.json` href skipped in the manifest.

    The snapshot test accepts any committed version of the script, so the fix needs no new snapshot.
- **The probe counts any RuntimeError after both patches as bounded,** whatever its message. The after
  record's message is the patch's, and is bound, so the evidence is sound. A rerun on other code could
  mislead.
- **The probe's exit codes.**
  - Exit 1 is both a timeout and any refusal, which exits 1 as an uncaught exception. Only the record,
    which a refusal never writes, tells them apart.
  - The report gives the expected statuses, 1 and 0, as the check.
- **The probe's voxel sentinel** traps only indexing. Real villa's first touch of a patch it does not
  reject is `volume.shape`, which raises AttributeError, not the sentinel's message. The probe still
  stops; only the message differs.
- **The probe's corner and pre-checks are bare `assert`s,** which `python -O` removes.
- **The probe hashes each mesh file with `read_bytes()`,** which loads it whole into memory.
- **Run times.** The fiber report gives the audit tests' and smoke's times as 0.08 s and 6.7 s in its
  text, and 0.09 s and 6.8 s in its command block: two runs, presumably.
- **The audit's unknown values differ.** A missing frame is grouped as `unknown`, and a null source
  resolution as `None`.

## Verification

- **New tests:** 29 passed, and the owner's nine audit tests pass beside them.
  - **43 of 43 mutants** of the probe fail a test.
  - **46 of 46 perturbed figures** fail a test, as do the record's Python version, villa base, the
    fiber report's 13/40 and the draft's 64-attempt budget.
  - A later edit to either fiber script, or a test added to the audit tests, does not fail.
- **Ruff** 0.9.10 `check` and `format` are clean on the new test files.
- **The ledger** passes over this doc.
- **The suite coverage guard** (`test_validation_suite_covers_the_loop.py`) passes. The new tests
  exercise repro scripts, not the loop's code, so they are outside the standard suite, as round 106's
  were. The guard once read a stand-in module's literal `"config.py"` as the loop's
  `scripts/training/config.py`, so the stand-ins name their modules without the suffix.
- **Doc guards.** Every test file that reads a changed doc or globs the docs (11 files) gives 378
  passed and 2 skipped on main and on the branch.
- **Doc audit:** the branch gains no entries.
- **The standard suite** with the locked-package overlay, on the first commit: 2813 passed, 22 skipped
  and 1 xfailed, as on main. The ten failures are main's ten environmental ones: nine need villa
  files, one is `gp_winner`.
- **Independent review** of the first commit found one blocking item: the mutant claim above was
  false, with 15 probe mutants surviving. Its should-fix items were:
  - a missing-frame claim the counts cannot make;
  - script-hash and test-count bindings that no later edit could satisfy;
  - a proposed downloader fix that contradicts the owner's tests.

  All are fixed in the second commit, with its nits: the stand-in descriptions, the manifest wording,
  local-path counting and three more bound figures.
