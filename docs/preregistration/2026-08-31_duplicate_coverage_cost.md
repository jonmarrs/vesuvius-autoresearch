# Pre-registration: does duplicate winding coverage inflate `total_fg_pixels`?

**Written 2026-08-31, before any metric has been computed on any arm.** Registered because the
prediction is mine and I want it falsifiable: I argued in
`reports/spiral_ink_objective_reachability.md` that `overall_fg_fraction` cannot see duplicate
coverage, and labelled that reasoning rather than measurement. This measures it.

## The claim under test

villa's `spiral-fitting/autoresearch.md` sets `total_fg_pixels` as the objective and names one
anti-gaming guard:

> if a change balloons `total_fg_pixels` only by inflating the surface with garbage geometry, the
> fraction will collapse

and classifies the resulting signature explicitly:

> A change that lifts both, or lifts total while holding fraction roughly steady, is a real win.

My argument: that reasoning holds for surface added over BLANK papyrus, and fails for surface added
over INKED papyrus already counted, because duplication raises numerator and denominator together.
If so, duplicated coverage produces the exact signature the doc calls a real win while recovering no
new text.

## Arms

All from the same 30,000-step baseline fit, same render and scoring settings, lasagna path.

* **A, baseline**: windings w010..w019, ten distinct windings.
* **B, duplicate**: the same ten, plus a second copy of w015 inserted as w015d. Adds rendered
  surface, adds NO new papyrus.
* **C, honest growth**: eleven distinct windings, w010..w020. Adds rendered surface AND new papyrus.

B and C add a comparable amount of rendered area. The difference is that C's addition is real.

## Predictions, fixed now

1. `total_fg_pixels`: **B > A**, by roughly the ink content of one winding.
2. `overall_fg_fraction`: **B is approximately A**, within the run-to-run spread. Quantified below.
3. C also raises `total_fg_pixels` and roughly holds the fraction. **If B and C are
   indistinguishable on both numbers, the metric pair cannot tell duplicated coverage from real new
   coverage**, which is the finding.

## Decision rule

Let `dT = (total_fg_pixels(X) - A) / A` and `dF = fg_fraction(X) - fg_fraction(A)`.

* **Claim SUPPORTED** if `dT(B) > +0.02` and `|dF(B)| < 0.02`. That is the doc's stated "real win"
  signature produced with zero new papyrus.
* **Claim REFUTED** if `dF(B) < -0.02`, i.e. the fraction does collapse and the guard works as
  described.
* **Claim UNRESOLVED** if `dT(B) <= 0.02`: the duplicate did not meaningfully raise the total, so
  the setup does not exercise the question and nothing is concluded.

The 0.02 thresholds are set before seeing any number and are not to be moved afterwards.

## Controls that can fail

* **Duplicate integrity.** `scripts/measure_winding_overlap.py` must report a large rise in
  gap>=2 duplicate coverage for B against A. If the duplicate does not actually overlap, B is not a
  duplicate and the run is void.
* **Arm C must differ from B in papyrus.** C's overlap must stay near A's 0.09%. If C also shows
  heavy duplication the arms are not distinct and the run is void.
* **Render alignment.** Every arm must render non-blank (`p95 > 0`). A black strip means the frame
  conversion failed and that arm is void, not a null.

## What this cannot show

One fit, one ten-winding span, one scroll, no repeats. A single duplicated winding is a crude stand
in for what an optimiser would do if it were exploiting this, and finding the signature here does
NOT show villa's loop has ever produced it. The satisfaction metrics, which the doc also directs the
loop to watch, are outside this test and might catch what the fraction misses.
