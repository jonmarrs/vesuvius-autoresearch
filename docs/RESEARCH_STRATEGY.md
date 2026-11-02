# Research strategy: useful progress on one RTX 4090

**Reviewed October 28, 2026 UTC.** This is the current strategy, replacing the
July plan. [FINDINGS](../FINDINGS.md), published measurements and registrations
remain the record of results. The budgets and gates below are proposals for
new work, not registrations or measured runtimes. No new experiment was run
for this review.

The best-supported route is a useful contribution that others can run in the
existing Vesuvius workflow: finish the pending fixes, improve conservative
fiber tracing, then test a small label-quality intervention. Keep ink-model
exploration bounded until it demonstrates new signal on independent data.
Our September $250 award for useful merged Villa PRs is evidence that this
kind of work can be recognized; it does not establish an award probability
or expected amount ([award record](PROGRESS_PRIZE_AWARDS.md)).

## Current rules and our local experimental contracts

The [official prize rules][prizes], read at Villa commit
`39a8cf3a124bdd5540ee826e1cb30047c8dc8c85`, say:

> Large windows are fine, but you must demonstrate that the text is not
> hallucinated — for example by finding plausible text on held-out regions.

That quotation is from the Grand Prize false-positive requirement; First
Letters makes the same allowance and asks for different, plausible letters
on a held-out region. These rules require no training/prediction overlap,
reproducible inputs and methods, held-out validation and evidence of genuine
letterforms. They do **not** impose our historic 64-pixel / 0.5-mm cap.
The previous strategy wrongly treated that local restriction as current
eligibility policy and used it to dismiss larger-context research.

The detector and submission tools still impose their own conservative window
contracts. Their pass/fail results are local checks, not prize eligibility or
scientific validation. This strategy does not relax those runtime contracts,
change trained models or revise frozen experiments. A larger-window study
needs a separate explicit configuration, evidence contract and untouched
validation regions. Check the current official rules again before filing.

For Progress Prizes, the same official source favors work that is released
early, actually used, improves real-data results, fixes tools people use, or
produces actionable analysis. Small fixes should be bundled. Prizes remain
at the organizers' discretion; adding internal tests or PRs alone does not
establish community impact. The October deadline is October 31 at 11:59 p.m.
Pacific; the existing [filing plan](PRIZE_PLAN_2026-10_FINAL_WEEK.md) targets
October 29 and should not wait for new research.

## Ranked work

