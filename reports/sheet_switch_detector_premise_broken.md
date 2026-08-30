# The detector's premise looks wrong, and the injection cannot ever validate it

**2026-08-30.** Written after the third injection attempt. This supersedes the "branch cut is ruled
out" conclusion in `reports/sheet_switch_baseline_signal.md`.

## The observation

Three injection designs, each fixing the previous one's flaw, all produce the same thing:

```
                    satisfied quads (median)   mean #windings   mean minority fraction
baseline                           293              0.950              0.0000
scan-space      k=1                126              1.017              0.0001
spiral-space    k=1                141              1.000              0.0000
anchor-fixed    k=1                164              0.967              0.0000
anchor-fixed    k=2                 26              0.917              0.0000
```

Displacement lands in band (3.54x dr in scan units, consistent with the transform's scale).
Satisfied quads collapse. **The minority fraction never moves off exactly 0.0000.**

## Why, from the metric's own construction

`get_patch_satisfied_areas` computes **one** target per patch, from the median valid column, and
accepts a quad only when its shifted radius is within `satisfaction_radius_tolerance` (0.45) of that
target in units of `dr`. Geometry displaced by a whole winding sits `1.0 * dr` away. It therefore
**cannot** be satisfied on the new winding; it can only fail.

The per-quad winding index is
`target_winding_idx = round((target_shifted_radius - cum_adj + branch_offset) / dr)`.
Neither `cum_adj` nor `branch_offset` is a property of where the surface *is*: both are theta-wrapping
bookkeeping, accumulated along columns and propagated across subrows by the branch BFS.

**So two winding indices among satisfied quads cannot arise from geometry sitting on two wraps.**
They arise from theta bookkeeping.

## Two consequences, both bad for this line of work

**1. The injection can never validate this detector.** Not because the harness is broken, but because
the condition it is asked to create is not reachable by displacing geometry. A displaced region
leaves the satisfied set instead of joining it on another winding. Three attempts failed for three
different-looking reasons and the fourth would too.

**2. A real sheet switch would behave the same way.** If displaced geometry cannot be satisfied on a
neighbouring winding, then a genuine switch in a fit would also show up as *unsatisfied*, not as a
second winding. The detector would not see it either.

## What this does to the earlier conclusions

**Superseded:** "the theta=0 branch cut is largely ruled out, because only 0.6% of minority regions
are full-height bands". That test assumed a branch cut must span the patch height. But `cum_adj`
accumulates along **columns** and `branch_offset` is per **subrow**, so wrapping bookkeeping can
produce localized regions too. The 0.6% figure does not exclude what I claimed it excluded.

**Still standing, and now more puzzling:** seed agreement of 0.9696 against a 0.0263 floor. Whatever
the flags are, they reproduce across independent fits. Theta bookkeeping is deterministic given the
geometry, so a bookkeeping artefact would also reproduce perfectly. That result never distinguished
the two, and its own write-up said so.

**Unaffected:** the extractor, the caching, the frozen detector's mechanics, and the 5.02% flag rate.
What changes is the *interpretation*: 7.4% of patches carrying two winding indices is most likely a
statement about theta wrapping, not about sheet switches.

## Status of the September bet

By the pre-registered rule 2, a detector that cannot be shown to beat its floors is not filed. Recall
cannot be measured, and the reason is structural rather than fixable with more harness work. **The
honest outcome is to file nothing on this, and to publish the negative.**

That is a real loss: about a day of work, a converged second fit, five tools and three reports, for a
detector whose premise does not survive reading the metric carefully enough. The cheapest version of
this lesson was available on day one by reading `get_patch_satisfied_areas` for what makes a quad
satisfied, before building anything.

## What would change the verdict

A demonstration that two satisfied quads in one patch can differ in winding index for a reason other
than `cum_adj` or `branch_offset`. That is a source-reading exercise, not a compute one, and it is the
only thing worth doing next on this line.
