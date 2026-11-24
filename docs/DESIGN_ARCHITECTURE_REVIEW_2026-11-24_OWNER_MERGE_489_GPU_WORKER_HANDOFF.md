# Design and architecture review — the owner's #489, the GPU-worker handoff

Date: 2026-11-24. Baseline: `dc49c48` (main after the owner's #549).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 12:12 UTC firing on 2026-11-24. Since round #227's merge, the owner merged #547 and #549. Both
are listed below for later rounds.

It takes **#489**, which changes two documents and no code:
- **`docs/RESEARCH_STRATEGY.md`** gains an operating workflow, dated 2026-11-22. It connects the roadmap, the
  November 16 review and the November filing draft. It also sets how campaign failures go through normal engineering,
  and gives a Villa report checklist for agents.
- **`docs/LAB_NOTEBOOK.md`** gains a dated GPU-worker handoff with the same date. It covers the Monthly Progress Prize
  lanes, the single-GPU campaign gate and a read-only weekly scorecard.

Both are the owner's dated records. This round checks them against the repository and changes neither.

## What changed

Nothing in the code or tests. #489 has no code to test. This record states what was checked and what was found.

## Verified, no change needed

- **Every relative link and anchor in the two documents resolves.** That includes the strategy's link to the
  notebook's new entry and the notebook's links back to three strategy sections. The doc audit does not check
  anchors, so this round checked them with GitHub's heading rule.
- **The prize-history claims match the repository's records.**
  - The September filing lists five merged Villa fixes: #1721, #1722, #1780, #1805 and #1842.
  - The two October receipts record five more: #2022, #2044 and #2155, then #2141 and #2259. Both were received
    before the October deadline.
  - Three of the five are documentation (#2022, #2155 and #2259), as the strategy says.
  - #2044's entry records Scroll 1 scoring completed at 13.8 GB after stock scoring was killed for memory.
  - The award record credits September's $250 to "assorted useful merged villa PRs".
- **The November lane matches the filing draft and the evidence.**
  - Villa #2258 merged on 2026-11-01, with the merge commit the draft links.
  - The seed-placement report gives the third plane moving from z104 to z105, and the seed count from 1,589 to
    1,590, on `s1_00497_01497_03997_256`. At the default 64-voxel spacing, all five seed arrays are byte-identical.
  - The 2026-11-23 open-PR evidence shows #2463, #2465 and #2501 open and unmerged, as the strategy says of
    2026-11-22.
  - The filing draft gives the November deadline as 11:59 p.m. Pacific on 2026-11-30.
- **The seam lane's findings exist.** Findings 106 to 109 are the block-seam, default-zone, cross-block duplicate
  and seam-confirmation reports, each with its registration, and the filing draft cites them.
- **The limits are the existing ones.** Three open Villa PRs and two code-fix PRs a week are the roadmap's and the
  trim draft's limits.

## Observations for the owner (not changed)

- **One claim in the handoff has no record in the repository.** The notebook's seam-lane row says the prior handoff
  records an exact apply check passing on Villa c8f3ba45.
  - The repository's record of that apply check is the trim draft's, which checked it on 2026-11-09 at Villa main
    c3d9da6fe.
  - c8f3ba45 appears only in the 2026-11-23 open-PR evidence, a day after the handoff, as the Villa main used to cite
    #2501's renderer.
  - The handoff itself says the docs change did not repeat the check. If a check at c8f3ba45 was run elsewhere, its
    record is not here.
- **The doc audit does not check anchors.** `scripts/audit_doc_references.py` resolves paths and commits, not
  `#anchor` fragments. #489's two documents link each other by heading text, so renaming a heading would break those
  links silently. All resolve now.

## Verification

- **Ruff and mypy.** Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it. Mypy is clean over
  the whole repository, 1,118 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives 284 failing ids. They are round #227's 282, and 2 cases the owner's #549
  added to `test_proofreader_session.py`. Those two need Villa's pinned proofreader source, as the module's other 59
  do here.
- **The 314 test modules outside the suite** give the same 24 failing ids as round #227's run, with 3,583 passed and
  3 xfailed. One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `dc49c48`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **No file of the owner's is changed.** The checks read the two documents, the filings, the award record, the
  seed-placement report, the trim draft and the open-PR evidence.
- **Not checked here:** the October comparables the strategy names, and the state of Villa PRs and commits after
  2026-11-23. Those rest on the official winners page and on GitHub, which this round did not read.
- **Still not reviewed from the owner's merges since round #182:** #493, #496, #505, #517, #519, #524, #527, #535,
  #541, #543, #545, #547 and #549.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