| Rank | Direction and concrete next deliverable | Proposed bounded pilot | Continue / stop decision |
| --- | --- | --- | --- |
| 1 | **Finish usable upstream engineering.** Resolve feedback on Villa [#2141][wal], [#2258][grid] and [#2259][headless], then complete the current object-store replay for the prepared seed-heading change. Publish one reproducible before/after workflow and a command a user can run. | Two engineer-days; zero GPU for feedback and closed-run export replay. Use an already configured native environment. Allow at most two GPU-hours for the retained two-cube tracer integration check once the GPU is free. These are scheduling ceilings, not runtime estimates. | Require current-main real-data behavior, native export/readback and preserved identities. Fixture tests alone are insufficient. If dependencies, data or upstream access block completion, record that dependency and move to another usable deliverable. Respect the existing three-open-PR / two-code-fixes-per-week limits. |
| 2 | **Conservative fiber tracing that reaches farther without switching fibers.** Finish the existing signed-CT-axis seed proposal, then investigate one failure mode such as premature confidence stops. Keep the two changes separate. Export accepted traces through Villa's native store for actual annotation or fitting use. | After integration, a four-GPU-hour development pilot on a few fixed crops, with stock and one candidate given the same CT halo, presence inputs, seeds and trace budget. Freeze the rule before any new confirmation data. | Measure independent human-click reach or independently reviewed continuity, wrong connections, precision and cost; coverage alone cannot pass. Require no observed increase in wrong connections on the reviewed pilot and at least a 10% useful-continuity gain to justify a larger registered test. Report uncertainty: a small pilot is a screen, not proof of safety. Stop if the gain depends on extra context, a learned reference, or a precision loss. |
| 3 | **Better labels in hard regions, with a measured downstream effect.** Release a small reviewed CT/label correction set for compressed or curved papyrus, using existing annotation formats and tools. Compare the original labels with one conservative correction method. | First inspect 12 bounded crops across two scans, with a two-hour human-review budget and no training. If the physical feature and recto side are identifiable, permit six GPU-hours total for a paired fine-tuning feasibility check from an existing model. | Obtain independent review before treating a CT ridge or model output as truth. Keep unresolved regions ignored. Advance only if correction agreement and held-out topology/continuity improve without new sheet switches; stop if labels cannot be adjudicated or only the correction method's own score improves. An insufficiently trained pilot is inconclusive. |
| 4 | **A small, controlled cross-scroll ink experiment using released models.** Test one training-data or resolution intervention on the current native ink workflow. Use a released checkpoint; do not start collection-scale foundation pretraining. | After the active registered study closes, budget at most 12 GPU-hours total for three paired seeds, stock and one intervention, with matched successful update counts. Profile a short run first and reduce scope or stop if the required schedule cannot fit. | Lock checkpoint choice and all thresholds using development data. Confirm once on disjoint regions of another scroll after checking all upstream training/pseudo-label exposure. Report AP lift, ROC AUC, fixed-rule F1, null controls and readable images together. Teacher agreement or best-epoch selection on the test region does not establish independent reading. Stop if there is no credible signal beyond the unchanged-training spread. |

Ranks 2 and 3 address explicit official requests: reliable fiber connectivity,
more accurate labels and small amounts of carefully chosen annotation
([open problems][problems]; [label generation #193][labels]). Rank 4 addresses
cross-scroll transfer, but the local evidence does not justify treating it as
a likely First Letters win. A whole-scroll Grand Prize pipeline is a potential
team contribution, not a realistic solo promise on the current evidence.

## Evidence that constrains these pilots

- The [seed-heading study](../reports/neural_tracer_steep_heading.md) already
  found 1.11× and 1.28× coverage for the proposed signed-axis rule on two
  Scroll-5 cubes. The stronger `sheet` arm is a different rule; its failed
  Scroll-3 prediction remains a failure. The existing 21-cube corpus has
  already informed development and cannot be recycled as unseen confirmation
  for a new tweak. Keep model-training exposure separate from researcher
  selection exposure.
- [Finding 101](../reports/neural_tracer_confidence_stops.md) (2026-11-01, registered) closes premature confidence
  stops as a coverage lever for villa's neural tracer. Perfect continuation from every confidence stop whose
  hand-traced fiber goes on would add at most a median 8.3% of held-out coverage. 65% of those stops are splits that
  another trace already continues, so continuity is a separate question. Two-thirds of the tracer's interior
  confidence stops lie off the reference, most of them already off it 20 voxels before they stop.
- [Finding 102](../reports/neural_tracer_continuity_ceiling.md) (2026-11-01, registered after finding 101 and
  because of it) keeps that line open as a continuity lever. The same perfect continuation, joining split traces
  where neither merges, would raise held-out ERLpen by up to a median 31%. But it reaches only 6.1% within 20 voxels
  of each stop, and a rule that continued every confidence stop would extend about two off-reference traces for each
  on-reference one. A development pilot needs the owner's GPU decision.
- The [reference audit](../reports/fiber_reference_provenance_2026-10-23.md)
  distinguishes human control points from tracer-generated line points.
  Following a reference generated by the same tracer can favor that tracer;
  separately report click-based and line-based evaluations. The upstream
  [sheet-plane proposal #2265][sheet-plane] likewise reports a line-score gain
  without a resolved human-click gain. Do not duplicate its intervention.
- [ScrollGT's CPU reproduction](../reports/scrollgt_corpus_reproduction_2026-10-27.md)
  verifies the existing scorer on all 21 targets under a 7 GiB address-space
  cap. Extend it when a real user needs an additional contract or baseline;
  another audit of unchanged numbers is not the next scientific result.
- The clean distilled students' held-out Scroll-1 ROC AUC of approximately
  0.731–0.746 is close to the teacher's 0.753, not proof that they outperform it
  ([measurement](../reports/detector/registered_gt_heldout_validation.md)).
  **A constant predictor's ROC AUC is 0.500.** The legacy detector's measured
  0.518 is not an all-positive mathematical floor. Prior strategy text used
  the wrong label. Detection metrics do not establish legible letters, and
  historical registration uncertainty still limits interpretation.

## Where to reuse existing work

The [community catalogue][catalogue], read on October 28, already lists
ScrollFiesta, winding-sync, winding-ruler, spiralcheck, TIFXYZ Doctor, an ink
validation harness and first-letters-survey. Prefer an adapter, a measured
fix or a useful dataset over another general evaluator or rendering wrapper.
The present contribution queue also contains work by other contributors:

- [#2248][fiber-qa] checks fiber geometry; [#2265][sheet-plane] tests a
  sheet-plane penalty. Reuse or evaluate these rather than offering parallel
  implementations.
- [#2294][render-memory] already includes another contributor's render-memory
  patch and asks for real-data validation. Independent reproduction could be
  useful; a competing implementation is not the default next task.
- Plain-Zarr patch coordinates ([#2205][plain-zarr]), loader oversubscription
  ([#2311][loader]) and legacy fiber import ([#2321][import]) already have PRs.
  Recheck their state before starting related work.

These are source observations, not endorsements of unmerged code. The three
owner PRs in rank 1 were still open at this review; no additional merged
credit or maintainer adoption is assumed.

## Resource and release discipline

Use one RTX 4090 with 24 GB VRAM and the project's existing 500 GB storage
budget. Stream bounded crops, cap cache sizes and profile memory before a
larger run. Choose one primary research pilot at a time. During the registered
[unchanged-control window](preregistration/2026-10-27_loop_unchanged_control.md),
use the counts-only status command and separate review checkouts; a pull into
the live checkout ends the window. Defer competing GPU work until it closes.
Outside a registered window, use the documented `./stop.sh` / `./start.sh`
controls and checkout lock rather than the obsolete manual-PID instructions.

A completed pilot should leave a pinned input/model/code manifest, baseline
and candidate commands, both successful and failed cases, time/memory costs,
and output that a Villa or VC3D user can consume. Ask whether it changes a
real user's decision or removes an obstacle. Measured adoption and real
pipeline improvement are the route to stronger future prize submissions.

[prizes]: https://github.com/ScrollPrize/villa/blob/39a8cf3a124bdd5540ee826e1cb30047c8dc8c85/scrollprize.org/docs/34_prizes.md
[problems]: https://github.com/ScrollPrize/villa/blob/39a8cf3a124bdd5540ee826e1cb30047c8dc8c85/scrollprize.org/docs/37_2026_open_problems.md
[catalogue]: https://github.com/ScrollPrize/villa/blob/39a8cf3a124bdd5540ee826e1cb30047c8dc8c85/scrollprize.org/docs/20_community_projects.md
[wal]: https://github.com/ScrollPrize/villa/pull/2141
[grid]: https://github.com/ScrollPrize/villa/pull/2258
[headless]: https://github.com/ScrollPrize/villa/pull/2259
[labels]: https://github.com/ScrollPrize/villa/issues/193
[sheet-plane]: https://github.com/ScrollPrize/villa/pull/2265
[fiber-qa]: https://github.com/ScrollPrize/villa/pull/2248
[render-memory]: https://github.com/ScrollPrize/villa/issues/2294
[plain-zarr]: https://github.com/ScrollPrize/villa/pull/2205
[loader]: https://github.com/ScrollPrize/villa/pull/2311
[import]: https://github.com/ScrollPrize/villa/pull/2321
