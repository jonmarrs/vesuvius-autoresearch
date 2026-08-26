# villa's spiral-fit satisfaction metric cannot see a whole-winding displacement, at any magnitude

**Bottom line.** `get_patch_satisfied_areas` — the function villa uses to decide whether a
patch is "satisfied" by a fitted spiral — scores a patch moved exactly one whole winding off
its true position *identically* to the correctly placed patch. Measured delta in satisfied-quad
fraction: `+0.000000e+00`. The blindness is not a one-winding special case: it is periodic in the
displacement's distance from the nearest integer winding, and indifferent to the displacement's
magnitude. A patch displaced by 23.8006 windings — roughly 305 voxels, at the real measured
winding spacing — scores identically satisfied (`1.000000`) to the correctly placed patch,
because it lands only 0.1994 of a winding from the nearest integer, while a patch displaced by
exactly half a winding is rejected outright (`0.000000`) regardless of how small that
displacement is in absolute terms (§2, §7). That is the "sheet switch" failure mode villa's own
`scrollprize.org/docs/37_2026_open_problems.md` bottleneck table lists fourth ("Meshes can jump
from one wrap to another"), and for which that same row asks for "stronger local continuity
constraints and **conservative failure detection**". The metric is not a conservative failure
detector for this mode; it is exactly blind to it, across the full displacement range measured.

The mechanism is that the metric derives its target from the patch's *own* position. It takes
the patch's median shifted-radius and snaps it to the nearest integer winding
(`satisfaction_metrics.py` lines 242-248), then checks two residuals against that
self-derived target. Absolute winding annotations do exist in the codebase and are load-bearing
in the fit — `losses.get_patch_abs_winding_loss` selects point collections on
`metadata.winding_is_absolute` (line 1059) and is called from `fit_spiral.py` at lines 2720 and
3373 — but `satisfaction_metrics.py` never reads them. Ground truth is consumed by the fit and
never used to score it, so the score cannot distinguish "on the right wrap" from "on a wrap".

**The blindness is exact for a patch lying on a winding. It is not unconditional for a noisy
one.** For a well-placed patch the result is an algebraic identity (§1) and holds at every scale,
every measured displacement ratio, both of villa's configurations, and across the theta=0 seam.
Once the patch carries scatter, counterexamples appear: §4 reports the one pinned-grid cell where
villa's verdict changes under smooth nonlinearity, and Limits 7 reports the substantially larger
break under warps built from real measured winding spacings — 5 of 40 rays disagree at 4 voxels of
scatter and 8 of 40 at 6 voxels, with max |Δ| reaching 0.284848, some 6.7× the smooth sweep's
worst case. Two gaps this report originally left open — whether real-scale scatter alone starves
the correctly placed patch, and whether the blindness holds across the full measured displacement
span — are closed in §7 in the direction that strengthens the finding. The scatter-plus-real-warp
cell is the one that cuts the other way, and it is reported in Limits 7 rather than buried.

§8 now locates that break precisely instead of bracketing it: under the empirical warp and the
reporting configuration, the satisfied fraction first moves at 2.50 voxels of patch scatter, a
patch verdict first flips at 3.25, and the correctly placed reference itself first fails at 4.00
(per-ray median 3.75, `reports/spiral_satisfaction_onset.txt`). §9 measures what real traced
patches actually carry at the comparable window: median 0.846 voxels, p95 2.179, with only 0.82%
of windows at or above the verdict-flip onset (`reports/real_patch_scatter.txt`).

⚠ **CORRECTED 2026-08-25.** This paragraph previously concluded that real patches "therefore sit
below the threshold at which this report's own counterexamples start to appear". **That comparison
was made on unlike terms and the conclusion does not survive it.** The onsets above were measured
with INDEPENDENT per-point Gaussian noise. Real patch residuals are not independent: measured on
the same patches, their lag-1 autocorrelation across the grid has median **+0.357**, positive in
**73.2%** of windows, where white noise would sit near zero
(`reports/spiral_satisfaction_correlated_scatter.txt`).

Noise shape matters at equal magnitude, and it matters in the unfavourable direction. Swept at
identical RMS over the same 40 rays, the first level at which any patch verdict flips is **3.5
voxels for independent noise and 1.5 voxels for correlated noise**. At 2.5 voxels RMS the
independent arm flips nothing while the correlated arms flip 6 of 40. Real patch scatter has p95
**2.179 voxels**, which is inside that band, not below it.

So the honest statement is weaker than the one this paragraph originally made: real patches sit
below the onset **as measured with white noise**, and within the range where **correlated** noise
of their own measured magnitude already flips verdicts on a minority of rays. The threshold is
real, it is measured rather than bracketed, the §4 verdict-flipping cell still stands, and whether
real patches clear it is now **unresolved** rather than answered favourably.

**What villa already has.** `find_inconsistent_windings.py` in the same directory *does* derive a
patch's expected absolute winding by propagating `winding_is_absolute` annotations across the
patch graph — the very remedy this report ends by pointing at. It is a standalone debug tool,
invoked manually one `--patch-id` at a time, and it is wired into neither the fit loop nor the
scored metric. So the annotation-propagation machinery exists; what does not use it is the
metric. See Limits 8.

**What this is not.** This says nothing about how often real spiral fits actually misplace a
patch by a winding, and it is not a claim that any published fit is wrong. It is a statement
about what one metric can and cannot detect. Everything below was measured on synthetic patches
scored by villa's real, unmodified function; no fitted spiral checkpoint is published anywhere
under `dl.ash2txt.org/datasets/spiral_datasets/`, so no real *fit* was ever run in this
investigation.

Scored against villa pinned at `ced62390e`, where spiral fitting lives at
`villa/volume-cartographer/scripts/spiral/`. Upstream moved it to a top-level `spiral-fitting/`
directory in PR #1548 on 2026-08-21; our pin predates that, so every path cited here is the
pinned one.

---

## Pre-registered contract

From `docs/superpowers/plans/2026-08-24-spiral-satisfaction-winding-probe.md`, verbatim:

> **Hypothesis (H1).** `get_patch_satisfied_areas` is invariant under a displacement of exactly
> one winding. A patch moved onto the adjacent wrap scores the same satisfied-quad fraction as
> the correctly placed patch.
>
> **Primary outcome.** `satisfied_quad_fraction` for the displaced patch minus the same quantity
> for the reference patch.

| Result | Interpretation |
| --- | --- |
| \|Δ satisfied fraction\| ≤ 1e-6 **and** the control in Task 3 shows a drop > 0.5 | **H1 confirmed.** The metric is blind to one-winding displacement. Finding is real; proceed to write it up. |
| \|Δ satisfied fraction\| > 1e-6 | **H1 falsified.** The metric detects the displacement. Report the negative, drop the lane, do not publish a claim. |
| Control shows no drop | **Probe is uninformative.** The instrument is not exercising the metric at all. Fix the harness before interpreting anything. |

**Outcome: H1 confirmed.** Δ = `+0.000000e+00` (row 1 of the gate), and the control drops from
1.000000 to 0.000000 — a drop of 1.0, well past the required 0.5.

**Limitation on the pre-registration, stated up front.** The plan says "It must be committed
**before** any measurement in Task 2 or later runs." It was not. The plan commit is `3732f360`
(2026-08-24 08:31:45 -0700); the first two measurement commits are `81a86b78` (08:18:04) and
`25e6b538` (08:25:57). What is true is that the gate text was fixed in the dispatched task
briefs before those runs — `.superpowers/sdd/.../task-2-brief.md` was written at 08:08:14 and
`task-3-brief.md` at 08:22:13, both preceding the commits they governed — but that is a
filesystem timestamp on an untracked working file, not a git-history guarantee. Read the
pre-registration as *stated in advance and recorded late*, and weight it accordingly. There is
no argument that repairs this; it is a process defect in a run whose whole point was
pre-registration discipline.

Sources for every number below, all committed on branch `probe/spiral-satisfaction-winding`:
`reports/spiral_satisfaction_winding_probe.txt`,
`reports/spiral_satisfaction_winding_robustness.txt`,
`reports/real_winding_nonlinearity.txt`,
`reports/spiral_satisfaction_realscale.txt`. §7's numbers come from
`reports/spiral_satisfaction_untested_cells.txt`, committed on branch
`probe/spiral-winding-untested-cells` (commits `2b73bbb9`, `5726b809`). §8's numbers come from
`reports/spiral_satisfaction_onset.txt` (commit `7ae060d5`), and §9's from
`reports/real_patch_scatter.txt` (commit `ebeb9235`).

---

## 1. The invariance is exact, and provable

For a patch lying exactly on a winding, this is not an empirical near-miss — it is an algebraic
identity, and it holds for *any* invertible scan↔spiral transform `T`.

Displace the patch by one winding's worth of spiral-space radius `delta`, at fixed theta and z.
The displaced patch is

    p' = T_inv(T(p) + delta)

The metric's own snap-target for `p'` lands at exactly `T(p) + delta`, which `T_inv` maps back
to exactly `p'`. The scan-space distance the metric checks is therefore 0 both before and after
the displacement, and `T` cancels out of the comparison entirely. The spiral-space residual
cancels for the same reason: adding `dr` to every point's shifted radius adds `dr` to the
median, which adds `dr` to the snapped target, leaving `adjusted_shifted - target_shifted_radius`
unchanged.

Confirmed numerically at every scale tested (`spiral_satisfaction_realscale.txt`, Experiment A):

| dr | spiral_tol | scan_tol | ref combined | displaced combined | Δ combined |
| --- | --- | --- | --- | --- | --- |
| 100.00 | 45.0000 | 6.0000 | 1.000000 | 1.000000 | +0.000000 |
| 50.00 | 22.5000 | 6.0000 | 1.000000 | 1.000000 | +0.000000 |
| 25.00 | 11.2500 | 6.0000 | 1.000000 | 1.000000 | +0.000000 |
| 12.81 | 5.7645 | 6.0000 | 1.000000 | 1.000000 | +0.000000 |
| 8.04 | 3.6180 | 6.0000 | 1.000000 | 1.000000 | +0.000000 |

Worst-case |Δ combined| across the scale sweep: `0.000000`. The blindness is scale-invariant,
and in particular is not an artifact of the arbitrary `dr = 100` the first probe happened to
use.

## 2. The control — what makes the null mean anything

A null from an instrument that cannot produce a non-null is worthless. The metric *does* reject
fractional displacements, and the same harness that reports the null reports the rejection
(`spiral_satisfaction_winding_probe.txt`, dr = 100, winding 5):

| displacement (windings) | satisfied fraction |
| --- | --- |
| 0.00 | 1.000000 |
| 0.25 | 0.000000 |
| 0.40 | 0.000000 |
| 0.50 | 0.000000 |
| 0.60 | 0.000000 |
| 0.75 | 0.000000 |
| **1.00** | **1.000000** |
| **2.00** | **1.000000** |

The signature is periodicity in `dr`: every fractional offset is rejected outright, every
whole-winding offset is accepted in full, including two whole windings. The harness is
exercising the metric.

## 3. Both satisfaction conditions are independently fooled

The metric ANDs two checks: a spiral-space radius residual against
`satisfaction_radius_tolerance = 0.45` (in units of `dr`) and a scan-space distance against
`satisfaction_distance_tolerance = 6.0` (absolute voxels). Both values are read from villa's own
`metrics_config` **by the computation**; the header line of
`reports/spiral_satisfaction_winding_probe.txt` restates them as typed text (see the process
section, residual instances). If only one were fooled while the other saturated, the combined null would be
an artifact. It is not. Separating them (via villa's own `metrics_overrides` hook, neutralizing
one tolerance at a time rather than reimplementing villa's math) gives, at dr = 100:

| displacement (windings) | spiral | scan | combined |
| --- | --- | --- | --- |
| 0.00 | 1.000000 | 1.000000 | 1.000000 |
| 0.25 | 1.000000 | 0.000000 | 0.000000 |
| 0.40 | 1.000000 | 0.000000 | 0.000000 |
| 0.50 | 0.000000 | 0.000000 | 0.000000 |
| 0.60 | 1.000000 | 0.000000 | 0.000000 |
| 0.75 | 1.000000 | 0.000000 | 0.000000 |
| **1.00** | **1.000000** | **1.000000** | **1.000000** |
| **2.00** | **1.000000** | **1.000000** | **1.000000** |

At a whole winding both conditions pass independently. The null is not one gate masking another.

Two details in this table are worth naming because a critic will find them. The spiral condition
rejects only a narrow band around the exact half-winding: with a tolerance of `0.45*dr`, only
offsets whose distance to the nearest integer exceeds 0.45 are rejected, so 0.25, 0.40, 0.60 and
0.75 all pass it. And the 0.50 row rejects rather than sitting on a boundary because villa's
snap uses a strict `modulus < dr/2` (line 244), so an exact half-winding tie snaps *up*, giving
a residual of 50 against a tolerance of 45. That is a real boundary behaviour in villa's code,
not a harness artifact.

## 4. Robustness: scatter and nonlinearity

The exactness argument in §1 assumes a patch lying exactly on a winding. A real patch has
scatter and sits some nonzero distance `d` from its winding, and for a *nonlinear* `T_inv` the
post-displacement comparison

    ||T_inv(target + delta) - T_inv(T(p) + delta)||   vs   ||T_inv(target) - T_inv(T(p))||

need not be equal, because the deformation stretches space differently at different radii. That
is the only mechanism by which the finding could weaken, so it was swept directly
(`spiral_satisfaction_winding_robustness.txt`): patch scatter (Gaussian on spiral-space radius,
std = `scatter_std_frac * dr`, one fixed seeded draw reused at every level so reference and
displaced patches share identical noise) crossed with `RadialPowerLawTransform`
`s = r0*(r/r0)**alpha` at `r0 = winding*dr = 500`, exact closed-form inverse. `alpha = 1.0`
dispatches to the real `IdentityTransform`.

Δ combined, by cell:

| scatter \ alpha | 1.00 | 0.95 | 0.90 | 0.80 | 0.60 |
| --- | --- | --- | --- | --- | --- |
| 0.00 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| 0.01 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| 0.02 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| 0.05 | +0.000000 | +0.000000 | -0.006061 | -0.018182 | -0.042424 |
| 0.10 | +0.000000 | +0.000000 | -0.012121 | -0.018182 | -0.024242 |

Degradation requires *both* knobs. Δ is exactly zero in every cell where scatter is 0 (any
alpha) or alpha is 1.0 (any scatter), matching the algebra. Worst case on the pinned grid:
`|Δ| = 0.042424` at scatter 0.05, alpha 0.60.

`ref_spiral` and `disp_spiral` are `1.000000` in every row of this sweep: at dr = 100, all
degradation is in the scan condition. §6 corrects the reading we first drew from that.

### One cell in the pinned grid *does* flip villa's verdict

This is the sweep's real bound on the finding, and it is a counterexample to unconditional
blindness, so it gets its own heading.

Δ in satisfied *fraction* is not what villa acts on. villa's patch-level rule
(`satisfaction_metrics.py:317`) is `num_satisfied_quads >= satisfied_patch_quad_fraction *
total_valid_quads` — integer quad counts against a threshold. The swept patch is 12x16 points,
so 11 x 15 = **165** valid quads, and the default threshold is `0.95 * 165 = 156.75` quads.
Applying that rule to every cell of the sweep, computed by `verdict_flips()` in
`scripts/probe_spiral_satisfaction_robustness.py` and printed in the artifact:

| cell | reference | displaced | Δ combined | verdict |
| --- | --- | --- | --- | --- |
| scatter 0.05, alpha 0.80 | 0.963636 = 159/165 → **satisfied** | 0.945455 = 156/165 → **not satisfied** | -0.018182 | **FLIPS** |

**One of 25 cells flips.** Under combined scatter and nonlinearity at that setting, villa's
metric does report the one-winding-displaced patch as unsatisfied while reporting the correctly
placed one as satisfied. The blindness is not unconditional once both knobs are on.

The reasoning trap here is worth naming, because this report previously fell into it: **|Δ| is
not a proxy for whether the verdict changes.** The flip happens at Δ = -0.018182 — *less than
half* the grid's worst-case Δ. What decides a flip is proximity to the threshold, not the size
of the delta. The alpha = 0.60 cells have larger Δ and do not flip only because both of their
arms already sit far below threshold (136/165 and 129/165 at scatter 0.05). An earlier draft of
this document argued from the worst-case Δ that no verdict could flip; that inference was
invalid and its conclusion was false. See the process section.

Two things this cell does not establish. It is one cell of a 25-cell synthetic grid, not a rate.
And it is a flip under the *reporting* configuration. The splicing configuration that actually
gates the output mesh (Limits 3) does not reproduce it.

⚠ **CORRECTED 2026-08-25.** This paragraph previously argued the flip would not occur under
splicing because "148.5 quads, which both 159 and 156 clear", while noting that the looser
tolerances would also change the fractions themselves and that we had not measured it. That
caveat was well placed: the reasoning was wrong. 159 and 156 are the *reporting* configuration's
quad counts, and comparing them against the *splicing* threshold mixes two configurations.
Measured properly (`reports/spiral_satisfaction_splicing_and_seam.txt`, section C), under
splicing both arms score **165/165** against a 148.50-quad threshold — not 159 and 156. The
conclusion is unchanged, the flip does not recur there, but it holds because the looser
tolerances satisfy *every* quad in both arms, not because two borderline counts clear a lower
bar.

**The bound is real and the invariant does break past it.** Informal, **unpinned** probing one
step beyond the grid (scatter 0.02, alpha 0.20) found Δ combined around **-0.36**, roughly 8x
the pinned worst case. This is disclosed in the committed sweep artifact itself. The sweep
establishes that the invariance survives smooth nonlinearity down to alpha = 0.60; it does not
establish anything about alpha below that.

### The contrast that may be the single most persuasive fact

At scatter 0.10, alpha 1.00 — a *correctly placed* patch, with noise — the combined satisfied
fraction is **0.769697**, below villa's own `satisfied_patch_quad_fraction = 0.95`. That patch
is reported as not satisfied. A *clean* patch a whole winding out of place scores **1.000000**
and is reported as satisfied. Under this metric a correctly-placed noisy patch can fail while a
cleanly-placed wrong-wrap patch passes.

## 5. The real field

To find out whether alpha = 0.60 is a conservative or a generous stand-in for the real
scroll, the actual inter-winding geometry of PHercParis4 was measured from the published
`winding_model/` product (7 shards, sha256-verified against each shard's `manifest.json`;
1.46M rays, 26.7M crossings). Consecutive crossings on one ray at adjacent winding levels give
the real local inter-winding spacing (`real_winding_nonlinearity.txt`).

**Inter-winding gap** (scale-0 voxels, n = 25,283,382): min 2.6662, p05 **8.0441**, p25 10.4326,
p50 **12.8099**, p75 16.3058, p95 25.1224, max 163.2435. Per-shard medians span 11.32-16.74.

**Adjacent-gap ratio** `g[k+1]/g[k]` (n = 23,823,211): min 0.0446, p05 **0.7171**, p25 0.8939,
p50 **0.9985**, p75 1.1155, p95 **1.3799**, max 23.8006. Per-shard medians all within
0.9837-1.0060. 21.6330% of ratios fall outside [0.8, 1.25]; 0.9990% fall outside [0.5, 2.0].

Read plainly: the real field is close to uniform in the middle but carries real, substantial
*local* spread. That spread is a different perturbation from the smooth power-law warp §4 swept,
and §6 records the consequence.

**The equivalent-alpha number is deliberately not quoted as a result.** The measurement report
does derive one (median 0.1171, IQR 0.0630-0.2582) by fitting a local power law per crossing
triple in the same convention the sweep used, but it must not be read as "the real field's
alpha", for two reasons stated in the artifact itself. First, it is strongly
convention-sensitive: stratified by absolute local winding number `n0`, the median falls
monotonically from 0.3310 (n0 < 20) to 0.0798 (n0 in [100, 200)) with *no change in the
underlying ratio noise* — the convention (`r0 = n0*D`, one-winding step) simply makes the modeled
ratio less sensitive to alpha as `n0` grows. Second, roughly half the population is
unresolvable: 11,371,061 of 23,823,211 ratios could not be inverted, and 98.4% of those sit
*below* the model's floor, i.e. the observed gap shrinks by more than even maximal compression
in this convention can produce. That points at local fiber waviness and winding-inference noise
rather than a smooth global drift — which is to say the power-law model is the wrong shape for
this data, and a statistic derived from the wrong shape should not be the headline. The raw
adjacent-gap ratio distribution above is the directly observed, convention-free quantity and is
the trustworthy one.

## 6. At the real scale, the finding is stronger, not weaker

Two things about the original sweep did not match the measured field, and both were corrected
(`spiral_satisfaction_realscale.txt`).

**Scale.** The real median inter-winding gap is 12.81 voxels. villa's scan tolerance is 6.0
voxels *absolute*. So on the real scroll the scan acceptance band is roughly 47% of the winding
spacing. Our original probe used dr = 100 against the same 6.0, i.e. 6% — about 8x stricter than
reality. We were testing the metric under conditions far harsher than the ones it actually
operates in.

**Which condition binds flips at the real scale.** This is the self-correction. Three times
during this investigation we wrote that villa's spiral-space condition "barely discriminates" or
"contributes nothing", on the strength of §3's table. That was an artifact of `dr = 100`. The
spiral tolerance is `0.45*dr` — it *scales* — while the scan tolerance is `6.0` voxels —
*absolute*. Which one binds depends entirely on `dr`, and the crossover sits inside the real
range. From Experiment A's `tighter_tol` column:

| dr | spiral tol (0.45*dr) | scan tol | numerically tighter |
| --- | --- | --- | --- |
| 100.00 | 45.0000 | 6.0000 | scan |
| 50.00 | 22.5000 | 6.0000 | scan |
| 25.00 | 11.2500 | 6.0000 | scan |
| **12.81** (real p50 gap) | **5.7645** | 6.0000 | **spiral** |
| **8.04** (real p05 gap) | **3.6180** | 6.0000 | **spiral** |

At the real measured gap the **spiral** condition is the tighter of the two, not the vestigial
one. The earlier claim is withdrawn.

That column is a comparison of villa's two tolerance *constants*, not an observed pass/fail
split: scatter is held at zero throughout Experiment A, so neither condition is empirically seen
rejecting anything (every `ref_*` and `disp_*` cell reads 1.0). The report says so on its own
face.

**Displacement shape.** In reality, "move to the adjacent wrap" means moving by the *local* gap,
not by the nominal `dr`. Experiment B holds `dr` at the real 12.81 and sweeps the displacement
across the measured ratio distribution — five values drawn from the measured quantiles (p05
rounded to 0.72, p25 0.8939, p50 0.9985, p75 1.1155, p95 rounded to 1.38) plus the two edges of
the [0.8, 1.25] band the ratio report characterises. (The realscale artifact's prose calls all
seven "quantiles"; 0.80 and 1.25 are band edges. The script's own comment is precise; the
narrative line is loose. Noted rather than papered over.)

| ratio | displacement (vox) | ref combined | displaced combined | Δ combined |
| --- | --- | --- | --- | --- |
| 0.7200 | 9.2232 | 1.000000 | 1.000000 | +0.000000 |
| 0.8000 | 10.2480 | 1.000000 | 1.000000 | +0.000000 |
| 0.8939 | 11.4509 | 1.000000 | 1.000000 | +0.000000 |
| 0.9985 | 12.7908 | 1.000000 | 1.000000 | +0.000000 |
| 1.1155 | 14.2896 | 1.000000 | 1.000000 | +0.000000 |
| 1.2500 | 16.0125 | 1.000000 | 1.000000 | +0.000000 |
| 1.3800 | 17.6778 | 1.000000 | 1.000000 | +0.000000 |

7 of 7 leave the displaced patch scoring satisfied by villa's own combined criterion. The reason
is the acceptance band's width: the largest deviation from an exact winding across these seven
levels is **0.3800** of a winding (at ratio 1.3800), which still sits inside the `0.45*dr`
spiral tolerance (5.7645 voxels at this dr) and the 6.0-voxel scan tolerance.

This is the strongest form of the finding. Because the spiral acceptance half-width is `0.45*dr`,
bands around adjacent integer windings nearly *tile* the space — only a narrow strip near each
half-winding midpoint is rejected. A displaced patch therefore does not need to land precisely on
the adjacent wrap to be scored satisfied; the real field's own typical local gap noise already
fits inside the acceptance band. The blindness measured on the idealized sweep is not an
idealization that reality would soften.

## 7. Closing the two untested cells

Limits 4 and 5 named the two biggest remaining gaps and said a sceptic would ask for them first.
Both are now measured (`reports/spiral_satisfaction_untested_cells.txt`,
`scripts/probe_spiral_satisfaction_untested_cells.py`), through the same pinned
`get_patch_satisfied_areas` call, reporting villa's own patch-level verdict
(`satisfaction_metrics.py:317`, 165 valid quads, threshold 156.75 quads) alongside the satisfied
fraction. Both cells use the identity transform only — no nonlinearity. They extend §1-§3 and the
`alpha = 1.00` column of §4's grid; they do not touch §4's nonlinear robustness sweep, and in
particular do not bear on the one verdict flip §4 reports (more on this below).

### Cell 1 — scatter crossed with the real scale

The fractional parameterization (`scatter_std_frac * dr`) §4 used is not comparable across
scales: 0.05*dr is 0.64 voxels at the real dr = 12.81 but 5 voxels at dr = 100, against the same
6.0-voxel absolute scan tolerance in both cases. Re-running the pinned fractional levels at the
real scale (Cell 1a) makes this concrete: the same fractions that spanned 0-10 voxels at dr=100
now span only 0.000-1.281 voxels, and every cell — reference and displaced alike — stays
satisfied (`Δ = +0.000000` throughout).

Because real patch scatter is physical and does not shrink with winding spacing, Cell 1b sweeps
scatter in **absolute voxels** instead, at both dr = 12.81 and dr = 100, up to and including 6.0
voxels — villa's entire scan tolerance:

| dr | scatter (vox) | ref combined | ref verdict | disp combined | disp verdict | Δ combined |
| --- | --- | --- | --- | --- | --- | --- |
| 12.81 | 0.00 | 1.000000 | SAT | 1.000000 | SAT | +0.000000 |
| 12.81 | 6.00 | 0.969697 | SAT | 0.969697 | SAT | +0.000000 |
| 100.00 | 0.00 | 1.000000 | SAT | 1.000000 | SAT | +0.000000 |
| 100.00 | 6.00 | 0.975758 | SAT | 0.975758 | SAT | +0.000000 |

(Intermediate levels 0.5, 1.0, 2.0, 4.0 voxels read the same pattern; the full 12-row table is in
the artifact.) Across all 12 cells: **0 of 12 show villa's verdict distinguishing the two arms,
and 0 of 12 push the correctly placed reference patch below threshold** — even with scatter equal
to the entire 6.0-voxel scan tolerance, the reference stays satisfied (0.969697 and 0.975758,
both above the 0.95 quad-fraction bar). The report's own question — does the metric stop
accepting anything at real scale, which would change the question from "can it detect a wrong
wrap" to "does it accept anything at all" — is answered: no, it keeps accepting both arms.

This does not touch §4's one verdict flip. That flip required combining scatter *with*
nonlinearity (alpha = 0.80); every alpha = 1.00 row in §4's own table already reads Δ = 0 at
every scatter level, and Cell 1 only ever ran the identity transform. Cell 1 extends the
alpha = 1.00 column to the real scale and to absolute-voxel scatter; it says nothing about, and
does not retract, §4's finding that nonlinearity combined with scatter can flip the verdict. The
harder cross — real-scale scatter *combined with* nonlinearity — remains untested (Limits 4,
updated below).

### Cell 2 — displacement ratios across the full measured span

Experiment B (§6) swept only the p05-p95 quantile band (ratio 0.72-1.38). Cell 2 sweeps the full
measured adjacent-gap ratio distribution (0.0446 to 23.8006, §5), at dr = 12.81, no scatter,
including integers and half-integers, to resolve whether acceptance tracks displacement
*magnitude* or distance to the *nearest integer winding*.

It is the latter. Selected rows (full 21-row table in the artifact):

| ratio (windings) | offset from nearest integer | displaced verdict |
| --- | --- | --- |
| 0.50 | 0.5000 | **unsat** |
| 1.00 | 0.0000 | SAT |
| 1.50 | 0.5000 | **unsat** |
| 5.00 | 0.0000 | SAT |
| 5.50 | 0.5000 | **unsat** |
| 23.8006 | 0.1994 | SAT |

The largest displacement tested, 23.8006 windings (≈304.9 voxels at this dr), is accepted because
it lands only 0.1994 of a winding from the nearest integer — smaller than every half-winding
case, which is rejected regardless of how small its absolute displacement is (0.5 windings, only
≈6.4 voxels, is already enough to reject). Across all 21 cells, the displaced patch is **accepted
in 13 and rejected in 8**; every acceptance has an offset of 0.44 or less, every rejection an
offset of 0.46 or more. Displacement magnitude does not appear in that split at all — only
proximity to an integer winding does. That is the periodicity Limits 5 flagged as untested, now
measured directly rather than assumed from villa's snap-to-nearest logic.

**The acceptance edge, bracketed and re-resolved.** Four points bracket the edge near ratio 0:
0.40 and 0.44 accepted, 0.46 and 0.48 rejected — so the edge sits strictly between an offset of
0.44 and 0.46. The same bracket, re-run five windings out (5.44 accepted, 5.46 rejected), lands
identically: the edge does not move with displacement magnitude, confirming by direct
measurement — not by reading `spiral_tolerance = dr * 0.45` in source alone — that only the
offset from the nearest integer winding governs the verdict.

That measured bracket is also what makes the "~10% strip" figure quotable. The offset ranges from
0 to 0.5 within each winding period, by symmetry around the nearest integer, and the measured
edge sits in `(0.44, 0.46]`. The rejected span per period is therefore `2 * (0.5 - edge)`, which
the bracket confines to between `2*(0.5-0.46) = 0.08` and `2*(0.5-0.44) = 0.12` — roughly a tenth
of each winding's span rejected, and roughly nine tenths accepted. An earlier draft of this
investigation derived this figure from villa's tolerance constant (`0.45*dr`) alone, with no
measured cell behind it, and correctly declined to report it (see the process section). It is
reported here only because Cell 2's bracket now measures, rather than assumes, the number that
constant predicts.

## 8. Locating the onset

Limits 7 bracketed the break between 2 and 4 voxels of scatter. This locates it at 0.25-voxel
resolution (`reports/spiral_satisfaction_onset.txt`), using the same empirical warp (40 rays,
seed 20260825, shard_0, ≥10 crossings each) and a one-winding displacement throughout, varying
only the patch's scatter.

**Three distinct thresholds, under the reporting configuration.** The satisfied fraction moving
at all, a patch verdict flipping, and the correctly placed reference itself failing are not the
same event:

| onset | scatter (voxels) |
| --- | --- |
| satisfied fraction first moves | 2.50 |
| a patch verdict first flips | 3.25 |
| the correctly placed reference first fails | 4.00 |

5 of 40 rays flip somewhere in the swept range; per-ray onset has median 3.75v, range 3.25-4.00v.
These headline figures are a `min` over the 40 sampled rays and can only fall as more rays are
drawn — a property of the sample as much as of the metric. The per-ray median (3.75v) is the
sample-size-stable figure and should be preferred when the exact number matters.

**The splicing configuration is more robust**, consistent with its looser tolerances (Limits 3):
the satisfied fraction does not move until 4.00 voxels, and neither a verdict flip nor a
reference failure occurs anywhere in the swept range (0 of 40 rays flip, up to 4.25v).

**Absolute scan tolerance, not relative spiral tolerance, governs the onset.** Binning the 40
real rays by their own `dr` is confounded — across this population `dr` is strongly
anti-correlated with knot count (Pearson −0.882) and mildly correlated with local irregularity
(+0.147; bin medians 0.547/0.605/0.653) — so the artifact prints that table labelled confounded
and it must not be read as a `dr` effect. The clean test rescales each ray's warp *shape* to a
target `dr`, holding relative irregularity fixed and moving only the spacing:

| target dr | verdict onset (voxels) | onset as fraction of dr |
| --- | --- | --- |
| 10.0 | 3.50 | 0.350 |
| 13.0 | 3.50 | 0.269 |
| 16.0 | 3.25 | 0.203 |
| 20.0 | 3.25 | 0.163 |
| 25.0 | 3.25 | 0.130 |

The onset in absolute voxels is nearly flat (3.25-3.50) across a 2.5x range of `dr`, while the
onset as a fraction of `dr` falls by more than half (0.350 to 0.130). A relative check would hold
the fraction roughly constant as `dr` varies; this does the opposite. villa's 6.0-voxel absolute
scan tolerance, not its 0.45×dr relative spiral tolerance, is what sets the onset.

## 9. Does real patch scatter reach the onset?

§8 locates the break; it says nothing about whether real traced patches ever carry enough
scatter to reach it. `reports/real_patch_scatter.txt` measures that directly on 10 patches from
the published `verified_patches` set, with radii taken from the published umbilicus — data, not
metric; no villa code involved.

**The window size decides the answer, and this is the load-bearing methodological point.** Scatter
is the RMS residual of a patch's radius after removing a smooth trend fit across a grid window.
One grid step is ~20.0 voxels (median, both axes, across all 10 patches), so a window sized to
match the synthetic patch's 12x16 *point* grid spans roughly 240x320 real voxels — five to fifteen
times the synthetic patch's own ~22x64-voxel extent. At that mismatched scale the "residual" is
dominated by genuine surface curvature rather than roughness, and it inverts the conclusion. The
probe therefore prints the full sensitivity surface, four window sizes crossed with two fit orders
(plane, quadratic), and marks the comparable cell:

| window (grid cells) | extent (voxels) | fit | p50 (vox) | p95 (vox) | share ≥ 3.25v (verdict-flip onset) |
| --- | --- | --- | --- | --- | --- |
| 3x4 | 60x80 | plane | 0.846 | 2.179 | 0.8% ← comparable |
| 3x4 | 60x80 | quad | 0.255 | 0.633 | 0.0% |
| 4x6 | 80x120 | plane | 1.595 | 3.836 | 10.3% |
| 6x8 | 120x160 | plane | 2.828 | 7.125 | 39.4% |
| 12x16 | 240x320 | plane | 8.135 | 15.374 | 97.7% |

The 3x4 window is the one whose real-space extent (60x80 voxels) is closest to the synthetic
patch's (~22x64); the 12x16 row — the naive choice matching point-grid dimensions rather than
real-space extent — reports 97.7% of windows above the verdict-flip onset, the opposite of the
comparable window's answer. **Both rows are measured on the same data; only the window differs,
and the conclusion inverts.**

**Two checks on this figure, both run 2026-08-25 after review raised them.**

*Pooling.* One sampled patch (`0000_top_band`, 241x13168) is orders of magnitude larger in grid
extent than the other nine, so a pooled statistic could have been its statistic. It is not: the
probe caps sampling at 400 windows per patch, so that patch contributes 10.3% of pooled windows.
Dropping it entirely moves the pooled median from 0.812 to 0.822 and p95 from 2.071 to 2.086.
Per-patch medians run 0.635 to 1.084, median-of-medians 0.843. The headline is not one patch's
number.

*Trend model.* A plane over a 3x4 window is 12 points fitting 3 parameters, and the fit order
moves the answer by more than 3x: plane gives median 0.846, quadratic 0.255.

⚠ **CORRECTED 2026-08-25.** This paragraph originally concluded that real scatter is "bracketed
between roughly 0.26 and 0.85 voxels" with the plane figure as "the conservative end". **The
bracket points the wrong way and the plane figure is not conservative.** Injection recovery on
real patch geometry (`reports/scatter_estimator_calibration.txt`) — inject a perturbation of known
magnitude and correlation length into a curvature-only reference, and see what each estimator
returns:

| estimator | contamination floor | constant attenuation k |
|---|---|---|
| plane | 0.2193 vox | **0.602** |
| quadratic | 0.0116 vox | **0.378** |

Both estimators **under**-report correlated scatter. Correcting the reported figures:

- reported median **0.846** vox → true **≈1.4** vox
- reported p95 **2.179** vox → true **≈3.6** vox

**Quote these as a band, not a point.** Across defensible reference smoothing the corrected median
runs 1.37 to 1.44 and the tail 3.6 to 3.8; seed variation adds a little more. The direction is the
well-established part; the third digit is not.

**Three caveats on the mechanism, each of which corrects an earlier overstatement here.**

*The shortfall is mostly definitional, not "the fit absorbing a trend."* Of the plane's ≈1.6x
under-report, a factor of ~1.26 is that a 3x4 window carries less variance than the whole field,
and ~1.15 is that the estimator normalises by n rather than n−p (which alone returns √(9/12)=0.866
on white noise). Only the modest remainder is genuine absorption of correlated structure. The
number is unaffected — the units match the onset probe's global-rms convention — but the earlier
one-line explanation was a post-hoc story.

*The correlation length is fitted to a statistic, not calibrated to the real field.* It targets
lag-1 on the raw injected field; the real +0.357 was measured on a plane-fit *residual*. The same
surrogate, windowed and detrended identically, has residual lag-1 near −0.10, and the real value is
**unreachable** for any isotropic Gaussian sigma. The real residual is also **anisotropic** (+0.357
along columns, −0.076 along rows) where the surrogate is isotropic. Both are limitations of unknown
sign. They matter less than they might: the correction's direction holds across the whole plausible
correlation range, white through the fitted sigma.

*The floor is a definitional choice, not a measurement.* It falls monotonically from 0.55 to 0.006
as the reference smoothing goes from σ=2 to σ=20, with no plateau — the boundary between "curvature
the fit should remove" and "scatter it should keep" is set by that parameter. What survives is that
k barely moves (0.588–0.602) and the correction with it (1.37 to 1.44). The chosen σ=6 yields the
**smallest** correction of the defensible set, so the quoted figure is the conservative end of that
sensitivity. Separately measured: at σ=6 real-magnitude roughness leaks back into the residual at
0.0094 vox against a 0.2193 floor, so the floor is curvature rather than the probe's own injected
signal, and the design does not beg its question.

*Both sides of the onset comparison are not yet at the same correlation length.* The 1.5-voxel
onset comes from the correlated-scatter probe's σ=1 arm, a correlation length this calibration
argues is too high.

**At the comparable window (3x4, plane fit):** median 0.846 voxels, p95 2.179, max 5.406, n =
3897. Against §8's three onsets:

| onset | scatter (voxels) | share of real windows at or above it |
| --- | --- | --- |
| fraction moves | 2.50 | 2.67% |
| verdict flips | 3.25 | 0.82% |
| reference fails | 4.00 | 0.13% |

So real traced patches, measured at the scale the synthetic probes actually operate on, carry
scatter that sits below the onset located in §8 — the overwhelming majority of windows (99.18%)
never reach the level at which villa's verdict can flip. This does not soften §4's counterexample
cell or the fact that the empirical-warp break is real (both stand): it says that on this
evidence, well-traced real patches do not typically carry enough scatter to reach it.

---

## Limits

Stated plainly, because each is a place this work could mislead.

1. **The pre-registration was committed after the measurements ran.** See the Contract section
   above. The gate was fixed in task briefs beforehand, but not in git history. This is a
   limitation of the run, not a technicality to argue past.

2. **Everything is synthetic patches scored by villa's real, unmodified function.** No fitted
   spiral checkpoint is published anywhere under `dl.ash2txt.org/datasets/spiral_datasets/` —
   the `winding_model/` product used in §5 is ray/crossing inference output, not a
   `checkpoint_fitted.ckpt` — so producing one would require running `fit_spiral.py` ourselves
   (~60 GB pull, GPU, editing constants in a 3886-line script). This establishes what the metric
   *cannot detect*. It does **not** establish how often real fits actually misplace patches, and
   nothing here should be read as a claim about the quality of anyone's fit.

   **This is the one substantive limit still open**, and it may stay open. Limit 7 closes the
   nearest reachable approximation — the deformation is now taken from real measured winding
   positions rather than a synthetic model — but measured radial geometry is not a fitted
   transform, and a reconstruction from published crossings is not the thing a maintainer would
   run. Treat every result here as a statement about the metric, never about a fit.

3. **We measured the configuration that prints, not the one that gates the mesh.** Every number
   in this report uses villa's *default* `metrics_config` (`satisfaction_metrics.py:24-26`:
   radius tolerance 0.45, distance tolerance 6.0, patch fraction 0.95). That is the
   configuration of the reporting call site, `satisfaction_metrics.py:529` inside
   `save_overlay_and_print_satisfaction`. There is a second call site:
   `spiral_helpers.py:1314`, inside `save_mesh`, which decides which patches are **spliced into
   the output mesh**, and it overrides all three thresholds (`spiral_helpers.py:1308-1312`):
   radius tolerance **0.495**, distance tolerance **12.0**, patch fraction **0.90**. villa's own
   comment there says splicing "is deliberately more permissive than the reported satisfaction
   metrics".

   ✅ **CLOSED 2026-08-25** (`reports/spiral_satisfaction_splicing_and_seam.txt`, section A).
   The splicing configuration was swept, and the finding holds there. The whole-winding delta
   is still exactly `0.000000`, and the acceptance edge moves **outward**, from a bracket of
   `(0.44, 0.46]` under reporting to `(0.49, 0.499]` under splicing. So the configuration with
   downstream consequences is the *more* permissive of the two: it rejects roughly one percent
   of each inter-winding period against the reporting config's eight to twelve. Our framing was
   understated, as suspected, and is now measured rather than suspected.

   What remains true, and is why this entry stays: §6's binding-condition table, the
   47%-of-winding-spacing figure, the `0.45*dr = 5.7645` arithmetic, and §4's threshold flip
   analysis are all still stated for the *reporting* configuration. A reader should not
   transplant those specific numbers onto the splicing path.

4. **Scatter combined with the real scale — closed for the identity transform, in §7.** §4
   swept scatter at dr = 100 under smooth nonlinearity; §6 ran at dr = 12.81 with scatter held at
   zero. The cross of the two was flagged as the cell a sceptic should ask for first. §7 Cell 1
   measured it under the identity transform: 0 of 12 cells show villa's verdict distinguishing
   the reference from the displaced patch, and 0 of 12 push the correctly placed reference below
   threshold, even at scatter equal to the full 6.0-voxel scan tolerance. What remains untested is
   the harder, three-way cross — real-scale scatter *combined with* the nonlinearity that produces
   §4's one verdict flip. That combination was not run.

5. **Ratio tails beyond p05-p95 — closed, in §7.** Experiment B covered only the pinned quantile
   grid (0.72-1.38). §7 Cell 2 swept the full measured span, 0.0446 to 23.8006, plus
   half-integers, and re-resolved the acceptance edge five windings out. The invariance is
   periodic, not magnitude-bounded: the largest displacement tested (23.8006 windings, ≈304.9
   voxels) is accepted because it lands 0.1994 of a winding from the nearest integer, while a
   0.5-winding displacement (≈6.4 voxels) is rejected outright. The acceptance edge sits between
   an offset of 0.44 and 0.46 from the nearest integer winding, measured identically near ratio 0
   and five windings out. This closes the tail gap for the identity transform; it says nothing
   about the tails under nonlinearity, which Limits 7 still covers.

6. **The theta = 0 seam — closed** (`reports/spiral_satisfaction_splicing_and_seam.txt`,
   section B). The patches used elsewhere span theta 0.30-1.30 rad and never cross the branch
   cut, so `get_theta_crossing_step_adjustments` and the branch-offset unwrap were never
   invoked. A patch spanning theta 6.0-6.6 rad does cross it: its recovered shifted-radius
   jumps a whole `dr` mid-patch purely as an artifact of `theta % 2pi`, which is exactly what
   that unwrap exists to repair. Both acceptance edges reproduce exactly, under both
   configurations. The blindness is not an artifact of avoiding the seam.

7. **The nonlinearity sweep tested a smooth shape where the real field is locally noisy —
   NARROWED, not closed, and the invariance does break here.** §4 perturbs smoothly (a global
   power law), which has a slowly varying derivative by construction; §5 shows the real field's
   irregularity is local and noisy. A warp interpolated from the measured inter-winding spacing
   sequences of 40 real rays (`reports/spiral_satisfaction_empirical_transform.txt`) supplies
   the shape a power law cannot, and it is a *stronger* perturbation than any pinned alpha,
   displacing points by a median of ~0.87 `dr` against 0.067 `dr` at alpha 0.95 and 0.514 `dr`
   at alpha 0.60.

   ⚠ **CORRECTED 2026-08-25.** This entry was briefly marked **closed** on the strength of that
   probe reporting max |Δ| = `0.000000` across all 40 rays. That was wrong, and wrong in the
   flattering direction. **The probe ran at zero scatter**, and at zero scatter §1's algebra
   *guarantees* Δ = 0 for any invertible transform — §4's own `scatter 0.00` row already
   publishes `+0.000000` at every alpha. The probe could not have failed. A zero over empirical
   warps was not evidence about those warps.

   Measured with scatter present, under the reporting configuration:

   | scatter (voxels) | max abs Δ | verdict differs | reference fails |
   |---|---|---|---|
   | 0.0 | 0.000000 | 0/40 | 0/40 (degenerate) |
   | 3.0 | 0.030303 | 0/40 | 0/40 |
   | 4.0 | 0.121212 | **5/40** | 1/40 |
   | 6.0 | **0.284848** | **8/40** | 25/40 |

   At 6.0 voxels — villa's entire scan tolerance — max |Δ| is **6.7× §4's pinned worst case**
   of 0.042424. The splicing configuration is more robust, holding to 4–5 voxels (Δ 0.006061)
   before breaking at 6.0 (Δ 0.260606, 3/40), which is consistent with its looser tolerances.

   So the version of this limit that this report originally carried — that the smooth sweep
   "must not be read as bounding the real field's local irregularity, which is comparable to or
   beyond the breaking regime" — **was correct**, and the correction restores it. What the
   empirical probe legitimately establishes is narrower: §1's exactness holds against a real,
   non-analytic, locally irregular warp, and the *degenerate* row confirms the algebra rather
   than the geometry.

   **What the knots are.** The measured *sequence of inter-winding spacings* along each ray,
   re-anchored at zero and read as radial knots — not the scroll's radial map. The rays are
   oblique (median |step_z| 0.215 across the selected rays, max 0.826) and this code places the
   first crossing at radius 0 though it sits at a real radius in the scan, so part of the
   measured irregularity is crossing-*angle* variation rather than radial spacing. The probe
   needs only that the warp be real, monotone and locally irregular, which it is.

   This does **not** discharge Limit 2. It is real measured spacing geometry, not a fitted
   transform, and a real fitted transform would not be purely radial.

   **The onset is now located, not bracketed (§8).** Under the reporting configuration: the
   satisfied fraction first moves at 2.50 voxels of patch scatter, a patch verdict first flips at
   3.25, and the correctly placed reference itself first fails at 4.00 (per-ray median 3.75,
   sample-size-stable; the 3.25 figure is a min over 40 sampled rays and can only fall with more
   rays). Under the splicing configuration the onset is later and, within the swept range up to
   4.25 voxels, no verdict ever flips. The onset is set by villa's **absolute** 6.0-voxel scan
   tolerance, not its **relative** 0.45×dr spiral tolerance: rescaling each ray's warp shape to a
   fixed target dr while holding relative irregularity constant leaves the onset nearly flat in
   absolute voxels (3.25-3.50 across dr 10-25) while it falls sharply as a fraction of dr
   (0.350 to 0.130) — the opposite of what a relative check would produce.

   **Whether that onset matters in practice is answered, separately, in §9.** Real traced patches
   from the published `verified_patches` set, measured at the window whose real-space extent
   matches the synthetic patch (3x4 grid cells, plane fit), carry median scatter 0.846 voxels
   (p95 2.179) — below all three onsets above. Only 0.82% of measured windows reach the
   verdict-flip onset. That is real evidence that well-traced patches do not typically carry
   enough scatter to trigger the break §4 and this entry describe — it is not a claim that the
   break is unreachable, only that it sits above what these 10 patches, at this window, show.

8. **villa already contains annotation-propagation machinery; the metric just does not use it.**
   `find_inconsistent_windings.py` derives a patch's expected absolute winding by propagating
   `winding_is_absolute` annotations across the patch graph — direct votes from absolute-winding
   pcls attached to the seed patch, plus long-range votes reached by BFS over relative-winding
   pcl edges. That is materially the remedy this report proposes. It does not weaken the
   finding: it is a standalone debug tool that "does no fitting/training" (its own docstring),
   requires `--patch-id` and so runs one seed patch at a time by hand, and nothing imports it
   (`plot_winding_graph.py` consumes its output JSON rather than calling it). It is wired into
   neither the fit loop nor `get_patch_satisfied_areas`. The correct reading is therefore
   sharper than "villa cannot detect sheet switches": villa has the annotation-propagation
   machinery already, and the scored metric does not consult it.

9. **Two import-time stubs were required.** `kornia` (absent from the environment) and villa's
   own `visualization.py` (a `SyntaxError` under the project's pinned Python: PEP 646
   subscript-unpacking needs 3.14) were stubbed into `sys.modules`. Neither is reachable from
   `get_patch_satisfied_areas`: it spans lines 31-325, while `kornia` is reached only via
   `get_track_satisfied_counts_in_chunks` (line 581) and `save_overlay` (line 682), both inside
   the sibling `save_overlay_and_print_satisfaction` (line 493+). No file under `villa/` was
   modified.

## What would change the conclusion

- **A real fitted PHercParis4 spiral**, with real patches carrying real scatter, displaced by
  one winding and rescored. If Δ there is materially nonzero, the synthetic result would be
  shown to be an idealization. §1's algebra says it should not be, and §6 says the real
  tolerance/spacing ratio makes it less likely rather than more — but it has not been run.
- **A scatter × real-scale × nonlinearity cross.** §7 answered the two-way version of this
  question (real-scale scatter alone, identity transform): the reference patch never fails and no
  verdict disagreement appears in 12 cells, even at scatter equal to the full scan tolerance. What
  would still change the conclusion is the three-way cross — real-scale scatter *combined with*
  the nonlinear transform that produces §4's one flip. If that combination flips a larger share of
  the grid, or flips even at scatter levels below §4's, the flip would look less like an edge
  case.
- **A three-way cross: real-scale scatter, combined with a real locally-irregular warp, swept
  finely enough to locate the onset — SUBSTANTIALLY ANSWERED, §8 and §9.** The onset is now
  located at 0.25-voxel resolution rather than bracketed: under the reporting configuration the
  satisfied fraction first moves at 2.50 voxels, a verdict first flips at 3.25, the reference
  first fails at 4.00 (per-ray median 3.75); the onset is governed by villa's absolute 6.0-voxel
  scan tolerance, not its relative spiral tolerance (§8). And real patch scatter, measured on 10
  patches from the published `verified_patches` set at the window matching the synthetic patch's
  real-space extent, has median 0.846 voxels — below all three onsets, with only 0.82% of
  measured windows reaching the verdict-flip onset (§9). What is still open: this is 10 patches
  at one comparable window, the 3.25v figure is a min over 40 synthetic rays that can only fall
  with more rays, and the empirical-warp cross was not run together with the *smooth alpha*
  nonlinearity that produced §4's specific verdict flip — that remains the harder cross named in
  the bullet above. With those caveats, the headline claim now has direct evidence, not just an
  algebraic argument, that it holds for the patches this investigation was able to measure.

- **Reading the absolute winding annotations in `satisfaction_metrics.py`.** The annotations
  already exist, already drive `get_patch_abs_winding_loss`, and are already propagated across
  the patch graph by `find_inconsistent_windings.py` (Limits 8). None of that reaches the scored
  metric, which still derives its target from the patch's own median. If the metric compared
  against a propagated absolute winding instead of against a self-derived snap, this entire
  finding would evaporate — which is the practical point of reporting it.

## A process finding

Reported as a finding, not an apology, because the pattern is the useful part.

Three hand-asserted statistics shipped into committed reports in this series, and **all three
were wrong on substance**, not merely unanchored to their source data. The third was in this
document — the one written to describe the pattern.

- In `real_winding_nonlinearity.txt`, the fraction of unresolvable ratios sitting below the
  model floor was written as "93%". The counts say 11,193,569 / 11,371,061 = **98.4%**. The
  correction strengthened the conclusion it appeared in, which is exactly why nobody had
  reason to re-check it.
- In `spiral_satisfaction_realscale.txt`, "the largest observed deviation" was rendered as a
  range, "about 0.28-0.38". The seven actual deviations are 0.0015, 0.1061, 0.1155, 0.20, 0.25,
  0.28, 0.38. A superlative — one value — had been written as a range, and the range's lower
  bound was the *second-largest* value, not a bound at all; the true spread bottoms out at
  0.0015. The conclusion survived only because 0.38 happened to be the upper end.
- In the first draft of **this report**, §4 asserted that the worst-case `|Δ| = 0.042424` was
  "small enough that the satisfied/unsatisfied verdict at villa's 0.95 patch threshold does not
  flip." It does flip, at scatter 0.05 / alpha 0.80: 159/165 satisfied → 156/165 not satisfied.
  The failure here was not a mistyped digit but an **invalid inference**: |Δ| was used as a
  proxy for "does the verdict change", and it is not one — the flip occurs at less than half the
  worst-case Δ, because what governs a flip is proximity to the threshold. The claim was made
  about data already printed in the artifact it cited, and it happened to be the most favourable
  reading available.

All three survived an implementer and a full review. All three were caught only by a second pass
that re-did the arithmetic or re-read the claim as written. The second occurred in a new file
*one task after* the first was fixed, and after the task brief had explicitly forbidden it and
named the fix to follow. The third occurred in the very document whose process section, as first
drafted, said this keeps happening — written by an author who had just read both prior
instances. The lesson does not transfer on its own, not across files and not even across
paragraphs.

One related decision cuts the other way and is worth recording alongside the three failures. An
earlier draft of this report computed a "~10% rejected strip" figure from villa's tolerance
constant (`0.45*dr`) and declined to state it, because no cell had actually measured the edge —
only the constant implied it. §7's Cell 2 has since bracketed the acceptance edge directly (0.44
accepted, 0.46 rejected, unchanged five windings out), and the figure is quoted there now because
it is measured rather than derived. The refusal was not a hedge that later turned out
unnecessary: it was correct at the time it was made, and it stayed correct until the missing
measurement existed. Withholding an unmeasured number is not the failure mode the rest of this
section is about; asserting one without checking it is.

