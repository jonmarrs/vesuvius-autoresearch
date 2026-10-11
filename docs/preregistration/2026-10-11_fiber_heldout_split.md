# Pre-registration: does ScrollGT's fiber reference mask, and the tracer built on it, hold up on cubes the mask never trained on?

**Written 2026-10-11, before any held-out cube was run through `fiber_hz_vt` or the tracer.** Chain
`repro/fibers/run_heldout_chain.sh`; analysis `scripts/fiber_heldout_analysis.py`, committed with this file on branch
`fiber-heldout-split`, which is stacked on `scrollgt-current-annotations` (vesuvius-autoresearch PR #19).

## The question

Finding 82 found that `scrollprize/fiber_hz_vt`, ScrollGT's reference mask and our tracer's semantic layer, trained on
every ScrollGT fiber target. Its training fingerprint (18 cubes: 13 at 256³, 5 at 512³) matches villa's
`fiber-skeletons` Dataset002, which holds all 11. Every number ScrollGT publishes for a mask-based entrant is therefore
in-sample. Connected components labels the whole mask, so its coverage is the mask's recall; our tracer has no learned
parameters of its own.

villa's Dataset004 (2025-07-28) holds 10 annotated cubes absent from Dataset002 and Dataset003:
* eight from Scroll 3 at 512³, a scroll the mask never saw;
* two new Scroll 5 cubes at 256³, from a scroll it trained on.

If the mask's recall holds on them, ScrollGT's in-sample numbers are a fair guide to what an entrant gets elsewhere. If
it drops, they overstate it, and ScrollGT needs a held-out split to say anything about generalization.

## Reachability, checked before this registration

All 10 cubes were downloaded from Dataset004 (`imagesTr`, `labelsTr`, `nml`) to `spiral_out/fiber_d004/heldout/`.

| cube | fibers (scored) | in-bounds nodes | nodes on villa's semantic label |
|---|---:|---:|---:|
| s3_00994_00494_01994_512 | 655 (649) | 32,774 | 1.000000 |
| s3_00994_01994_00494_512 | 736 (728) | 55,450 | 1.000000 |
| s3_00994_02494_01494_512 | 659 (656) | 42,273 | 1.000000 |
| s3_01994_01494_00994_512 | 643 (637) | 37,432 | 1.000000 |
| s3_01994_01994_01494_512 | 726 (718) | 26,619 | 1.000000 |
| s3_02994_02494_01994_512 | 604 (602) | 38,479 | 1.000000 |
| s3_03494_01494_00494_512 | 741 (741) | 52,810 | 1.000000 |
| s3_04494_00994_01494_512 | 669 (665) | 34,283 | 1.000000 |
| s5_13497_01497_02497_256 | 169 (166) | 2,846 | 1.000000 |
| s5_16997_03997_04497_256 | 287 (282) | 8,022 | 1.000000 |

Every NML declares 7.91 µm. Every CT and label is uint8 at the cube's size. The local `fiber_hz_vt` checkpoint's
SHA-256 (`a80d98f1…`) equals the Hugging Face LFS hash, and its local fingerprint has the same 13 + 5 composition.
**Nothing has been run through the model or the tracer.**

## Method

* **Mask:** `bench_cli trace` computes and caches the `fiber_hz_vt` probability with the recipe the published targets
  used: `3d_fullres`, 128³ patches, tile step 0.5, no mirroring, AMP, CUDA. The mask is P ≥ 0.5.
* **Tracer:** finding 80's configuration, the published defaults. The 512³ cubes use `--detect-block 128`, shown
  bit-identical to dense in finding 80's Amendment 1.
* **Scoring:** ScrollGT 0.5.0 functions (fiber scoring version 2, tolerance 2.0), the same filter (fibers with more
  than one in-bounds node). Rows: the oracle, the four floors, the tracer.
* **Gate, per cube:**
  * NML nodes on villa's semantic label at ≥ 0.999 (already measured above);
  * NML nodes on the P ≥ 0.5 mask at more than 5× its density, ScrollGT's frame test.

  A cube failing the gate is excluded and reported, not scored.
* **In-sample comparison:** the published ScrollGT 0.5.0 rows (current annotations), registered as constants in the
  analysis script:
  * connected-components coverage on the 512³ Scroll 5 cubes: 0.8882, 0.8130, 0.8223;
  * on the 256³ Scroll 5 cubes: 0.8666, 0.9119, 0.8185.

## Predictions, fixed now

1. **The mask's recall drops on Scroll 3.** The median connected-components coverage over the eligible Scroll-3 cubes is
   below 0.8130, the lowest in-sample 512³ value. Confidence moderate. Unseen scroll, unseen scan conditions, and an
   18-cube training set.
2. **It drops on the two new Scroll-5 cubes too:** both below 0.8666, the in-sample Scroll-5 256³ median. Confidence
   low. The scroll is seen, and the in-sample values already fell when villa revised their annotations (finding 82).
3. **Connected components beats the tracer on raw ERL on every eligible cube.** Confidence high: in-sample it is
   3.7–6.2× ahead everywhere.
4. **The tracer beats connected components on merge-penalized ERL on at least 75% of the eligible Scroll-3 cubes.**
   Confidence low-moderate. In-sample it leads on all three 512³ cubes, because connected components merges many
   fibers there. A worse mask on an unseen scroll could fragment the components and merge less.

**Descriptive, no prediction:** connected-components precision, the tracer's coverage, mask density, oracle ERL, and
merges, each beside the in-sample values for its size class.

## Decision rule

| outcome | conclusion |
|---|---|
| fewer than 6 of 8 Scroll-3 cubes pass the gate | no Scroll-3 verdict (P1 and P4 not evaluated); find out why first. |
| a chain output is missing for any cube | INCOMPLETE, no verdict. |
| P1 holds | ScrollGT's in-sample coverage overstates the mask's recall on an unseen scroll. ScrollGT adds the eligible cubes as a `held_out` split, and the README quotes the drop. |
| P1 fails | no drop is visible in recall at tolerance 2 on Scroll 3. Say so plainly; the in-sample disclosure stands, but its practical cost is not shown. |
| P4 fails | the tracer's 512³ lead does not transfer to Scroll 3. ScrollGT's "ahead on 4 of 11" gets that context. |

Adding the eligible cubes to ScrollGT does not depend on the outcome. They are the only annotated fiber cubes the mask
did not train on.

## What the result cannot do

* Scroll 3 confounds an unseen scroll with unseen cubes, and both with a different scan. A drop there cannot be
  assigned to any one of them.
* Two Scroll-5 cubes are two cubes. Any statement about them is descriptive.
* Dataset004's annotations are newer than Dataset002's. If later annotations are more complete (finding 82: the
  revisions added 21–37% length), recall against them drops for that reason alone. The comparison should use current
  annotations on both sides, and it does. Whether annotation completeness differs between the two sets cannot be
  checked.
* The tracer is classical, so any change in its scores comes through the mask. It says nothing about a learned tracer.

## Cost

GPU, serial: per cube, about 5–10 minutes of `fiber_hz_vt` inference plus the trace (30–50 minutes at 512³, from
finding 80). About 6–8 hours in all, launched detached with `setsid nohup`. Scoring is CPU, about 2–5 minutes per 512³
cube.
