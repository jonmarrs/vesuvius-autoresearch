# The objective does not detectably track strip area — and my registered statistic could not have told me

**2026-09-19.** Registered in `docs/preregistration/2026-09-19_can_the_loop_win_by_enlarging_the_strip.md`,
written before the statistic was computed.

## The verdict the rule returns, and why I am not reporting it as the answer

Slope of `log(total_fg_pixels)` on `log(total_pixels)`, within tier, never pooled:

| tier | n | slope | Spearman ρ | p | area spread | ink spread |
|---|---:|---:|---:|---:|---:|---:|
| current | 15 | **+0.479** | **+0.075** | 0.791 | 1.065× | 1.269× |
| pinned | 24 | +0.308 | −0.006 | 0.977 | 1.068× | 1.266× |

The registered rule reads **PARTLY** on the current tier, and my registered prediction was PARTLY.
**That match is illusory and I am not claiming it.**

**The slope's 95% bootstrap CI is [−0.36, +1.87]**, width 2.23. It contains zero, it contains one, and
it contains every threshold in the decision rule. The pinned tier is worse: [−1.08, +1.85]. A rule
whose every branch sits inside the confidence interval of its own statistic has not decided anything.

## Why the design could not work

The predictor barely varies. **Strip area spans 6.5% across arms while ink spans 27%.** Fitting a
log-log slope through that is fitting a line through a vertical cloud: the estimate is dominated by
noise in the outcome, and its uncertainty swamps the range of interest.

I should have seen this before running it. The spreads were visible in the table I built the
registration from, and the registration even quotes them — *"fraction spans 0.0068–0.0083 within the
current tier while area spans ~6%"* — as an argument for the prediction rather than as a warning about
the instrument.

## What the data does support

**Spearman ρ is +0.075 (p = 0.79) and −0.006 (p = 0.98).** There is no detectable monotone
relationship between strip area and recovered ink at arm level, in either tier. Rank correlation
needs no x-variance assumption and is the statistic that survives here.

So the honest answer to the question asked — *can villa's loop raise its objective by enlarging the
strip?* — is **no evidence that it can**, from 39 arms across two code tiers and many configs. That is
a reassuring negative about their objective, and it is the opposite of what finding 42's bin-level
association might have suggested generalises.

**It is a weak negative, not a strong one.** With this little area variation the test could not have
detected a moderate effect either. What it rules out is a large one.

## What would actually answer it

Arms with **deliberately varied strip extent** — a config change that grows or shrinks the surface on
purpose, rather than the incidental 6% spread that fitting produces. Three arms at each of two
deliberately different extents would carry more information about this than the 39 arms here do,
because the predictor would actually move.

That is a tractable study on this hardware. It is not one I should design in the same session that
produced this one.

## Record

Four registered predictions in this line: three wrong, and this one "right" for a statistic that
could not have been wrong. **The registration did its job anyway** — it fixed the rule in advance, so
the gap between "the rule says PARTLY" and "the rule cannot discriminate" is visible rather than
something I could quietly resolve in my own favour.
