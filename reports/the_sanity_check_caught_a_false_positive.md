# A registered validity gate caught a significant result that was an artefact

**2026-09-13.** Registered in `docs/preregistration/2026-09-13_separation_within_winding.md`.
`scripts/measure_separation_within_winding.py`, `reports/separation_within_winding.json`.

## What happened

The test correlated **local sheet separation** (3D distance between the two arms' fitted surfaces at
the same strip cell) against **local ink disagreement**, in the strip's own row/column grid — chosen
because the row index is the across-winding coordinate, fixing the winding-mixing confound that voided
the previous attempt.

It returned, on all three baseline pairs:

| pair | blocks | median separation | ρ | p |
|---|---:|---:|---:|---:|
| `curbase_s1` vs `s2` | 3,487 | 153.5 vx | **+0.209** | <0.001 |
| `curbase_s1` vs `s3` | 3,554 | 194.1 vx | **+0.181** | <0.001 |
| `curbase_s2` vs `s3` | 3,386 | 148.3 vx | **+0.245** | <0.001 |

**Positive ρ, highly significant, on every pair, in exactly the direction the mechanism predicts.**
That is the result I went looking for.

**It is an artefact, and the registration said so before the number existed.**

## The gate

The registration required the median separation to land in **10–30 vx**, on the grounds that two
independent measurements had already put the seed-to-seed surface offset at ~24 vx (anchor gate) and
14–18 vx (per-row radius difference), and that a value far outside that range would mean the frame was
still wrong:

> *If it comes back near 3 vx again, the frame is still wrong and the result is void — and it would be
> reported as void rather than as a null.*

It came back at **148–194 vx** — an order of magnitude high, and close to the strip's entire radial
span (~129 vx across ten windings). **Cells in the two grids are not describing the same place.**

## Why the artefact points the right way

This is the part worth keeping. Where the resampled grids misalign badly, cell *(i, j)* in one arm sits
on a **different winding** from cell *(i, j)* in the other. Both quantities then rise together for the
same trivial reason: separation is large because the cells are on different sheets, and ink disagrees
because they are different sheets. **A misalignment artefact produces exactly the correlation the
hypothesis predicts**, which is why "significant and in the predicted direction" was worth nothing
here.

## What went wrong with the frame

The premise I checked before registering — median radius per row correlates 0.957–0.973 between arms —
was **too weak**. Row profiles agreeing in aggregate does not make cell *(i, j)* correspond to cell
*(i, j)*. Proportional resampling maps relative position, and the strips are trimmed to different
bounding boxes, so a small relative offset crosses a winding boundary (~45 rows) and the comparison
silently changes sheets.

## Status of the question

* **Tangential** displacement: refused, with a sensitive positive control
  (`ink_offsets_are_not_coherent.md`).
* **Normal** displacement: **still untested.** Two attempted frames, both void. Neither the earlier
  "0 of 3 not supported" nor this "3 of 3 significant" bears on it.
* The observation that prompted all this is untouched: seeds agree on `total_fg_pixels` to 1.2% and on
  ink placement at r ≈ 0.70.

## What a third attempt would need

Correspondence established **in the volume, not by grid index** — for each cell of arm A, the nearest
point on arm B's surface, as `measure_winding_identity.py` already does per winding. That is a
KD-tree per winding rather than a grid resample, and it is the only version of this that does not rely
on two independently-trimmed grids happening to line up.

**I am not attempting it now.** Two voided frames in one thread is the point at which the honest move
is to stop and say the question is open, rather than build a third variant and hope.

## The lesson, which is about the gate and not the geometry

I have written many pre-registrations that fix a decision rule. **This one fixed a validity
threshold**, and that is what earned its keep: the decision rule would have said SUPPORTED, three
times over, at p < 0.001. The number that saved it was a sanity range taken from two independent
measurements of the same physical quantity.

*Register what the answer must look like to be believable, not only what counts as a yes.*
