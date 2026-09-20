# Pre-registration: does radial displacement CAUSE the ink loss, or merely accompany it?

**Written 2026-09-19, before any displaced arm is rendered or scored.** Reachability was confirmed
first (below); nothing about the outcome is known.

## The question

`reports/the_gap_fix_moves_the_surface_radially.md` found the gap-expander fix moves the scored
surface inward **3.96 voxels** (10/10 windings, all significant) while `total_fg_pixels` falls
**10.35%**, and stated plainly that this is **observational**: the fix changes a config, and both the
displacement and the loss follow. Displacement could be the cause, a side effect, or a correlate of a
third change.

This is the controlled version. **Displace the surface radially and change nothing else.**

## Why this is cheap, and why that is the point

`scripts/build_radial_displacement_arm.py` takes an existing fit's `_spliced` meshes and pushes every
valid point along its radial direction. **No refitting.** The geometry is otherwise bit-identical to
its source, so the manipulation is exactly one variable.

**The floor is therefore the PIPELINE floor, not the seed floor.** Every previous study here compared
different fits and paid the seed CV (11.8-12.3% at 3v3). These arms all derive from `baseline01`'s own
meshes, so the applicable floor is render/score reproducibility, measured twice at **1.42%** and
**0.0016%** (`reports/the_determinism_floor_rests_on_one_draw.md`). **The conservative 1.42% is used
throughout.** A 10% effect is detectable with a single pair, which is why this study costs three
renders instead of eighteen fits.

## Reachability, confirmed before designing anything

The lesson of `reports/sheet_switch_detector_premise_broken.md` is to ask whether the manipulation is
reachable before pre-registering how to validate it. Checked, in order:

1. displaced meshes are written in tifxyz and villa's `is_tifxyz` returns **True**;
2. villa's own `load_tifxyz` loads them;
3. the displacement **survives the round trip**: `Patch.valid_zyxs` gives mean radius
   2340.548 → 2336.547, **−4.000 vx against −4.000 requested**;
4. the valid point count is **unchanged** (165,940 both), so the manipulation moves the surface
   without dropping geometry.

The builder also **asserts** its achieved shift matches the request to 0.01 vx and exits non-zero
otherwise, so an arm cannot be silently built wrong.

## Amendment, 2026-09-19, made BEFORE any arm was scored

**The ZERO gate as registered above is wrong, and is downgraded to a diagnostic.**

The registration says ZERO "must reproduce `baseline01`'s existing w120-w129 score" or the study is
VOID. But `baseline01`'s stored score was **rendered 2026-09-01 on an older villa tree**, while ZERO,
IN and OUT all render today on pinned `be09a8503`. `reports/rerender_test_verdict.md` measured
**+1.44% from a render-code change** — wider than this study's entire 1.42% floor. So a ZERO/baseline
mismatch cannot distinguish:

* render code changed across that interval, from
* the displacement rebuild path altering the surface at delta = 0.

Voiding the study on a number that conflates those would discard a valid experiment for an unrelated
reason.

**The fix, and it makes the study stronger rather than weaker: IN and OUT are measured against ZERO,
not against `baseline`.** All three arms are one fit's meshes, rendered the same day on one pinned
tree, differing only in `--delta`. That is a cleaner control than `baseline` ever was — it removes
the render-tree difference from every effect instead of importing it.

`baseline` vs ZERO is still computed and reported, as a **render-code drift diagnostic**: if it lands
inside the floor, that is independent evidence the render path has not drifted since 2026-09-01.

Made before `radial_work_rad0/ink_metric/metrics.json` existed; `scripts/analyse_radial_displacement.py`
and its tests were amended in the same commit, and a test asserts effects are computed against ZERO.

## Arms

All from `baseline01`'s `fitted_baseline01` meshes, windings **w120-w129**, one axis derived once
from the source and reused for every arm. Identical render and scoring settings throughout.

| arm | delta | purpose |
|---|---:|---|
| **ZERO** | 0 vx | **positive control.** Must reproduce `baseline01`'s existing w120-w129 score to within the 1.42% pipeline floor. If it does not, the rebuild path itself is broken and the other arms are void. |
| **IN** | −4 vx | matches the gap fix's observed −3.96 |
| **OUT** | +4 vx | the opposite direction, which the observational finding cannot speak to at all |

## Predictions, fixed now

1. **ZERO reproduces `baseline01` within 1.42%.** If it does not, the study stops and reports a
   pipeline defect instead of a result.
2. **IN loses ink, between 5% and 15%.** Reasoning: it reproduces the gap fix's displacement, so if
   displacement is the cause it should reproduce most of its 10.35%.
3. **I do not predict OUT.** Ink could rise (the surface moves toward better-inked papyrus) or fall
   (any displacement off the fitted surface costs). I have been wrong three times predicting what an
   observable does, and the direction here is genuinely not implied by anything measured.

## Decision rule

Against the **1.42%** pipeline floor, on `total_fg_pixels` over w120-w129:

| outcome | conclusion |
|---|---|
| ZERO off `baseline01` by > 1.42% | **VOID.** Pipeline defect; no claim about displacement. |
| IN within 5-15% loss | **Displacement is sufficient to cause the loss.** The gap fix's cost is explained by where it puts the surface, not by what it does to the fit. |
| IN loses < 1.42% | **Displacement is NOT the cause.** The gap fix's 10.35% comes from something else that changed with it, and the radial shift is a side effect. |
| IN loses > 15%, or gains | Displacement matters but **not as the gap fix's mechanism**; reported as a separate effect. |

OUT is reported in whichever direction it falls and **carries no prediction**.

## What this cannot settle

**It cannot show displacement is the ONLY mechanism.** A 10% loss from a −4 vx shift is consistent
with displacement explaining the gap fix, but the fix also changes the fit itself; this isolates one
channel, it does not partition them.

**`total_fg_pixels` is an area count.** "Less ink" is not "less readable text", and a displaced
surface could plausibly lose true ink and false positives at different rates. Nothing here
distinguishes those.

**One fit, one ROI, one scorer, one displacement magnitude.** A sweep over magnitudes would give the
sensitivity curve; this gives one point on it and the sign of a second.

## Cost

Three renders at ~2-3h plus scoring at ~0.25h each: **about 9 hours**, sequential, no refitting.
Renders must not overlap (~26G resident each); `scripts/guard_heavy_analysis.py --fail-if-any` gates
each start.
