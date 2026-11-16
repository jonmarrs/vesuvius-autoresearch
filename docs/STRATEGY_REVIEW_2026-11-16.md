# Strategy review: regional reading before more infrastructure

**November 16, 2026. Discussion proposal, not an adopted experiment or permission to run.**
This dated assessment supplements the [accepted strategy](RESEARCH_STRATEGY.md) and
[November 12 roadmap](PRIZE_ROADMAP_2026-11-12.md). It preserves their historical
measurements and registrations. It changes no runtime configuration, training loop,
publication gate or active work assignment. No model, GPU experiment or checkpoint
was run for this review. Recommendations and budget caps below are judgments, not
measured success probabilities or promised awards.

## Decision in brief

Keep regional First Letters exploration as the main research line, using released
models and careful surface selection on one RTX 4090 with 24 GB VRAM. Complement it
with a few fixes demonstrated in actual Villa workflows. Do not compete with larger
teams through foundation-model pretraining or broad architecture sweeps.

Three changes matter now: remove PHerc. 211 as a First Letters target, compare newer
released readers before widening the search, and use the sheet score for triage
rather than as proof that a surface follows one sheet. The immediate deliverable is
a small reproducible positive-control comparison, not another evaluator framework.

## Prize status: use dated announcements as well as static lists

The [official November 15 announcement][211] awards Priyank Aranke $50,000 for
PHerc. 211 and says **seven First Letters prizes remain**. It reports 37 submissions
from 15 contestants or teams and further promising entries under review. PHerc. 211
is now useful for reproduction and broader unwrapping, not another First Letters win.

At this review, the [prize page][prizes] still lists eight awards and 20 volumes,
including PHerc. 211. Subtracting the announced winner gives a **provisional 19
candidates**, not a newly verified official eligibility list. Check announcements
and volume eligibility again before allocating a substantial run.

First Letters and Grand Prize eligibility are different lists: the static page has
20 and 13 volumes respectively; PHerc. 1447 is Grand-Prize eligible but absent from
the First Letters list. The June 25, 2027 deadline and First Letters requirement of
ten legible letters within one 4 cm² area remain the relevant milestone criteria.
Meshes, traceable programmatic images, held-out evidence and reproducibility are
required. Keep possible discoveries private until officially announced. Larger
windows are allowed with convincing anti-hallucination evidence; this repository's
64-pixel contracts are local controls, not the contest's current size limit.

The [November Progress round][prizes] closes November 30 at 11:59 p.m. Pacific.
Awards favor early release, actual use, demonstrated improvements and bugs encountered
on real workflows; standalone auditing or evaluation tools are discouraged. Small
contributions belong in a bundle. The month's best submission is guaranteed $20,000;
**there is no guaranteed monthly award for this project.**

The [official winners page][winners] now announces October: $20,000 for substantial
unwrapping work, $5,000 for reader-v3, $2,500 for automated-fiber work, and smaller
awards for practical contributions. It confirms Jonathan Marrs's September $250;
his name is not in the October section. This supersedes the earlier strategy's
"October unannounced" snapshot without changing the filing receipts. October's
First Letters awards for PHerc. 306B and PHerc. 343 remain useful precedents.

## What the existing evidence earns

