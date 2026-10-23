# Design and architecture review — the findings summary's numbers, against their sources

Date: 2026-10-23. Baseline: `87a3ca2b` (main after #191).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `reports/SPIRAL_FINDINGS_SUMMARY.md`, the third document read as current beside the README and
FINDINGS.
- **What earlier rounds did.** #189 and #190 bound the README's and FINDINGS' headline numbers to their
  sources, and corrected what had drifted. #190 recorded that the summary "was not probed number by number".
- **This round** does that for the summary: 91 findings and a floors table.

Main has not moved since #191. There are no open pull requests. This round covers the 23:13, 00:12, 01:12
and 02:12 UTC firings.

## How it was checked

- **A perturbation probe.** Each of the summary's 1,211 numeric tokens was changed by one in its last digit,
  one at a time. The doc tests that read the summary were run on each change (eight files, four scratch
  worktrees).
  - On main, 83 changes were caught.
  - Most of the 83 were finding numbers, or figures already bound for the README.
  - The figures in findings 49–70's own titles were caught for none.
- **Four read-only checkers**, each covering a quarter of the summary, checked every quantitative or
  directional claim against the report or JSON it cites, and against any later correction.
- **The corrections** were then verified against their sources here, one by one, before any edit.
- **An independent review** of the result came next. It found more, and that is fixed too (below).

## What changed

- **The summary carries the corrections its reports made.** It is a live document, so each is corrected
  in place with a dated italic note:
  - **The outer floor.** It was 8.4% at n=4. The pinned tier's 24 fits, all scored on w120–w129 and
    pooled at df=18, give CV 0.0514 and a floor of 10.3%. So the inner floor is about 2.1× too wide, not
    2.6×. This is in the floors table, its prose, finding 14's text and title, and the sentence on what
    n=4 variances got wrong.
  - **The ten-winding duplicate baseline** (0.00%) is the registered inner span w010–w019, not "the span
    all arms are measured on". Finding 7 puts most duplication in the outer strip that later arms are
    scored on.
  - **Finding 1:** +92.47% is 65× the one-draw determinism floor and 30× the 3.04% second draw.
  - **Finding 14:** the arm that "did not clear" was the seven-fit one (13b). At twelve, finding 13
    established the cost.
  - **The sd-multiple correction** was 1.6×, not "nearly twice".
  - **Findings 17, 21 and 26:** ~9.6% and ~12% are the design MDE, not what the data exclude. The data
    exclude [−18.4%, +16.7%] and [−20.7%, +13.1%]; the three pinned nulls' half-widths run from 8.5% to
    17.5%.
  - **Finding 28** (title and body) now carries the control-sensitivity correction FINDINGS already had.
    Against the render-matched controls the null is −5.49% [−14.52%, +3.53%].
  - **Findings 29 and 38:** the count "agrees to 1.2%" on three unusually tight seeds. Across all nine it
    is 6.4%.
  - **Finding 34:** it was set against a render-code figure and a seed CV that were both superseded. It now
    gives 3.04% for a same-code re-render, with the code change's 1.44% inside it. The seed CV is 0.0536
    pooled within groups, 6.4% across the nine `curbase` seeds, and 0.0909 fit-only.
  - **The noise line's closing note and findings 34 and 40** credited the flatten with placement. Re-laid
    out, the same fit agrees on placement at 0.94–0.97 (finding 56), so the flatten's share is the count.
    The closing note also gave only the `curbase` fit-only floor, and now gives the pooled one beside it.
  - **Finding 52:** "9.5× flatten cost" is stage-0 throughput. In wall time the deterministic flatten
    takes 637–679 s against ~4 min, about 2.7×. The same wording is fixed in README, FINDINGS, the
    preregistration template, the report, and a comment and the banner in `run_render.sh`.
  - **Finding 58:** six displaced copies; the seventh offset is the fitted surface.
  - **Finding 68** extends finding 25, not finding 23.
  - **Finding 70:** smooth moves the extreme windows 6–7× the control bound (7–13× each window's own
    largest control), not 7–20×. Its report carried the same ratio and gains a note.
  - **Finding 84:** the 0.289 maximum is over the in-sample Scroll-5 cubes; over all eleven it is 0.296.
- **`tests/test_summary_headline_numbers.py`** (24 tests) recomputes the title figures of findings 49–70
  and every correction above from the committed JSON, or from the report table where no JSON holds it,
  and asserts the summary states each one, rounded once. The floors it compares against are read from
  their reports, not typed in.
- **Two existing bindings moved.** `test_readme_headline_numbers.py` and `test_findings_headline_numbers.py`
  pinned "9.5× flatten cost". They now bind the throughput and the wall-time ratio separately.

## Verified, no change needed

- **The checkers confirmed most of the summary** against its sources: findings 2–13, 15–16, 18–20, 22–25,
  30–31, 33, 35–37, 39, 41–51, 53–57, 59–67, 69, 71–83 and 85, apart from the items above.
- **The 2.6× in the original n=4 measurement** is kept as the record of what was measured, with the df=18
  figure beside it.
- **The September SUBMIT filing** says "9.5× flatten cost". It is a filed record and stays as filed.

## Observations for the owner (not changed)

- **The 2.1× is still soft.** It sets an inner CV at n=4 (df=3) against an outer CV at df=18. Only the
  outer side improved.
- **Finding 32's "highest of all six"** contradicts its own source table. `consensus_forward_verdict.md`
  gives `curbase_s6` 0.726 beside "0.665–0.744" for the others, and no JSON holds the per-arm values to
  settle which is wrong.
- **The mechanism closing note's "six registered tests (findings 38–43)"** may count finding 39, which
  was closed by three probes rather than a registered study. The source calls finding 43 "this sixth
  test", so it was left.
- **The rescoring closing note's ugrep mislabelling** of three sweep arms has no record in `reports/`,
  `docs/` or the git log. It could not be verified.
- **Finding 15** quotes four-seed column figures. A later report gives six-seed figures (0.1877 / 0.1871 /
  0.0075). Both are measurements; the newer ones could replace them.
- **What remains unbound.** The new test binds the titles and the corrections. Most body figures across
  the 91 findings are still bound by nothing, though the checkers found them correct today.

## Verification

- **The probe on the final commit:** 213 of 1,291 one-digit changes are caught, against 83 of 1,211 on
  main. The corrections added 80 numbers. Leaving out the finding numbers themselves, it is 202 of
  1,206 against 76 of 1,126.
- **Doc tests:** the six files that read the live documents give 98 passed.
- **Doc guards.** Every test file that reads a changed document (27 files, excluding the new one) was run
  on main and on the final commit:
  - 613 passed on both;
  - the one failure on both is `test_live_documents_stay_clean`, from villa paths.
- **Doc audit** (`audit_doc_references.audit()`): the branch gains no entries.
- Ruff 0.9.10 `check` and `format` are clean on the three changed test files.
- **The standard suite** with the locked-package overlay: 2811 passed, 22 skipped and 1 xfailed, as on
  main. The ten failures are main's ten environmental ones (nine need villa files, one is `gp_winner`).
  The new test reads only reports, so the suite-coverage guard does not require it in the suite.
- **Independent review** of the first four commits. It found three blocking issues:
  - finding 34's note gave the pooled CV as the nine seeds';
  - findings 17 and 26 still presented the design MDE as the bound;
  - two titles stated corrected figures.

  It also found should-fix items:
  - placement credited to the flatten in two more places;
  - the 9.5× wording in four more documents;
  - broken or undated notes;
  - 11 of 27 mutants surviving.

  All are fixed in the fifth commit. Each surviving mutant's figure is now bound.
