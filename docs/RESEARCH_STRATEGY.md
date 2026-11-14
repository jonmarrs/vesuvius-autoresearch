# Research strategy: First Letters and biting fixes on one RTX 4090

**Reviewed November 10, 2026 UTC and accepted by the owner that day.** This replaces the October 28 strategy,
whose first rank (Villa #2141, #2258 and #2259) has merged. [FINDINGS](../FINDINGS.md), published measurements
and registrations remain the record of results. The budgets, dates and gates below are proposals for new work,
not registrations or measured runtimes. The probabilities are judgements, not measurements. No new experiment
was run for this review.

The owner's goal is a Progress Prize every month while working towards a milestone prize. The record below
bounds the first half: bundles of merged fixes earned us \$0, \$0 and \$250 in three months, comparable work by
others earned \$250 to \$1,000, and the \$20,000 awards went to whole unwrapping capabilities shown at scale.
More of the same work reaches neither goal. The one five-figure prize whose published winning method fits this
machine is First Letters. So the main line is a
First Letters campaign on unread scrolls with the public PHerc. 343 recipe, and the monthly submissions are
what running it produces: fixes where Villa's tools break on consumer hardware, a documented workflow, meshes,
and nulls. The measured fiber-generator fixes are landed alongside.

The strongest argument against this ordering is that the chance of letters on any one scroll is low. A
community survey rendered 971 cm² across 21 scrolls and found none, and other contributors already run the same
recipe on eligible scrolls. The campaign ranks first anyway because its kill test is cheap, its by-products are
the kind of work the monthly prize has paid for, and nothing else measured here has a route to more than about
\$1,000.

## Current rules and our local experimental contracts

The [official prize rules][prizes], read at Villa commit
`740f0103b9574e9e88bbb24a8438dbe1d5a1a0c0` (November 9, 2026), say:

> Large windows are fine, but you must demonstrate that the text is not
> hallucinated — for example by finding plausible text on held-out regions.

That quotation is from the Grand Prize false-positive requirement; First
Letters makes the same allowance and asks for different, plausible letters
on a held-out region. These rules require no training/prediction overlap,
reproducible inputs and methods, held-out validation and evidence of genuine
letterforms. They do **not** impose our historic 64-pixel / 0.5-mm cap.
The July plan wrongly treated that local restriction as current
eligibility policy and used it to dismiss larger-context research.

The detector and submission tools still impose their own conservative window
contracts. Their pass/fail results are local checks, not prize eligibility or
scientific validation. This strategy does not relax those runtime contracts,
change trained models or revise frozen experiments. A larger-window study
needs a separate explicit configuration, evidence contract and untouched
validation regions. Check the current official rules again before filing.

First Letters pays \$50,000 per scroll to the first team that shows 10 legible letters within a single 4 cm²
area of an eligible volume, for at most 8 more scrolls, with a deadline of June 25, 2027 at 11:59 p.m. Pacific.
A submission needs the tifxyz mesh with its flattening, one programmatically generated image with a 1 cm scale
bar and annotated rows, a reproducible method, false-positive mitigation and held-out validation. The winner
must open-source code, data, model weights and results under a permissive license after winning. The same
section says:

> As with the Grand Prize, you **must not** make your discovery public until the prize is officially announced.

This repository is public. Renders, predictions and notes that show or locate possible text on an eligible
volume therefore stay out of it, out of Villa issues and PRs, and out of Discord, until the organizers announce
a result or the owner decides to publish a null. Until the owner chooses a private location, they stay on local
disk.

For Progress Prizes, the same source favors work that is released early, actually used, improves real-data
results, fixes bugs in tools people use, or is well documented. Since Villa [#2450][criteria] (merged
November 5) it also says:

> We discourage standalone analytic, auditing or evaluation tools, and instead encourage work that directly
> **advances unwrapping or ink detection**.

and that fixes for issues that are "theoretically wrong but rarely or never cause problems in practice are
unlikely to be awarded". Small fixes should be bundled. Prizes remain at the organizers' sole discretion; a
merged PR is not an award. The November deadline is November 30 at 11:59 p.m. Pacific; the
[November filing draft](PRIZE_FILING_2026-11_DRAFT.md) holds what will be filed.

## What the prize record shows

Read from the [winners page][winners] at the same commit. October's Progress Prizes were not announced at this
review.

| Award | What won it, July to September 2026 |
| --- | --- |
| \$20,000 | A whole unwrapping capability shown at scale: the ScrollFiesta automatic surface mesher (July), patch-based unwrapping with about 365 cm² of PHerc. 1667 (August), automated fiber extraction integrated with VC3D and the spiral fitter (September, Villa #1930). |
| \$2,500 to \$5,000 | Continued work on those pipelines, a 9 µm surface model, the reader-v2 ink model. |
| \$1,000 | One coherent enabling capability or documented study: spiral fitting on consumer GPUs, `fit_spiral` fixes, Zarr 3 read fixes, and an end-to-end First Letters attempt on PHerc. 0826 published with its commands, failures and costs. |
| \$250 to \$500 | A bundle of merged fixes, or one fix that bites: a renderer memory fix (\$500), a shared disk cache (\$250), spiralising PHerc. 0211 (\$250). |

Ours: July \$0, August \$0, September \$250 for merged Villa PRs ([award record](PROGRESS_PRIZE_AWARDS.md)). The
September award shows that this kind of work can be recognized. It does not establish an award probability.

Three further facts set the ranking:

- **The automated fiber generator we are fixing is September's \$20,000 winner.** Fixes to it are fixes to a
  tool VC3D ships, not a new capability.
- **Two First Letters prizes were awarded in October 2026**, for PHerc. 306B and PHerc. 343. The
  [PHerc. 343 repository][recipe] publishes its whole method. The PHerc. 306B method was not read for this
  review.
- **The wishlist is empty.** Villa issues #191, #192 and #193 were closed on November 1. On November 10 no open
  issue carried `help wanted`, `good first issue` or `VC3D`. The [open problems page][problems] is the only
  live list of what the organizers want.

## Ranked work

| Rank | Direction and next deliverable | Bounded first step | Continue / stop decision |
| --- | --- | --- | --- |
| 1 | **A First Letters campaign on unread scrolls with the published PHerc. 343 recipe.** Next deliverable: the first band on an eligible scroll, read as a detection test. | The kill test passed on November 10 for the chain from the published windings to the image: 99.95% of the published image's pixels rebuilt identically, none off by more than 5 of 255 ([report](../reports/first_letters_343_reproduction.md)). The mesh step (distance field, spiral fit, snap, flatten) ran here on November 12: windings fitted on this machine lie on the published sheets (76% and 81% of nodes within 2 voxels) and carry the published ink (r = 0.86 over the letter boxes against controls of 0.17), in about 3.5 hours, 3 h 09 min of it the fit ([report](../reports/first_letters_343_mesh_step.md)). Next, one band of one scroll at a time, with no training on the target. | The stop condition on the mesh step did not fire: it runs here and its windings show the published ink. From here the controls and the kill criterion in [the campaign section](#the-first-letters-campaign) decide. Judged chance of letters on a given scroll: low, a single-digit percentage. Confidence that the by-products are prize-eligible work: high. |
| 2 | **Land the measured fiber fixes in Villa:** the seam trim (findings 106 and 107), cross-block duplicates (108), link splice (105) and seed heading (100 and 103). The aim is unchanged: fibers that reach farther without switching. | No new GPU work. Finding 109, a registered confirmation of both seam changes on ten cubes ScrollGT does not ship, was running at this review and is not reported here. Each Villa PR or issue is posted on the owner's decision, inside the limits of three open PRs and two code-fix PRs a week. | Propose only what held up on held-out cubes, and say where it does nothing: VC3D's default zone is one block, where the trim changes nothing, so the case rests on multi-block zones. Promise no reading gain; no geometry change measured here has produced one. If finding 109 does not confirm, propose only the part it supports. Confidence of a merge: moderate. Of more than \$250 to \$500: low to moderate. |
| 3 | **Fix the defects the campaign hits on a 4-core, 31 GB, one-4090 machine.** Deliverable: each fix as a small Villa PR with before/after logs from the real run, bundled monthly. | CPU only. A fix starts from a failure reproduced here on current Villa main, never from reading code. At most two code-fix PRs a week. | No queue exists in advance: of eight open issues checked as starting candidates on November 10, six already had an open PR that references them (see [reuse](#where-to-reuse-existing-work)). Do not compete with an open patch; validate it on real data if that is what its author asks for. Confidence: moderate, conditional on rank 1 running at all. |
| 4 | **Dense winding inputs for scrolls other than PHerc. Paris 4.** | Parked, with no budget. | Start only if rank 1 shows that these inputs are the binding constraint on a fit. Two attempts argue for caution: a contributor's CT peak count was wrong on a quarter to a third of segments, and our ink-derived constraints were circular. Confidence: low. |

Rank 2 addresses the official request for conservative fiber tracing, and rank 4 the request for automated
prior information for the spiral fit ([open problems][problems]). Rank 1 also serves the larger prize: the
prize page calls the Grand Prize's ink stage the same problem as First Letters and says to start there, and
twelve of the thirteen Grand Prize volumes are also First Letters volumes.

## The First Letters campaign

**Eligible volumes.** `prizeEligibility.json` at the same commit lists 20: PHerc. 0125, 0175A, 0175B, 0191,
0211, 0257, 0268, 0358, 0483A, 0483B, 0490A, 0490B, 0800, 0813, 0826, 0846A, 0846B, 1203, 1218 and 1545. The
Grand Prize list has 13; all but PHerc. 1447 are among the 20.

**The recipe.** The [PHerc. 343 repository][recipe] (commit `e8370f1f`, MIT, read on November 10; steps 2 to 5
run here the same day, at one depth) describes five steps. Villa's spiral chain at commit `0fb38c45` is run on
the band z 9500 to 11000 with the author's own scroll axis, and the windings are snapped onto the m7 surface
prediction and flattened with lasagna. Two adjacent windings are joined into one segment. VC3D `41701aa` renders
66 layers one voxel apart. Four released 9 µm ink models (dense_native, ink_9um seeds 42 and 43, Hecate 9.6 µm),
none trained on that volume, run at every depth from −15 to +15. The image is the mean of the four models'
z-scores. It asks for Linux and one 24 GB NVIDIA GPU.

**What we already have.** A converged `fit_spiral` run and a lasagna render path on Scroll 1
([`repro/spiral_render/`](../repro/spiral_render/README.md)). Nothing on an eligible volume.

**What is published for other scrolls.** The community's eligible-spiral-dataset reports tracks for 9 of the 13
Grand Prize scrolls and an umbilicus for 3. At our September 7 read the umbilicus was published for PHerc.
0125, 0211 and 0826, and the dense winding inputs (`winding_inference/`, `outer_shell/`) for PHerc. Paris 4
only. Recheck both before choosing a scroll.

**Evidence against.**

- The first-letters-survey grew 65 patches (971 cm²) on the 21 First Letters scrolls that had no catalogue
  segments and found no letters. Its own calibration on PHerc. 0841, a scroll the models never saw, showed ink
  only at blob level on the team's surfaces, and its automatically grown patches left the text-bearing sheet.
  The catalogue's summary is that a null from that pipeline says little. It does say that released models may
  show less than letters even on a correct surface of an unseen scroll.
- The spiral-winding-audit found that the recipe's snap step stacked 15 to 17% of consecutive windings onto one
  surface on PHerc. 0175A and 0800 fits, against 1.7% on the awarded PHerc. 343 pair. A band can therefore
  render the same papyrus twice and look like a result.
- We are not first on these scrolls. The catalogue and winners page show recipe fits on PHerc. 0175A and 0800,
  an end-to-end attempt on PHerc. 0826 and a spiral fit of PHerc. 0211.
- The PHerc. 343 author reports rented RTX 4090/5090 machines and a local RTX 3090. The render and the ink models
  fit this host (8 minutes, and 17 minutes for the eight jobs of one depth, at a peak of 3,174 MiB of GPU
  memory). Whether the spiral fit and the flattening fit its 4 cores and 31 GB of RAM is unmeasured.

**Controls, fixed before any eligible-scroll result is read.**

1. The PHerc. 343 image reproduced here (the kill test). Passed on November 10 from the published windings
   onward ([report](../reports/first_letters_343_reproduction.md)), and on November 12 for the mesh step
   ([report](../reports/first_letters_343_mesh_step.md), finding 110).
2. PHerc. 0841 as a hard positive control: record what the recipe shows where text is known and the models
   are unseen. The ink half ran on November 13 on the team's three published, labelled surfaces
   ([report](../reports/first_letters_0841_surface_control.md), finding 111): `BLOB_LEVEL_SIGNAL`. At a depth and
   side chosen with labels on one segment, the four-model ensemble scores AUC 0.75 and 0.72 against the labels on
   the other two, with a slid-map floor of 0.53 and the team's own model at 0.92 and 0.87. The maps show strokes
   where the letters are and no readable letter. The mesh half cannot run on PHerc. 0841 from public inputs: its
   lasagna normal and gradient volumes are not published.
3. A stacked-winding check on every band before its image is read.
4. Depth-shuffled renders through the same models, as the negative control for model-invented letterforms.
5. No training on the target until a band shows row-aligned signal. If iterative labelling starts, training
   and prediction regions stay disjoint, as the rules require.

**What the PHerc. 0841 control changes.** A band on an eligible scroll is a detection test: it is read with a
depth sweep on both sides (on PHerc. 0841 one side scored 0.76 and the other at most 0.56), a blank band is weak
evidence of no ink, and strokes are not letters until a sharper ink step than these four models says so.

**Which scrolls the fit can run on.** Read on November 13: of the 26 scrolls with published spiral tracks, 14
also have the lasagna volumes the fit requires. The eligible ones among them are PHerc. 0125, 0191, 0211, 0257,
0268, 0358, 0800, 0813 and 0826.

**Kill criterion.** If three scrolls show nothing by the end of February 2027 with the positive control
reproduced, stop, publish the nulls and meshes, and reassess.

## Proposed timeline

- **November (to the 30th).** Finish and report finding 109. The kill test ran on November 10; the recipe's
  mesh step on the PHerc. 343 band ran on November 12. Both reproduced. File November with Villa #2258
  and whatever else has merged; expect \$0 to \$250.
- **December.** The PHerc. 0841 ink control ran on November 13 (blob-level signal). Run the first band on an eligible scroll with published tracks and
  umbilicus: PHerc. 0125 first, with low confidence that it is untried, else 0211 or 0826. Turn each obstacle
  into a Villa fix. Submit the workflow as run on this machine, with scripts, costs, fixes and meshes.
- **January and February.** Automate more bands and scrolls overnight. Apply the kill criterion at the end of
  February.
- **March to June.** Only if a band shows row-aligned signal: iterative labelling with strict separation, kept
  private, then a submission before June 25.

## Not recommended

- **The 64-pixel training loop as a prize path.** No lever has improved its reading under a control. It holds
  about 13 GB of the card during a cycle with the GPU mostly idle (4% and 13% busy in two samples on
  November 10). Confidence that it has produced nothing prize-relevant so far: high. That it will not:
  moderate.
- **New ink architectures or pretraining** on one GPU, and label sets that need annotator hours we do not have.
- **More evaluation tools.** ScrollGT, inkdelta and inkagree stay maintained as our own instruments; the
  current rules discourage submitting such tools.
- **The Title prize as a primary goal, and a solo Grand Prize.** A solo Grand Prize win is judged well under
  1%. The realistic route there is supplying components to a leading team.

## Decisions that remain the owner's

Accepting this strategy did not settle these:

1. Whether the training loop is paused or shrunk for campaign GPU runs. Answered on November 10: yes. The kill
   test stopped it for 22 minutes.
2. Where eligible-scroll outputs are kept, since this repository is public.
3. Whether and when to post the Villa seam PR (with or without the duplicate change), the splice issue and the
   seed-heading proposal.
4. How many hours a week are available for hand refinement in VC3D. The survey's failure was unrefined
   surfaces.

Not verified for this review: how PHerc. 306B was won, and the organizers' First Letters workflow post.

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
- [Finding 104](../reports/neural_tracer_refit_retry.md) (2026-11-03, registered) ran that pilot with the one
  continuation rule villa's tracer already has, its refit retry. It cut confidence stops by 21% and raised coverage on
  every held-out cube, but only 0.202 of the length it added lies on the reference, merges rose by 219 against the
  floor's 35, and the median held-out ERLpen gain is 0.003 against the 0.10 bar. It closes as a continuation rule; the
  confidence-stop line needs a rule that tests whether a continuation is on the fiber before keeping it. Presence,
  checked afterwards and not registered, is too weak a test: it separates the retry's on- from off-reference
  additions with a median AUC of 0.71, no better than on the stock trace.
- [Finding 105](../reports/neural_tracer_link_splice.md) (2026-11-05, registered) joins the tracer's own pieces
  instead of continuing them. villa's tracer keeps short overlaps "for joining" and records which fiber each piece's
  ends touch, but nothing joins them. Splicing each piece to the fiber whose end it overlaps raised held-out ERLpen on
  all ten cubes, by a median 30% at tolerance 4 and 6.3% at tolerance 2 (under the 0.10 bar there), with summed merges
  +1.2%. The polyline tool and its VC3D export are untested, and any villa proposal is the owner's decision.
- [Finding 106](../reports/afv_generator_block_seams.md) (2026-11-07, registered) measured villa's automated fiber
  generator (#1934, VC3D's **Generate automated fibers…**) across block borders. Where a block's border cuts a fiber,
  the block's spline bends, and both blocks' copies fail the stitcher's tests and are written. Trimming 16 voxels at
  each cut end raised held-out ERLpen on all eight Scroll-3 cubes, by a median 13% at tolerance 4 and 7.1% at
  tolerance 2, with summed merges at tolerance 2 −12.1%. More crossings at the block faces are lost (172 to 278 of
  1,304). A diagnosis after the verdict found that 176 of the 178 crossings the trim improves gain a join, and 63 of
  the 198 it worsens lose one. At 125 more of those, never chained, a trimmed copy stops 16 voxels sooner past the
  face. VC3D's default zone is one block, where the trim changes nothing, and any villa PR is the owner's decision.
- [Finding 107](../reports/afv_generator_default_zone.md) (2026-11-09, registered) ran finding 106's trim at villa's
  default block size: one 1024³ zone of the Scroll-3 scan in 8 blocks of 512, centred on a held-out cube. On main,
  0.120 of the zone's written length lies beside a same-family copy, and 0.052 with the trim. In the cube, ERLpen rose
  16.0% at tolerance 4 and 5.6% at tolerance 2, with merges at tolerance 2 92 → 82 and coverage −3.7% at tolerance 4.
  Decision `BITES_AT_DEFAULTS`: the villa PR's real-use example, whose posting is the owner's decision.
- [Finding 108](../reports/afv_generator_cross_block_duplicates.md) (2026-11-09, registered) found the rest of the seam
  defect. With the trim, copies of a fiber fitted by two neighbouring blocks still lay along each other, and the
  catalogue kept both: its own `compare()` calls them duplicates, but only the sub-voxel strict test could suppress
  them. Suppressing such a copy, only between sources of different blocks, scored on finding 106's held-out cubes from
  their cached fields (ERLpen at τ = 4 up on 8 of 8, median +5.7%; merges at τ = 2 386 → 384; median duplicated share
  0.104 → 0.032): `SUPPORTED`. With both changes, eight blocks reach 0.905 to 1.026 of one block's ERLpen at
  tolerance 4 (main: 0.703 to 0.923). The change adds 18 lines to villa's `catalog.py` and removes 2; any villa PR is
  the owner's decision.
- [Finding 103](../reports/seed_heading_confirmation.md) (2026-11-03, registered) traced the queued seed-heading fix
  on the ten fiber-skeletons cubes that ScrollGT does not ship. None skipped 20% of its dots (the most, 0.167), so
  the coverage gain went untested and still rests on finding 100's two Scroll-5 cubes. The fix cost at most 0.013
  precision and 2.7% of ERLpen on each cube at tolerance 2. At tolerance 4 one cube lost 6.2%. Seven of the ten
  have in-sample presence, where skips are rare; a test of the gain needs cubes that skip often.
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

The [community catalogue][catalogue], read on November 10, lists ScrollFiesta, eligible-spiral-dataset,
spiral-winding-audit and first-letters-survey among others. For the campaign, reuse them before writing a
wrapper: the dataset assembler for `fit_spiral` inputs, the winding audit for control 3, the survey's patches as
a record of where automatic growth failed. States below were rechecked on November 10.

- Six of the eight issues checked as rank-3 candidates already have an open PR that references them:
  [#2371][downloader] (#2379), [#2294][render-memory] (#2446), #2320 ([#2321][import]), #2104 (#2389),
  #2080 (#2081) and the canvas shift in [#2370][canvas] (#2447). Do not duplicate them. #2478 and #2346 are
  questions about rendering, not reproduced defects.
- [#2370][canvas] is the defect our canvas-shift tool measures. Its reporter offered to add the drift term to
  Villa's `transfer`; the Villa fix is theirs.
- [#2265][sheet-plane] (open) tests a sheet-plane penalty in the fiber tracer. [#2248][fiber-qa] and
  [#2311][loader] were closed unmerged, and [#2205][plain-zarr] merged.

These are source observations, not endorsements of unmerged code. The owner had two Villa PRs open at this
review (#2463 and #2465); no further merged credit or maintainer adoption is assumed.

## Resource and release discipline

Use one RTX 4090 with 24 GB VRAM, 4 cores, 31 GB of RAM and the project's existing 500 GB storage budget.
Stream bounded crops, cap cache sizes and profile memory before a larger run. Run one heavy side job at a
time, each in its own systemd user unit, and stop or start the training loop only through `./stop.sh` and
`./start.sh`. The owner allowed the loop to be stopped for campaign GPU runs (November 10); restart it as soon as
the run ends.

A completed campaign step should leave a pinned input/model/code manifest, the commands, both successful and
failed cases, time and memory costs, and output that a Villa or VC3D user can consume. For an eligible volume
that record is written at once and published only under the confidentiality rule above. Ask whether a result
changes a real user's decision or removes an obstacle. Measured adoption and real pipeline improvement are the
route to stronger future prize submissions.

[prizes]: https://github.com/ScrollPrize/villa/blob/740f0103b9574e9e88bbb24a8438dbe1d5a1a0c0/scrollprize.org/docs/34_prizes.md
[winners]: https://github.com/ScrollPrize/villa/blob/740f0103b9574e9e88bbb24a8438dbe1d5a1a0c0/scrollprize.org/docs/15_winners.md
[problems]: https://github.com/ScrollPrize/villa/blob/740f0103b9574e9e88bbb24a8438dbe1d5a1a0c0/scrollprize.org/docs/37_2026_open_problems.md
[catalogue]: https://github.com/ScrollPrize/villa/blob/740f0103b9574e9e88bbb24a8438dbe1d5a1a0c0/scrollprize.org/docs/20_community_projects.md
[criteria]: https://github.com/ScrollPrize/villa/pull/2450
[recipe]: https://github.com/Nieuwlaar/pherc343-first-letters
[canvas]: https://github.com/ScrollPrize/villa/issues/2370
[downloader]: https://github.com/ScrollPrize/villa/issues/2371
[sheet-plane]: https://github.com/ScrollPrize/villa/pull/2265
[fiber-qa]: https://github.com/ScrollPrize/villa/pull/2248
[render-memory]: https://github.com/ScrollPrize/villa/issues/2294
[plain-zarr]: https://github.com/ScrollPrize/villa/pull/2205
[loader]: https://github.com/ScrollPrize/villa/pull/2311
[import]: https://github.com/ScrollPrize/villa/pull/2321
