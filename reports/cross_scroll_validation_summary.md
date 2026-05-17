# Cross-Scroll Consistency Validation

This report measures the consistency between the autoresearch model's ink predictions and an independent CT-derived fiber-label signal (from PR ScrollPrize/villa#922's `generate_fiber_labels_from_ct.py`). For each ranked Scroll 2 / Scroll 3 candidate region, the metric `ink_anti_fiber_ratio` is the ratio of the model's mean ink prediction in non-fiber regions to its mean prediction in fiber regions. Real ink sits on the surface above fiber bundles, so a value greater than 1 indicates the model's predictions concentrate in non-fiber regions (consistent), while a value at or below 1 indicates predictions are uniform or biased toward fiber regions (inconsistent).

This is a *consistency* metric, not a ground-truth Dice or `val_bpb`. There is no manual ink ground truth for Scroll 2 / Scroll 3 (that is the prize problem). The fiber label is purely Frangi vesselness on CT, independent of the ink model.

## Aggregate (per scroll + division)

| Scroll | Division | N | mean ink_pred | mean fiber | mean anti-fiber ratio | stdev ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| PHerc0125 | div_100 | 5 | 0.0222 | 0.0001 | 0.804 | 0.300 |
| PHerc0125 | div_90 | 5 | 0.0427 | 0.0002 | 0.890 | 0.234 |
| PHerc0332 | div_90 | 2 | 0.0210 | 0.0000 | 1.787 | n/a |

## Per-candidate

| Idx | Stem | Scroll/Div | (z,y,x) | ink_pred_mean | fiber_mean | ink_in_fiber | ink_in_nonfiber | anti-fiber ratio | status |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | pred_18176_4128_4128_64x64 | PHerc0125/div_90 | (18176,4128,4128) | 0.1048 | 0.0004 | 0.1068 | 0.1048 | 0.981 | OK |
| 1 | pred_18176_4128_4000_64x64 | PHerc0125/div_90 | (18176,4128,4000) | 0.0445 | 0.0001 | 0.0497 | 0.0444 | 0.894 | OK |
| 2 | pred_18176_4000_4128_64x64 | PHerc0125/div_90 | (18176,4000,4128) | 0.0211 | 0.0002 | 0.0340 | 0.0210 | 0.617 | OK |
| 3 | pred_20224_4000_4128_64x64 | PHerc0125/div_100 | (20224,4000,4128) | 0.0203 | 0.0000 | 0.0201 | 0.0203 | 1.008 | OK |
| 4 | pred_18176_4000_4000_64x64 | PHerc0125/div_90 | (18176,4000,4000) | 0.0226 | 0.0001 | 0.0308 | 0.0226 | 0.735 | OK |
| 5 | pred_20224_4128_4128_64x64 | PHerc0125/div_100 | (20224,4128,4128) | 0.0256 | 0.0001 | 0.0315 | 0.0256 | 0.811 | OK |
| 6 | pred_18304_4128_4128_64x64 | PHerc0125/div_90 | (18304,4128,4128) | 0.0206 | 0.0001 | 0.0169 | 0.0207 | 1.225 | OK |
| 7 | pred_20224_4128_4000_64x64 | PHerc0125/div_100 | (20224,4128,4000) | 0.0233 | 0.0002 | 0.0228 | 0.0233 | 1.020 | OK |
| 8 | pred_20224_4000_4000_64x64 | PHerc0125/div_100 | (20224,4000,4000) | 0.0201 | 0.0000 | 0.0529 | 0.0200 | 0.379 | OK |
| 9 | pred_20096_4128_4128_64x64 | PHerc0125/div_100 | (20096,4128,4128) | 0.0219 | 0.0000 | n/a | 0.0219 | n/a | OK |
| 10 | pred_29568_7712_7712_64x64 | PHerc0332/div_90 | (29568,7712,7712) | 0.0174 | 0.0000 | n/a | 0.0174 | n/a | OK |
| 11 | pred_29568_7712_7840_64x64 | PHerc0332/div_90 | (29568,7712,7840) | 0.0245 | 0.0000 | 0.0137 | 0.0245 | 1.787 | OK |
