# Conservative fiber tracer: first real-data result (negative on raw CT)

**Date:** 2026-07-29
**Status:** tracer machinery validated; **blocked on input signal**, not on the tracer.

## Headline

On synthetic tubes the tracer is exact. On a real 7.91 um scroll cube, driven only by
classical Hessian vesselness from raw CT, it is **at roughly chance**: traced voxels land on a
hand-traced fiber with precision **0.026** against a base rate of **0.0126**, a lift of **2.06**.

That lift is not a coincidence. Measured directly, max-normalized vesselness separates
hand-traced fibers from background by a mean ratio of only **2.2** (0.0107 inside the label vs
0.0049 outside, at `gauss_sigma=1, sigma=2`; 2.68 at `gauss_sigma=2, sigma=4`). The tracer
inherits its input's discrimination and cannot exceed it.

**Conclusion: classical vesselness on raw scroll CT is not a good enough fiber detector to trace
from.** This is consistent with the project's own history: villa ships a *learned* semantic fiber
model (`fiber_hz_vt`) rather than a classical filter, and the open-problems post describes fibers
as both "a blessing and a curse" precisely because beam decohesion blurs them.

## What is validated and working

Synthetic three-tube volume (64³, radius 2, parallel along x):

| Property | Result |
| --- | --- |
| Instances recovered | **exactly 3 for 3 tubes** (no splits, no merges) |
| Length traced | ~63 of 63 possible voxels each |
| Tangent direction | \|x-component\| = **1.000** |
| Seeds tried | 3 (claim mechanism suppressed 957 redundant candidates) |
| Stop reasons | all `out_of_bounds`, i.e. ran off the cube as expected |

Anti-hallucination behaviours, all pinned by tests: a constant volume yields **zero** fibers;
pure noise traces under half the length of structured signal; two tubes 4 voxels apart are never
fused into one instance; every walk reports a termination reason; the confidence filter is
monotonic and non-mutating.

Ground-truth reader validated against the shipped labels: in-bounds NML nodes land on
semantic-positive voxels at **exactly 1.000** on both cubes checked, which is what pins the
(z, y, x) convention and the filename origin parsing.

## Two real bugs found along the way

1. **Orientation was returned in (x, y, z) while volumes index (z, y, x).** `hessian()` builds
   its matrix with index 0 <-> x, so raw eigenvectors come out reversed relative to array
   indexing. The tracer stepped along z while following a fiber running along x. It produced
   zero fibers and looked superficially plausible. `fiber_direction()` now reverses into
   (z, y, x) and a regression test compares against the raw eigenvector at the per-voxel
   argmin index.
2. **Trilinear sampling rejected coordinates like -5.7e-17.** A direction component that is
   mathematically zero produces a tiny negative float, which floors to -1 and reported
   out-of-bounds. This killed every walk seeded on a face of the volume.

## A design property worth stating

A **flat** response field carries no centre-line information. Seeding on a saturated or binary
semantic mask scatters seeds across each fiber's cross-section: on the three-tube volume a
perfect but binary mask gave **15 instances instead of 3**. Centre-line geometry has to come
from the Hessian. The tracer therefore separates the two roles: `response` gates continuation
(where fibers are), `seed_response` ranks centre-line-ness (where to start). Passing `volume`
builds the latter automatically. This is pinned by a test that asserts the over-splitting still
happens, so the docs cannot drift from the behaviour.

`seed_percentile` was added for the same reason. Because global vesselness discrimination is only
~2.2x, any absolute global threshold either admits most of the background or almost nothing: an
absolute `seed_threshold` of 0.3 found 17 seed candidates in a whole cube. Seeding at a
percentile **of the voxels inside the gate** asks the answerable question, "which voxels here
look most like a ridge centre".

## Leakage note (why the promising-looking number was discarded)

An intermediate run used the shipped `labelsTr` semantic label as the continuation gate and
recovered 22 fibers where ~24 ground-truth fibers intersect the sub-cube. That number is **not
reported as a result**, because `labelsTr` is a rasterization of the very NML skeletons being
scored against. Using it as tracer input is ground-truth leakage, and any ERL computed that way
measures nothing. It also revealed why the walks were short: the label is a ~1-voxel-wide
centreline rasterization, not a thick fiber mask, so a sub-voxel step off it terminates the walk.

The honest configuration is CT-only or a learned prediction, and the honest CT-only number is the
0.026 precision above.

## What would unblock this

The intended production path, already named in the August plan, is to **consume the published
semantic model instead of a classical filter**: `scrollprize/fiber_hz_vt` (an nnUNet trained on
exactly these hand traces), or one of `fiber_selftrain_teacher_epoch30`,
`fiber_dinoguided_2class_step010000`, `fiber_ink_4class_selfdistill`. All four are public on
Hugging Face. A learned probability map is also not flat, so it can plausibly serve as both gate
and seed field.

That requires nnUNet inference plumbing for these cubes, which is real work but is the
architecturally correct next step. The alternative, improving classical fiber detection to close
a 2.2x discrimination gap, is the thing the project already tried and moved away from.

## Cost note

The walk loop is pure Python and takes ~10 s per 128³ sub-cube. Fine for evaluation on 256³/512³
cubes, too slow for a whole scroll. Not worth optimizing until the input-signal question is
settled, since the inner loop may change.
