# Design and architecture review — the owner's #227 (October priorities after the context studies)

Date: 2026-10-25. Baseline: `b7fa8c32` (main after the owner's #227).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:13 and 04:12 UTC firings. The 00:12, 01:12 and 02:12 firings found main unmoved after
#226. #227 updates `docs/PRIZE_PLAN_2026-10_FINAL_WEEK.md` after findings 96–98:
- the withdrawn octant study is dropped from the plan;
- the coverage gains of findings 97 and 98 are recorded;
- the October 25 checks of the villa PRs are recorded.

## What changed

- **This series' own record of #226 broke its claim of no audit entries.**
  - `docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-24_OWNER_MERGES_219_220_224_225.md` says the branch adds no doc-audit
    entries.
  - Its last edit, made after that audit ran, cited ScrollGT's context tool as a backticked repository path. That
    added an entry, a path this repository does not have.
  - The citation is now plain text, as a file in another repository, and the claim holds again.

## Verified, no change needed

- **#227's figures** are the findings':
  - coverage up 1.76–2.78× on the 256³ cubes (finding 97) and 1.19–1.35× on the 512³ ones (finding 98);
  - ScrollGT v0.9.0 is the filing's cite;
  - the 371-word answer is bound by the form-answer test.
- **#227's limits match the reports.** Findings 97 and 98 kept the presence unchanged, with zeros outside the cube,
  and compared against our tracer's unpadded rows.
- **Withdrawal:** the plan keeps #219's octant registration withdrawn.

## Observations for the owner (not changed)

- **The plan's local verification counts are not checkable here.** They are 20 fractional-seeding cases, five SQLite
  cases, 13 native-retry cases and 86 evidence checks. So are its villa CI statuses. They describe runs on the owner's
  machine and on villa's CI, and nothing in this repository records them.

## Verification

- **Tests:** the form-answer, filing, withdrawn-claims and doc-audit tests give 97 passed and 4 skipped. The one
  failure is `test_live_documents_stay_clean`, which needs villa paths and model checkpoints absent here, as before.
- **Doc audit:**
  - main after #227 has one entry more than before #226, from #226's own record;
  - with this round's correction, the branch has none beyond #225's own, a ScrollGT path in a dated document.
- **No independent review this round.** The change is one reworded citation.
