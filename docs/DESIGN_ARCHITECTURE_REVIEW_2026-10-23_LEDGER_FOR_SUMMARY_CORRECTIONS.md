# Design and architecture review — the corrections of #192 and #195 enter the withdrawn ledger

Date: 2026-10-23. Baseline: `1862350c` (main after #195).
Reviewer: Claude (Anthropic), at the owner's request.

#192 and #195 corrected figures in the summary, README and FINDINGS that later reports had already
corrected. Those corrections are bound where they were made. Nothing kept the claims from coming back
elsewhere, or from surviving in the dated reports that first made them. The withdrawn-claims ledger
(`tests/test_withdrawn_claims_stay_withdrawn.py`) is the repo's mechanism for that.

This round covers the 08:13 UTC firing. The owner's #196 and #197 merged while it ran; they touch none of
its files, and main is merged in.

## What changed

- **Four ledger entries.** Each names the correction a paragraph quoting the claim must carry:
  - **The count "reproducing to 1.2%"**, also as "`total_fg_pixels` to 1.2%". 1.2% is the CV of
    `curbase_s1-s3` (0.0124): three seeds, since found unusually tight. Across all nine seeds of that
    configuration it is 6.4% (`control_sensitivity.md`). Marker: 6.4%, 0.0644, the `s4-s9` seeds' 7.4%,
    or "three (unusually) tight".
  - **The inner floor "2.6× too wide"** for the outer windings, also as "two and a half times quieter".
    2.6× is 0.1086 / 0.0421, the inner CV over the outer one at n=4. Pooled over the pinned tier's 24
    outer fits at df=18 the outer CV is 0.0514, and the ratio about 2.1× (`noise_floor_by_tier.md`).
    Marker: 2.1×, or the summary's "about twice at df=18". df=18 alone is not one: a paragraph can name
    the pooling and keep the 2.6×.
  - **Nulls "bounded at ~12%".** ~12% is the pinned tier's design MDE, not what the data rule out. Marker:
    "is the design MDE", which says what 12% is. Naming the MDE beside the bound does not.
  - **Finding 70's "7–20×"**, also as "7 to 20 times". Smooth interpolation moves the two extreme windows
    6–7× the 2.8% control bound (`interp_scorer_stability.json`). Marker: 6–7×.
  - The decimal figures are guarded against longer numbers: 12.6× is not 2.6×, and 12.1× is not 2.1×.
- **They found stale copies in ten dated reports and one review doc.** Each gains a dated note:
  - **Seven reports of the placement line** took the count's 1.2% as their premise. They gain a head note
    saying what 1.2% was and giving the nine-seed 6.4%:
    - `ink_count_is_more_stable_than_ink_placement.md`;
    - `ink_placement_in_volume.md`;
    - `render_confound_is_bounded_and_minor.md`;
    - `consensus_retest_confirmed.md`;
    - `normal_separation_contributes_but_does_not_explain.md`;
    - `the_sanity_check_caught_a_false_positive.md`;
    - `ink_offsets_are_not_coherent.md`.

    `normal_separation` ran on `curbase_s4-s9`, whose count CV is 7.4%, and its note says so.
  - **`outer_winding_noise_floor.md`**, which measured the 0.0421, called the outer windings "two and a
    half times quieter". Its note gives the df=18 CV, the 2.1× and the 10.3% floor, which -11.03% exceeds
    only narrowly.
  - **`gap_fix_outer_windings_still_not_established.md`.** Its 2026-09-02 correction gave the 2.6×. A note
    now gives the floor as 2 × 0.0514 = 10.3%, the 2.1×, and the floor's df=18 interval, 7.8–15.2%, which
    still straddles -11.03%; so UNRESOLVED stands.
  - **`six_unused_seeds_double_the_current_floor.md`** said a null "actually bounds ~12%"; a note says
    that is the design MDE.
  - **Round 106's review doc** quoted README's "bounded at ~12%" and now says what 12% is.
- **Tests:** the four entries; two live phrasings of each, with markup, that must be matched and not
  cleared; and the guards above, that a longer number neither matches nor clears.

## Verified, no change needed

- **"7–20×"** survives only beside its correction (6–7×), in its report and the summary.
- **Every live copy** of the four claims in README, FINDINGS and the summary already carries its
  correction, from #192 and #195.

## Observations for the owner (not changed)

- **"9.5× flatten cost"** has no ledger entry. Its one remaining copy is the September SUBMIT filing, a
  filed record; an entry would need a note in it.
- **`manipulation_effects_survey.json`** still labels the pinned nulls "null, bounds 12%", which is the
  design MDE. JSON is not scanned by the ledger.

## Verification

- **The ledger:** 46 passed. Each of the eleven notes, reverted alone to main's text, fails it.
- **Doc guards.** Every test file that reads a changed document, or globs the reports or docs (11 files,
  excluding the ledger), gives 378 passed and 2 skipped on main and on the branch.
- **Doc audit** (`audit_doc_references.audit()`): the branch gains no entries.
- **The standard suite** with the locked-package overlay, on the first three commits: 2813 passed, 22
  skipped and 1 xfailed, as on main. The ten failures are main's ten environmental ones: nine need villa
  files, one is `gp_winner`. The later commits change documents and the ledger, which is not in the suite;
  the doc guards above cover the suite tests that read documents.
- **Independent review** of the first three commits found one blocking item: the two placement reports
  that said "`total_fg_pixels` to 1.2%" with no note of the nine-seed 6.4%. The pattern did not see
  them. Its should-fix items were:
  - digit guards on the decimal figures;
  - df=18 alone clearing the 2.6×, and "design MDE" alone clearing the bound;
  - more markers for the count, and the reworded and marked-up forms of each claim;
  - this section.

  All are fixed in the fourth commit, with its nits: a ragged wrap, the gap-fix note's interval and
  derivation, and this doc's description of the 2.6×.
