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

---

## Addendum: the off-mode minority is not scattered — it sits further out

The probe named the 11–18% of off-mode points as the one opening it left. Characterising them
(14 patches sampled, 9 usable, ~9,500 resolved points):

**Not a few bad patches.** Off-mode fraction runs 0.044–0.253 with a median of 0.144 — every patch
carries some, none dominates.

**Not an edge artefact.** Points within 3 rows/columns of a patch's valid bounding box are off-mode at
**0.140**, the interior at **0.152** — edges are 0.92× the interior rate, if anything slightly cleaner.

**They are further out.** Against an axis *derived from the sampled points* (cx 3874, cy 5461):

| | n | radius median | radius mean |
|---|---:|---:|---:|
| on-mode | 8,062 | 1107 | 1126 |
| **off-mode** | 1,427 | **1209** | **1307** |

**d = +0.32**, observed gap **181 voxels** against a point-shuffle null whose p95 is **30 voxels**.

This coheres with two things already measured: patch satisfaction falls with radius (**r = −0.21**,
`reports/patch_bootstrap_verdict.md`), and selecting on satisfaction starves the outer windings *where
ink is scored* (`reports/SPIRAL_FINDINGS_SUMMARY.md`). **The labels that are off-surface are
concentrated where the reading happens.**

### The caveat that limits this

**The shuffle null overstates significance.** It permutes point labels independently, but points
within a patch are spatially correlated, so the effective sample is far smaller than 9,489. **Treat
`d = +0.32` as the honest summary and the p-value as decorative.** A patch-aware null is the right
test and was not run.

Also unchanged from above: level-1 resolution only, a ±2 off-mode threshold that is arbitrary, and
9 patches.

### What this does to the recommendation

The recommendation not to start a *general* snapping study stands — 85% of label points are already on
the surface, and moving them is moving nothing.

But the narrow question is now **better posed than when this probe began**: *do the outer-winding
labels, where reading is scored and where labels are measurably worse, repay snapping?* That is a
smaller study with a named population, a known endpoint (`total_fg_pixels` on w120–129), and a
plausible mechanism. It is the version worth registering, if the direction is pursued at all.

**I also had to correct myself mid-probe.** The first radius comparison used a hardcoded axis guess of
(4500, 4700). The derived axis is (3874, 5461), and the effect it gives is roughly twice the size. A
geometric claim resting on an unverified centre is not a measurement.

---

## Second addendum: the off-mode points are one voxel away — that is quantisation, not drift

Before proposing the narrow study above, the gating question was how far a snap would actually move a
label. For every off-mode point, the nearest voxel at the modal value was located by direct search
(±6 level-1 voxels, offsets ordered by distance so the first hit is the nearest):

| | level-1 voxels | level-0 voxels |
|---|---:|---:|
| median | **1.00** | 2.00 |
| p25 / p75 | 1.00 / 1.00 | 2.00 / 2.00 |
| p90 | 1.41 | 2.83 |

**100%** of off-mode points had an on-surface voxel within the search radius.

**The median is exactly 1.00, the smallest non-zero distance a voxel grid admits**, and p75 is also
1.00 — about three quarters of off-mode points are simply *adjacent* to an on-surface voxel. That is
what **discretisation** looks like: a label lying on the surface but falling the wrong side of a voxel
boundary reads as off-mode. Genuine drift — labels sitting in the wrong fibre layer, which is what
villa's figures show — would give larger and far more varied distances.

### This weakens the narrow study proposed above, and probably kills it

The first addendum proposed registering "do the outer-winding labels repay snapping?" on the strength
of the off-mode population being real and spatially concentrated. **It is spatially concentrated and
probably not real.** Snapping would move those points by one voxel, into an adjacent voxel that the
fit's own interpolation already spans.

It also supplies a competing explanation for the radius effect, and a duller one: surfaces at larger
radius meet the voxel grid more obliquely, so more of their points land off-voxel. **The radius
finding may be measuring grid geometry rather than label quality.** That was not tested and is not
distinguished by anything measured here.

### Standing conclusion

**Do not run a label-snapping study on this dataset at this resolution** — neither the general version
nor the narrow one. 85–91% of labels sit exactly on the surface, and the remainder sit one voxel off,
which is the resolution floor rather than an error to correct.

The only version that could still be live needs **full-resolution data**, where sub-voxel drift is
distinguishable from voxel-boundary rounding. That is a different dataset, not a different analysis.

**Recorded because it reverses my own proposal from an hour earlier.** The first addendum should have
asked how far snapping would move things *before* declaring the question well-posed — the same
ordering error the parent probe exists to prevent, repeated one level down.