The asymmetry is the finding: **every measurement in this investigation held up under scrutiny.
What repeatedly failed was the prose describing it** — which is the half a reader actually
consumes. A reader who trusts a report's numbers and skims its narrative was, three times,
reading the less reliable half. Note also the direction: each of the three errors, uncorrected,
would have made the work look better than it was.

The durable fix is structural, not vigilance. It is now implemented in both scripts:

- `pct(numerator, denominator)` in `scripts/measure_real_winding_nonlinearity.py` (line 518) —
  any narrative percentage is computed from the same counts dict that feeds its table, so the
  two cannot drift on a rerun. Applied to every sibling statistic in that file, not only the one
  that was wrong.
- `max_ratio_deviation(rows_b)` in `scripts/probe_spiral_satisfaction_realscale.py` (line 143) —
  the deviation statistic is computed from the swept data, so changing `RATIO_LEVELS` cannot
  leave a stale number in the prose.
- `verdict_flips(rows)` in `scripts/probe_spiral_satisfaction_robustness.py` — added for the
  third instance. It applies villa's own patch-level rule to integer quad counts across the
  sweep, so the flip set is computed rather than inferred from Δ, and the count is printed in
  the artifact itself.
- Drift-guard tests that parse the **rendered report text** by regex and compare the quoted
  figure against independently computed counts. All were mutation-verified: they fail on the
  reintroduced bad literal (or, for `verdict_flips`, on a version that ranks by Δ magnitude) and
  pass on revert.

