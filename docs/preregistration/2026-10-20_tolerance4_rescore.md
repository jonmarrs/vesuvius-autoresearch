# Pre-registration: does villa's neural tracer keep its Scroll-3 lead, and its deficit elsewhere, at a 4-voxel tolerance?

**Status: REGISTERED 2026-10-20, before our tracer or connected components has been scored at tolerance 4.** The
owner approved the rescoring the same day. CPU only, at nice 19 with the loop running. **Run 2026-10-20, 11:24–12:20
PDT: finding 94, `reports/tolerance4_rescore.md`. P1 held (8 of 8) and P2 failed (8 of 11).**

## The question

ScrollGT scores fibers at a tolerance of 2 voxels. Finding 91 found that villa's neural fiber tracer leads our tracer
on merge-penalized ERL on all 8 Scroll-3 cubes and trails it on all 11 in-sample cubes. ScrollGT 0.8.0 publishes those
rows. The exploratory section of `reports/neural_tracer_entrant.md` (#151, #157) then found the following:
* Most of the thin entrants' Scroll-3 advantage over the in-sample 512³ cubes lies within 2–4 voxels of the ground
  truth.
* On 5 of the 11 in-sample cubes the ground truth sits about a voxel off the CT's fibers.

Finding 91 scored the neural tracer at tolerance 4 as a descriptive check. Our tracer and connected components have no
tolerance-4 rows, so whether the comparison holds at 4 is unmeasured.

**Why it matters:** ScrollGT's published Scroll-3 lead, and the in-sample deficit, are tolerance-2 results. If either
reverses at 4, the published rows need a note.

## Data, fixed now

* **Our tracer:** the saved instance labellings that ScrollGT's `tracer_strict_relink` rows were scored from.
  * The 11 in-sample cubes: finding 80's, `spiral_out/tracer_rescore/<cube>_instances.npy`.
  * The 10 held-out cubes: finding 83's, `spiral_out/fiber_heldout/run/<cube>_instances.npy`.
* **Connected components:** ScrollGT's own `floor_connected_components` of each cube's published mask.
* **Villa's neural tracer:** finding 91's tolerance-4 rows (`descriptive_tolerance_4` in
  `reports/neural_tracer_entrant.json`), not re-run.
* **Identity:** a labelling must reproduce its published row's tolerance-independent fields: instance count,
  predicted length, ground-truth length and ground-truth fibers. If any field differs on any cube, the status is
  IDENTITY_FAILED and there is no verdict.
* **Scoring:** ScrollGT `score_tracing`, scoring version 3, tolerance 4.0, every other argument as published.
  `scripts/tolerance4_rescore.py` writes `reports/tolerance4_rescore.json`.

## Predictions, fixed now

1. **The Scroll-3 lead holds at tolerance 4.** The neural tracer's merge-penalized ERL is above our tracer's on at
   least 6 of the 8 Scroll-3 cubes. Confidence moderate. The neural tracer's own Scroll-3 median rises from 25.30 to
   62.40 at 4. Our tracer's instances are thick, so a wider tolerance adds less coverage to them, but it also adds
   merges.
2. **The in-sample deficit holds at tolerance 4.** The neural tracer's merge-penalized ERL is below our tracer's on at
   least 9 of the 11 in-sample cubes. Confidence low. At tolerance 2 the gap is wide (7.82 against 20.75), but most of
   the thin entrants' in-sample loss is placement within 2–4 voxels, which tolerance 4 forgives.

**Descriptive, no prediction:** connected components at 4; every entrant's tolerance-4 over tolerance-2 ratio, by
group; coverage and merges.

## Decision rule

| outcome | conclusion |
|---|---|
| any labelling fails the identity check | IDENTITY_FAILED, no verdict |
| fewer than 6 Scroll-3 or 9 in-sample cubes scored | that prediction unevaluated; INCOMPLETE |
| P1 holds | "the Scroll-3 lead holds at tolerance 4" |
| P1 fails | "the Scroll-3 lead is tolerance-dependent": recommend a ScrollGT note where the lead is claimed |
| P2 holds | "the in-sample deficit holds at tolerance 4" |
| P2 fails | "the in-sample deficit is tolerance-dependent": recommend a ScrollGT note where the deficit is claimed |

Any change to ScrollGT is a separate decision by the owner.

## What the result cannot do

* **Two tolerances, not a curve.**
* **Ground truth as published.** The offsets on 5 in-sample cubes stay in it.
* **The neural tracer's tolerance-4 rows are finding 91's.** They come from the same run, scored with the same ScrollGT
  version.
