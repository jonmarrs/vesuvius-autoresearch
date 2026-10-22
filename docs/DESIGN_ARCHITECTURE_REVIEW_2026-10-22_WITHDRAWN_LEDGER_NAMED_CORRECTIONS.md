# Design and architecture review — every withdrawn claim names its correction

Date: 2026-10-22. Baseline: `305a69ed` (main after #190).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `tests/test_withdrawn_claims_stay_withdrawn.py`, the ledger that keeps a withdrawn claim from surviving as
a live assertion, and the documents it scans.
- **How it works.** The ledger matches the claim, not the digits. A paragraph that asserts a withdrawn claim
  passes only if it also carries the correction.
- **The generic list.** Until #190 the correction could be any of fifteen withdrawal words: "withdrawn",
  "superseded", "corrected", "becomes" and others.
- **What #190 found.** FINDINGS still said two flattens "land on surfaces 7.15 vx apart". Its paragraph passed
  because it said "superseded" about something else. #190 gave that one entry a named correction. It recorded the
  other eleven as an open question: they still took any word.

Main has not moved since #190. There are no open pull requests. This round covers the 22:12 UTC firing.

## What changed

- **The coarse exemption cleared a stale claim a second time.**
  - The scan: every paragraph each older entry matches, with the withdrawal words that cleared it.
  - **The hit:** `two_seed_check_lets_through_one_in_six.md` still said two seeds catch a 5% gain "75% of the
    time". Its 09-13 revision was itself superseded on 09-19: at the nine-seed CV 0.0536 it is 44%.
  - **What cleared it:** "superseded", which there means "the superseded tree", and "withdrawn", which there
    belongs to the 99.2% beside it.
  - **Change:** the paragraph carries a dated note.
- **Every entry now names its correction.** The fifteen-word list is gone. Each entry's fourth element is what a
  paragraph quoting the claim must also say: the replacement figure, or the retraction's own words.
  - **The replacement figure:**
    - 0.0536 for the two withdrawn CVs;
    - 12% for the two loop resolutions;
    - 44% for the two-seed powers;
    - 660 MB for the image size;
    - 206 for the offline test count.
  - **Or the retraction's own words:**
    - "[WITHDRAWN", "RETRACTION" or 2.0× for the 4.1× ratio;
    - "one draw", 3.04% or 0.0014% for the 1.4% floor;
    - "cannot apportion" or "originally read" for the 59% share.
  - Every paragraph the old list cleared still passes, except the stale one above. A test requires every entry
    to name its correction.
- **"4× quieter" outlived "4.1× quieter".**
  - The entry matched only the exact figure. The rounded form survived in two places:
    - the summary's finding 27: villa's fits "just got 4× quieter";
    - `two_seed_check_lets_through_one_in_six.md`.
  - The current and pinned tiers differ 2.0×, which is not established.
  - **Change:**
    - the pattern takes the rounded figure;
    - the summary is corrected in place;
    - the report gains a note.
- **The current-code null's ±3% bound had no entry.**
  - #190 withdrew it in FINDINGS. It rests on three control seeds at CV 0.0124. Against the six render-matched
    seeds the null is −4.41% [−12.18%, +3.37%] (`control_sensitivity.md`).
  - #190 left it out of the ledger. Most copies quote the interval itself, which is a true measurement for the
    registered control.
  - **The new entry matches the bound, not the interval:** "excludes … ±3%", "bounds ±3%", "the ±3% bound".
  - **It found five live copies:**
    - the summary's finding 27, corrected in place;
    - `noise_floor_by_tier.md` and `step2_across_surfaces.md`, which carry notes;
    - the September filing draft, twice. Its head note now lists the bound among the withdrawn figures.
- **Tests:** in `tests/test_withdrawn_claims_stay_withdrawn.py`:
  - the new entry;
  - the broadened 4.1× pattern, with a test that it still ignores "a 14x quieter scorer";
  - the 75% example, rewritten to show a stray "superseded" no longer clears it;
  - a test that every entry names its correction.

## Verified, no change needed

- **The other paragraphs the old list cleared** name their correction:
  - the 4.1× retraction and its bracketed note;
  - "now 0.0536" beside the September draft's 0.0263;
  - "becomes 44%";
  - "one draw" beside each 1.4%;
  - "originally read" beside the 59%.
- **The interval [−2.56%, +3.13%]** is quoted in about a dozen dated reports and the filing records. It is the
  registered control's measured interval, true as stated. The bound drawn from it is what was withdrawn.

## Observations for the owner (not changed)

- **A named correction is only as good as its marker.** "control seeds" or "12%" in a paragraph could belong to
  another sentence. The markers are the replacement figures, which rarely appear by chance, but a stray match
  would clear a stale claim as the old list did.
- **The ledger covers only claims entered in it.** Each correction this round and the last two fixed was in a
  report, missing elsewhere, and found by reading. A correction that never enters the ledger has no guard.

## Verification

- `pytest tests/test_withdrawn_claims_stay_withdrawn.py`: 17 passed.
- **Mutants:**
  - main's version of each of the five changed documents fails the new ledger;
  - main's ledger passes main's documents (15 passed), and the new ledger fails them on its three new or
    tightened entries.
- **Guards and audit:**
  - The nine doc-guard files, six report-number files and the FINDINGS test were run on main and on the branch,
    with the doc audit (`audit_doc_references.audit()`). They differ only by the two new tests: 200 passed on
    main, 202 on the branch.
  - The one failure is `test_live_documents_stay_clean`, from villa paths, as on main.
  - The audit gains no entries.
- Ruff 0.9.10 `check` and `format` are clean on the test file.
- **The standard suite** with the locked-package overlay: pending. Of its files, only
  `test_findings_headline_numbers.py` reads a changed document (the summary).
- **Pending:** the standard suite and the independent review.