**Residual instances, disclosed rather than fixed.** Two hand-typed figures remain in committed
artifacts. Both were checked and are correct; neither is anchored to its source, and they are
listed here rather than repaired because four downstream artifacts were measured against those
pinned scripts and editing them for cosmetics is not worth invalidating that chain.

- `scripts/probe_spiral_satisfaction_winding.py` types its report header as
  `"spiral-space 0.45*dr=45 units vs scan-space 6.0 voxels absolute"`. The computation reads
  villa's `metrics_config`; only this display line restates the values.
- `reports/spiral_satisfaction_realscale.txt` hardcodes `0.0446`, `23.8006` and `21.6%` in its
  closing caveat, sourced from `measure_real_winding_nonlinearity.py`'s output rather than
  computed in the script that prints them. A cross-file drift of exactly the kind the `pct()`
  pattern prevents within a file.

## Reproduction

```bash
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_winding.py
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_robustness.py
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_realscale.py
uv run python scripts/measure_real_winding_nonlinearity.py   # pulls 210 MB, sha256-verified
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_untested_cells.py  # §7
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_empirical_transform.py  # Limits 7
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_splicing_and_seam.py     # Limits 3, 6
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_onset.py  # §8
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_real_patch_scatter.py         # §9
CUDA_VISIBLE_DEVICES="" uv run pytest \
  tests/test_probe_spiral_satisfaction_winding.py \
  tests/test_probe_spiral_satisfaction_robustness.py \
  tests/test_probe_spiral_satisfaction_realscale.py \
  tests/test_measure_real_winding_nonlinearity.py \
  tests/test_probe_spiral_satisfaction_untested_cells.py \
  tests/test_probe_spiral_satisfaction_empirical_transform.py \
  tests/test_probe_spiral_satisfaction_splicing_and_seam.py \
  tests/test_probe_spiral_satisfaction_onset.py \
  tests/test_probe_real_patch_scatter.py -q      # 80 passed
```

Full execution history, including every ruling, every reviewer objection and both corrections
above, is in `.superpowers/sdd/2026-08-24-spiral-satisfaction-winding-probe/progress.md`.
