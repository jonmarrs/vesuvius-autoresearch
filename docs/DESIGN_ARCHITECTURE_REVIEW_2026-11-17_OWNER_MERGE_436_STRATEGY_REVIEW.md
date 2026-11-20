# Design and architecture review — the owner's #436, the November 16 strategy review

Date: 2026-11-17. Baseline: `9ac273d` (main after round #179's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 02:12 UTC firing on 2026-11-17. Main had not moved.

It takes **#436**, merged at 04:10 UTC on 11-16. #436 adds `docs/STRATEGY_REVIEW_2026-11-16.md`, a dated
discussion document that recommends regional reading before more infrastructure. It also adds a five-line pointer
to it in `docs/RESEARCH_STRATEGY.md`. #436 changes no code, configuration or registration.

This round checked the review's claims about this repository against their sources. The review is the owner's
dated record, so it is left as it is.

The round first looked at **#437**, the proofreader session binding. 30 of its 40 tests fail in this container
because they need the villa proofreader, so a mutant sample would show nothing here. #437 is left for a
container with a villa checkout.

## What changed

Nothing but this record. The review's repository claims all hold, as listed below.

## Verified, no change needed

- **The evidence table cites its sources correctly.**
  - "99.95% identical pixels" is the PHerc. 343 reproduction report's headline.
  - The mesh stage's "about 3 h 31 min, 12.7 GB GPU, 10.8 GB process RSS and 17.1 GB unit memory" is finding
    110's record:
    - 12,676 s across the steps and the selection;
    - a GPU peak of 12,701 MiB;
    - 10,772,508 kB maximum RSS;
    - 17,084,878,848 bytes of sampled cgroup memory.
  - "AUC about 0.72 to 0.75" is finding 111's two held-out segments, 0.7194 and 0.7478.
  - "+23.0% at tolerance 4" on the comparable four cubes is finding 109's report, table and text.
  - The training control's "−0.00271 F1 and −0.01022 AUC" is the 10-30 unchanged-control readout, Q1 and Q2.
- **The claims about finding 117 match its record.** The review says 70 tiles, AUC 0.895, all 32 tiles at the line
  right, and a "right" label that needs half of the covered nodes within two voxels. It says the snapped surfaces
  have no wrong tiles: 122 right and 0 wrong. It says none of the wrong tiles lies on a neighbouring sheet. Each of
  the 17 wrong tiles has 34% to 71% of its covered nodes within 4 voxels of the published winding, so none lies
  wholly on another sheet.
- **The 496-jobs question is the one the review of #401 recorded on 11-13.** The review cites it, and it is still
  open.
- **The pointer in `docs/RESEARCH_STRATEGY.md` adds and changes nothing else.** It says the review adopts no new
  experiment and keeps the November 10 decision record.

## Observations for the owner (not changed)

- **Parts of the review have been overtaken since it was written.** The review was merged at 04:10 UTC on 11-16.
  - It describes #434 and #435 as open. Both were merged within two hours.
  - It says the tile gate's scorer questions were unresolved. Round #177 has since recomputed finding 117 and tested
    the scorer's table, floor and tile rules: 37 of 38 mutants are now killed, and the last is equivalent. What it
    left open is the review's own point: the gate was measured on a fit that turns the published way, with no
    wrong tile on a neighbouring sheet.
  - Its recommended positive control on PHerc. 211 has since been run for the recipe's readers, as finding 118
    (`READER_AGREES`, round #179). The comparison with newer readers it recommends has not been run.
  A dated line in the strategy, or in the review, would say which recommendations stand.
- **The review's claims about outside sources were not checked.** These are the prize pages, the announcement,
  the winners page, and the licences and sizes of other repositories. This container has no general web access
  for them.

## Verification

- **Ruff and mypy.** No code changed. Round #179's run is clean on the same tree.
- **The standard suite and the modules outside it.** Main's tree is round #179's validated head, `0645c0e`, merged.
  This branch adds only this record. Round #179's figures stand: the same 234 and 23 failing ids as round #178's
  run, all for want of a villa checkout.
- **The doc audit**, run alone, lists the same unresolved references as on `9ac273d`.

## A note on this round's work

- **This was a document review.** No mutants were run, because #436 has no code.
- **Still not reviewed:** #437 (needs villa), #433, #422, #424 and #428, the rest of #390, #396 and #411, and the
  parts of #421 and #423 that rounds #170 and #171 listed.
