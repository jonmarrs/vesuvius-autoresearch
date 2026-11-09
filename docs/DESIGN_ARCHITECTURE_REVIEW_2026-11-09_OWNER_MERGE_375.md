# Design and architecture review — the owner's #375

Date: 2026-11-09. Baseline: `1e69d0b9` (main after round #155's merge, which carried #375).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12 UTC firing on 2026-11-09. The owner merged #375 at 02:21 UTC, during round #155, which left
its review to this round. #375 corrects what finding 106's report and its villa draft say a face crossing is, and
what merge-penalized ERL is scored against.

## What changed

**#375's second coverage correction is now tested** (`tests/test_afv_generator_block_seams_report.py`).

- In this report, "the reference" is arm one: the arms list reads "one: one block, the reference".
- #375 changed both coverage sentences from "the reference" to "the hand tracing", which coverage is scored against:
  - "covered a median +0.0152 more of the hand tracing than one block";
  - "the two copies of a fiber … miss the hand tracing in different places".
- Only the first was tested. The added assertion fails on the text before #375.

## Verified, no change needed

- **A crossing follows arm one's fibers, as #375 now says.**
  - The registration defines "each reference crossing of a mid plane (a one-block `main` fiber with 40 voxels on both
    sides)".
  - `run()` sets the reference to arm one's main fibers. It is the only caller of `crossings()`.
  - So the report's "a fiber of arm one (main)" and the draft's "a fiber written from the cube as one block" match both.
  - The old "hand-traced fiber" wording matched neither. #375's test reads `run()`'s source to pin it.
- **ERLpen is scored against the hand tracing.**
  - `score_tracing` takes the cube's hand tracing, and the crossings never enter it.
  - So "scored against the hand tracing, not at these crossings" is right where "counts both" was not.
- **No other text still calls these crossings hand-traced.** The strategy entry and the November draft give only the
  counts (172 → 278 of 1,304), which #375 does not change.
- **#375's figures are unchanged.** It rewords sentences only; every number in the report and the draft is the same.
- **#375's tests.**
  - Its new test and its updated assertions pass.
  - Each fails on the text before #375, which still said "hand-traced fiber crosses" and "counts both".

## Observations for the owner (not changed)

- Four lines of the report and one of the draft run past 120 characters, the line length the other documents keep.
  One of them is #375's: the report's crossing definition, now 124 characters.

## Verification

VERIFICATION

## A note on this round's work

- #375 merged during round #155. That round merged it into its branch and ran finding 106's modules (58 passed), and
  left the review to this one.
