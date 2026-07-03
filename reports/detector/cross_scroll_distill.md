# Cross-scroll distillation: diversity experiment (held-out PHerc 1667)

**All metrics are agreement-with-teacher (the released canon predictions), NOT ground-truth accuracy.** No arm trained on any PHerc-1667 data. Arms A and B use the same 4-region training budget (region *count* held constant; sampling layout differs: A = 2 segments x 2 regions on one scroll, B = 4 segments x 1 region across two scrolls). Caveat: the held-out region also serves as **arm B's** best-epoch selection set, an advantage arms A and the legacy baseline do not get — so the most robust comparison is **arm B vs the legacy baseline** (AP-lift 2.12 vs 1.47, roc_auc 0.689 vs 0.591), which needs no selection asymmetry to hold. AP and roc_auc are threshold-free.

Teacher provenance: `scroll1/20230702185753` uint8 range [0,248]; `scroll1/20231005123336` uint8 range [0,250]; `pherc0139/20250108000000-w025_2025010863` uint8 range [0,245]; `pherc0139/20250108000001-w026_2025010854` uint8 range [0,246]; `pherc1667/20240304141531-w013_20240304141531_flatboi` uint8 range [0,245]; `pherc0139/20250108000002-w027_2025010845` uint8 range [0,244]. Labels binarized at >= 128 after uint8 scaling.

Held-out: `pherc1667_20240304141531-w013_20240304141531_flatboi_y4000_x2500`  |  arm B best ckpt: `detector_epoch=7.ckpt`

| model (on held-out 1667) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| legacy detector (no distillation) | 0.2055 | 0.2035 | 0.1468 | 1.4671 | 0.1333 | 0.4480 | 0.1000 | 0.5909 |
| arm A: Scroll-1 student (existing) | 0.1925 | 0.1903 | 0.1217 | 1.2162 | 0.1259 | 0.4089 | 0.1000 | 0.5512 |
| arm B: multi-scroll student (2xScroll1 + 2xPHerc0139) | 0.2781 | 0.2748 | 0.2119 | 2.1178 | 0.2089 | 0.4160 | 0.1000 | 0.6890 |

Secondary (same-scroll read-outs):

| model / fragment | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| arm B on held-out PHerc-0139 region | 0.2625 | 0.2275 | 0.2261 | 5.6570 | 0.2825 | 0.2451 | 0.0400 | 0.7496 |
| arm B on Phase-2 held-out Scroll-1 region | 0.5884 | 0.5863 | 0.6450 | 2.8195 | 0.5530 | 0.6286 | 0.2288 | 0.8202 |
| arm A on Phase-2 held-out Scroll-1 region | 0.6616 | 0.6583 | 0.7417 | 3.2419 | 0.6586 | 0.6647 | 0.2288 | 0.8652 |

Renders (held-out 1667): [arm B](xscroll_armB_1667.png) | [arm A](xscroll_armA_1667.png) | [teacher](xscroll_teacher_1667.png).
