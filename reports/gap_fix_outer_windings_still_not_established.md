# The gap-expander fix, measured where it acts: still not established

**2026-09-01.** Registered in `docs/preregistration/2026-09-01_gap_fix_measured_where_it_acts.md`,
before either render. **The registered expectation is met, and it was an expectation of a null**: one
fit per arm cannot clear the different-fit floor except for a large effect, and it did not.

## Why this arm exists

`reports/gap_expander_fix_improves_the_fit.md` reports that `model_gap_expander_num_windings`
130 -> 133 raises `satisfied_area` by 7 to 9 sd on two seeds, while `total_fg_pixels` moved +2.5%,
far inside its floor, and concluded the ink effect was "not established".

That conclusion was correct but the measurement behind it was **aimed at the wrong region**. The
shortfall concerns losses sampling out to `shell_outer_winding_idx = 130`, so it acts on the
**outermost** windings; every ink render in this work covered w010-w019, the innermost ten. The
measurement was blind to the region the change acts on and would have read null either way.

This arm re-measures on **w120-w129** of the same two fits. No new fits: the meshes already existed,
only the render and score were needed.

## Controls, both registered before the data

**Both arms render non-blank.** A blank strip would mean a render fault rather than absent ink, and
would void the arm.

| arm | tiles | strip px | nonzero | p95 per tile |
|---|---:|---:|---:|---|
| BASE-OUTER | 6 | 352,174,200 | 47.2% | 254, 230, 196, 247, 128, 0 |
| GAP-OUTER | 6 | 362,131,100 | 45.5% | 254, 191, 178, 250, 162, 0 |

The trailing zero is the ~750px sliver tile in both arms, mostly padding; its p99 is 253.

**The arms are the fits they claim to be.** Re-read from each fit's own
`satisfaction_metrics_fitted.json`, the two reproduce the numbers already on record, so these are the
same objects the satisfaction result was measured on and not re-fits sharing a name:

| fit | `satisfied_area_fraction` | on record |
|---|---:|---|
| baseline01 | 0.8398 | inside the honest band 0.8382-0.8404 |
| gap133 | 0.8480 | the confirmation arm's 0.8480 |

**Surface areas agree to 0.05%** (concat `area_vx2` 1,019,676,800 against 1,019,120,800), so the
comparison is not between differently sized pieces of scroll. The rendered strips still differ by
2.83% in pixel count, which is why `fg_fraction` is reported beside the objective below.

## Result

| key | BASE-OUTER | GAP-OUTER | rel diff |
|---|---:|---:|---:|
| `total_fg_pixels` | 1,789,206 | 1,591,857 | **-11.03%** |
| `total_pixels` | 352,174,200 | 362,131,100 | +2.83% |
| `overall_fg_fraction` | 0.005080 | 0.004396 | -13.48% |
| `overall_line_score` | 0.34610 | 0.33783 | -2.39% |
| `overall_column_score` | 0.24251 | 0.12956 | -46.57% |

**`dT` = -11.03%, inside the 21.7% different-fit floor. Under the pre-registered decision rule this
is uninterpretable and is reported as "still not established", NOT as evidence of no effect and not
as evidence the fix costs ink.** The direction is negative and that fact carries no weight at this
sample size; the same report that set the floor showed two seeds of one config landing at 249,913 and
214,923 either side of a baseline.

Normalising for the 2.83% area difference makes it slightly worse, not better (-13.5%), so the
result is not an artefact of the wider strip.

## One post-hoc observation, flagged as post-hoc

`overall_column_score` fell **46.6%**, which would exceed the 26.9% floor implied by that quantity's
seed CV of 0.1343. Two reasons it is not claimed here:

1. **It was not pre-registered for this arm.** The registered quantity is `total_fg_pixels` with the
   21.7% floor. Promoting whichever unregistered observable happened to move is the exact failure
   this project's decision rules exist to prevent.
2. **The floor is transferred from a different region.** Every CV on record was measured on
   w010-w019. Nothing establishes that the outer windings are equally stable, and there is positive
   reason to doubt it: the outer ten are where duplicate coverage concentrates, and column detection
   looks for ~850px columns in a strip whose detected median column width is 278px (BASE) against
   256px (GAP), nowhere near the target in either arm.

It is recorded so a later, properly registered arm can look at it, not as a finding.

## What would answer the question

A single pair cannot clear a 21.7% floor except for a large effect. Answering properly needs **three
seeds per arm, six fits, about nine hours**, per `reports/two_seed_check_lets_through_one_in_six.md`.
The honest value of this arm is that it measures the right region at all.

## Cost and tooling, which the outer windings changed

Both were new obstacles, and both are documented in `repro/spiral_render/README.md` section 7 with
the patch in `repro/spiral_render/serial_folds.patch`:

* **The stock scorer OOMs at this size.** Three fold subprocesses hold the whole strip's logits at
  once; on a 32GB box memory reached 30.9GB and a fold died with rc=-9. `INK_METRIC_SERIAL_FOLDS=1`
  runs folds one at a time and accumulates the ensemble in place, peaking at 18.8GB.
* **The scorer is not bit-deterministic, patched or not.** Three runs over one fixed inner strip gave
  `total_fg_pixels` 249,913 / 249,905 / 249,906, spread **0.0032%**. The **stock** path also failed to
  reproduce its own earlier number, so the drift is nnU-Net on GPU and not the patch. Against the
  1.42% floor for a full render+score re-run, essentially all of that 1.42% is the render.
* **Rendering ten outer windings took 2h02m** against about 8 minutes for ten inner ones;
  `vc_render_tifxyz` reached 26.1GB RSS and the box swapped.

## Limits

One fit per arm, one dataset, one ROI. The outer ten windings are also where duplicate coverage
concentrates (median wmax 126), so the region is atypical in a way that could affect ink scoring
independently of the config change. Outer-winding ink density is about half the inner windings'
(0.508% against ~0.93%), so no number here is comparable to any previously reported `total_fg_pixels`;
the arms are comparable to each other and to nothing else.
