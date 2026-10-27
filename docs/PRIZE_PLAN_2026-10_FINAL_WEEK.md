# October Progress Prize: readiness and final-week plan

Plan updated **2026-10-27 UTC**. The rules, form, links and merge states were
rechecked; the [latest snapshot](../reports/evidence/october_prize_readiness_2026-10-27.json)
supplements the October 23 and 25 records. We have a credible submission now, based on three
merged Villa contributions. Additional merges or research results can improve
it; they are not prerequisites for filing the work already completed.

The deadline is **October 31, 2026 at 11:59 p.m. Pacific** (November 1 at
06:59 UTC). Target filing on **October 29**, leaving time to check the receipt.
Do not mark the package filed or create a submission tag until it is actually
submitted and the receipt is preserved.

## What is ready

| Evidence | Verified status |
| --- | --- |
| Villa #2022: runner instructions | Merged October 11 Pacific; fixes launch and silently dropped overrides. |
| Villa #2044: sequential ink-scoring folds | Merged October 11 Pacific; a real outer strip changes from OOM to completing at 13.8 GB. |
| Villa #2155: pip CUDA dependency group | Merged October 21 Pacific; package-selection evidence is in the PR. |
| October detailed filing | 31 existing number/version checks pass, with no skips after checking fresh sibling repositories. |
| Live upstream claim checker | Passes; the three October merges and their Pacific dates match GitHub. |
| Existing filing URLs | All 19 pre-update links returned HTTP 200. Recheck final text on filing day. |
| Live form | October title and four-part contribution question confirmed; required email/name/team/terms and optional Discord field identified. |

[Concise engineering form answers](PRIZE_FILING_2026-10_FORM_ANSWERS.md) lead with the
three merged fixes. The [longer draft](PRIZE_FILING_2026-10_DRAFT.md) preserves
the benchmark research and its disclosures. Three merges are evidence of
integration, not a guarantee of a particular award or of ongoing usage.

An [optional separate research answer](PRIZE_FILING_2026-10_RESEARCH_FORM_ANSWERS.md)
now focuses on October's ScrollGT releases and the context studies. It gives
Finding 99 its sampled-population and exploratory limits. Keep the engineering
bundle ready independently; a new research experiment is not needed to file it.

The [public-data CPU reproduction](../reports/scrollgt_cpu_reproduction_2026-10-25.md)
has now run. It found and reproduced a 512³ scorer allocation failure; the
merged ScrollGT fix completes that same control at 2.57 GiB peak RSS under
the unchanged budget, with the published row reproduced exactly. Its public
walkthrough records the limit, source hashes and comparison scope.

