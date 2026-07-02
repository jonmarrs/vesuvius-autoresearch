# Distilled detector vs teacher (held-out SOTA segment region)

**All metrics are agreement-with-teacher (the released canon prediction), NOT ground-truth accuracy.**

Teacher provenance: `20230702185753` uint8 range [0,248]; `20231005123336` uint8 range [0,250]; `20231210121321` uint8 range [0,247]. Labels binarized at >= 128 after uint8 scaling.

Note: the held-out region also serves as the best-epoch selection set; AP and roc_auc are threshold-free and unaffected by threshold tuning.

Held-out: `20231210121321_y4000_x2500`  |  best student ckpt: `detector_epoch=9.ckpt`

| model | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| current detector (baseline) | 0.3724 | 0.3104 | 0.2242 | 0.9801 | 0.2288 | 1.0000 | 0.2288 | 0.4992 |
| distilled student | 0.6616 | 0.6583 | 0.7417 | 3.2419 | 0.6586 | 0.6647 | 0.2288 | 0.8652 |

Renders: [ours](sota_distill_ours.png) vs [teacher](sota_distill_teacher.png).
