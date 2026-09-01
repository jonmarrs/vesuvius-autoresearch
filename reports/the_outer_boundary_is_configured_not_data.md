# The fit's outer boundary is a config constant, not the end of the data

**2026-09-01.** Answers the question left open by
`reports/margin_arm_void_and_a_premise_withdrawn.md`, which withdrew the extrapolation explanation
for the outer-winding duplication and recorded "I do not know where the data ends". Now measured.

## Result

Radial extent of all 38,616 input verified patches, from their `meta.json` bboxes, against the
spiral centre (4348.8, 4844.4) used throughout this work:

```
max patch radius   6510
p99                3523
p95                3158

patches reaching radius 2376 (median radius of the duplication):  12,718  (32.9%)
patches reaching radius 2504 (median radius of output winding w129): 10,605  (27.5%)
```

The fit's outermost output winding sits at radius ~2504 by median. **Over a quarter of the input
patches extend beyond it, and the data reaches more than twice that radius.**

## What this settles

**Extrapolation is ruled out.** The outer output windings are not fitted past the end of the patch
data; the data continues well beyond them. The explanation withdrawn on 2026-09-01 is not merely
unproven, it is **wrong**, and the withdrawal was correct.

**The output bound is configured.** `config.py:489` sets `shell_outer_winding_idx = 130`, and
`spiral_helpers.py:1372` clamps the written range to it. The fit stops at w129 because it is told
to, not because it runs out of scroll. That also explains why the MARGIN0 arm could not move the
printed range: the clamp dominates the margin arithmetic entirely.

## What it does NOT settle

The duplication still concentrates at w124 to w129, and its cause remains unknown. This result
**changes the character of the boundary** rather than removing it: the outermost fitted windings
have unfitted data on their outer side, so they are a truncation boundary rather than a data
boundary. That is a plausible mechanism and it is **not** established here. I have proposed three
explanations for this concentration and two are now dead; a fourth offered without a test would be
worth no more than the others.

The obvious test remains what it was: fit with `shell_outer_winding_idx` raised, so the truncation
moves, and see whether the duplication moves with it. That is a single-variable config change on a
value the fit prints, and unlike the three mis-specified conditions before it, the observable
(where the output range ends) demonstrably responds to it. It has not been run.

## Limits

Patch bboxes are axis-aligned, so a corner radius slightly overstates a patch's true reach; the
conclusion does not depend on precision, since the margin is a factor of two rather than a few
percent. Radius is measured against one centre estimated from the fitted meshes. One dataset.
