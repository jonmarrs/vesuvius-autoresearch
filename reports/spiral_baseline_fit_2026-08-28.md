# Converged baseline fit, 2026-08-28: the injection study is POWERED

30,000 steps, `FIT_SPIRAL_RUN_TAG=baseline01`, 1h 34m wall clock, no errors.
Checkpoint: `spiral_out/2026-08-28_s1_slice-13056-18432_38442-patch_baseline01/checkpoint_fitted.ckpt`.
Config as `repro/spiral_s1/run_smoke.sh` with the step override removed.

## The pre-registered gate

`docs/preregistration/2026-08-28_winding_injection_conditional_on_acceptance.md`, rule 1: below
`N = 30` baseline-satisfied units the study is declared UNPOWERED.

```
satisfied_patches = 25,148 / 38,439   (65.4%)
```

**N = 25,148.** The gate is cleared by three orders of magnitude.

> **SUPERSEDED 2026-08-29.** The study was powered and was still **shelved without being run**. On
> villa#1621 @pmh47 stated as design authority that the periodicity is intended, which dissolved the
> question rather than answering it. Clearing a power gate says the study *could* have run, not that
> it *should* have. See `docs/preregistration/2026-08-28_winding_injection_conditional_on_acceptance.md`.

The 100-step smoke fit gave `N = 29`, one under the floor. That was entirely an artifact of stopping
at 100 steps, and it is worth recording that a number which looked like a study-ending result was
just an unconverged one. Rule 1 was still right to exist; it simply was not triggered.

## Convergence

| | step 0 | step 29,800 |
|---|---:|---:|
| total loss | 3182.7 | 43.5 |
| `patch_radius` | 839.0 | 8.3 |
| `abs_winding` | 888.1 | 2.3 |
| `rel_winding` | 699.9 | 3.4 |
| `shell_outer` | 611.1 | 2.5 |

A 73x reduction overall. `abs_winding`, the largest single term at initialisation, falls to 2.3:
the absolute-winding annotations are satisfied by the converged fit, which is the input the
satisfaction metric never consults.

## Full metric set

```
satisfied_patches                 25,148/38,439   65.4%
satisfied_patches_area_weighted                   73.4%
boundary_satisfied_patches        25,733/38,439   66.9%
satisfied_area                                    84.0%
satisfied_unattached_pcls              50/52      96.2%
satisfied_unattached_pcl_points       704/708     99.4%
save_mesh fitted: winding range [10, 130)
```

**The unit question is now settled empirically.** At 100 steps `satisfied_patches` (0.1%) and
`satisfied_area` (10.0%) differed by two orders of magnitude; converged they are 65.4% and 84.0%,
within a factor of 1.3. The pre-registration scores quads and patches separately, which remains the
right call, but the two units no longer disagree about what the fit is.

## `spiral_outward_sense: "CW"` survives

Flagged since it was written as the weakest field in the manifest, a binary with no independent
corroboration. A converged fit reaching 65.4% patch satisfaction and driving `abs_winding` from
888.1 to 2.3 could not happen under an inverted winding sense: the absolute annotations would be
fought, not fitted. The winding range `[10, 130)` is stable between the 100-step and 30,000-step
runs.

That is strong evidence, not proof. It remains conceivable that some other compensating error makes
both senses fit; nothing here rules that out directly.

## Cost, for planning

1h 34m for 30,000 steps, an average of **5.3 it/s** including about six minutes of startup. Slower
than the 8.7 it/s the smoke run's early iterations suggested, because that sample was taken before
the expensive loss terms engaged. A fit is an evening, not a day, so the injection study's arms are
affordable.

## Deviations, unchanged

`input_use_fibers`, `input_use_tracks`, `input_use_pcl_drawn_control_points` all off; z restricted
to the fetched ROI [13056, 18432). Not comparable to villa's numbers, and not intended to be.
