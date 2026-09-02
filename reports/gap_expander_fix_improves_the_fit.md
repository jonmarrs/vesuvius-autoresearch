# Fixing villa's config warning measurably improves the fit, on three seeds

> **Update, 2026-09-02.** A third seed, `gap133s3`, was fitted to supply the ink arm registered in
> `2026-09-02_gap_fix_ink_six_fits.md`, and its pre-registered control re-tested this result:
> `satisfied_area` **0.8489**, **+9.8 sd**. The two sets remain completely disjoint at 3 against 4.
> The table below is the two-seed version as originally published; the third seed is added to it.

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
