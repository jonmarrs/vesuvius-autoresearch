# October Progress Prize: readiness and final-week plan

## October 28 readiness decision

The engineering entry is ready for final owner fields and filing. The
[October 28 audit](../reports/evidence/october_prize_readiness_2026-10-28.json)
rechecks the three merged Villa contributions (#2022, #2044 and #2155), the
current rules, release identity and filing links. The October form accepts
responses. Submit on **October 29** if possible; the deadline remains
**October 31, 2026 at 11:59 p.m. Pacific**. Nothing has been submitted.

Both prepared answers are frozen and unchanged: 371 words for engineering
and 554 for the optional separate research entry. A refreshed copy-ready
candidate, `october-progress-prize-candidate-2026-10-28_134941-PDT.zip`,
preserves those answers and adds dated checks and optional research links.
Its SHA-256 and payload identity are recorded in the audit. Historical HTTP
checks remain distinct from today's GitHub connector retrieval checks.
The filing suites pass all 91 tests; CPU smoke passes eight checks with
three expected skips. This is a readiness check, not a new research result.

The useful work for the remaining days is bounded:

| Priority | Work | Finish condition |
| --- | --- | --- |
| 1 | File the completed engineering entry; choose whether to file the separate research entry. | Owner completes personal fields and terms, checks the form on filing day, submits, and preserves each receipt and the exact submitted text. |
| 2 | Keep Villa #2141, #2258 and #2259 ready for maintainer review. | All three remain open; #2141's latest feedback is addressed. Count no additional merge credit until a merge occurs. The three-PR cap is full. |
| 3 | Use completed ScrollGT work as optional research support. | v0.9.1, the exact 21-target/315-field CPU reproduction and the public annotation audit are published. They verify usability and provenance, not a new model-quality improvement. |
| 4 | Verify current-main object-store/tracer integration when its native environment and a free GPU are available. | Use correctly identified public CT. Existing local-crop runs cannot be relabeled with `--ct`. This is not a filing dependency. |
| 5 | Prepare a small hard-region label packet using the existing crop tools, if expert review is available. | Start with 12 crops across two scans and preserve review/provenance; generated hints are not ground truth. A new model claim needs separate confirmation. |

The registered unchanged-training comparison remains undisturbed: no live
measurements were read, no GPU jobs were started and no runtime was deployed.
Do not launch a competing sweep or wait for that window to file. The earlier
dated notes below preserve the progression of this plan; this October 28
decision is the current filing status.

## Earlier October 27 checks

Plan updated **2026-10-27 Pacific (2026-10-28 UTC)**. The rules, form, links and merge states were
rechecked; the [latest follow-up](../reports/evidence/october_prize_readiness_2026-10-27_followup.json)
supplements the [earlier October 27 snapshot](../reports/evidence/october_prize_readiness_2026-10-27.json)
and the October 23 and 25 records. We have a credible submission now, based on three
merged Villa contributions. Additional merges or research results can improve
it; they are not prerequisites for filing the work already completed.

**Latest October 27 follow-up:** [PR #264](https://github.com/jonmarrs/vesuvius-autoresearch/pull/264)
registers the old augmentation recipe against unchanged training from the
promoted checkpoint. It waits for #263's recorded identities and starts no
earlier than October 27 at 16:00 PDT. Use its `status` command for counts only
until the window closes. Ten cycles per arm are the target, at least six each
are required, and the window can end early or run beyond the prize deadline.
Do not delay either prepared filing for this study. Once its window opens,
another pull into the research checkout ends it; analyze from a separate
checkout. The review below fixes the reader without deploying or reading live
study measurements.

The control-evidence review freezes all comparisons at the registered stop,
checks complete validation and code/config identities, and removes dependence
on the analysis host's timezone. The separate repeatability probe now requires
a recorded complete warm start, at least one applied update and distinct
training sampling seeds. New probe reports use contract 2 and retain step,
skipped-update and warm-start diagnostics; archived contract-1 reports and
registrations are unchanged. These are measurement safeguards, not new quality
results. The three Villa merges and accepting October form were rechecked.
The integrated control, loop, historical-readout and filing suites passed
284 checks with three raw-source skips. After the final source-file guard and
immutable-checkpoint test review, both changed suites passed all 100 checks.
Ruff and targeted mypy pass on the four changed Python files; the full
repository suite was not rerun. No new GPU training or deployment was performed.

The deadline is **October 31, 2026 at 11:59 p.m. Pacific** (November 1 at
06:59 UTC). Target filing on **October 29**, leaving time to check the receipt.
Do not mark the package filed or create a submission tag until it is actually
submitted and the receipt is preserved.

The current repository includes [PR #262](https://github.com/jonmarrs/vesuvius-autoresearch/pull/262),
which publishes the owner's promoted batchgeneratorsv2 checkpoint, F1 0.271004,
and fixes historical-reference reproduction after an incumbent changes. Its
saved metrics and recorded validation identity were checked on CPU; that is
not a fresh evaluation or a comparison against unchanged training. The three
Villa merge credits in the engineering answer remain the same.

The latest engineering follow-up strengthens
[cycle provenance](LOOP_CYCLE_PROVENANCE.md) before future control comparisons.
It records the baseline and trial settings, fingerprints Git-visible code
contents, and prevents the live replicate rule from pooling different
baselines or unidentified code. Older journal rows stay preserved but cannot
fill the new evidence pool without these identities. Deployment on the
research host is still a separate step; no new GPU experiment was run here.
The filing checks still pass and the October form is accepting responses.
Keep the October 28 narrative freeze and October 29 filing target.

A [read-only probe plan](../reports/evidence/unchanged_training_probe_plan_2026-10-27.json)
prepares four unchanged-config repeats from the promoted checkpoint using
the existing isolated `f1_noise_probe.py` runner. Its training budget is
four times 900 seconds, or 60 minutes, plus validation and startup. This is
an operational preview from the cloud checkout: it does not establish data,
GPU or checkpoint compatibility and has launched no training. Regenerate it
on the research host before execution:

```sh
uv run python scripts/f1_noise_probe.py --config config.json \
  --checkpoint best_model.pt --runs 4 \
  --out local_data/unchanged_training_control_2026-10-28
```

The command plans only; `--execute` runs the repeats in isolated directories
and requires the research lock and GPU slot to be free. It measures descriptive
spread from unchanged settings, with actual warm starts checked by the runner.
Register any confirmatory comparison and stopping rule before collecting
its results. This bounded probe is more predictable to schedule than waiting
for enough adaptively sampled control cycles. It can proceed separately from
filing the completed engineering and fiber research work.
If the registered #264 window has opened, defer this isolated probe until it
closes. Pausing that window or pulling new runtime code would compromise its
intended uninterrupted conditions.

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
The [October 27 research-claim audit](../reports/evidence/october_research_claim_review_2026-10-27.json)
also checks the ranking, precision and corrected report citation before the
October 28 narrative freeze.

The [public-data CPU reproduction](../reports/scrollgt_cpu_reproduction_2026-10-25.md)
has now run. It found and reproduced a 512³ scorer allocation failure; the
merged ScrollGT fix completes that same control at 2.57 GiB peak RSS under
the unchanged budget, with the published row reproduced exactly. Its public
walkthrough records the limit, source hashes and comparison scope.

The [whole-corpus follow-up](../reports/scrollgt_corpus_reproduction_2026-10-27.md)
now reproduces the connected-components row on all 21 released targets: all
315 published field values match exactly, with every CLI process under the
same 7 GiB address-space limit. Peak RSS is about 0.57 GiB for the ten 256³
cubes and 2.55–2.57 GiB for the eleven 512³ cubes. The frozen harness, per-case
measurements and all 21 raw scorecards and logs are published with the report.
This verifies the patched scorer's usability and rounded numerical results;
it does not recompute the other floors or measure a new model-quality gain.
The prepared form answers and submission candidate remain unchanged. The
October form and three claimed Villa merges still pass their live checks.

[ScrollGT v0.9.1](https://github.com/jonmarrs/scrollgt/tree/v0.9.1) now gives
the merged memory fix a versioned source tag. The [release record](../reports/evidence/scrollgt_release_0.9.1_2026-10-27.json)
captures the reviewed commit, tag identity, package-build checks and five
passing CI jobs on Python 3.10–3.14. The default local suite passes 511 tests
with the ten opt-in heavy cases deselected. The installed wheel reproduces
a real target's 15-field row, and its source distribution retains all 63
fiber target files unchanged. This packages existing measured work; it is
not a new quality result or extra Villa merge credit. The prepared answers
and copy-ready candidate remain valid and unchanged. Keep the October 28
freeze and October 29 filing target; nothing has been submitted.

The [October 27 publication audit](https://github.com/jonmarrs/scrollgt/pull/16)
also corrects stale benchmark instructions: the legacy model's 0.518 AUC is
separate from the constant floor's 0.500, the old 0.60 contributor threshold
is retired, fiber target assets total 38.79 MB, and the README now cites the
measured 0.9.1 memory use and states which prediction inputs are needed.
The constant floor was recomputed on the shipped 4096×4096 ink target: AP lift
1.000 and F1 0.311230. More directly relevant to the fiber filing, all 21
recorded upstream NML annotations were freshly fetched: every hash matches,
and both the existing verification CLI and an independent XML parser reproduce
all nine skeleton arrays per target. The [public audit](https://github.com/jonmarrs/scrollgt/blob/24b2da4ca4e8e6771d80998e1555cdc3f3f3a791/docs/GUIDANCE_AUDIT_2026-10-27.md)
preserves all 189 array comparisons, source/input hashes and raw harness/logs.
This verifies annotation identity and packaging, not physical accuracy in CT
or model quality. Target data, scoring behavior and version tags are unchanged.
The prepared form answers and submission candidate remain unchanged; no new
merged Villa credit or live-study result is claimed.

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
| 5 | Prepare upstream publication of the reviewed Villa seed-heading proposal from Finding 100 when a PR slot and access permit. | [Owner PR #235](https://github.com/jonmarrs/vesuvius-autoresearch/pull/235) and its follow-up review are merged here; no upstream PR is posted. Its `keep` rule matches training's signed CT axis (1.11× and 1.28× coverage on two held-out Scroll-5 cubes). The recorded AFV re-run at `322cb0899` reproduces both before/after traces; the newer object-store CLI remains unverified here. The `sheet` experiment recovered more (1.20×, 1.43×) but is a different rule. Keep their evidence distinct; recheck current main, the upstream PR cap and the owner's required commentary before posting. Further experiments are optional after the filing is frozen. |

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

The [batchgeneratorsv2 confirmation](preregistration/2026-10-25_loop_batchgeneratorsv2.md)
and [replicate-rule test](preregistration/2026-10-26_loop_replicate_rule_window.md)
have closed and their readout is published below. The registered command gave
no reading; the owner accepted the disclosed post hoc audit. Preserve the
original records and that distinction. These completed analyses no longer
need to hold up the filing.

A [new CPU-only follow-up](../reports/loop_incumbent_reference_2026-10-27.md)
found that the unchanged incumbent already records ROC AUC 0.574202 and AP
lift 1.169277. Of the 26 published pre-window batchgeneratorsv2 cycles, 25
have AUC above that saved reference. This resolves a metadata lookup; it is
not a new model evaluation, an unchanged-training control or confirmation
of the exploratory gain. A new GPU run is unnecessary just to recover the
saved numbers. Fresh evaluation would still be needed to check today's
runtime and exact current inputs.

The useful conditional next experiment is an unchanged-training control or a
small preregistered matched-step comparison,
if the original data, checkpoint, GPU slot and time are available. The
observational step-count adjustment alone cannot establish the cause. Keep
any new measurements separate from the registered reading and from claims of
cross-scroll improvement. Avoid a new model sweep before the filing freeze.

### Latest review and next measurements

The combined rollover/form checker now passes, including the historical PR
lookup that failed earlier. The October form returns HTTP 200, its exact
October title and an accepting response form. November's form remains closed
and Villa #2301 remains open. All **12 URLs** in the two prepared form-answer
files return HTTP 200. The upstream claim checker still confirms exactly
Villa #2022, #2044 and #2155 as October merges. The latest follow-up snapshot
preserves these checks separately from the earlier snapshots. Nothing has
been submitted; complete personal details and terms, submit on October 29
if possible, then preserve the receipt and exact answers.

[PR #259](https://github.com/jonmarrs/vesuvius-autoresearch/pull/259) adds an
unchanged-training control to the sampler. Review reproduced a retry fallback
that could run the control every cycle. Controls are now excluded while their
config is among the previous 20 cycles; that history survives retry exhaustion
and also stays bounded in memory. Its 22-cycle regression runs controls at
cycles 1 and 22. A control keeps the normal cycle budget and unpinned runtime
settings, and does not guarantee a daily sample count.

[PR #260](https://github.com/jonmarrs/vesuvius-autoresearch/pull/260) corrects
the exactly-eight-cycle cutoff and offers header-based joins after the readout.
Review also found balanced score collisions could still select the wrong run:
the header mode now verifies every cycle identity and refuses missing or
ambiguous matches. Fully headless logs keep the legacy join. Registered mode
requires the original score join and cannot label a header join as registered.
Original numerical artifacts and registrations are unchanged. Raw source-host
logs, sysstat and the retained candidate are absent here, so their six checks
skip; the analysis checks that use published artifacts and synthetic cases pass.
The integrated review passes **337 checks**, with those six skips, across
19 suites including both PRs, promotion/lifecycle checks and the October filing
checks. Ruff passes on all 12 changed Python files; targeted mypy passes too.
The full repository suite was not rerun on these final review commits.

The most useful new research measurement is whether a tweak beats unchanged
training from the **same checkpoint and inputs**, now that the sampler supports
that control. For a confirmatory claim, register the comparison, endpoints and
stopping rule before collecting its results. A matched-step augmentation pair
would separately address the time-budget confound. Both need a configured
research host and preserved inputs; neither is a result of this CPU review.
No live-host deployment, model promotion or new GPU experiment was performed
here. File the completed work independently of those optional measurements.

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

The [finished-tile object-store replay check](VILLA_OBJECT_STORE_EXPORT_CHECK.md)
now prepares export verification on that configured host without a new GPU
run. It plans by default and, with `--execute`, copies a closed run, invokes
the current export CLI twice and checks exact native coordinates, stable
identities, links and volume metadata through the native reader. Fixture tests
verify failure detection; no native export or current-main tracer inference
was run here. Complete the real-data replay and current-main before/after
tracer comparison before posting the seed-heading proposal. The prepared
filing answers and candidate are unchanged; the October form is still accepting
and the same three Villa merges pass their live claim check.

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

### Published readout and promotion-tool review

[Owner PR #254](https://github.com/jonmarrs/vesuvius-autoresearch/pull/254)
has now published the closed window's
[readout](../reports/loop_confirmation_readout_2026-10-27.md).
The registered command returns **UNMATCHED_RUNS, no reading**: seven of 135
cycles have ambiguous matches when rounded scores recur outside the window.
The post hoc header audit resolves all seven and all four predictions hold
on the corrected rows. Across the eight standing cycles, the audited effects
are +0.00435 F1, +0.0110 AUC and +0.0419 AP lift. Preserve both results and
the disclosure that the audit was written after seeing the effects; do not
describe this as a successful registered confirmation or a cross-scroll gain.

[PR #256](https://github.com/jonmarrs/vesuvius-autoresearch/pull/256) prepares
an explicit manual promotion. Its review fixes checkpoint-byte consistency,
validation-diagnostic checks, log-header preflight and checkout locking.
It also rejects an incumbent, config or validation-input change between the
checks and apply. The tests apply only to temporary synthetic checkouts;
this review neither pauses the source host nor promotes its retained model.
The owner's acceptance, checkpoint choice and decision to adopt the rule are
now recorded in [Amendment 2 / PR #257](https://github.com/jonmarrs/vesuvius-autoresearch/pull/257).
The result stays post hoc and the original UNMATCHED_RUNS record is preserved.

[PR #258](https://github.com/jonmarrs/vesuvius-autoresearch/pull/258) adds the
rule beside the single-cycle margin, with the registered scoring function and
thresholds unchanged. Its review preserves #256's guards and binds journal
observations to the starting checkpoint's SHA-256, budget, validation protocol,
input fingerprint and complete patch counts. Records without that identity
cannot support the rule. A corrupt journal or rejected candidate records a
failed rule decision and leaves the cycle reverted. The checked checkpoint
bytes go through the shared promotion writer, with restoration on write failure.
These are repository changes; this review has not deployed them to the source
host or promoted its model. Pulling into that checkout and its planned manual
promotion remain an explicit operational step. The frozen registered analysis
files are unchanged.

The filing's three merge claims and the live October form were rechecked
again after the readout. They still pass. A historical-rollover lookup in
the combined checker failed at GitHub's PR-diff endpoint; a direct check
of the pinned October form returned HTTP 200, its exact October title and
an accepting response form. Recheck on filing day and preserve the receipt.
Keep the October 29 filing target independently of any promotion decision.

Before month end, prioritize the engineering filing and the separate fiber
research answer already prepared. On the source host, a useful next step is
the reviewed promotion dry run if the owner accepts the audited evidence.
A matched-step augmentation comparison or unchanged-training control could
address the remaining causal question, with a new registration before runs,
if data, GPU time and the filing schedule permit it. Additional sweeps and
the live replicate-rule rollout can wait until after the filing. Existing
Villa PRs still need maintainer access; the new loop result does not change
their pending status or add merged credits.

## Completed research and October 25 review

### October 27 research-answer review

[PR #261](https://github.com/jonmarrs/vesuvius-autoresearch/pull/261) names
merge-penalized ERL wherever the filing says the ranking is unchanged.
Coverage is a different result: the `sheet` arm overtakes our tracer on one
cube at tolerance 2 and four at tolerance 4. The context result, first on
10 of 21 cubes versus eight with cube-only inputs, was independently checked
against all three recorded comparison methods: our tracer, the generator and
connected components.

The precision statement now gives the measured changes, **−0.0171 to +0.0068
at tolerance 2**, on the ten held-out cubes. The failed Scroll-3 prediction
and limits of the two Scroll-5 cubes remain explicit. The form answer's
Finding 100 URL now pins the corrected report at `2fb41b27`; changing the
current report alone would have left the filing linked to its older wording.
The original JSON results and registrations are unchanged.

The filing/report/claim-guard suites pass **134 checks with no skips**.
Ruff and targeted mypy pass on the three changed test files. The ScrollGT
v0.7.0 README was fetched and checked directly for the 126 re-scored rows;
the full repository suite was not rerun for this documentation review.
The engineering answer is unchanged, its three merge claims pass, and the
live October form still accepts responses. Nothing has been submitted.

The newest opportunity scan found existing proposals for the plain-array
patch-coordinate bug ([Villa #2205](https://github.com/ScrollPrize/villa/pull/2205)),
Numba worker oversubscription ([#2311](https://github.com/ScrollPrize/villa/pull/2311))
and legacy fiber import into the object store ([#2321](https://github.com/ScrollPrize/villa/pull/2321)).
All three are open; do not duplicate them as new contributions. Our own
#2141, #2258 and #2259 remain open without new review feedback, and the
integration still lacks merge access. The prepared native-retry and
seed-heading proposals remain the useful next publication candidates when
the existing PR cap and workflow-validation requirements permit them.

Freeze the two prepared answers and their evidence links on October 28.
Recheck the form and upstream status on October 29, complete personal fields
and terms, submit and save the exact text and receipt. Use October 30–31 for
material updates and receipt problems. Optional unchanged-training and
matched-step experiments can proceed on a configured research host without
delaying the completed submissions; this review ran no GPU experiment or
live-host deployment.

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
  96–100 against the updated filing. The seed-heading proposal and its AFV
  re-run at `322cb0899` are complete; the newer object-store CLI still needs
  validation in a configured environment. Keep the withdrawn octant tracing study
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
