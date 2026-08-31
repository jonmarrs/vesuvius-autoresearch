# The pipeline is deterministic to 1.4%, and I applied the wrong floor to arms B and D

**2026-08-31.** Pre-registered in `docs/preregistration/2026-08-31_pipeline_determinism.md`.
Prediction met: `|dT| = 0.0142 < 0.02`.

## Result

Render and score re-run on byte-identical input meshes, verified by md5:

| run | total_fg_pixels | total_pixels | fg_fraction | line | column |
|---|---:|---:|---:|---:|---:|
| original baseline01 | 240,088 | 26,754,900 | 0.00897 | 0.438 | 0.232 |
| repeat, identical input | 236,683 | 26,754,900 | 0.00885 | 0.427 | 0.223 |

```
pipeline-only dT = -0.0142
```

`total_pixels` is *exactly* identical, so the lasagna flatten reproduces its geometry; the 1.42% is
the ink count moving, most plausibly threshold-boundary pixels under three-fold nnU-Net ensembling
and GPU non-determinism.

**Decomposition of the 18.93% seed difference: about 1.4 points pipeline, about 17.5 points fit.**
`reports/objective_seed_noise_floor.md` stands as written: that spread really is the fit.

## The error: two floors, two kinds of comparison

Yesterday I withdrew arms B and D against the 18.93% seed floor. **That was the wrong floor.**

The seed floor measures how much the score moves between *different fits*. Arms A, B, C, D and E are
all rendered from **one fit**, `baseline01`. B is A's meshes plus a copy; C is A's meshes plus a real
eleventh winding. No new fitting happens, so seed-to-seed variation cannot enter those comparisons.

| comparison | kind | applicable floor | dT | multiple |
|---|---|---|---:|---:|
| BAD 100-step vs GOOD | different fits | seed 18.93% | -0.5951 | 3.1x |
| seed02 vs baseline01 | different fits | seed 18.93% | -0.1893 | 1.0x |
| B duplicate vs A | same fit | pipeline 1.42% | +0.1259 | 8.9x |
| C honest vs A | same fit | pipeline 1.42% | +0.1283 | 9.0x |
| D duplicate vs A | same fit | pipeline 1.42% | +0.1763 | 12.4x |
| E duplicate-all vs A | same fit | pipeline 1.42% | +0.9247 | 65.1x |

**Arms B and D are reinstated.** They clear the applicable floor by 8.9x and 12.4x.

## Being careful, because this correction favours me

A correction that restores my own withdrawn results deserves more scepticism than one that costs me,
so the residual uncertainty is stated rather than glossed:

**There is no exactly-matched floor for B and D.** The 1.42% figure comes from re-running *identical*
meshes. B's concat contains eleven meshes where A's has ten, so its lasagna flatten solves a
different problem and could vary by more than 1.42%. The true floor for a same-fit,
different-mesh-set comparison lies somewhere between 1.42% and 18.93%, and probably near the low end
because the underlying fit geometry is fixed, but **I have not measured it.** So 8.9x and 12.4x are
multiples of a lower bound, not exact.

**The finding does not depend on picking a floor at all.** The claim is that the metric cannot
separate duplicated coverage from real coverage, and that rests on B against C:

```
B  duplicate, zero new papyrus   +0.1259
C  honest, a real new winding    +0.1283
   difference 0.24 percentage points
```

Both are eleven-mesh renders off the same fit, differing only in whether the eleventh mesh is a copy
or new papyrus. They land 0.24 points apart, inside even the pipeline floor. That comparison is
like-for-like and needs no external floor.

## What changes in the other reports

* `duplicate_coverage_inflates_the_objective.md`: the withdrawal banner is replaced. B and D stand,
  with the lower-bound caveat above.
* `objective_seed_noise_floor.md`: unchanged in its measurement, corrected in its consequences. The
  18.93% remains the right floor for comparing *fits*, which is what it was measured on, and remains
  the right reason the two-seed check `autoresearch.md` prescribes is load-bearing.
* `objective_does_track_fit_quality.md`: unchanged. GOOD vs BAD is a different-fits comparison and
  3.1x the seed floor is the correct statement.

## Limit

One repeat, one seed pair. Both floors are point estimates, not distributions.
