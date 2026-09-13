# The normal-displacement test ran as registered and is uninformative

**2026-09-13.** Registered in `docs/preregistration/2026-09-13_normal_separation_vs_agreement.md`.
**This is a failed test, not a null result**, and the distinction is the whole point of the report.
`scripts/measure_separation_vs_agreement.py`, `reports/separation_vs_agreement.json`.

## What was registered, and what it returned

Per (z, θ) bin: **separation** = |difference in the two arms' mean surface radius|, **disagreement** =
`|ink_A − ink_B| / (ink_A + ink_B)`, correlated by Spearman against a 1,000-shuffle null.

| pair | bins | median sep | ρ | p | registered verdict |
|---|---:|---:|---:|---:|---|
| `curbase_s1` vs `s2` | 5,194 | 3.6 vx | **−0.053** | 0.000 | opposite (surprise) |
| `curbase_s1` vs `s3` | 5,305 | 3.7 vx | −0.003 | 0.803 | not supported |
| `curbase_s2` vs `s3` | 5,122 | 3.7 vx | +0.016 | 0.243 | not supported |

By the registered rule that is **0 of 3 supporting** the normal-displacement mechanism.

## Why that verdict should not be believed

The median separation came out at **3.6 vx**, against the ~24 vx point-to-surface distance the anchor
gate measured between the same arms. That gap prompted a check the registration did not require:

> **Within-bin radial spread: 43.7 vx median, 95.8 vx at p90**, over ~103 surface points per bin.

**Each bin averages over a radial range twelve times larger than the difference being measured.** The
strip spans radius 2,337–2,466 across ten windings — about 13 vx per winding — so a (z, θ) bin at
96 × 256 contains points from **several windings at once**. Its mean radius is an average across
windings, and the difference of two such averages is not a measure of local sheet separation in any
useful sense.

The registration asserted "radius stands in for the normal: a spiral's sheet normal is predominantly
radial". That is true **per winding** and false for a bin that mixes windings, which is what these
bins do. The error is in the binning, not the geometry.

## So what is actually known

* **The tangential form of the surface explanation is refused** — `ink_offsets_are_not_coherent.md`,
  with a positive control showing the test detects a 3° coherent shift.
* **The normal form is untested.** This attempt does not bear on it either way, and the "0 of 3" above
  must not be cited as evidence against it.
* The one significant result, ρ = −0.053, is both tiny and produced by the confounded statistic. It is
  recorded because the registration said all three pairs would be reported whatever they showed, not
  because it means anything.

## What a real test would need

Surface separation measured **within a winding**, not across a bin that mixes them — nearest-point
distance between the two arms' meshes restricted to corresponding windings, which is what
`measure_winding_identity.py` already computes globally and would have to compute locally. The strip's
**row** index is the across-winding coordinate and was collapsed here; it should be a binning
dimension, not a summation axis.

## The pattern worth naming

This is the **third** time in this thread that a binning choice has driven a result:

1. the consensus fraction moved from 89.7% to 43.2% purely with bin size;
2. the strip-space within/between gap (p = 0.046) was an artefact of comparing in a frame each fit
   defines differently;
3. this test's separation statistic is confounded by within-bin winding mixing.

In the first two the binning was caught before publication. Here it was caught after the test had
already produced a verdict — and the only reason it was caught at all is that 3.6 vx did not match a
number measured elsewhere. **Cross-checking a statistic against an independently measured quantity is
what surfaced all three.**
