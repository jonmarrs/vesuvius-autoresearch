# Design and architecture review — the owner's #193 and #194, and the MDE in README and FINDINGS

Date: 2026-10-23. Baseline: `9f222e32` (main after the owner's #193 and #194; #192 merged before them).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12, 04:12, 05:13, 06:12 and 07:13 UTC firings.
- **#193** added the evidence and harness for villa #2258, which fixes fractional fiber seed planes:
  - a report;
  - `repro/fibers/check_fractional_plane_spacing.py` and its example;
  - three evidence JSONs;
  - the upstream patch and its PR record.
- **#194** added the record of villa #2259, which documents headless AppImage CLI use: an evidence JSON,
  the patch, and an opportunity review.
- **Both** updated the October filing draft for villa #2155's merge.

## What changed

- **The fractional plane-spacing harness had no test.**
  - What the evidence rests on is what the harness refuses:
    - running the rest of villa's `volume.py`, whose model imports are not installed;
    - a source whose seed functions changed shape;
    - a mask that is not the published one;
    - a default spacing whose seed arrays moved;
    - overwriting an evidence file.
  - `tests/test_check_fractional_plane_spacing.py` (11 tests) drives both scripts on a stand-in
    `volume.py`. Its module top imports a package that does not exist and then raises, so a harness that
    ran it would fail.
  - The tests use synthetic packed masks, so neither villa nor the data is needed.
  - Eight mutants of the scripts' refusals each fail a test.
- **The fractional plane-spacing report's figures are bound to its evidence.**
  - The before → after dot-count table equals the final JSON's nine rows.
  - The claim that every result row, seed-array hashes included, equals the initial measurement holds:
    the two JSONs' rows are identical and only the source hashes differ.
  - "+8/-2 production lines, plus 58 lines of tests" is the committed `.patch`.
- **villa #2259's PR record is bound to its evidence** (`tests/test_villa_headless_cli_record.py`, 3 tests):
  - the proof table: SIGSEGV and shell status 139 for the direct binary; exit 0 through `AppRun` and
    extract-and-run; usage and exit 1 for the trim tool;
  - the release name and hash, and the headless environment;
  - "+29/-1 lines" in two files.
- **README and FINDINGS still gave the design MDE as the bound.** Both said the two pinned ink nulls (patch
  bootstrap, stripmatch) are bounded at ~12%.
  - The README test read that figure from each study's `mde` field.
  - The data exclude [−18.4%, +16.7%] and [−20.7%, +13.1%].
  - #192 corrected the summary the same way; the two front documents were missed.
  - Both now carry the correction, and `test_readme_headline_numbers.py` binds the intervals in both from
    `manipulation_effects_survey.json`.
- **The villa PR candidate for #1866** gains a head note. Its posted text says the deterministic flatten
  costs "roughly 9.5× the flatten time (~11 min instead of ~4)". 9.5× is the stage-0 throughput; ~11 min
  against ~4 is about 2.7× the wall time.

## Verified, no change needed

- **The October filing draft's #2155 entry.** It merged at `2026-10-21T19:50:31Z`, which is 21 October
  Pacific. The filing checker's test pins it.
- **The fractional plane-spacing defect.** The old `range(..., int(52.73))` gives planes 0, 52, 104;
  quantising each global multiple gives 0, 52, 105, as the report and example state.
- **villa #2259's record** matches its evidence JSON on every row.

## Observations for the owner (not changed)

- **villa #1866's posted text** still says "roughly 9.5× the flatten time". Correcting it means a comment on
  the upstream PR, which this review does not post. The local record now says so.
- **The September SUBMIT filing** keeps "9.5× flatten cost" as filed.
- **The headless record's extract-and-run row** names `APPIMAGE_EXTRACT_AND_RUN=1`. The evidence JSON
  records the command but not the environment it ran under.

## Verification

- Pending: the standard suite, doc guards and audit, independent review.
