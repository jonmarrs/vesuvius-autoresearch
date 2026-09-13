# The objective is far more reproducible than the ink it counts

**2026-09-13. EXPLORATORY — not pre-registered.** Noticed while looking for work after the anchor
study closed, so it carries none of the protection a registered result does and should be read as a
lead, not a finding. `scripts/compare_ink_placement.py`, `reports/ink_placement_all_arms.json`.

## The question

villa's spiral loop optimises `total_fg_pixels` — a **count**. Every ablation we have run returns null
on that count. But a count says nothing about *where* the ink is: two fits could recover 2.9M pixels
in different parts of the scroll and the objective would not notice.

## What was measured

For each of nine current-code arms, the ink pixels per column of the flattened strip, summed over
rows, compared between arms at relative position with a lag search.

**Positive control passed first:** the profiles reproduce each arm's published `total_fg_pixels`
exactly (2,904,520 / 2,901,177 / 2,841,071 for the baselines).

| comparison | n | mean r | range |
|---|---:|---:|---|
| **within config** (same manipulation, different seed) | 9 | **0.655** | 0.564–0.711 |
| **between configs** (different manipulation) | 27 | **0.611** | 0.538–0.704 |

Welch t = 2.24, **p = 0.046** — so changing the constraints moves the ink barely more than changing
the RNG seed does.

## The finding, and it is about the within-config number

**Three fits differing only by RNG seed agree on the ink COUNT to 1.2% (CV 0.0124) while their ink
PROFILES correlate only 0.66.** Those are very different levels of agreement about the same
underlying object.

If that gap is real, then `total_fg_pixels` is a stable summary of an unstable thing, and a loop
optimising it is not necessarily optimising where the scroll is legible.

## The null, established on real profiles — because 0.66 means nothing without it

A correlation is only interpretable against what "no correspondence" scores. Destroying the
correspondence between two real arms while keeping their spectral content:

| comparison | r |
|---|---:|
| `curbase_s1` vs `curbase_s2` — **true pair** | **0.676** |
| vs the same profile **reversed** | 0.073 |
| vs the same profile **rolled half a strip** | 0.083 |
| vs **itself reversed** | 0.048 |
| vs **shuffled** | 0.028 |

**The null is ~0.05, so 0.66 is real agreement** — far above chance, and far below the ~1.0 that
identical placement would give.

This control was not optional. Building a synthetic fixture out of three sinusoids made two
*independent* draws correlate at **0.62** under the same lag search — indistinguishable from the
observed between-arm figure. Near-periodic signals are alignable in ways real ink profiles are not,
and had I validated only against that fixture I would have had no way to tell 0.66 from noise.

## Controls, because the method has an obvious failure mode

The strips differ in length by up to **3.6%** — each fit makes its own flattening — and a length
difference could depress correlation without any ink having moved.

* **Uniform stretch is fully absorbed.** A profile against a stretched copy of itself scores
  **r = 1.000** at every stretch from 0.5% to 5%, because resampling to relative position undoes a
  uniform scale exactly. This artefact is ruled out, not assumed away.
* **Local warping is not ruled out.** Reproducing r ≈ 0.63 by smooth non-uniform distortion needs an
  amplitude of about **0.2% of strip length, ~180 columns**. Whether the flattenings differ that much
  locally is **not established here**. For scale, the winding-identity gate measured seed-to-seed
  surface displacement of ~24 vx, which maps to roughly 14 columns — an order of magnitude less — but
  that displacement is predominantly *normal* to the surface, not along-strip, so it is not the right
  quantity and the comparison is indicative only.
* Lags found were **|lag| ≤ 9** of a 256 window, so the correlation is not being rescued by the lag
  search.

## What this does and does not support

**Supported:** the count is reproducible to ~1% where the profile agrees at ~0.66, and the obvious
confound (uniform length differences) is excluded by control.

**Not supported:** that the ink is genuinely in different places. A local flattening warp of ~0.2%
would produce the same number, and this analysis cannot separate the two.

**The test that would separate them** is comparing ink placement in *volume* coordinates rather than
strip coordinates — mapping each ink pixel back through the flattening to the scroll — which the
tifxyz meshes make possible and which this does not attempt.

## Why it is worth recording anyway

Every null we have published on `total_fg_pixels` inherits this. "Removing 5,413 constraints changes
reading by +0.28%" is a statement about a count whose relationship to *where* text is legible is now
an open question rather than an assumption.