The official rules favor early releases, actual use, real-data improvements,
useful fixes, actionable analysis and documentation. They explicitly ask for
small bug fixes to be bundled. The October 27 checked source is Villa `39a8cf3a`,
[`scrollprize.org/docs/34_prizes.md`](https://github.com/ScrollPrize/villa/blob/39a8cf3a124bdd5540ee826e1cb30047c8dc8c85/scrollprize.org/docs/34_prizes.md#progress-prizes).
The live form loaded successfully. Direct access to the deployed prizes page
previously returned HTTP 403; this check uses the current repository source.

## Work ranked for the time remaining

| Priority | Work and useful outcome | Finish condition / dependency |
| --- | --- | --- |
| 1 | Freeze and file the engineering bundle based on the three confirmed merges. | Final personal fields and terms, filing-day rechecks, actual submission and saved receipt. Target October 29; deadline October 31 at 11:59 p.m. Pacific. Do not wait for more merges. |
| 2 | Publish the completed CPU reproduction and merged ScrollGT memory fix (#14). The 512³ control exposed a whole-volume EDT allocation failure under a 7 GiB address-space budget. | The bounded-slab fix is merged: 213 fiber checks and CI pass; real label and score comparisons are exact. Keep the scoring definition and published rows unchanged. Preserve both the baseline failure and the successful run, with commands and limits. |
| 3 | Package the optional research submission around the released benchmark and Findings 96–100. | Review the separate form answer; preserve in-sample, context and exploratory disclosures. Finding 100 is complete; retain its failed Scroll-3 prediction and distinguish its two heading rules. |
| 4 | Complete the existing Villa contributions when access permits: #2141, #2258, #2259, then the prepared native-retry and reference-provenance branches. | The integration remains read-only. A maintainer must merge the existing PRs; prepared PR creation returned HTTP 403. All passing checks and pushed branches stay separate from merged credits. Incorporate actual new feedback if it arrives. |
| 5 | Prepare upstream publication of the reviewed Villa seed-heading proposal from Finding 100 when a PR slot and access permit. | [Owner PR #235](https://github.com/jonmarrs/vesuvius-autoresearch/pull/235) and its follow-up review are merged here; no upstream PR is posted. Its `keep` rule matches training's signed CT axis (1.11× and 1.28× coverage on two held-out Scroll-5 cubes). The current-Villa-main re-run reproduces both before/after traces on those two cubes. The `sheet` experiment recovered more (1.20×, 1.43×) but is a different rule. Keep their evidence distinct; recheck current main, the upstream PR cap and the owner's required commentary before posting. Further experiments are optional after the filing is frozen. |

The integration's creation and merge errors are preserved in
[the review record](../reports/evidence/villa_pr_review_2026-10-23.json).
No upstream comments or messages were sent as part of this planning review.
Open or pushed work stays separate from the filing's merged credits.

The [October 26 follow-up review](VILLA_PR_REVIEW_2026-10-26.md) rechecked all
three upstream PRs and fixed a resume-compatibility gap in the prepared
seed-heading proposal. Both patches are pushed to the fork. No new upstream
PR or merge resulted: the PR cap remains full, Vercel requires authorization,
and the merge attempt again returned HTTP 403. These remain pending work,
not additional merged credits for the filing.

## October 27 priorities

The engineering bundle is ready for final personal fields, terms and filing.
The live October form and the three claimed Villa merges were rechecked on
October 27. Keep the October 29 target; the optional research answer and new
loop work do not need to delay it. Nothing has been submitted here.

The most useful remaining research is the **already registered**
[batchgeneratorsv2 confirmation](preregistration/2026-10-25_loop_batchgeneratorsv2.md)
and [replicate-rule test](preregistration/2026-10-26_loop_replicate_rule_window.md).
Read them only after the window ends: the end of the eighth standing cycle,
a promotion, or October 29 at 16:00 PDT (23:00 UTC), whichever comes first.
The six-cycle minimum permits a reading at a closed deadline window; it is
not permission to peek at six or seven cycles before a stopping condition.
Preserve both rotated run logs and the retained candidate checkpoints, add
only allowed code epochs from the loop checkout's reflog, and keep the frozen
predictions and analysis rules. Keep the step-count adjustment secondary.
No confirmation-window measurements were read for this readiness update.

A [new CPU-only follow-up](../reports/loop_incumbent_reference_2026-10-27.md)
found that the unchanged incumbent already records ROC AUC 0.574202 and AP
lift 1.169277. Of the 26 published pre-window batchgeneratorsv2 cycles, 25
have AUC above that saved reference. This resolves a metadata lookup; it is
not a new model evaluation, an unchanged-training control or confirmation
of the exploratory gain. A new GPU run is unnecessary just to recover the
saved numbers. Fresh evaluation would still be needed to check today's
runtime and exact current inputs.

After the registered readout, the useful conditional next experiment is a
small preregistered matched-step comparison, or an unchanged-training control,
if the original data, checkpoint, GPU slot and time are available. The
observational step-count adjustment alone cannot establish the cause. Keep
any new measurements separate from the registered reading and from claims of
cross-scroll improvement. Avoid a new model sweep before the filing freeze.

The remaining upstream engineering priority is landing #2141, #2258 and
#2259 through a maintainer, then using a freed PR slot for the prepared
native-retry or seed-heading fix. The current integration remains read-only;
repeating rejected merge attempts adds no evidence. The seed-heading branch
already includes the resume guard. These are pending contributions, not
additional merged credits. The separate ScrollGT research filing can use
the released benchmark and merged memory fix now.

Villa main has since moved fibers from AFV files to `vc_object_store`
(#2316, `39a8cf3a`). Both prepared seed-heading patches still apply, but the
recorded real CLI re-run is at `322cb0899`. Verify the object-store CLI path
before posting; do not present the older AFV run as a current-main re-run.
This integration check is useful engineering work if the current dependencies
and data are available; it is not a prerequisite for filing the completed work.

### October 27 follow-up

At 14:17 UTC the October form still accepted responses and the upstream claim
checker still found exactly the three merged Villa contributions above. The
engineering answer remains ready for personal details, terms and submission.
The separate research answer can use the released ScrollGT benchmark and merged
memory fix; it does not need a new loop result. Keep the October 29 filing target.

The newest SQLite review fixed a symlink case in
[Villa #2141](https://github.com/ScrollPrize/villa/pull/2141): checking for a WAL
beside the alias could silently omit committed rows beside the target. The
pushed fix resolves the target before checking its WAL; all six local SQLite
tests and available GitHub Actions pass. The PR is still open and requires a
maintainer to merge it. It adds no merged credit to the filing.

[Research PR #252](https://github.com/jonmarrs/vesuvius-autoresearch/pull/252)
uses only published pre-window cycles and the source host's archived CPU load
table. Measured load explains 60% of the within-tweak step variation. This
supports a useful diagnostic, but the exclusion assumption remains unverified;
it does not establish that fewer steps cause better ranking. Its review fixes
runner-timezone dependence, JSON hash/parse consistency and the supplemental
eight-cycle cutoff. The registered confirmation analysis stays unchanged.
Preserve the source host's sysstat files along with the rotated run logs before
they expire. Their absence in this cloud checkout prevents a fresh raw-log
reproduction here; no confirmation-window measurements were read.

The PR's 14:21 UTC update reports that the eighth standing cycle finished on
October 27 at 05:19:55 PDT (12:19:55 UTC), and that the source host copied its
sysstat files through that cycle. This is a reported stopping condition, not
a reading of its measurements. The registered readout can now proceed on that
host, with the eighth cycle's end as the input cutoff and the frozen rules.

The object-store check confirms that current Villa imports `vc_object_store`
while loading the volume tracer, and its export flags are now `--fibers-template`
and `--no-fibers`. The cached environment lacks that native module. Run the
current-main CLI and real-data export in a configured environment before
posting the seed-heading proposal. Do not change the pinned historical AFV
launcher, which reproduces the older measurements.

## Completed research and October 25 review

The [octant tracing registration](preregistration/2026-10-23_tracing_context.md)
was withdrawn by the owner on October 24, never run. Finding 95 remains a
rescore of cropped whole-cube predictions, not independent octant tracing.
The replacement studies are already complete:

- [Finding 96](../reports/neural_tracer_boundary.md) identifies the neural
  tracer's boundary-related seed loss.
- [Finding 97](../reports/neural_tracer_ct_context.md) supplies real CT around
  all ten 256³ cubes; [Finding 98](../reports/neural_tracer_ct_context_512.md)
  does the same for all eleven 512³ cubes. Neural-tracer coverage increases
  on all 21, by 1.76–2.78× and 1.19–1.35× respectively.
- These runs keep the original presence inside the cube and zeros outside.
  Our tracer's comparator rows remain unpadded. They do not establish a
  matched-context comparison between both tracers or a new mask-model result.
  The detailed filing includes these results and cites ScrollGT v0.9.0.
- [Finding 99](../reports/neural_tracer_heading_residual.md) classifies every
  small-cube dot and samples the large-cube dots. The remaining classified
  failures are CT-axis disagreements and correlate with sheet tilt. This is
  an exploratory diagnosis, not a measured improvement to a new tracer.
- [Finding 100](../reports/neural_tracer_steep_heading.md) has now tested both
  heading arms on all 21 cubes in a registered GPU run. The `sheet` arm adds
  1.20–1.43× coverage on the two held-out Scroll-5 cubes; Scroll 3's median
  1.017× misses the registered 1.05×. Four of five predictions held. This does
  not establish tilt as the cause. The detailed filing includes the failed P2
  in its tally of 23 failed registered predictions.

The October 25 PR review found no further defects in the three existing Villa
PRs or the two prepared branches. Their heads remain unchanged. Available
GitHub Actions runs on #2141, #2258 and #2259 pass; Vercel still requires team
authorization. Local verification passed 20 fractional-seeding cases, five
SQLite cases, 13 native-retry cases and 86 supporting evidence checks. The
published AppImage's extracted `AppRun vc_render_tifxyz --help` also exited 0.
These checks are verification, not additional research results.

Villa still reports read-only permissions. A fresh native-retry PR creation
attempt returned HTTP 403, “Resource not accessible by integration”. No new
upstream PR was created, neither prepared branch has been merged, and the
three existing PRs still need a maintainer to merge them. The earlier error
record remains unchanged; this paragraph records the follow-up check.

## Suggested sequence

- **October 23–24:** finish the filing evidence checks and concise narrative;
  keep the existing PRs ready for maintainer review. Prepare the native retry
  handoff and the benchmark reproduction example.
- **October 25–27:** publish the completed CPU reproduction and review Findings
  96–100 against the updated filing. The seed-heading proposal and current-main
  re-run are also complete in this repository. Keep the withdrawn octant tracing study
  withdrawn. Complete the prepared upstream contributions when publication
  and merge access become available.
- **October 28:** freeze the submission narrative and public evidence links.
  Review each claim against its source; make pending/merged status explicit.
- **October 29:** recheck the current rules and form, complete personal fields
  and terms, submit, then save the receipt and exact submitted answers.
- **October 30–31:** reserve for receipt issues and material updates. A new
  merge can be included if the form's update mechanism permits it; first
  check whether the receipt supplies an edit link.

Avoid a broad architecture rewrite or a last-week model sweep: neither has
a demonstrated path to a useful community result within this schedule.
Additional test counts and internal refactors are verification, not separate
claims of improved reading. A separate research filing is warranted only if
the result has its own clear contribution and evidence; the small-fix bundle
is ready to proceed independently.

## Original October 23 checks

The [dated readiness record](../reports/evidence/october_prize_readiness_2026-10-23.json)
preserves live merge timestamps, rules/form fingerprints, the public form's
required questions, sibling repository revisions and all HTTP link results.
The concise contribution answer is 371 words. The October 23 detailed draft
included Finding 95 with a new numeric binding test; subsequent updates add
Findings 96–98. The concise answer stays focused on the three merged fixes.

```sh
VILLA_REVIEW_ROOT=/workspace/villa-native-retry AGENTS_AGENT_MODE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
/workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 \
  /workspace/villa-review-evidence/run_python.py -m pytest -q \
  tests/test_filing_2026_10_numbers.py \
  tests/test_october_prize_form_answers.py \
  tests/test_check_filing_upstream_claims.py tests/test_octant_crop_report.py
# 59 passed in 0.55s

python3 scripts/check_filing_upstream_claims.py --month 2026-10 \
  --filing docs/PRIZE_FILING_2026-10_DRAFT.md
python3 scripts/check_filing_upstream_claims.py --month 2026-10 \
  --filing docs/PRIZE_FILING_2026-10_FORM_ANSWERS.md
# Both: PASS: every upstream claim in the filing matches GitHub.

VILLA_REVIEW_ROOT=/workspace/villa-native-retry AGENTS_AGENT_MODE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
/workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 \
  /workspace/villa-review-evidence/run_python.py scripts/smoke_test.py
# 8/11 passed, 3 skipped, 0 failed in 6.7s
```

The smoke skips need absent training data or the unavailable bg2 augmentation
entry point. No packages were installed. Fresh sparse checkouts supplied the
tools' actual version files and ScrollGT's tagged metadata, so the filing's
four previously skipped sibling checks now run. This does not constitute a
fresh run of the complete benchmark or its GPU entrants.
