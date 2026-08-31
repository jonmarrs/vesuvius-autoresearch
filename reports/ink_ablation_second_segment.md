# A second segment: the members read, and the ordering was weaker evidence than I said

**2026-08-30.** Follow-up to `reports/ink_ablation_transfer_result.md`, which reported a monotone
ladder from one segment and called the ordering "suggestive rather than established". That hedge
was right. This puts a number on it, and separates two claims that the original report ran together.

## There is no second segment with scoreable human ground truth

ScrollGT's other two Scroll 1 targets, `scroll1_20230702185753` and its `y7000_x4000` crop, are both
marked `scoring enabled: False`. The reason is a property of the data, not of any model:

> Local placement error on this segment reaches ~102 level-2 px (~0.98 mm), which is ~1.9x the
> 512 um prize analysis window, so within a single window a model can be scored against ground
> truth from a different part of the sheet.

So the monotone ladder **cannot be validated** on a second segment against human labels. The
substitute is corroboration against the published canon prediction on a different segment,
`20231012184424`. Canon is a model, so agreement with it is similarity to a model, not correctness.
It is a usable reference here only because it was independently checked against our own registered
ground truth at AUC 0.8243, and because the claim under test is an ordering rather than a level.

## The members do read a second segment

Same six checkpoints, `clip(0,200)/255` at level 0, 62-slice centred window, 4096^2:

| member | tiles | seg A vs human GT | seg B vs canon |
|---|---:|---:|---:|
| it1 | 3,396 | 0.5064 | 0.4609 |
| it2 | 8,970 | 0.5317 | 0.4589 |
| it3 | 15,286 | 0.6865 | 0.5971 |
| it0 | 20,075 | 0.7184 | 0.6473 |
| it4 | 24,773 | 0.7265 | 0.6524 |
| it5 | 33,061 | 0.7276 | 0.7141 |

Every level is lower on B. That is the reference changing, not the models: canon itself only agrees
with human ground truth at 0.8243, so scoring against canon caps what is reachable.

## The right null for "does it read": roll the reference

400 draws, each a large random torus roll of the reference. Texture statistics preserved exactly,
correspondence destroyed. A member reads if it beats that distribution.

| member | seg A p | seg B p | verdict |
|---|---:|---:|---|
| it1 | 0.3675 | 0.6725 | reads neither |
| it2 | 0.0100 | 0.6625 | reads A only |
| it3 | 0.0000 | 0.0550 | reads A, borderline on B |
| it0 | 0.0000 | 0.0000 | reads both |
| it4 | 0.0000 | 0.0000 | reads both |
| it5 | 0.0000 | 0.0000 | reads both |

it5's 0.7141 on segment B beats a null whose maximum over 400 rolls is 0.5972. **The top rungs read
held-out ink on a second segment, under a control that can fail.** it1 and it2 sitting at chance on
both segments is itself a reproduction: the same two rungs were called chance in the first report.

## The ordering: I used a statistic whose null I had not looked at

Two questions were tangled together, and they need different nulls.

**Does reading ability track training-tile count?** Hold the six observed AUCs fixed and permute
which member owns which tile count. Exact over all 720 permutations:

| run | rho | p | slope/decade | p |
|---|---:|---:|---:|---:|
| seg A, 4096^2 | +1.0000 | 0.0014 | +0.2665 | 0.0014 |
| seg A, centre 2048^2 | +0.9429 | 0.0083 | +0.3088 | 0.0028 |
| seg B, 4096^2 | +0.9429 | 0.0083 | +0.2736 | 0.0042 |

The dose-response survives, on all three.

**But could a misaligned reference have produced that ordering anyway?** Apply the roll null to the
ordering statistic itself. It can, 6 to 13% of the time:

```
seg A   ladder rho +0.9429   null sd 0.7236   null p95 +0.9429   max +1.0000   p = 0.1275
seg B   ladder rho +0.9429   null sd 0.6514   null p95 +0.9429   max +1.0000   p = 0.0625
```

Six mutually correlated models get ranked coherently by *any* reference, right or wrong. The null
standard deviation of the rank statistic is 0.65 to 0.72, so with n=6 the difference between a
"clean" +0.94 and a "null" +0.77 is well under one standard deviation.

The roll null is the wrong null for the dose-response question, because it collapses every member to
~0.50 and then asks about the ordering of noise. Under it the AUC spread is ~0.03 against an observed
~0.26. So it does not overturn the label-permutation result. What it does establish is that **the
rank pattern is the weakest of the three lines of evidence, not the strongest**, and the
dose-response stands on the magnitudes.

I led with between-segment rank agreement (rho 0.943, one adjacent swap) as though it were the
headline. It carries the same defect and should not have been the headline. Four hand-picked
controls had already hinted at this, one of them returning +0.7714, and the correct response to that
was to build the null rather than to note the gap and move on.

## What changes upstream

Nothing yet reported upstream is affected, because none of this has been reported upstream. The
claim that would have gone out is narrowed:

* **stands**: the released PHerc 1667 ablation series reads held-out Scroll 1 ink, on two segments,
  above a 400-draw misalignment null, with the four highest rungs clearing on both;
* **stands, on magnitudes**: reading improves with source-scroll pseudo-label density, exact
  permutation p 0.0014 to 0.0083;
* **narrowed**: it2 reads one segment and not the other, so the bottom of the ladder is not
  established at all;
* **withdrawn as evidence**: rank agreement between segments, which a misaligned reference
  reproduces too often to carry weight at n=6.

## A documentation error in the previous report

`ink_ablation_transfer_result.md` says its table is "Same frame, no shift, 2048^2". The numbers are
the full 4096^2 frame: at 4096^2 it2 reproduces at 0.5317 against the reported 0.5317, and every
member reproduces to within 0.0034, while the centre 2048^2 crop gives it2 0.5510 and diverges by up
to 0.047. The residual ~0.003 at full frame is unexplained and is likely a threshold or mask detail;
the numbers are reproduced to that tolerance, not exactly.
