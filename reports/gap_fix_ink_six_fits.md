# Does the gap-expander fix cost ink? Not established at n=7, and leaning

**2026-09-02.** Registered in `docs/preregistration/2026-09-02_gap_fix_ink_six_fits.md`, with
`scripts/analyse_gap_ink_arm.py` written and committed before `gap133s2` and `gap133s3` existed.
This is the arm that was meant to decide finding 13. **It does not decide it**, and the honest
summary is that the answer moved from "borderline" to "leaning negative, still short of the bar".

## The seven fits

| fit | arm | `satisfied_area` | `total_fg_pixels` | `fg_frac` | `line` | `col` |
|---|---|---:|---:|---:|---:|---:|
| baseline01 | BASE | 0.8398 | 1,789,206 | 0.00508 | 0.346 | 0.243 |
| seed02 | BASE | 0.8404 | 1,732,741 | 0.00470 | 0.364 | 0.154 |
| seed03 | BASE | 0.8382 | 1,620,364 | 0.00448 | 0.336 | 0.163 |
| seed04 | BASE | 0.8399 | 1,682,825 | 0.00472 | 0.358 | 0.203 |
| **gap133** | GAP | 0.8480 | 1,591,857 | 0.00440 | 0.338 | 0.130 |
| **gap133s2** | GAP | 0.8465 | 1,604,683 | 0.00429 | 0.351 | 0.177 |
| **gap133s3** | GAP | 0.8489 | 1,448,920 | 0.00409 | 0.355 | 0.198 |

Both registered gates passed: per-arm `satisfied_area` spreads 0.0022 (BASE) and 0.0024 (GAP), each
inside the 0.01 band, and the arms were **never pooled across** for that gate. The control on the new
fit passed: `gap133s3` at 0.8489 reproduces finding 12 for a third seed.

## Primary result: NOT ESTABLISHED

`total_fg_pixels`, Welch two-sided, 4 vs 3:

```
BASE mean 1,706,284      GAP mean 1,548,487
rel -9.25%,  95% CI -19.35% to +0.85%,  t = -2.565, df = 3.91, p = 0.0637
```

**p = 0.0637 does not clear alpha = 0.05, so under the rule fixed before the data the effect is not
established.** The registered null reading applies and is not softened: this arm can see effects of
about **9.0%** and no smaller, so the correct statement is *"no effect larger than roughly 9%"*,
never *"no effect"*. The observed effect is **-9.25%**, essentially exactly the detectable size — the
arm was powered for precisely this magnitude and still could not resolve it, which is what an
underpowered design looks like when the true effect sits at its threshold.

**Registered prediction: MET.** I predicted the difference of means would be negative. It is.

## The confirmatory check disagrees, and it was registered as subordinate

```
complete separation: all three GAP below all four BASE   (p = 2.86% in a named direction)
```

Every gap fit scores below every baseline fit. Under the null that has probability 1/C(7,3) = 2.86%,
which *would* clear 0.05 as a standalone test.

**It does not change the verdict, because the registration says it cannot.** The rule reads
"reported alongside and never in place of" the Welch test, precisely so that a disagreement could not
be resolved after the fact in favour of whichever test gave the nicer answer. Recording the tension
honestly: the two registered tests point the same *direction* and differ on whether it clears, and I
am bound by the one I named primary.

## Secondary metrics, clearly labelled

| metric | rel | p | note |
|---|---:|---:|---|
| `overall_fg_fraction` | **-10.28%** | **0.0249** | nominally significant |
| `overall_line_score` | -0.93% | 0.7026 | flat |
| `overall_column_score` | -11.83% | 0.4681 | swamped by its own noise |

`overall_fg_fraction` clears 0.05 on its own. **It should not be promoted to the headline**, for three
reasons: it is secondary by registration; four metrics were tested, so a Bonferroni-adjusted
threshold puts it at roughly p = 0.10, not significant; and this report's own companion finding is
that `fg_fraction` is the *noisier* of the two across seeds (CV 0.0521 against 0.0421), which makes
it the less trustworthy of the pair, not the more.

The `column` movement is large and meaningless here, exactly as finding 15 predicts: its noise is
`col_width_conformity`, a tail count evaluated three widths outside its design range.

## The exploratory hypothesis is retired

Addendum A registered a post-hoc observation — that `col_gap_contrast` was the only quantity clearing
its floor at one gap fit — as a prediction, to be tested at three.

```
BASE mean 0.8133 (CV 0.0082)   GAP mean 0.7967
rel -2.04%,  95% CI -5.54% to +1.46%,  p = 0.1536,  separation: none
```

**MISS, and recorded as one.** The n=1 observation did not survive three gap fits. The registered
consequence was written in advance and is applied without argument: it was most likely **selection
across the six quantities inspected**, and the hypothesis is **retired**. That is the value of having
registered it the same afternoon it was noticed — it cost nothing and it closed cleanly instead of
lingering as a plausible-sounding aside.

## Where finding 13 now stands

Not established, and leaning. The accumulated picture across seven fits is consistent in direction —
every gap fit below every baseline fit, every ink metric negative, the objective at -9.25% and the
normalised measure at -10.28% — but the primary test does not clear, and the arm's power runs out at
almost exactly the observed effect size.

**What would settle it:** more fits, and the requirement is now quantified rather than guessed. At
the measured outer CV of 0.0421, resolving a 9% effect at 80% power needs roughly **6 per arm**, so
five further fits (~2.5h each) plus five outer renders (~2.5h each) — about a day of compute. Whether
that is worth spending on a config change whose *geometry* benefit is already established at 7 to 10
sd is a judgement call, and this report does not make it.

## Limits

One dataset, one ROI, one winding decade, one architecture. Seven fits differing only in seed and one
config flag. The renders span two days on one machine; `gap133s2` was rendered twice after an OOM
kill and its second flatten differs from its first by 1.1%, which is inside the pipeline re-run floor
but is a real difference between it and the arms rendered once. Nothing here bears on whether the fix
helps ink on the *inner* windings, which were never the region it acts on.
