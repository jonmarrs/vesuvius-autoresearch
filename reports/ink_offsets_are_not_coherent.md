# The ink offsets between seeds are not a coherent slide — the attractive story fails

**2026-09-13.** Registered in `docs/preregistration/2026-09-13_ink_offset_coherence.md`, whose
decision rule was committed before this number existed.
`scripts/measure_ink_offset_coherence.py`, `reports/ink_offset_coherence.json`.

## The hypothesis being tested

`reports/ink_placement_in_volume.md` found the between-seed ink disagreement has a characteristic
scale of tens of voxels, close to the ~24 vx seed-to-seed **surface** displacement measured
independently by the anchor gate. The attractive reading was that *the ink moves because the surface
moves*.

That report said two magnitudes agreeing is not a mechanism, and named coherence as the
discriminator: a continuous sheet displaced between two fits moves neighbouring regions of the scroll
together; independent detector noise does not.

## Result: no coherence

Angular shift best aligning one arm's ink to another's, per z-slice, then the lag-1 autocorrelation of
those shifts ordered by z. Null = the same statistic over 1,000 shuffles of the slice **order**, which
destroys adjacency while preserving the shift distribution exactly.

| pair | slices | lag-1 | null mean | p |
|---|---:|---:|---:|---:|
| `curbase_s1` vs `curbase_s2` | 24 | −0.025 | −0.044 | 0.597 |
| `curbase_s1` vs `curbase_s3` | 24 | −0.097 | −0.035 | 0.611 |
| `curbase_s2` vs `curbase_s3` | 24 | −0.130 | −0.046 | 0.724 |

**0 of 3 pairs coherent.** All three reported, as registered; none dropped.

## The null is meaningful, because the test is sensitive

A null from a blind instrument says nothing. Injecting a known smooth angular shift into one arm's own
map and re-running:

| injected amplitude | lag-1 | p | detected |
|---:|---:|---:|---|
| 2 bins (~2.8°) | 0.929 | <0.001 | **yes** |
| 4 bins | 0.962 | <0.001 | yes |
| 8 bins | 0.966 | <0.001 | yes |
| 16 bins | 0.649 | 0.001 | yes |

**The test detects a coherent slide of under 3 degrees.** The real offsets are nowhere near that
structured.

## What this rules out, and what it does not

**Ruled out:** the between-seed ink disagreement is a smooth *tangential* slide of the sheet. If the
surfaces slid past each other along the winding direction, this would have seen it easily.

**Not ruled out, and this is the honest limit:** the ~24 vx figure it was being compared against is a
**point-to-surface distance, predominantly NORMAL to the sheet**. A purely normal displacement moves
the surface through the volume without rotating it, changing *which voxels the detector samples*
without shifting ink angularly — and this test, which measures angular shift, is blind to that by
construction.

So the surface explanation is not dead; its *tangential* form is. Testing the normal form needs a
different statistic — ink agreement as a function of local surface separation between the two arms —
which this does not attempt.

## What it leaves standing

The measurement that started this is unaffected: seeds agree on `total_fg_pixels` to 1.2% while
agreeing on ink placement at r ≈ 0.70 in the scroll's own frame, with disagreement concentrated below
~50 vx. **What has changed is the explanation, not the observation.** The disagreement looks locally
independent rather than like a bulk displacement, which points toward per-region detector behaviour or
fine-scale surface differences, not a rigid shift.

## Prediction

None was registered, and that was the right call again: I found the surface story compelling enough to
write down as the likely mechanism, and the registered test refused it.
