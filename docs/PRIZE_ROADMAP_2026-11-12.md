# Prize roadmap, November 2026 to June 2027: staying on the sheet with one RTX 4090

**Prepared 2026-11-12 at the owner's request. A proposal, not a registration.** It does not replace the accepted
[research strategy](RESEARCH_STRATEGY.md) of November 10. The section "What this changes in the accepted strategy"
lists the differences, and each one is the owner's decision. No experiment was run for it. Every probability and
award range below is a judgement, not a measurement.

**Status correction, November 13:** the image-chain kill test already passed on
November 10 ([reproduction report](../reports/first_letters_343_reproduction.md)).
The remaining prerequisite is reproducing the mesh stage; the spiral fit, snap
and flatten were not run in that test. This corrects the scheduling assumptions
below without adopting this proposal's owner decisions.

Read for this roadmap on 2026-11-12:

- **Villa main of that day** (commit 03a280ad): the prize rules page, the winners page and the 2026 open-problems
  page, from the website's source.
- **Villa's open issues**: 55 open issues and 111 open pull requests, read from the public list pages by a helper.
  It saw titles, dates and authors only. Labels, assignees and linked PRs were not visible, so every issue named
  below needs its PR status checked before any work starts.
- **This repository**: the strategy, findings 100 to 108, the [November filing draft](PRIZE_FILING_2026-11_DRAFT.md)
  and the drafted Villa contributions.

Not read: Discord, the newsletter, the PHerc. 343 recipe's code, and Villa's merged or closed PRs. October's Progress
Prizes were not on the winners page at this read. The count of 20 eligible First Letters volumes is the strategy's,
from November 9.

## The short version

1. **Keep the main line: a First Letters campaign.** It is still the only five-figure prize whose published winning
   method fits this machine. Eight awards remain and the deadline is June 25, 2027. The image-chain kill test has
   passed; the mesh-stage reproduction comes next.
2. **Add one piece of new work: a winding snap that cannot put two windings on one sheet.** That failure is what
   stopped the published recipe on other contributors' fits, and sheet switches are on the organisers' own
   bottleneck list. It is CPU-only geometry.
3. **Test the fiber fixes where they are consumed, in the spiral fit.** If the fit does not change, stop making
   fiber fixes after the measured ones land.
4. **File two things each month from December:** one substantial item and one bundle of fixes that bit during real
   use, both released in the first half of the month.
5. **Free the GPU and the automation budget.** Pause the 64-pixel training loop, and run fewer internal audits.

## What can be won

| Prize | Amount | Deadline | What it takes | Judged chance for us |
| --- | --- | --- | --- | --- |
| 2027 Grand Prize | \$800,000, then \$100,000, \$50,000 and \$50,000 | June 25, 2027 | One of 13 scrolls unrolled whole and readable: all of the recto, at most 8 documented hours of human input, integrated in VC3D, 70% of each counted column's characters legible. | Solo: well under 1%. As a supplier of components to a team: the owner's decision. |
| First Letters | \$50,000 a scroll, for at most 8 more scrolls | June 25, 2027 | 10 legible letters inside one 4 cm² of an eligible volume, with the flattened mesh, a programmatic image, a reproducible method, false-positive mitigation and held-out validation. Nothing made public before the announcement. | About one in ten of at least one award, conditional on the remaining mesh-stage reproduction and three to five scrolls getting a correct surface. |
| PHerc. Paris 4 title | \$50,000 | Listed as June 25, 2027; the rules also say submissions stay open until it is won | An image of the title on any Scroll 1 scan, including the 2.4 µm volumes. The expected region has shown no detectable ink so far. | Very low. Worth one time-boxed pass, not a line of work. |
| Progress Prizes | \$20,000 guaranteed to the month's best submission; others \$250 to \$20,000 | Monthly; next is November 30 | Open-source work that helps read the scrolls. See the next two tables. | See "What a month should produce". |

### What September paid

The winners page lists 27 September awards, \$40,500 in all.

