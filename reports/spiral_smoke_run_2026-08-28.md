# The spiral fit runs here: smoke run, 2026-08-28

**Not a result.** 100 optimizer steps against a default of 30,000, run only to establish that the
instrument works on this box with the published data and a hand-constructed scroll manifest.
Log: `spiral_out/smoke.log`.

## It ran, end to end, with no errors

```
loaded and filtered 38,442/38,616 verified patches (89.4s, peak RSS 2.84 GiB)
compact patch topology: 45,481,905 quads, 0.66 GiB host
lasagna normals: resident pool 46,769/166,244 bricks x2 channels (2.85 GiB) in 7.5s
theta topology ready (114.0s, peak RSS 7.78 GiB)
trainable parameters: 180,039,389 (720.2 MB)
step 0: loss = 3182.7  (patch_radius 839.0, abs_winding 888.1, rel_winding 699.9,
                        shell_outer 611.1, unattached_pcl_radius 108.0, dense_normals 18.6, ...)
save_mesh fitted: winding range [10, 130)
```

This retires several things the repository had only asserted:

* the constructed `spiral-scroll.json` parses and drives a real fit
* the `winding_inference` path override resolves to the published `winding_model/`
* the sidecar-derivation assumption holds: normals loaded from
  `las_008_nx.ome.zarr.respool_g4_pair` with the source zarr absent
* the absolute-winding point collections are live, `abs_winding` being the largest single loss term
  at step 0 (888.1)
* `spiral_outward_sense: "CW"` is not obviously wrong; the fit produces a winding range of
  `[10, 130)`, 120 windings, rather than an inverted or degenerate one. This is weak evidence, not
  proof: 100 steps from initialisation cannot distinguish a correct sense from one that has not yet
  had time to fail.

## Two numbers that change the plan

**A full fit is about an hour, not a day.** The displayed `0.3 it/s` is a cumulative average
dominated by 5m 21s of startup. Between iteration 1 and 88 the elapsed time moves 5m 21s to 5m 31s,
so **87 iterations in 10 seconds, roughly 8.7 it/s**. At that rate 30,000 steps is **under an
hour**, plus about six minutes of fixed startup. A real baseline is cheap.

**The pool is far smaller than even the corrected estimate.** Only **46,769 of 166,244** normals
bricks load, 2.85 GiB rather than the 10.15 GiB full-range figure, because the z-ROI restriction
applies. VRAM was never close to binding here.

## The number that matters for the pre-registration

```
satisfied_patches = 29 / 38,439  (0.1%)
```

`docs/preregistration/2026-08-28_winding_injection_conditional_on_acceptance.md` fixes rule 1: if
the count of baseline-satisfied units is `N < 30`, the study is declared **UNPOWERED** and no
`retained` ratio is reported.

**N = 29.** One below the line, on a threshold set before any fit existed.

That is not the study's answer, because this is a 100-step smoke fit and satisfaction should rise
substantially with training. It is a warning that rule 1 was not a formality: the pre-registration
called this a live risk on the basis of §4 quad-matched windows being 0% satisfied at every dr, and
the first real fit landed one unit under the threshold.

Two things follow. The injection study must run against a **converged** fit, not this one. And if
the converged `N` is still marginal, the honest outcome is UNPOWERED, which rule 1 already commits
us to reporting rather than working around.

> **SUPERSEDED 2026-08-29.** The converged fit gave `N = 25,148`, so the smoke run's 29 was an
> artifact of stopping early and rule 1 never bound. The study was then shelved unrun for an
> unrelated reason: @pmh47 confirmed the periodicity is intended. Both statements above stand as
> written; neither outcome they anticipated is what happened.

Note `satisfied_area` is 10.0% while `satisfied_patches` is 0.1%: area-level and patch-level
acceptance differ by two orders of magnitude, so **which unit the study counts is load-bearing**.
The pre-registration says quads and patches are scored separately, which now looks like the right
call rather than a hedge.

## Observation worth recording

**4,272 of 38,616 patches (11.1%)** emit `has multiple disconnected subrow components; using only
the component containing the center column`. The fitter silently keeps one component and discards
the rest. Not investigated here; noted because a tenth of the input geometry being partially
dropped is the kind of thing that should be known before any result rests on it.

## Deviations from villa's default, unchanged

`input_use_fibers`, `input_use_tracks` and `input_use_pcl_drawn_control_points` are all off, for the
reasons in `repro/spiral_s1/SPIRAL_SCROLL_JSON.md`. Numbers here are not comparable to villa's.
