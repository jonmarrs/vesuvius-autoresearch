# Design and architecture review — the corrections of #192 and #195 enter the withdrawn ledger

Date: 2026-10-23. Baseline: `1862350c` (main after #195).
Reviewer: Claude (Anthropic), at the owner's request.

#192 and #195 corrected figures in the summary, README and FINDINGS that later reports had already
corrected. Those corrections are bound where they were made. Nothing kept the claims from coming back
elsewhere, or from surviving in the dated reports that first made them. The withdrawn-claims ledger
(`tests/test_withdrawn_claims_stay_withdrawn.py`) is the repo's mechanism for that.

Main has not moved since #195. There are no open pull requests. This round covers the 08:13 UTC firing.

## What changed

- **Four ledger entries.** Each names the correction a paragraph quoting the claim must carry:
  - **The count "reproducing to 1.2%".** 1.2% is the CV of `curbase_s1-s3` (0.0124): three seeds, since
    found unusually tight. Across all nine seeds of that configuration it is 6.4%
    (`control_sensitivity.md`). Marker: 6.4%.
  - **The inner floor "2.6× too wide"** for the outer windings. That was the n=4 outer CV. Pooled over the
    pinned tier's 24 outer fits at df=18, it is about 2.1× (`noise_floor_by_tier.md`). Marker: 2.1× or
    df=18.
  - **Nulls "bounded at ~12%".** ~12% is the pinned tier's design MDE, not what the data rule out. Marker:
    "design MDE".
  - **Finding 70's "7–20×".** Smooth interpolation moves the two extreme windows 6–7× the 2.8% control
    bound (`interp_scorer_stability.json`). Marker: 6–7×.
- **They found stale copies in seven dated reports.** Each gains a dated note:
  - **Five reports of the placement line** took the count's 1.2% as their premise. They gain a head note
    saying what 1.2% was and giving the nine-seed 6.4%:
    - `ink_count_is_more_stable_than_ink_placement.md`;
    - `ink_placement_in_volume.md`;
    - `render_confound_is_bounded_and_minor.md`;
    - `consensus_retest_confirmed.md`;
    - `normal_separation_contributes_but_does_not_explain.md`.

    The last ran on `curbase_s4-s9`, whose count CV is 7.4%, and its note says so.
  - **`gap_fix_outer_windings_still_not_established.md`.** Its 2026-09-02 correction gave the 2.6×; a
    note now gives the df=18 figures.
  - **`six_unused_seeds_double_the_current_floor.md`** said a null "actually bounds ~12%"; a note says
    that is the design MDE.
- **Tests:** the four entries, and one live phrasing of each that must be matched and not cleared. Each of
  the seven notes fails the ledger when reverted to main's text.

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

- Pending.