| Award | Count | What won it |
| --- | --- | --- |
| \$20,000 | 1 | Automated fiber extraction, integrated with VC3D and the spiral fitter. |
| \$5,000 | 2 | The ScrollFiesta pipeline's clean surfaces over large areas; the reader-v2 ink model, "now seeing wide use". |
| \$1,000 | 3 | A new method with promise (sheet instance embeddings; assigning patches to windings); a chunk compressor that VC3D now supports. |
| \$500 | 9 | One fix that bites (renderer memory); a tool people use (winding annotations, winding consistency); data for prize scrolls (umbilici, full-scroll inferences); an experiment with real-data numbers (cross-scroll ink, pseudo-label filtering, faster inference); a lighter tutorial. |
| \$250 | 12 | A bundle of merged Villa PRs (five of the twelve, ours among them); a platform port; one small VC3D feature; a spiralised length of one scroll; a 35% inference speed-up. |

### The rules that shape a submission

- **Since November 5** the prize page discourages "standalone analytic, auditing or evaluation tools" and says that
  fixes for issues that "rarely or never cause problems in practice are unlikely to be awarded".
- **Villa's contributing guide** accepts a fix only when it comes from running the tool on real scroll data. It asks
  for a screenshot of the error, a before/after comparison on real data, and human-written commentary on any
  LLM-written PR. It says PRs that look like LLM "fishing expeditions" may be closed.
- **The wishlist is empty.** The "help wanted" label has no open issue. The open-problems page is the live list.
- **Review capacity is short.** With 111 PRs open, a small PR with its evidence attached is the kind that gets read.

So a plan cannot promise a prize every month. Our local award record confirms September's \$250;
July and August totals are unverified here, and October was unannounced at this read. A realistic
floor is \$250 in a month when two or three real-use fixes merge. \$500 to \$1,000 needs one item a month that other
people use or that shows a result on real data.

## What the organisers ask for, against this machine

The open-problems page names six ways to help. The machine is one RTX 4090 (24 GB), 4 cores, 31 GB of RAM and a
500 GB storage budget.

| The ask | Fits this machine? | What we already hold | Verdict |
| --- | --- | --- | --- |
| Better-localised recto labels, or surface models that keep sheet topology | Labels: yes, on CPU. Training a leading surface model: no. | The canvas-shift measurement; the proofreader uncertainty masks. | Later, and only with a small-scale proof. |
| Geometry and C++ tools that avoid holes, mergers and sheet switches without a human checking each piece | Yes, CPU. | Nothing yet. | **New work: the stack-free snap (rank 2).** |
| Label quality: snapping and active learning, where "careful, small-scale work can matter more than scale" | Yes. | The active-learning catalogue and the uncertainty hand-off. | Conditional, from March. |
| Conservative fiber tracing: "a tracer that confidently follows fewer fibers correctly is more useful" | Yes: GPU inference per cube, CPU scoring. | Findings 100 to 108 and ScrollGT. | **Land the measured fixes, then test them in the fit (rank 3).** |
| Spiral fit: evaluation suites, loss functions, automated winding annotations | The fit runs on a consumer GPU. | One converged Scroll 1 fit. | Reached through ranks 2 and 3. No new annotation generator: two attempts failed (see the strategy). |
| Direct 3D ink segmentation; self-supervised 3D representations | Pretraining: no. Inference and light fine-tuning: yes. | A distillation history with no reading gain under a control. | Not a research line. Inference-side work only (rank 5). |

The common thread in what fits is geometry that stays on one sheet: at the scale of a fiber, of a winding, and of
a label. The organisers' bottleneck table has the same thread ("No built-in connectivity", "Sheet switches",
"Approximate surface labels").

## Ranked work

### 1. The First Letters campaign (unchanged, with three additions)

The strategy's campaign stands as written: its recipe, its five controls and its kill criterion. Three additions:

- **Order the scrolls by scan similarity.** The released ink models worked on PHerc. 343, 306B and 1667. Before
  choosing a scroll, compare each eligible volume's voxel size, energy and beamline with those scans, and start
  with the closest. This costs an hour of reading metadata. The volumes' parameters were not read for this roadmap.
- **Look at the plain render as well.** The rules say ink is sometimes visible in the flattened render with no
  model, and that this alone qualifies. Record the plain render of every band beside the model output.
- **Treat the calendar as the main risk.** Other contributors run the same recipe, two prizes went in October, and
  eight remain. The image-chain check passed on November 10; the mesh-stage reproduction remains. Each further
  week costs more than any other item here.

