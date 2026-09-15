# The spiral dataset's labels already sit on the surface — snapping has little headroom here

**2026-09-15.** A feasibility probe, run *before* designing any validation, because this project has
already built one study whose premise turned out to be unreachable
(`sheet-switch detector`, closed unbuilt-on). The rule taken from that: **ask whether the condition
can occur before pre-registering how to measure it.**

`scripts/probe_label_surface_offset.py`.

## The question

villa names label quality "one of the main unwrapping bottlenecks" and proposes **label snapping** —
moving approximate labels onto the most plausible surface using the CT signal. That presumes the
labels are *off* the surface. Are they, here?

## The signal, and why it is not circular

`lasagna_inputs/las_008_surf_sdt...respool_g1` (33 GB) is a surface signed-distance field derived
from CT. It is **independent of the spiral fit**, so using it avoids the circularity that made
`reports/patch_bootstrap_verdict.md` uninformative about label quality — that study selected on the
fit's own residual.

Patch labels are level-0 coordinates; the field is level 1, so indices are halved. Storage is a
custom sparse "respool" v2 (32³ bricks, a grid table of row indices, one flat `u8` file).

## Result

10–12 patches, ~3,500 surface points, against random points drawn from the **same stored bricks**:

| | IQR | median | within ±2 of 126 |
|---|---:|---:|---:|
| **labels** | **0.0** | 126 | **82–89%** |
| random | 6.0 | 130 | 27% |

**12× more concentrated, 3.1–3.3× enriched**, in a field spanning 0–167 whose own most common values
are 130 and 126. The labels are pinned to a single value.

**Read: the labels already lie on the surface this field encodes.** Snapping them has little to move.

## The statistic this probe got wrong first, and why it matters

The first version reported a standardised mean difference: **|d| = 0.066, "labels not distinguishable
from arbitrary voxels"** — which points at the opposite conclusion. That statistic is wrong for this
question. **Labels lying on a surface look like a spike, not a shift**, and a location statistic
pooled over variance discards exactly the concentration that carries the answer. The means genuinely
are close (126.3 vs 125.0); the distributions are not remotely alike.

Same family as an error made earlier the same day: reading a render's *resident* memory alone while a
third of it sat in swap. **Pick the statistic that matches the shape of the effect, not the one that
is conventional.**

## What this does and does not close

**Does:** for the spiral dataset's `verified_patches`, label snapping has little headroom at level-1
resolution. A study premised on "these labels are off-surface" would be measuring almost nothing.

**Does not:**

* **Sub-voxel offsets are invisible here.** The field is level 1 — half resolution. Villa's figures
  show drift "across fiber layers", which may live below what this resolves.
* **11–18% of label points are *not* at the modal value.** That minority is where any headroom is,
  and this probe does not characterise it. If snapping matters here, it matters there.
* **These patches are named `verified_`.** They may be the good labels by construction. Villa's
  concern explicitly includes human meshes and semi-automatic fiber traces, which are not this.
* **The `u8` encoding is inferred, not documented.** 126 is read as "on surface" because labels pile
  onto it; nothing here confirms the scale or zero point.

## Recommendation

**Do not start a label-snapping study on this dataset's verified patches.** The cheap version of the
question has been asked and the premise does not hold for the bulk of them.

If the direction is pursued, the two openings this probe leaves are (a) the **11–18% off-mode points**,
and (b) **full-resolution** data, where sub-voxel drift would be visible. Both are narrower and better
posed than the general question, which is the point of having run this first.
