# Pre-registration: does the community `spiralcheck` evaluator see what our fits differ by?

**Written 2026-09-24, before spiralcheck was run on any of the twelve study fits.** Written from
`docs/preregistration/TEMPLATE.md`. Decision code `scripts/analyse_spiralcheck_validation.py`, tests
`tests/test_spiralcheck_validation.py`, both committed with this file.

## The question

spiralcheck (github.com/Nicodol/spiralcheck, v0.4.0, commit `d1b50e29`) is a community evaluator. Its
`intrinsic` mode checks a fitted winding family **without ground truth**. Along rays from the
umbilicus, in 10 z × 48 θ bins, it takes the radial gap between adjacent windings and counts:

* **violations:** gap ≤ 0;
* **collapsed:** gap < 0.2 × the median pitch;
* **inflated:** gap > 2.5 × the median pitch.

Its own VALIDATION.md held the fit seed fixed. So nobody has measured three things:

* how much its numbers move when only the fit RNG changes;
* whether it separates fit configs;
* whether it has anything to do with the ink a fit reads.

We have the data that can answer all three: twelve fits in three configs, each with a deterministic
ink score and villa's own `satisfied_area_fraction`.

**What changes with the answer.**

* If a metric tracks ink within a config, it is the first geometry measure we have that predicts
  reading. It would also be a cheap screen: ~5 s on CPU, against a ~40 min render.
* If it separates configs but not ink, it joins `satisfied_area` as geometry that does not
  transmit to reading.
* If it does neither, its sensitivity at this scale is below fit-seed noise. That is worth
  telling its author.

## Reachability — checked before designing

**Tool:**

* Installed at the registered commit (`uv sync --group dev`). It ran its demo and the clean twin.
* On `baseline01`, two repeat runs gave an identical `intrinsic` block, in ~5 s each.
* It parsed our umbilicus: 120 windings, 57,120 bins checked, median pitch 18.29 vx, 156
  violations. That fit is **not** one of the twelve.

**Arms:**

* All twelve fitted dirs exist.
* For every arm, the 10 scored windings (`w120`–`w129`, `_spliced`) are **byte-identical**
  (md5 of `x.tif`) to the meshes in its `detfit_*` work dir. So the geometry measured is exactly
  the geometry whose ink was scored.

**Which mesh variant:** spiralcheck's default `--variant spliced` loads `wNNN_spliced` where it
exists. That is what is rendered, so it is the primary input. It prints a warning that spliced
meshes embed the fit's input patches; that is expected and not a defect here.

## Arms (read-only; no fit, no render, no new data)

| fit tag | config | ink work dir |
|---|---|---|
| anchor10cov_pilot | anchor10cov | detfit_an1 |
| anchor10cov_s2 | anchor10cov | detfit_an2 |
| anchor10cov_s3 | anchor10cov | detfit_an3 |
| nosamecur_s1 | nosamecur | detfit_ns1 |
| nosamecur_s2 | nosamecur | detfit_ns2 |
| nosamecur_s3 | nosamecur | detfit_ns3 |
| curbase_s4 … curbase_s9 | curbase | detfit_s4 … detfit_s9 |

**Paths:**

* Fit dirs: `spiral_out/<date>_s1_slice-13056-18432_38442-patch_<tag>/meshes/fitted_<tag>`.
* Ink: `spiral_out/detfit_*/ink_metric/metrics.json` → `summary.total_fg_pixels`. These are the
  deterministic-flatten renders the pooled fit-only floor was measured on.
* Geometry: `satisfaction_metrics_fitted.json` in each run dir.

These twelve fits are the set of `reports/the_pooled_fit_only_floor.md`.

## Inputs, two scopes

* **all:** the whole fitted dir, 120 windings. This is how a user would run the tool. Used for
  Q1, Q2 and Q4.
* **scored:** a directory of symlinks to `w120_spliced_<tag>` … `w129_spliced_<tag>` only. These
  are the ten windings that are rendered and scored. Used for Q3. Satisfaction falls with radius
  (r = −0.21), so a family-wide number can miss the scored region; that is why Q3 uses this scope.
  spiralcheck re-derives its z bins from the subset's own extent, which is intended.

