# Pre-registration: does the geometry/ink decoupling survive on current villa?

**Written 2026-09-11, before any arm is fitted.** Baselines already exist (`curbase_s1..s3`).

## Why this has to be re-measured

Four studies on villa-spiral `6847063f` found `satisfied_area` and `total_fg_pixels` moving
independently, and a corpus correlation of r = -0.121 (95% CI [-0.50, +0.30]) over 24 fits.

**Current villa recovers 67.6% more ink through a byte-identical scorer**
(`reports/current_code_baseline.md`). The geometry improved enormously. A relationship measured on
materially worse geometry may not hold on better geometry — the earlier corpus may simply have been
operating where the fit was too poor for satisfaction to track reading.

So the honest status of our headline result is: **measured on superseded code, unknown on current.**
Filing it without re-measuring would be presenting a stale claim as live.

## The manipulation

Repeat the **same-winding ablation**, which gave the cleanest previous result: empty
`same_windings.json` (5,413 constraints removed), everything else identical. Three arms
`nosamecur_s1..s3`, seeds 1-3, against the three existing `curbase` baselines.

Chosen over the patch-bootstrap repeat because it needs no dataset construction, `abs_winding.json`
stays intact so absolute numbering stays anchored, and it is the one whose old result was
*significant on geometry* (-0.69%, p=0.0027) rather than null — so it has something to fail to
reproduce.

## Endpoints and rule

* **Primary: `total_fg_pixels`** on w120-w129, Welch two-sided, alpha = 0.05, ABLATED vs `curbase`.
* **`satisfied_area_fraction` is REPORT-ONLY**, for the same reason as the original: the
  manipulation removes 5,413 of the inputs satisfaction is computed against, so a *rise* can mean
  "less left to satisfy". A *fall* is not subject to that confound.

| outcome | conclusion |
|---|---|
| ink null AND geometry falls | **The decoupling reproduces on current code.** The old finding generalises past the code it was measured on. |
| ink falls significantly | **The decoupling does NOT reproduce.** On better geometry the constraints do reach reading, and our earlier result was an artefact of a poorer fit. This would require retracting the generalised claim. |
| ink rises significantly | Surprising; needs a mechanism before belief. |
| both null | Weaker than before: the geometry effect itself failed to reproduce, so the study says nothing about decoupling. |

Power: at 3v3 and the previously measured outer CV of 0.0421, 80% power reaches **9.6%**. Note the
CV was measured on the OLD tree; if current code is less variable the true MDE is smaller, and if
more variable, larger. **The seed spread on the new baselines is 2.2%**, which is consistent with the
old floor rather than wider.

## Prediction, fixed now

**I predict ink null and geometry falls — the decoupling reproduces.** Reasoning: the mechanism we
proposed (satisfaction measures agreement with inputs, ink measures what the surface lands on) is not
obviously dependent on fit quality. But I hold this loosely: a 68% ink improvement upstream is
exactly the kind of regime change that can dissolve a relationship measured below it, and I have been
wrong on four of eight registered predictions.

## Cost

Three arms at the observed ~5h each on current code: **about 15 hours**. Control already exists.
Fits and renders both on villa `be09a8503`, whose only hot-path delta from the baselines'
`d8c5f488a` is inert for this pipeline (shell-dir-crop, never exercised).
