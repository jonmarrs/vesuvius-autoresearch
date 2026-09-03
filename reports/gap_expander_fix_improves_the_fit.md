# Fixing villa's config warning measurably improves the fit, on three seeds

> **Update, 2026-09-03: now 5 gap seeds against 6 base seeds, and the sd figures below are
> CORRECTED DOWNWARD.** Fits run for the ink arms accumulated controls on this quantity, and with a
> larger base sample the effect is unchanged while its standardisation shrinks:
>
> | | n | mean | sd | range |
> |---|---:|---:|---:|---|
> | BASE | 6 | 0.83897 | 0.00167 | 0.8359-0.8404 |
> | GAP | 5 | 0.84764 | 0.00105 | 0.8465-0.8489 |
>
> Welch: **+1.034%** (absolute +0.00867), t = 10.46, df = 8.48, **p = 3.9e-06**, and the two sets are
> **completely disjoint** with 0.0061 between the highest base and the lowest gap fit.
>
> **The "+7.3 to +9.8 sd" quoted below is too large.** It divided by a base sd of 0.00095 estimated
> from only four fits. Six fits give 0.00167, and the same gap fits then sit **4.5 to 5.9 sd** above
> the base mean. The effect did not shrink; my estimate of the noise it had to clear was too small,
> which is the ordinary behaviour of a variance estimated from n=4 and the same trap that made the
> outer-winding floor wrong in the other direction.
>
> Prefer the Welch p-value to any sd multiple: it does not depend on which sample the denominator
> came from. This is an accumulating control rather than a registered arm, and no fit was excluded.

**2026-09-01.** Confirmation arm registered in
`docs/preregistration/2026-09-01_gap133_confirmation_seed.md`. **Prediction met.** The satisfaction
gain from `GAP133` reproduces, so `reports/spiral_default_config_gap_expander_shortfall.md` gains a
measured consequence.

## Result

Raising `model_gap_expander_num_windings` from **130 to 133**, the value villa's own warning asks
for, changing nothing else:

| fit | satisfied_area | vs honest mean |
|---|---:|---:|
| honest seeds (4, default config) | 0.8382 to 0.8404 | — |
| **GAP133**, default seed | **0.8480** | **+8.9 sd** |
| **GAP133S2**, seed 2 | **0.8465** | **+7.3 sd** |
| **GAP133S3**, seed 3 | **0.8489** | **+9.8 sd** |

```
honest four seeds   mean 0.83957   sd 0.00095   range 0.8382-0.8404
gap=133 three seeds mean 0.84779                range 0.8465-0.8489
```

**The two sets are disjoint**: the lowest gap=133 fit exceeds the highest honest fit. It therefore
passes the strict two-seed rule ("both beat both") from
`reports/two_seed_check_lets_through_one_in_six.md`, and passes it far more convincingly than that
rule's 16.6% null rate suggests, because that figure was computed at `total_fg_pixels`' CV of 0.1086
while this quantity's CV is **0.00114**. Using our own noise measurement to size the test is what
made two seeds sufficient here.

`satisfied_patches_fraction` moves the same way: 0.6642 and 0.6648 against an honest 0.6542 to
0.6616.

## What does NOT move

**Duplicate coverage is unaffected**: 0.0909% and 0.10%, both inside the honest 0.0897 to 0.1042%.
`GAP133`'s registered null on duplication stands, and the outer-winding concentration remains
unexplained after four dead explanations.

**The ink objective is uninterpretable here.** The two-seed mean is 232,418 against an honest 226,808,
`dT` +2.5%, far inside the 21.7% different-fit floor. Individually the two arms are 249,913 and
214,923, which straddle the honest mean. **This says nothing about ink recovery in either direction**,
and the wide spread across two seeds of the same config is itself a demonstration of why that floor
exists.

## What this establishes

villa's shipped default asks for a capacity it does not provide: `shell_outer_winding_idx = 130`
requires `model_gap_expander_num_windings >= 133`, and the default is 130. Setting it to 133 raises
the fit's own geometry diagnostic by about 0.008, seven to nine standard deviations above seed noise,
reproducibly across three seeds.

So the finding is no longer "a default that warns about itself", which could be dismissed as cosmetic.
It is a one-line config change that measurably improves fit quality on villa's own metric.

## Limits

Two fits against four, one dataset, one ROI, one architecture. It shows the change moves satisfaction,
not why: the mechanism, that dense and regularisation losses sample past the model's gap-expander
range, is a reading of the code and is not demonstrated. Satisfaction is a geometry diagnostic, and
**a better geometry score is not the same as more recovered ink** — `reports/geometry_and_ink_decouple_at_seed_scale.md`
shows the two decouple at seed scale, and the ink measurement here is inside its noise floor. Whether
this change helps the objective the loop actually optimises is **not established**.
