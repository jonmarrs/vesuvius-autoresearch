# Two nulls: fit-produced duplication could not be induced, and the search stops here

**2026-08-31.** Second and final arm of
`docs/preregistration/2026-08-31_satisfaction_vs_fit_produced_duplication.md`. **Prediction 1 failed
again. The stopping rule registered in addendum 3 fires: the search ends.**

## Result

| measurement | DENSESPACE0 | honest baseline | MINSPACE0 |
|---|---|---|---|
| gap>=2, full 120 windings | **0.04%** (4,740) | 0.0897 to 0.1042% | 0.10% |
| gap>=2, ten-winding span | **0.00%** (7 cells) | 0.00% | 0.00% |
| satisfied_area_fraction | **0.8444** | 0.8382 to 0.8404 | 0.8295 |
| satisfied_patches_fraction | 0.6631 | 0.6542 to 0.6616 | 0.6543 |
| total_fg_pixels | 205,455 | 240,088 (seed 1) | 242,128 |
| line / column | 0.398 / 0.234 | 0.438 / 0.232 | 0.432 / 0.151 |

`dT` on the objective is **-0.1443**, inside the 21.7% different-fit floor, so uninterpretable.

**Duplicate coverage FELL rather than rose**, from ~0.10% to 0.04%, more than halving. Registered
prediction 1 was a rise above 1.0%. It failed in the opposite direction.

## The manipulation is verified, but not by the condition I registered

Addendum 4 fixed the verification as: the `dense_spacing_winding_model_*` terms must appear **0
times** in the completed log. They appear **150 times**, same as honest fits. That condition was
**mis-specified**, and the correct observable is the logged loss VALUE:

```
dense_spacing_winding_model_relative   DENSESPACE0 0.0   honest 2.5    <- zeroed, as intended
dense_spacing_winding_model_density    DENSESPACE0 0.8   honest 0.5    <- still active, as intended
```

Only `loss_weight_dense_spacing` was set to 0; `loss_weight_dense_spacing_density` was deliberately
left at 12.0, and its term remains nonzero. So the change was single-variable and it took effect.

I also registered that `min_spacing` must appear 150 times to prove the barrier stayed on. It does,
but that check was worthless: its logged value is **0.0 in honest fits too**, because it is a barrier
that reads zero whenever the constraint is satisfied. A term that is zero when working cannot be used
to verify that it is switched on.

Two mis-specified verification conditions in one pre-registration, both written from an assumed
symmetry between differently-implemented loss terms rather than from reading how each is logged.

## The registered branch, and the stop

> duplication does NOT rise above 1.0% -> prediction 1 failed, nothing is learned about satisfaction

That fires. **Satisfaction did move, to 0.8444, above every honest arm.** It would be easy to read
that as the guard responding. It is not: duplication went *down*, so there was nothing for a guard to
catch, and a fit that is simultaneously higher-satisfaction and lower-duplication is simply a
different fit, not a caught cheat.

Addendum 3 registered the stop in advance:

> if this arm also returns a null, I will not keep zeroing loss weights until something moves. Two
> failures would mean duplicate coverage is not controlled by any single spacing weight

**So the search ends.** The honest conclusion is that fit-produced duplication **could not be induced
by the obvious means**, not that a third knob is worth trying.

## What is now established, and what stays open

**Established**: two of the three spacing-related loss weights were removed one at a time from a
converged fit, both verified effective, and neither raised duplicate coverage. The min-spacing
barrier left it unchanged; the dense-spacing relative term more than halved it.

**An unlooked-for observation**: removing the dense-spacing relative loss *reduced* duplicate
coverage from ~0.10% to 0.04%, well outside the honest seed range (CV 0.067). That suggests the term
contributes to duplication rather than preventing it. This was not what the arm was testing, rests on
one fit, and is offered only as a lead.

**Stays open, and is now unlikely to be closed by this approach**: whether villa's satisfaction
metrics catch duplication produced through a fit. Both arms failed to produce any, so the guard was
never presented with the thing it might catch. The limit stated in
`reports/duplicate_coverage_inflates_the_objective.md` is unchanged.

**What this says about the exploit**: the mesh-level demonstration stands, and the metric's blindness
is unaffected. But two deliberate attempts to reach that state through the fit both failed, which is
evidence, if weak, that an optimiser would not stumble into it easily. That should temper how the
duplicate-coverage finding is read.
