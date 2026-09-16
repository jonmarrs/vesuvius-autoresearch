# The residual seed disagreement is part counting noise, part something real

**2026-09-16.** Registered in `docs/preregistration/2026-09-16_is_the_disagreement_counting_noise.md`,
written before the statistic was computed.

## Result

Render-clean arms (`s4–s9`), three disjoint pairs, same (z, θ) binning and derived axis (cx 4163,
cy 5004) as the normal-separation study. Fit `log|ink_A − ink_B| = a + b · log(mean ink)` over bins
with ink in both arms:

| pair | bins | ties dropped | **b** | shuffled 95% | |
|---|---:|---:|---:|---|---|
| s4–s7 | 2,398 | 31 | **0.723** | [1.009, 1.072] | differs |
| s5–s8 | 2,722 | 31 | **0.686** | [0.975, 1.039] | differs |
| s6–s9 | 2,290 | 33 | **0.802** | [1.029, 1.083] | differs |

**Median b = 0.723 → MIXED** by the registered rule. **Prediction (MIXED, leaning to the
counting-noise end): MET** — 0.723 sits 0.22 from Poisson's 0.5 and 0.28 from multiplicative's 1.0.

Ties dropped are ~1.3% of bins, reported because excluding them silently would bias `b` upward.

## What the shuffled control turned out to show

It was registered as a guard and answered a second question. **Randomly paired bins give b ≈ 1.0** —
proportional scatter is what *no relationship between the arms* looks like, since two unrelated bins
differ in rough proportion to their contents.

The observed 0.72 sits far below that, on all three pairs. **So the arms share substantial real
structure**, and the fit is measuring the data rather than the binning.

## Reading

Between-seed disagreement is **neither** a pure small-bin artefact **nor** pure relocation:

* Scatter grows **faster than √mean**, so something systematic moves ink in rough proportion to how
  much is there. Counting noise alone does not account for it.
* Scatter grows **slower than proportionally**, so a meaningful share of the disagreement *is* the
  sparse-bin effect — bins with little ink flipping between present and absent without anything
  having moved.

Combined with the two prior results, the picture for the placement instability is now:

| contribution | status |
|---|---|
| scorer | **excluded** — re-scoring one strip moves the count 0.0009% |
| tangential surface slide | **excluded** — offsets are incoherent |
| normal surface separation | **present, small** — median ρ = −0.117 |
| small-bin counting noise | **present, substantial** — b = 0.72 against Poisson 0.5 |
| remainder | still unattributed |

## What this changes about the headline number

**r ≈ 0.70 understates how much the pipeline agrees**, because part of the measured disagreement is
an artefact of binning sparse ink rather than ink being in different places. It does not overturn the
finding: the consensus result, which is what the number is used for, is unaffected — averaging works
whether the noise is Poisson or geometric, and that was confirmed forward at two values of k.

What it does mean is that **"placement reproduces at 0.70" should be read as a property of the
measurement as well as of the pipeline**, and a finer or coarser binning would move it.

## Limits

* It bounds how much room is left for a relocation mechanism; it does not identify one.
* `b` is a single exponent fitted across a wide range of bin contents; a process that is Poisson at
  low counts and multiplicative at high ones would also give an intermediate `b`, and this does not
  separate that from a genuine mixture.
* Three pairs, one scroll region — as with everything in this line.
