# Vesuvius Autoresearch: Experiment Log

Tracking mission-critical architectural changes and pretraining milestones.

| Timestamp | Model Size | val_bpb | Throughput | Notes |
|-----------|------------|---------|------------|-------|
| 2026-03-21 19:02 | 0.31M | 0.4204 | 0.00 | Initial test run with large S3 latency. |
| 2026-03-21 19:03 | 0.31M | 0.0177 | 0.05 | Block-based S3 loading (32 patches/block). |
| 2026-03-21 19:05 | 2.04M | 1.0131 | 0.00 | Scaled to 4 residual blocks. |
| 2026-03-21 19:06 | 2.04M | 0.0056 | 0.14 | Optimized block-based loading (128 patches/block). |
| 2026-03-21 19:11 | 2.04M | 0.0057 | 0.85 | 280s baseline run. Standardized TSV. |
| 2026-03-21 21:08 | 5.97M | 0.0054 | 0.48 | 1-hour deep training. 12 residual blocks. BS=8. |
| 2026-03-21 21:30 | 5.97M | 0.0169 | 0.23 | Cycle 1: Increase heads 4 -> 8. [NEW BEST for 5-min] |
| 2026-03-22 06:10 | 5.97M | 0.0079 | 0.22 | Cycle 3: Verified lr 2e-4. [NEW BEST for 5-min] |
| 2026-03-22 06:15 | 5.97M | 0.0079 | 0.22 | Cycle 4: Verified GELU in ResBlock3D. |
| 2026-03-21 21:40 | 7.94M | 0.0172 | 0.17 | Cycle 2: Increase blocks 12 -> 16. [REVERTED] |
- 2026-03-22 10:13: batch_size_6 - REVERTED
- 2026-03-22 10:39: lr_5e-4 - REVERTED
- 2026-03-22 11:09: batch_size_6 - REVERTED

## Automated Night Run (Background)
- 2026-03-22 11:15: batch_size_10 - REVERTED

## Automated Night Run (Background)
- 2026-03-22 14:49: blocks_10 - REVERTED
- 2026-03-22 14:55: wd_0.0 - **SUCCESS**
- 2026-03-22 15:00: heads_4 - **SUCCESS**
- 2026-03-22 15:05: lr_1e-4 - **SUCCESS**
- 2026-03-22 15:10: dropout_0.4 - **SUCCESS**
- 2026-03-22 15:15: batch_size_4 - **SUCCESS**
- 2026-03-22 15:20: lr_5e-4 - **SUCCESS**
- 2026-03-22 15:25: wd_0.1 - **SUCCESS**
- 2026-03-22 15:30: blocks_16 - **SUCCESS**
- 2026-03-22 15:36: dropout_0.15 - **SUCCESS**
- 2026-03-22 15:41: heads_32 - **SUCCESS**
- 2026-03-22 15:46: batch_size_12 - **SUCCESS**
- 2026-03-22 15:51: batch_size_10 - **SUCCESS**
- 2026-03-22 15:56: lr_5e-4 - **SUCCESS**
- 2026-03-22 16:01: dropout_0.0 - **SUCCESS**
- 2026-03-22 16:06: blocks_10 - **SUCCESS**
- 2026-03-22 16:11: heads_4 - **SUCCESS**
- 2026-03-22 16:17: wd_0.0 - **SUCCESS**
- 2026-03-22 16:22: batch_size_12 - **SUCCESS**
- 2026-03-22 16:27: lr_3e-4 - **SUCCESS**
- 2026-03-22 16:32: blocks_10 - **SUCCESS**
- 2026-03-22 16:37: heads_32 - **SUCCESS**
- 2026-03-22 16:42: wd_0.1 - **SUCCESS**
- 2026-03-22 16:47: dropout_0.0 - **SUCCESS**
- 2026-03-22 16:52: lr_1e-4 - **SUCCESS**
- 2026-03-22 16:58: dropout_0.0 - **SUCCESS**
- 2026-03-22 17:03: batch_size_16 - **SUCCESS**
- 2026-03-22 17:08: blocks_14 - REVERTED

## Automated Night Run (Background)

## Automated Sprint (Background - 6 Hour Run)
- 2026-03-22 18:02: wd_0.0 - REVERTED
- 2026-03-22 18:03: lr_3e-4 - REVERTED
- 2026-03-22 18:08: batch_size_4 - **SUCCESS**
- 2026-03-22 18:20: blocks_10 - REVERTED
- 2026-03-22 18:36: wd_0.0 - REVERTED
- 2026-03-22 18:45: patch_size_32 - REVERTED
- 2026-03-22 18:50: base_feat_64 - **SUCCESS**
- 2026-03-22 18:55: lr_1e-4 - **SUCCESS**
- 2026-03-22 19:00: blocks_18 - **SUCCESS**