Each input is run **twice**. Parameters are the tool's defaults (`theta_bins` 48, `z_bins` 10,
`collapse_frac` 0.2, `inflate_frac` 2.5), plus our `umbilicus.json`.

## Metrics (four)

* `violated_bin_fraction`
* `collapsed_bin_fraction`
* `inflated_bin_fraction` = `n_inflated / n_bins_checked`
* `median_pitch`

## Decision rule (implemented in `decide()`)

**Gates (run first):**

* **Partial sample:** fewer or more than the twelve fits, or group sizes other than 3/3/6 → refuse
  (exception).
* **Instrument:** if any input's two runs differ → **INSTRUMENT NONDETERMINISTIC**. No Q1–Q3
  verdict is issued.

**Q1, seed noise (reported, no verdict):** the pooled within-config sd, df 9, for each metric in
both scopes.

**Q2, config separation, scope all:** a one-way ANOVA F(2, 9) per metric, Bonferroni α = 0.05/4 =
**0.0125**.

| outcome | verdict |
|---|---|
| p < 0.0125 | SEPARATES CONFIGS |
| otherwise | DOES NOT SEPARATE |
| identical on all 12 | UNINFORMATIVE (not a null) |

**Q3, tracks ink within config, scope scored:** Pearson r of metric vs `total_fg_pixels`, both
config-centred, df = 12 − 3 − 1 = **8**, α = 0.0125, so the critical **|r| = 0.750**.

| outcome | verdict |
|---|---|
| p < 0.0125 | TRACKS INK (+/−) |
| otherwise | NO DETECTED RELATION |
| identical on all 12, or no within-config variation | UNINFORMATIVE |

**Q4 (descriptive, no verdict):** config-centred r of each scope-all metric vs
`satisfied_area_fraction`. This asks whether the two geometry measures agree.

**Headline:**

| condition | headline |
|---|---|
| any Q3 metric TRACKS INK | **READING-RELEVANT** |
| else any Q2 metric SEPARATES | **GEOMETRY-ONLY** |
| else | **NOT DISCRIMINATING HERE** |

## Predictions, fixed now

1. **Q1:** all four metrics vary between seeds in scope all. **Confidence moderate:** the fit RNG
   moves the scored surface enough to re-draw ~7% of the ink.
2. **Q2:** **withheld.** The ablations remove constraints whose effect on inter-winding *spacing* I
   cannot reason to. villa's satisfaction moved in the direction our own registration had called
   uninterpretable, which is a warning against guessing.
3. **Q3:** **NO DETECTED RELATION on all four; headline not READING-RELEVANT. Confidence
   moderate.**
   * Six registered geometry manipulations have never moved ink.
   * Placement instability comes from the fit, but it is a *placement* change of the ink, not a
     change of the winding spacing.
   * My last five magnitude predictions missed, so no magnitudes are predicted.

## What the result cannot do — computed now

* **A Q3 null excludes only strong relations.** At df 8 and α 0.0125 it takes |r| ≥ 0.750 to
  register. Any relation weaker than that is not excluded. A null does not say spiralcheck is
  irrelevant to reading.
* **It validates sensitivity and consistency, not correctness.** There is no positional ground
  truth on this region (`column-metric-line-closed`). A violation count is not shown to mark a real
  error.
* **Four metrics per question with Bonferroni** means a single p just under 0.0125 is thin. The
  report quotes r and p, not only the verdict.
* **Config differences could come from one pathological fit.** The report prints per-fit values
  for every metric.

## Limits

* One scroll region (s1 slice 13056–18432), one umbilicus, one tier of villa code, twelve fits.
* spiralcheck at one commit and its default thresholds.
* Ink is `total_fg_pixels` from one nnU-Net scorer. Its fit-only floor is 0.074 [0.051, 0.134],
  pooled, df 9.

## Cost

CPU only: 12 fits × 2 scopes × 2 runs × ~5 s ≈ 4 min. No fit, render or new data. It can run
alongside anything.

### Before running

- [x] spiralcheck HEAD == `d1b50e29` (checked in `collect`, which refuses otherwise)
- [x] arms byte-identical to the scored meshes (md5 over the 10 scored windings, 12/12)
- [x] rule and tests committed before the first `collect`
