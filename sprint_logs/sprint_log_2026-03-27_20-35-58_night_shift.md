# Night Shift Sprint - 2026-03-27
- **Start Time**: 20:35:58
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: blocks_20 (REVERTED)
- **Timestamp**: 20:51:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.401071, loss: 0.196920, params: 6.121M, vram: 2690.0MB, speed: 8.27Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: patch_size_64 (REVERTED)
- **Timestamp**: 21:07:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250170, loss: 0.077729, params: 5.957M, vram: 788.9MB, speed: 4.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: batch_size_16 (REVERTED)
- **Timestamp**: 21:22:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999811, loss: 0.500856, params: 6.121M, vram: 2690.0MB, speed: 11.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: patch_size_128 (REVERTED)
- **Timestamp**: 21:38:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.499999, loss: 0.239862, params: 6.351M, vram: 7163.5MB, speed: 16.81Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: dropout_0.1 (REVERTED)
- **Timestamp**: 21:53:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150612, loss: 0.304016, params: 6.121M, vram: 2690.0MB, speed: 7.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: batch_size_16 (REVERTED)
- **Timestamp**: 22:09:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.399917, loss: 0.237574, params: 6.121M, vram: 2690.0MB, speed: 19.51Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: blocks_10 (REVERTED)
- **Timestamp**: 22:24:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350274, loss: 0.120107, params: 3.475M, vram: 1436.2MB, speed: 20.51Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: base_feat_32 (REVERTED)
- **Timestamp**: 22:39:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999941, loss: 0.501836, params: 0.449M, vram: 2085.6MB, speed: 12.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: heads_8 (REVERTED)
- **Timestamp**: 22:55:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.449999, loss: 0.204633, params: 6.121M, vram: 2690.0MB, speed: 12.30Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: dropout_0.1 (REVERTED)
- **Timestamp**: 23:10:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.151476, loss: 0.157760, params: 6.121M, vram: 2690.0MB, speed: 12.43Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: base_feat_32 (REVERTED)
- **Timestamp**: 23:26:09
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999675, loss: 0.502258, params: 0.449M, vram: 2085.6MB, speed: 12.22Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: base_feat_64 (REVERTED)
- **Timestamp**: 23:41:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999846, loss: 0.502491, params: 1.619M, vram: 2253.7MB, speed: 10.16Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: patch_size_96 (REVERTED)
- **Timestamp**: 23:57:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350001, loss: 0.081395, params: 6.121M, vram: 2690.0MB, speed: 6.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: num_layers_12 (REVERTED)
- **Timestamp**: 00:12:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.352680, loss: 0.360798, params: 6.047M, vram: 2019.5MB, speed: 8.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: lr_1e-5 (REVERTED)
- **Timestamp**: 00:28:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999602, loss: 0.501496, params: 6.121M, vram: 2690.0MB, speed: 12.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: lr_1e-4 (REVERTED)
- **Timestamp**: 00:43:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999657, loss: 0.503030, params: 6.121M, vram: 2690.0MB, speed: 12.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: dropout_0.2 (REVERTED)
- **Timestamp**: 00:58:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.200058, loss: 0.121888, params: 6.121M, vram: 2690.0MB, speed: 11.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: patch_size_64 (REVERTED)
- **Timestamp**: 01:14:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.199992, loss: 0.049791, params: 5.957M, vram: 788.9MB, speed: 5.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: base_feat_128 (REVERTED)
- **Timestamp**: 01:29:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999885, loss: 0.504020, params: 6.121M, vram: 2690.0MB, speed: 12.26Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: batch_size_4 (REVERTED)
- **Timestamp**: 01:45:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350024, loss: 0.187968, params: 6.121M, vram: 2690.0MB, speed: 6.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: heads_4 (REVERTED)
- **Timestamp**: 02:00:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999633, loss: 0.503054, params: 6.121M, vram: 1784.1MB, speed: 12.39Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: num_layers_12 (REVERTED)
- **Timestamp**: 02:15:55
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.549999, loss: 0.282110, params: 6.047M, vram: 2019.5MB, speed: 9.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: blocks_20 (REVERTED)
- **Timestamp**: 02:31:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999820, loss: 0.501548, params: 6.121M, vram: 2690.0MB, speed: 12.09Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: patch_size_96 (REVERTED)
- **Timestamp**: 02:46:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999730, loss: 0.501643, params: 6.121M, vram: 2690.0MB, speed: 11.91Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: dropout_0.2 (REVERTED)
- **Timestamp**: 03:02:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.550219, loss: 0.150567, params: 6.121M, vram: 2690.0MB, speed: 11.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: heads_4 (REVERTED)
- **Timestamp**: 03:17:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999886, loss: 0.503571, params: 6.121M, vram: 1784.1MB, speed: 12.44Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: batch_size_4 (REVERTED)
- **Timestamp**: 03:33:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200523, loss: 0.238611, params: 6.121M, vram: 2690.0MB, speed: 6.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: blocks_10 (REVERTED)
- **Timestamp**: 03:48:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350589, loss: 0.211682, params: 3.475M, vram: 1436.2MB, speed: 20.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: num_layers_24 (REVERTED)
- **Timestamp**: 04:03:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250766, loss: 0.142058, params: 6.269M, vram: 3955.4MB, speed: 16.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: dropout_0.2 (REVERTED)
- **Timestamp**: 04:19:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.200006, loss: 0.152063, params: 6.121M, vram: 2690.0MB, speed: 12.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: num_layers_24 (REVERTED)
- **Timestamp**: 04:34:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.204418, loss: 0.303185, params: 6.269M, vram: 3955.4MB, speed: 16.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: wd_0.001 (REVERTED)
- **Timestamp**: 04:50:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999763, loss: 0.502487, params: 6.121M, vram: 2690.0MB, speed: 11.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: batch_size_4 (REVERTED)
- **Timestamp**: 05:05:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999865, loss: 0.503078, params: 6.121M, vram: 2690.0MB, speed: 6.08Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: heads_8 (REVERTED)
- **Timestamp**: 05:20:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.550471, loss: 0.159470, params: 6.121M, vram: 2690.0MB, speed: 12.22Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: patch_size_128 (REVERTED)
- **Timestamp**: 05:36:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450342, loss: 0.221483, params: 6.351M, vram: 7163.5MB, speed: 20.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 36: heads_4 (REVERTED)
- **Timestamp**: 05:51:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999040, loss: 0.504743, params: 6.121M, vram: 1784.1MB, speed: 12.11Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 37: blocks_10 (REVERTED)
- **Timestamp**: 06:07:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999682, loss: 0.502179, params: 3.475M, vram: 1436.2MB, speed: 20.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 38: dropout_0.0 (REVERTED)
- **Timestamp**: 06:22:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.300483, loss: 0.198818, params: 6.121M, vram: 1627.1MB, speed: 12.34Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 39: wd_0.01 (REVERTED)
- **Timestamp**: 06:38:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999618, loss: 0.502226, params: 6.121M, vram: 2690.0MB, speed: 11.72Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 40: dropout_0.1 (REVERTED)
- **Timestamp**: 06:53:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400006, loss: 0.258245, params: 6.121M, vram: 2690.0MB, speed: 11.89Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 41: blocks_12 (REVERTED)
- **Timestamp**: 07:09:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999463, loss: 0.503739, params: 4.005M, vram: 1688.3MB, speed: 17.66Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 AM
