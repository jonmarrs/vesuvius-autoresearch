# Scaled multi-scroll distillation (arm C) on held-out PHerc 1667

**All metrics are agreement-with-teacher (the released canon predictions), NOT ground-truth accuracy.** No arm trained on any PHerc-1667 data. Arm C is a **capability run**: it differs from arm B in BOTH training-scroll diversity (+PHerc0172) and data volume (6 vs 4 regions) -- it is not a single-variable experiment. Caveat: the held-out region serves as the best-epoch selection set for arms B and C (not for arm A or the legacy baseline) -- the asymmetry-free anchor is the **arm-vs-legacy-baseline** comparison. Baseline/A/B rows are cited from the committed cross_scroll_distill.json, not re-run.

Teacher provenance: `scroll1/20230702185753` uint8 range [0,248]; `scroll1/20231005123336` uint8 range [0,250]; `pherc0139/20250108000000-w025_2025010863` uint8 range [0,245]; `pherc0139/20250108000001-w026_2025010854` uint8 range [0,246]; `pherc1667/20240304141531-w013_20240304141531_flatboi` uint8 range [0,245]; `pherc0139/20250108000002-w027_2025010845` uint8 range [0,244]; `pherc0172/20250917143559-w062_20250917143559205_flatboi` uint8 range [0,236]; `pherc0172/20250926112011-w078_20250926112011918_flatboi` uint8 range [0,236]; `pherc0172/20250926113336-w079_20250926113336891_flatboi` uint8 range [0,236]. Labels binarized at >= 128 after uint8 scaling.

Held-out: `pherc1667_20240304141531-w013_20240304141531_flatboi_y4000_x2500`  |  arm C best ckpt: `detector_epoch=11.ckpt`

| model (on held-out 1667) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| legacy detector (cited) | 0.2055 | 0.2035 | 0.1468 | 1.4671 | 0.1333 | 0.4480 | 0.1000 | 0.5909 |
| arm A: 1 scroll, 4 regions (cited) | 0.1925 | 0.1903 | 0.1217 | 1.2162 | 0.1259 | 0.4089 | 0.1000 | 0.5512 |
| arm B: 2 scrolls, 4 regions (cited) | 0.2781 | 0.2748 | 0.2119 | 2.1178 | 0.2089 | 0.4160 | 0.1000 | 0.6890 |
| arm C: 3 scrolls, 6 regions | 0.2716 | 0.2704 | 0.2096 | 2.0953 | 0.2052 | 0.4015 | 0.1000 | 0.6724 |

Secondary (arm C same-scroll read-outs):

| model / fragment | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| arm C on held-out PHerc-0172 region | 0.5870 | 0.5766 | 0.6389 | 5.3686 | 0.5278 | 0.6611 | 0.1190 | 0.9193 |
| arm C on held-out PHerc-0139 region | 0.2578 | 0.2385 | 0.1991 | 4.9811 | 0.2420 | 0.2757 | 0.0400 | 0.7436 |
| arm C on Phase-2 held-out Scroll-1 region | 0.6310 | 0.6086 | 0.6960 | 3.0422 | 0.6097 | 0.6540 | 0.2288 | 0.8457 |

Renders (held-out 1667): [arm C](xscroll_armC_1667.png) | [arm B](xscroll_armB_1667.png) | [arm A](xscroll_armA_1667.png) | [teacher](xscroll_teacher_1667.png).
