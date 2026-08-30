# Seed agreement: the flags are geometry, not optimizer noise

**2026-08-29.** The control pre-registered in
`docs/preregistration/2026-08-29_sheet_switch_detector.md`, run with the tool committed before the
second fit finished (`scripts/compare_switch_flags.py`, `2c72075c`).

## The question

A sheet switch is a property of the traced geometry. A flag that appears in one fit and vanishes in
another fit of the **same data**, differing only in `optimizer_random_seed`, is a property of the
optimizer. The pre-registered reading: agreement at or below chance means the detector is measuring
fit noise and the line of work ends, regardless of any later recall number.

## Result

Two fits, identical except `optimizer_random_seed` 1 and 2. Both converged: `satisfied_patches`
65.4% and 66.2%; fitted `dr` 16.173 and 16.206.

```
baseline01   flagged 1,773 / 35,318   (5.02%)
seed02       flagged 1,789 / 35,291   (5.07%)
shared patches  34,776
intersection     1,752                 (chance expectation 91.1)

observed Jaccard        0.9696
analytic chance floor   0.0263
permutation floor       0.0263   (p95 0.0307, max 0.0367 over 2,000 shuffles)
```

**98.8% of baseline flags reappear in the independent fit**, at 37x the chance floor. Flag rates
agree to 0.05 percentage points.

## What this establishes, and what it does not

**Establishes:** the detector's output is reproducible across independent fits of the same data. The
flagged set is determined by the geometry and the traced patches, not by the optimizer's random
seed. The control could have failed and did not.

**Does not establish** that the flagged regions are sheet switches. A systematic artefact of the
fitting procedure, or of the satisfaction metric's own target assignment, would reproduce across
seeds exactly as faithfully as a real defect. Reproducibility rules out noise; it says nothing about
what the reproducible thing *is*. This wording is from the pre-registration, fixed before the
numbers existed, and is not a hedge added afterwards.

**Still outstanding:** the injection study, which supplies known positives at known locations and is
the only handle available on recall.

## Standing against the pre-registered bar

Unchanged, and still failing. The frozen detector flags 5.02% of patches on the baseline against
rule 3's 5% conservativeness bar: **it fails by seven patches.** The seed-agreement result does not
touch that; a reproducible flag rate above the bar is still above the bar.

Recorded again here because this is the number a favourable-looking result makes easiest to forget.

## Provenance

Both caches were re-extracted with the committed `scripts/extract_winding_indices.py`, not the
scratch spike that produced the first baseline cache, so both sides of the comparison come from
inspectable code at a known commit. The first attempt at this run failed with
`ModuleNotFoundError: kornia`: the extractor imports villa's fit code and must run in the
**spiral-fitting** venv, while the detector and comparator need only numpy and run in the
autoresearch venv. That split is now in the runner's header comment.