### 2. A snap that cannot stack windings (new)

**The problem.** The recipe snaps fitted windings onto the surface prediction. The community's winding audit found
that this step put 15 to 17% of consecutive windings onto the same surface on PHerc. 0175A and 0800 fits, against
1.7% on the awarded PHerc. 343 pair. A band can then render the same papyrus twice. The community survey's
automatically grown patches failed in a related way: they left the text-bearing sheet.

**The proposal.** Assign windings to sheets jointly instead of one at a time. Along each radial line the windings
and the predicted sheets are both ordered, so the assignment can be required to keep that order: two consecutive
windings can never take the same sheet. That is a monotone matching, which dynamic programming solves exactly for
each line, with a smoothness term between neighbouring lines. It needs no GPU.

**First step (two days, CPU).** Read the recipe's snap step and the audit's method. Reproduce the audit's stacked
share on one published fit. Whether the fits of PHerc. 0175A and 0800 are published in a usable form was not
checked here.

**Test.** The stacked share on the two failing fits and on the PHerc. 343 pair, before and after; then a render,
checked as the prize page asks: fibers visible along the surface, and one sheet per winding in cross-section.

**Continue or stop.** Continue if the stacked share falls below about 3% on the failing fits and the PHerc. 343
result does not move. Stop if the published fits are themselves off the sheet, because then the snap is not the
cause and the work belongs in the fit.

**Why it ranks second.** It removes the known reason the recipe fails on scrolls that others have already fitted,
which is a direct edge for rank 1. It answers the organisers' second ask. If it holds, it is a Villa proposal with
real-data evidence, in the class that September paid \$500 to \$1,000.

### 3. Land the measured fiber fixes, then test them in the spiral fit

- **Post what is measured.** The seam trim and the cross-block duplicate change go in one PR once finding 109
  reports ([draft](VILLA_DRAFT_afv_generator_seam_trim.md)). The link splice goes as an issue
  ([draft](VILLA_DRAFT_volume_splice.md)). Hold the [seed-heading proposal](VILLA_DRAFT_volume_seed_heading.md):
  finding 103 left its coverage gain untested.
- **Then measure the fixes where they are used.** September's award says the automated fibers feed the spiral
  fitter. Fit one band twice, with stock fibers and with fixed fibers, everything else equal, on a scroll with
  hand-traced segments to score against (PHerc. Paris 4 or 1667). Register the comparison first, as usual.
- **Stop rule.** If the fit does not change, make no further fiber fixes after the measured ones land, and move
  that effort to rank 2. If it improves, that is the real-use example the prize criteria ask for, and the fiber
  line continues with the continuity work of findings 102 and 105.

### 4. Fixes the campaign hits (the monthly bundle)

A fix starts from a failure reproduced here during a campaign run, with the screenshot and the before/after that
Villa requires. Open issues that sit on the campaign's path, by title only:

| Area | Issues | Note |
| --- | --- | --- |
| Flattening | #2500 (disconnected pieces flattened on top of each other), #2437 (NaN at the first inpaint iteration) | #2437 names a closed PR that fixed it. |
| Lasagna configurations | #2391, #2458 (shipped configurations that do not load or parse) | The recipe flattens with lasagna. |
| Spiral fit | #2029 and #2239 (two different scroll centres), #2105 (winding direction in the README for PHerc. 0826) | An open PR (#2494) changes the umbilicus fit. |
| Surface format | #2482 (mask values 1 to 254: the loader and the format document disagree) | |
| Small disks | #2478 (a download estimate before a render) | A feature, and it serves the "data scale" bottleneck. |
| Ink training | #1481 (zero padding inside normalisation statistics), #1231 (the tutorial trains with no validation set) | Only with a before/after on the public ink dataset. |

Leave alone the issues that already had an open PR at the strategy's check on November 10 (#2371, #2294, #2320,
#2104, #2080, #2370), and #2153, where #2513 is open. About fifteen open issues are defects in the published data
bucket. Those are the organisers' to fix; report a new one, and do not build tooling around them.

### 5. Calibrate the ink ensemble on scrolls with known text

This supports rank 1 and uses its second control. On PHerc. 0841 and 1667, which the released models did not train
on, measure which models, depths and ensemble rule show letters, and what each costs in time and memory on this
card. No new architecture and no pretraining. September paid \$250 to \$500 for work of this kind (ensembling,
faster inference, cross-scroll experiments).

