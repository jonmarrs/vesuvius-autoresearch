# villa's spiral-fit satisfaction metric cannot see a one-winding displacement

**Bottom line.** `get_patch_satisfied_areas` — the function villa uses to decide whether a
patch is "satisfied" by a fitted spiral — scores a patch moved exactly one whole winding off
its true position *identically* to the correctly placed patch. Measured delta in satisfied-quad
fraction: `+0.000000e+00`. That is the "sheet switch" failure mode villa's own
`scrollprize.org/docs/37_2026_open_problems.md` bottleneck table lists fourth ("Meshes can jump
from one wrap to another"), and for which that same row asks for "stronger local continuity
constraints and **conservative failure detection**". The metric is not a conservative failure
detector for this mode; it is exactly blind to it.

The mechanism is that the metric derives its target from the patch's *own* position. It takes
the patch's median shifted-radius and snaps it to the nearest integer winding
(`satisfaction_metrics.py` lines 242-248), then checks two residuals against that
self-derived target. Absolute winding annotations do exist in the codebase and are load-bearing
in the fit — `losses.get_patch_abs_winding_loss` selects point collections on
`metadata.winding_is_absolute` (line 1059) and is called from `fit_spiral.py` at lines 2720 and
3373 — but `satisfaction_metrics.py` never reads them. Ground truth is consumed by the fit and
never used to score it, so the score cannot distinguish "on the right wrap" from "on a wrap".

That blindness is exact for a patch lying on a winding, and it survives scatter and smooth
nonlinearity across almost all of the range swept — but not quite all of it. §4 reports the one
pinned-grid cell where villa's verdict does change, and reports it as the counterexample it is.

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
`reports/spiral_satisfaction_realscale.txt`.

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
And it is a flip under the *reporting* configuration; the splicing configuration that actually
gates the output mesh (Limits 3) uses a looser 0.90 patch threshold, i.e. 148.5 quads, which
both 159 and 156 clear — so this particular flip would not occur there. That configuration also
loosens both tolerances, which would change the fractions themselves; we did not measure it.

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

   Both directions matter. Our framing is *understated*: at 0.495 the spiral acceptance bands
   tile all but roughly a 1% strip around each half-winding midpoint, and the scan tolerance
   doubles, so the splicing path is more blind than anything measured here, not less. But §6's
   binding-condition table, the 47%-of-winding-spacing figure, the `0.45*dr = 5.7645`
   arithmetic, and §4's 0.95-threshold flip analysis are all for the *reporting* configuration.
   A maintainer could accurately reply that we measured the config that prints numbers, not the
   one that gates the mesh, and they would be right. The splicing configuration was not swept.

4. **Scatter was never combined with the real scale.** §4 swept scatter at dr = 100; §6 ran at
   dr = 12.81 with scatter held at zero. The cross of the two is untested, and it is the cell a
   sceptic should ask for first.

5. **Ratio tails beyond p05-p95 are untested.** The measured distribution runs from 0.0446 to
   23.8006 and 21.6330% of ratios fall outside [0.8, 1.25]. Experiment B covers the pinned
   quantile grid only; the invariance is not claimed for the more extreme local deviations.

6. **The theta = 0 seam is not exercised.** The synthetic patch spans theta 0.30-1.30 rad, so it
   never crosses the seam and `get_theta_crossing_step_adjustments` is never invoked. The
   invariance argument does not depend on seam handling, but the probe does not test it.

7. **The nonlinearity sweep tests the wrong *shape* for the real field.** §4 perturbs smoothly
   (a global power law); §5 shows the real field's irregularity is local and noisy, with roughly
   half of the ratio population failing to invert under the power-law model at all. The pinned
   sweep's clean "safe for alpha ≥ 0.60" story characterises smooth systematic nonlinearity
   only, and must **not** be read as bounding the real field's local irregularity — which the
   measurement suggests is comparable to or beyond the (unpinned) breaking regime for a
   meaningful fraction of local winding triples.

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
- **A scatter × real-scale cross.** If a patch's real scatter at dr ≈ 12.8 already pushes the
  reference below the 0.95 threshold, the practical question changes from "can the metric detect
  a wrong wrap" to "does the metric accept anything at all at this scale".
- **A demonstration that the real transform's local irregularity does break the invariance.**
  §4 shows it breaks at alpha ≈ 0.2 under a smooth power law; §5 argues the real field is not
  well described by a single alpha. Measuring the invariance directly against the observed local
  gap sequence, rather than against a fitted alpha, would settle it.
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
CUDA_VISIBLE_DEVICES="" uv run pytest \
  tests/test_probe_spiral_satisfaction_winding.py \
  tests/test_probe_spiral_satisfaction_robustness.py \
  tests/test_probe_spiral_satisfaction_realscale.py \
  tests/test_measure_real_winding_nonlinearity.py -q      # 47 passed
```

Full execution history, including every ruling, every reviewer objection and both corrections
above, is in `.superpowers/sdd/2026-08-24-spiral-satisfaction-winding-probe/progress.md`.