| Evidence | What it supports | What it does not establish |
| --- | --- | --- |
| [PHerc. 343 image reproduction](../reports/first_letters_343_reproduction.md): 99.95% identical pixels | The known image chain runs here | New text discovery; the depth was known and published contrast statistics were reused |
| [Mesh-stage reproduction](../reports/first_letters_343_mesh_step.md): about 3 h 31 min, 12.7 GB GPU, 10.8 GB process RSS and 17.1 GB unit memory including page cache | This band fits the available machine | Cost or success on every scroll; whole-scroll feasibility |
| [PHerc. 0841 control](../reports/first_letters_0841_surface_control.md): AUC about 0.72–0.75, no readable letters | Ink-localization signal, strong side/depth dependence | A sensitive test for absence of readable ink on a new scroll |
| [Fiber seam confirmation](../reports/afv_generator_seam_confirmation.md): comparable four-cube subgroup ERLpen +23.0% at tolerance 4 | A measured continuity improvement worth integration | Reading improvement; the larger ten-cube headline includes smaller-than-user blocks and coverage costs |
| [Unchanged training control](https://github.com/jonmarrs/vesuvius-autoresearch/pull/302): old recipe minus new −0.00271 F1 and −0.01022 AUC | A real controlled local metric gain | Unseen-scroll legibility or a compelling reason to keep continuous search occupying the card |

Do not say the training loop never improved anything. Its issue is the mismatch
between repeatedly selected validation metrics and readable new text. Likewise,
source/report tests establish integrity of the recorded calculation, not independent
reproduction of its underlying data or a scientific result.

The image-reproduction report's full-sweep projection needs reconciliation: it
mentions 496 jobs but extrapolates from eight jobs per depth over 31 depths.
[Review #413](https://github.com/jonmarrs/vesuvius-autoresearch/pull/413) records the
ambiguity. Profile a small matched workload rather than promising a nine-hour sweep.

## Geometry: a useful ranking is not a continuity certificate

At review time, [#434](https://github.com/jonmarrs/vesuvius-autoresearch/pull/434)
and [#435](https://github.com/jonmarrs/vesuvius-autoresearch/pull/435) are open,
author-owned research changes. Their findings are reported evidence, not results
rerun here; preserve their ownership and any registered consequences.

Finding 116 reports a wrong-handed fit scoring almost like the right-handed fit.
The score detects proximity to predicted sheets, not following one sheet around a
scroll. Finding 117 reports tile-ranking AUC 0.895 on two PHerc. 343 windings, with
all 32 high-scoring tiles meeting its reference criterion. That is encouraging for
triage, but the 70 tiles are correlated, the "right" label requires only half the
covered nodes within two voxels, and none of its wrong tiles lies on a neighboring
sheet. The snapped surfaces have no wrong tiles, so discrimination there is untested.

Separate review of [#435's published scorer][tile-scorer] and
[registration][tile-registration] leaves scorer/control-contract questions unresolved.
Do not treat `LOCAL_GATE_WORKS` as an independently cleared promotion gate before
the owner resolves those questions. This does not establish that the reported result
is invalid or imply post-result method selection. This note neither changes the
scorer nor duplicates the existing owner's remediation.

Before scaling inference, use a small frozen challenge containing sheet crossings
or wrong-sheet tiles, or blinded cross-sectional inspection of selected target tiles.
Check continuity over the actual image area, not just mean proximity. Do not expand
this into a new standalone evaluator project. A whole wrong-handed spiral need not
invalidate every local patch, but locality is not itself proof that a patch is sound.

The roadmap's monotone, stack-free snap is a plausible hypothesis, not yet a
guarantee across crushed folds, missing predictions or neighboring radial lines.
First establish that snapping, rather than the input fit, causes the observed
failure. Cap an initial prototype at two CPU days and stop without that diagnosis.

## Update the reader before expanding the search

The [PHerc. 343 recipe][343] explicitly targets one 24 GB NVIDIA GPU. Retain it as
a reproducible baseline. Compare [reader-v3][reader3] and the new
[Studio multiscroll model][studio] on matched public positive-control inputs before
making that older four-model ensemble the permanent campaign bottleneck. The winners
page describes reader-v3 as widely used in First Letters submissions; its repository's
quality claims still need local verification.

The Studio repository documents full training requirements of at least 96 GB GPU
memory and 128 GB host RAM. **Do not attempt that training recipe on this machine.**
Released-weight inference is a separate path with configurable batches and CPU
support. Its actual 24 GB memory footprint and speed were not tested here. Preserve
the documented 16-plane depth ordering; an arbitrary stack is not equivalent input.

Studio training includes PHerc. 0841, 0814 and 0009B. Our existing PHerc. 0841 control
therefore cannot count as unseen-scroll evidence for Studio. PHerc. 211 was excluded
from gradient training and is a natural public reproduction control, but the
[continued-training record][studio-development] repeatedly evaluates it and describes
development decisions after those evaluations. It is not an untouched generalization
test. Verify training and selection exposure separately for every reader and region,
including reader-v3.

Use readable strokes or independently assessed letterforms, false alarms, runtime
and memory beside AUC. The existing PHerc. 0841 segments overlap, Hecate's training
list is incomplete, and its 0.75 threshold is not calibrated to legibility. A blank
target band remains weak negative evidence unless geometry and reader sensitivity
are demonstrated. The [organizers' workflow][workflow] recommends small bands,
surface inspection and local patches where global fits fail. The [PHerc. 306B
account][306b] also shows the importance of local refinement and final readability,
not merely broad automated screening.

### Access and licensing are separate gates

The [Studio code][studio] is MIT. Its [released approximately 852 MiB checkpoint][weights], training
datasets and submission outputs are labeled CC BY-NC 4.0; the manual VC3D fork is
GPL-3.0. Third-party components retain their licenses. The checkpoint asset listing
and dataset cards were accessible; no weight download or execution occurred, and
individual submission ZIP contents were not verified. Code availability does not
make the weights unrestricted. Resolve attribution, redistribution and intended
competition-use compatibility before using those assets in a prize submission.

## Bounded next steps, when capacity and permissions permit

The GPU is occupied. **This review starts no work on it and changes no loop state.**
For a future approved 20 GPU-hour window, use these initial planning caps:

| Allocation | Hours | Decision it buys |
| --- | ---: | --- |
| Small matched public positive-control comparison and profiling | 4 | Which released reader is usable and informative here? |
| Two sequential regional passes on still-eligible targets | 12 | Does inspected surface area show reproducible row-aligned signal? |
| Optional fiber-to-fit integration/profile, only if prerequisites already exist | 2 | Can a downstream comparison run within a separately registered budget? |
| Reproduction or failed-run reserve | 2 | Can an apparent result survive a controlled check? |

These are caps, not runtime forecasts. The two-hour fiber allocation is feasibility
work, not an efficacy verdict; fit noise requires a separately justified comparison.
A capped pilot or one noisy fit pair cannot establish no downstream benefit.
Move it to reserve if prerequisites are absent. Stop and revise if the initial profile
makes the caps unrealistic; do not consume the reserve by widening an unvalidated search.
One heavy process at a time, bounded caches and regional data. Low GPU utilization
does not mean available VRAM or host memory. No rented compute is assumed.

PHerc. 0826 is an already-prepared candidate in the current strategy, subject to
fresh award/eligibility checks. PHerc. 0125 still has unresolved winding direction.
Do not spend another First Letters search window on PHerc. 211. Larger-compute teams
retain a training and broad-search advantage; regional inference, accurate surfaces
and careful refinement are the feasible competitive approach here.

Keep the calendar stop, but qualify "three scrolls tried" with inspected distinct
area, usable geometry, positive-control sensitivity, depth/side coverage and blinded
false positives. Three poorly segmented bands are not three strong negative tests.

For CPU/agent effort, favor campaign preparation over repeated unchanged-state
audits. Review changed evidence and consequential code; retain integrity tests, but
do not make internal review count or passing tests the research deliverable.

## Villa and November: finish useful work without duplicating owners

Villa implementation remains paused; this note does not resume it. Current owned
PRs #2501, #2463 and #2465 are open. Jon's #2464 is closed in favor of evilaliv3's
#2476; matcham0110 owns #2514 and #2515. Do not duplicate those changes or imply their
unmerged work is validated. The repository's three-open-PR discipline leaves no
automatic slot for another proposal.

When resumed, finish current-main evidence for existing owned work, then prioritize
the measured seam/duplicate fix when a slot exists. Hold seed-heading behind its
missing high-skip confirmation and native replay. Test splice integration narrowly.
New fixes should arise from real campaign use, not a quota or code-reading expedition.
The [Villa contribution rules][contributing] require real-data before/after evidence
and human review/commentary for LLM-assisted work; synthetic tests cannot substitute.

For November, review the existing [filing draft](PRIZE_FILING_2026-11_DRAFT.md):
separate merged contributions, unmerged proposals, local reproduction and adoption.
The PHerc. 343 reproduction/workflow can be described with its costs and limitations;
do not call reproduction a new discovery. Include a practical-fix bundle only for
work actually completed and eligible for that round. Recheck the form and criteria
on filing day. This documentation change submits nothing and promises no payment.

## Scope and publication boundary

This review uses public repository documents, selected PR evidence and official
announcements. It is not a full code audit, a model benchmark or legal clearance.
It publishes no new eligible-scroll render, location, prediction or discovery, and
does not change existing private-output, validation or human-approval holds. New
experiments require their own prerequisites and fixed comparison protocol.

[211]: https://scrollprize.substack.com/p/first-letters-emerge-from-pherc-211
[prizes]: https://scrollprize.org/prizes
[winners]: https://scrollprize.org/winners
[343]: https://github.com/Nieuwlaar/pherc343-first-letters
[reader3]: https://github.com/DomRusso2/reader-v3
[studio]: https://github.com/priyankaranke/vesuvius-studio-multiscroll-cpt
[studio-development]: https://github.com/priyankaranke/vesuvius-studio-multiscroll-cpt/blob/main/studio-multiscroll-cpt-20261023/README.md
[weights]: https://github.com/priyankaranke/vesuvius-studio-multiscroll-cpt/releases/tag/studio-softloss-20261023
[workflow]: https://scrollprize.substack.com/p/from-ct-scan-to-ancient-text-a-first
[306b]: https://scrollprize.substack.com/p/writing-seen-in-pherc-306b-for-the
[contributing]: https://github.com/ScrollPrize/villa/blob/main/CONTRIBUTING.md
[tile-scorer]: https://github.com/jonmarrs/vesuvius-autoresearch/blob/d57b31629317458bc786648a3fd643d1ae07a32b/repro/first_letters/pherc343/tile_gate/tile_gate.py
[tile-registration]: https://github.com/jonmarrs/vesuvius-autoresearch/blob/d57b31629317458bc786648a3fd643d1ae07a32b/docs/preregistration/2026-11-15_first_letters_343_tile_gate.md
