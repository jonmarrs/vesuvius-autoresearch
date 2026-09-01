# Duplicate coverage is not diffuse: 98% of it sits in the outermost windings

> **The EXPLANATION below is withdrawn, 2026-09-01. The measurement stands.**
> This report attributed the concentration to windings extrapolated past the patch data, reasoning
> that output `[10, 130)` with `output_winding_margin = 4` implies data ending at w125. That
> arithmetic is invalid: `spiral_helpers.py:1372` clamps the range by `shell_outer_winding_idx`,
> which `config.py:489` sets to the constant **130**. The bound says nothing about where the data
> ends, nothing logs the observed patch winding maximum, and the "52.5% of cells involve an
> extrapolated winding" figure is withdrawn.
>
> What survives is the measurement: the concentration in the outermost windings, median wmax 126,
> reproducible across five fits. Its cause is unknown. See
> `reports/margin_arm_void_and_a_premise_withdrawn.md`.


**2026-08-31.** Characterisation of the 0.09 to 0.10% gap>=2 overlap present in every converged fit
(`reports/a_cheap_guard_the_metrics_lack.md`). The question was whether it is diffuse background or
localised, because a few localised topology errors and uniform noise call for different responses.

It is localised, and the localisation reproduces across every fit measured.

## Result

Cell centres decoded from `measure_winding_overlap.py --dump-cells` at quant 4, radius taken from
the spiral centre (4348.8, 4844.4) measured by `scripts/measure_spiral_comparability.py`:

| fit | gap>=2 cells | median radius | beyond r=2000 | beyond r=2400 |
|---|---:|---:|---:|---:|
| baseline01 | 10,345 | 2376 | 98.3% | 45.9% |
| seed02 | 11,895 | 2381 | 98.9% | 47.3% |
| seed03 | 12,040 | 2388 | 98.7% | 47.9% |
| seed04 | 11,319 | 2376 | 98.8% | 46.1% |
| minspace0 | 11,237 | 2375 | 99.1% | 45.6% |

The fit's windings span radius ~389 (w010) to ~2504 (w129) by median. **The inner two thirds of the
spiral contain essentially no duplicate coverage**: for baseline01, 8 cells out of 10,345 sit below
radius 1735.

The median radius varies by **13 voxels across five independent fits**, including one with the
min-spacing barrier disabled. Whatever produces this is a stable property of the fitted geometry,
not seed noise and not the barrier.

## The winding indices, MEASURED rather than inferred

This report originally inferred "about w123" from radius and median spacing, and flagged that as
arithmetic rather than observation. The indices are now recorded directly
(`measure_winding_overlap.py --dump-windings`). The inference held:

```
median wmin 120   median wmax 126      (the radius inference said "about w123")
wmin range 45..127   wmax range 47..129

79.9% of cells involve a winding >= w120, the outermost ten
51.7% have BOTH windings >= w120

top pairs   w127+w129 533 cells,  w126+w128 357,  w126+w129 342,  w125+w128 289
gaps        2 -> 2,723,  3 -> 1,925,  4 -> 1,219,  5 -> 907, declining
```

So it is the outermost windings overlapping **each other** at small index gaps of 2 to 4, not
distant windings colliding. Half of all overlapping cells are claimed by two windings both inside
the last ten of the ROI.

## The likely explanation is a boundary effect, and that matters

The overlap concentrates in the **outermost ten windings of the fitted ROI**.

That is the edge of the fit, where the outermost windings have neighbours on one side only and the
least constraint from surrounding patches. **This is more likely an artefact of where the ROI stops
than a statement about scroll geometry**, and it should not be read as "the outer scroll is harder
to fit" without a fit whose ROI ends somewhere else.

A z-distribution is also non-uniform, peaking at 16819-17357 within the 13056..18432 ROI, but with a
broad spread rather than the sharp radial concentration.

## What this changes

**For the guard**: the signal it detects is concentrated and reproducible, which is a point in its
favour as a diagnostic. A fit could be checked at its outer windings specifically and far more
cheaply than 3 s.

**For the duplicate-coverage finding**: unchanged. The arms that demonstrated the metric cannot
price duplication used deliberately constructed mesh duplicates, not this background, and the
0.09% baseline is subtracted in every comparison.

**For interpreting the 0.09%**: it is not a uniform 0.09% tax on the fit. It is near-zero over most
of the spiral and concentrated in a band at its edge.

## Limits

One ROI, one scroll, five fits that share it. The boundary explanation is a hypothesis this data
cannot separate from a genuine radial effect: both predict exactly what is seen here. Distinguishing
them needs a fit over a different radial range, which has not been run. The winding indices are now measured
directly rather than inferred, and they confirm the radial picture. What remains unmeasured is
whether the same concentration appears at a different ROI boundary, which is the test that would
separate the two hypotheses.