### Opportunistic, each time-boxed

- **The title prize.** Once the ensemble runs here, one pass over the published title-region segments of Scroll 1
  at each resolution. Stop after one weekend.
- **Data for prize scrolls.** Umbilici, fits, meshes and nulls from the campaign. September paid \$250 to \$500
  for such data. Publish geometry and nulls on the owner's decision, and never anything that shows or locates
  possible text.

## Calendar

| Month | Work | What is filed | Judged award |
| --- | --- | --- | --- |
| November (to the 30th) | Pause the loop for the next run. Reproduce the mesh stage; the image-chain kill test passed. Report finding 109 and post the seam PR. Read the snap step and reproduce the audit. | What has merged, as the draft says. | \$0 to \$250 |
| December | The PHerc. 0841 control. The first eligible band, on the scroll the scan comparison ranks first. The snap prototype, measured on the failing fits. Fixes as they bite. | The recipe as run on a 4-core, 31 GB, one-4090 machine: commands, costs, failures, meshes. A bundle of fixes. | \$250 to \$1,000 |
| January | The fit comparison for the fiber fixes. Band sweeps overnight. The snap as a Villa proposal if it held. The ensemble calibration. | The snap, or the fit comparison. A bundle. | \$250 to \$1,000 |
| February | More bands and scrolls. Apply the campaign's kill criterion at the end of the month. Decide on a team. | Meshes and nulls for the scrolls tried. A bundle. | \$250 to \$500 |
| March to June | If a band shows row-aligned signal: private iterative labelling with disjoint regions, and a submission before June 25. If not: the geometry tools become the main line, for whichever teams are closest to the Grand Prize, with label snapping as the next study. | One substantial item and one bundle each month. | Depends on the branch. |

### What a month should produce

- **One substantial item**, filed on its own: a workflow, a tool, a data release or a study with real-data
  results.
- **One bundle** of fixes that bit during that month's runs.
- **Released by the middle of the month**, announced where users are, with questions answered. The prize page
  weighs early release and actual use.
- **Evidence in the organisers' terms.** For geometry: fibers visible on the surface and no sheet jump in
  cross-section. For ink: results on the public datasets.

## What to stop or shrink

- **The 64-pixel training loop.** The strategy already judges it unproductive. Pausing it frees capacity for
  the next campaign run; the image-chain kill test already ran with it temporarily stopped.
- **Internal audits and reviews.** The hourly design review is on its 162nd round. It has found real defects in
  our own tooling, but none of that work is prize-eligible under the November 5 rules, and this week it used up
  the assistant's usage allowance several times. A daily or on-demand review would leave that budget for
  campaign runs and for reproducing fixes.
- **New standalone evaluators.** ScrollGT, inkdelta and inkagree stay as instruments. Cite one only where it
  changed what a tool produces.
- **The seed-heading proposal**, until a test of its gain exists.
- **New ink architectures, and a solo Grand Prize.**

## What this changes in the accepted strategy

1. Adds the stack-free snap as rank 2.
2. Adds the spiral-fit comparison to the fiber line, with a stop rule for further fiber fixes.
3. Adds the scan-similarity ordering and the plain-render record to the campaign.
4. Adds the ink-ensemble calibration as its own small item, tied to the second control.
5. Sets a monthly filing pattern of one substantial item and one bundle.
6. Proposes fewer internal audits.

Unchanged: the campaign's recipe, controls, kill criterion and confidentiality rule; the limit of three open PRs
and two code-fix PRs a week; dense winding inputs stay parked.

## Decisions for the owner

1. **Pause the training loop for the next campaign run?** The image-chain kill test ran with a temporary pause;
   the remaining mesh-stage run still needs capacity scheduled by the owner.
2. **Where eligible-scroll outputs are kept**, since this repository is public.
3. **Whether to post the seam PR and the splice issue** once finding 109 reports.
4. **Hours a week** for hand refinement in VC3D and for the human-written commentary Villa asks for. Both are
   work only the owner can do.
5. **A team.** By the end of February, whether to offer the geometry tools to a team that is close to the Grand
   Prize, or to join one.
6. **How often the design review runs.**
