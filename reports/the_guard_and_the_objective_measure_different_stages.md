# villa's objective is a render-stage metric; its cross-check is a fit-stage metric

**2026-09-19.** Structural, verified from file locations and arm provenance. No compute.

## The question this closes

`reports/can_the_objective_be_won_without_reading.md` left one item open: is `satisfied_area` — the
guard villa's loop uses to cross-check `total_fg_pixels` — blind to duplicated coverage in the same
way the objective is?

**It is, and by construction rather than by oversight.**

## Why

| | computed where | from what |
|---|---|---|
| `total_fg_pixels` | **render stage** | `get_ink_metrics.py` on the rendered strip |
| `satisfied_area` | **fit stage** | `satisfaction_metrics_fitted.json`, written into the *fit* directory |

The render directories contain no satisfaction file at all. And all four duplicate-coverage arms —
`dup_armB`, `C`, `D`, `E` — carry meshes sourced from a single fit, `baseline01`.

**So every one of them has identical `satisfied_area`, whatever meshes were rendered.** Arm B's
duplicated winding raised `total_fg_pixels` by 12.59% and could not have moved the guard by anything,
because the guard was computed before the duplication existed.

## What follows

**The cross-check cannot catch a render-stage defect.** That is not a flaw in how `satisfied_area` is
calculated; it is a consequence of the two numbers describing different stages of the pipeline. A
change that duplicates, drops, or reshapes coverage *after* fitting is invisible to it.

**It also reframes the decoupling this project has documented four times.** Those cases —
gap-expander config, patch bootstrap, stripmatch, same-winding ablation — were reported as the two
metrics moving independently, which was treated as a property worth explaining. Part of the
explanation is simply that **they measure different stages**, so there is no mechanism requiring them
to track at all.

That does not dissolve the finding. The decoupling cases involved config changes that alter the *fit*,
which does propagate to the render, so those two metrics genuinely could have moved together and did
not. But "the guard and the objective are not measuring the same thing" is a structural fact that
belongs alongside the measurements, and it was not stated in any of the four.

## Limits

* This says nothing about whether `satisfied_area` is a *good* fit-stage metric.
* The four decoupling cases remain as measured; this offers a structural reason the two need not
  track, not a claim that it accounts for the observed magnitudes.
