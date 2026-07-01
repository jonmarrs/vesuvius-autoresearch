# ResEnc Phase 1 — same-scroll vs cross-scroll

Checkpoint: `models/detector_resenc/detector_epoch=11.ckpt` (best same-scroll val_f1 of 12 epochs)
TimeSformer baseline: same-scroll val_f1 0.393 / lift 2.07; cross-scroll lift 1.29

| fragment | scroll | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|---|
| PHercParis2Fr143 | scroll2_same | 0.3693 | 0.3054 | 0.3361 | 1.9489 | 0.2726 | 0.5724 | 0.1724 | 0.6795 |
| 20230702185753 | scroll1_cross | 0.2194 | 0.1959 | 0.1293 | 1.1551 | 0.1283 | 0.7575 | 0.1120 | 0.5696 |
