# Design and architecture review — every withdrawn claim names its correction

Date: 2026-10-22. Baseline: `305a69ed` (main after #190).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `tests/test_withdrawn_claims_stay_withdrawn.py`, the ledger that keeps a withdrawn claim from surviving as
a live assertion, and the documents it scans.
- **How it works.** The ledger matches the claim, not the digits. A paragraph that asserts a withdrawn claim
  passes only if it also carries the correction.
- **The generic list.** Until #190 the correction could be any of fifteen withdrawal words: "withdrawn",
  "superseded", "corrected", "becomes" and others.
- **What #190 found.** A FINDINGS paragraph still placed two flattens 7.15 vx apart, when they lie on the same
  surface 0.25 vx apart along the normal. It passed because it said "superseded" about something else. #190
  gave that one entry a named correction. It recorded the other eleven as an open question: they still took
  any word.

Main has not moved since #190. There are no open pull requests. This round covers the 22:12 UTC firing.

## What changed

- **Every entry now names its correction.** The fifteen-word list is gone. Each entry's fourth element is what a
  paragraph quoting the claim must also say: the replacement figure, or the retraction's own words. A test
  requires every entry to have one.
- **The current-tier noise figures had been replaced twice, and the ledger knew only the first time.** On
  2026-09-19 six unused seeds moved the current-tier CV to 0.0536 (df=11). Current code is then no quieter
  than the pinned tree: 1.0×, F(18,11)=0.92, p=0.84. The MDE at 3v3 is 12.3%, and two seeds catch a 5% gain
  44% of the time.
  - The ledger had entered the CV itself, but not the ratio, the MDE or the power as replaced figures.
  - The first commit made the earlier 2.0× ratio the 4.1× entry's correction, and wrote it into two notes. The
    independent review caught this. The marker is now 1.0× or F(18,11), and a new entry covers 2.0× itself
    (`F(18,6)=3.83`).
- **Markup and rewording hid live copies.** The patterns wanted the plain form. Bold between a figure and its
  context defeated them: the summary's finding 27 still said two seeds catch a 5% gain "**75%** of the time",
  where the figure is 44%. Each pattern now allows bold and spacing, and the near-variants:
  - the CV: "seed noise of", "seed CV of", "seed noise on `total_fg_pixels` is", "Current villa is";
  - the MDE: "sees 6.0%" as well as "resolves";
  - the 4.1×: "4× quieter" and "four times quieter";
  - the 1.42% floor: "deterministic to within" and the floor tables' "pipeline non-determinism";
  - the ±3% bound: "±3.0%", "+/-3%", "rules out", "within".
- **Markers tightened to the figure.**
  - "44%", "12.3%" and "890×" cannot match inside 1.44%, 0.44% or 112.3%.
  - The 206-test count needs "all 206" or "206 tests pass": 1,789,206 is an ink count.
  - The 1.42% floor needs "one draw" or the second pair's 890×. 3.04% is quoted beside the flatten in 31 files.
  - The ±3% bound needs the render-matched figure, or "three unusually tight" seeds. "Control seeds" and the
    CV 0.0124 appear in paragraphs that still state the bound.
  - The generic "retraction" is gone from the 4.1× entry. It keeps "[WITHDRAWN 2026-09-13", the stamp on
    the original paragraph.
- **The current-code null's ±3% bound had no entry.** #190 withdrew it in FINDINGS. It rests on three control
  seeds at CV 0.0124. Against the six render-matched seeds the null is −4.41% [−12.18%, +3.37%]
  (`control_sensitivity.md`). The new entry matches the bound ("excludes … ±3%", "the ±3% bound"), not the
  interval [−2.56%, +3.13%], which is a true measurement for the registered control.
- **What the new entries and patterns found, and how each is corrected:**
  - **The summary**, corrected in place:
    - Finding 26 still gave the CV as 0.0263, the ratio as 2.0× and the MDE as 6.0%. It now gives 0.0536,
      1.0× and 12.3%, with the history.
    - Finding 27 gave 75%. It now gives 44%, and 73% for a 10% gain. Its claim that the power criticism had
      expired is withdrawn: at 44% two seeds miss a 5% gain more often than they catch it. Its heading says the
      criticism "weakened".
    - The floors table gave the 1.42% determinism floor alone. It now gives the two draws, 1.42% and 3.04%.
    - Finding 45 still said same-winding-current "bounds ±3%" below its own correction. That phrase is struck.
  - **The two-seed report** gains a head note: 0.0536, 1.0×, 44% and 73%. Its 2026-09-12 section's 8.7× ratio,
    power column, "excellent power" and three-seed 86% were all computed at superseded CVs.
  - **`decoupling_does_not_cleanly_reproduce.md`** gains a 1.0× note beside its 2.0×. Its "three times more
    informative" rested on the ±3% bound and is noted.
  - **The September filing draft's** head note now names the replacements, 0.0536 and 12.3%, beside the
    figures it withdraws.
  - **Three reports** used 1.42% as the same-fit floor: `duplicate_coverage_inflates_the_objective.md`,
    `objective_seed_noise_floor.md` and `seed_spread_four_fits.md`. Each gains a head note: a same-tree repeat
    on 2026-09-20 gave 3.04%. Arms B and D still clear it.
  - **`anchor_ablation_verdict.md`** quoted the registration's CV of 0.0125 as "the current tier's". It gains a
    note.
  - **`noise_floor_by_tier.md`, `decoupling_does_not_cleanly_reproduce.md` and `step2_across_surfaces.md`**:
    their ±3% notes now say the bound was withdrawn, not the interval. Step 2's note adds that its comparison
    with the bound no longer holds.
- **Tests:** in `tests/test_withdrawn_claims_stay_withdrawn.py`:
  - the ±3% and 2.0× entries;
  - fourteen live phrasings, each of which outlived its entry, now matched and not cleared;
  - the tightened markers, against the strays that cleared the old ones;
  - "a 14x quieter scorer" still not matched;
  - the 75% example, rewritten to show a stray "superseded" no longer clears it;
  - every entry names its correction.

## Verified, no change needed

- **The paragraphs the old list cleared** that name their correction still pass:
  - the 4.1× retraction and its bracketed note;
  - "now 0.0536" beside the September draft's 0.0263;
  - "becomes 44%";
  - "one draw" beside each 1.4%;
  - "originally read" beside the 59%.
- **The interval [−2.56%, +3.13%]** is quoted in about a dozen dated reports and the filing records. It is the
  registered control's measured interval, true as stated.
- **Head notes** that clear a dated document are each a correction of that document's figures.
- **The ±3% withdrawal date.** The notes say 2026-09-27, the date of `control_sensitivity.md`, which found it.
  The September SUBMIT filing withdrew its own copy on 2026-09-29. Both dates are right.

## Observations for the owner (not changed)

- **A named correction is only as good as its marker.** The markers are now the replacement figures, bounded so
  they cannot match inside other numbers. A paragraph that quotes a stale claim and the replacement figure for
  an unrelated reason would still pass.
- **The ledger covers only claims entered in it.** Each correction this round and the last two fixed was in a
  report, missing elsewhere, and found by reading. A correction that never enters the ledger has no guard.
- **A replacement figure is a claim too.** The 2.0× and the 0.0263 were both replacements, and both were
  later superseded. When a figure is replaced, its predecessor's entry needs the new marker, and the
  predecessor's replacement needs its own entry.
- **One false positive is possible.** The ±3% pattern would also flag an unrelated bound of three percent
  written with the ± sign. Nothing in the corpus has one now.

## Verification

- `pytest tests/test_withdrawn_claims_stay_withdrawn.py`: 33 passed. Main's ledger has 15 tests.
- **Mutants**, each run against the ledger on a copy of the branch's documents:
  - Main's version of each of the ten changed documents fails.
  - 19 of 22 targeted mutants fail. These include reverting any note, bolding the 75% again, and restoring
    the 1.42% row. They also include eight stale paragraphs carrying a stray marker: the old ones cleared
    every such paragraph.
  - **The three that pass do so by design.** Finding 26 names 0.0536 in its history, so reverting only its
    headline figure is cleared by the same paragraph. Finding 45 opens with its correction. The two-seed
    report's head note covers its 4× note. The ledger works at paragraph level and is not built to catch these.
- **Doc guards.** Every test file that reads a changed document (25 files) was run on main and on the branch:
  - 561 passed on main and 579 on the branch, the difference being the 18 new ledger tests;
  - the one failure on both is `test_live_documents_stay_clean`, from villa paths.
- **One binding moved.** `test_readme_headline_numbers.py` pinned finding 26's old wording, "0.0263 (df=6) —
  first published as 0.0125". It now binds the current figure and the history that replaced it.
- **Doc audit** (`audit_doc_references.audit()`): the branch gains no entries.
- Ruff 0.9.10 `check` and `format` are clean on both changed test files.
- **The standard suite** with the locked-package overlay: pending.
- **Independent review** of the first commit: two blocking findings, both above, and eight should-fix
  findings, all fixed here. Its nits are fixed: the ragged wraps, the step 2 note, and the wording that read as
  if the interval itself were withdrawn. Its date nit is answered above.
