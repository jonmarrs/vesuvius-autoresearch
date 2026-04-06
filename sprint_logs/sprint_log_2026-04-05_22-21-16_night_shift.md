# Night Shift Sprint - 2026-04-05
- **Start Time**: 22:21:16
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: patch_size_96 (REVERTED)
- **Timestamp**: 22:36:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350825, loss: 0.134212, params: 6.121M, vram: 2690.0MB, speed: 4.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: dropout_0.2 (REVERTED)
- **Timestamp**: 22:52:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.350239, loss: 0.157470, params: 6.121M, vram: 2690.0MB, speed: 7.32Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: batch_size_4 (REVERTED)
- **Timestamp**: 23:07:55
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350040, loss: 0.159439, params: 6.121M, vram: 2690.0MB, speed: 3.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: dropout_0.4 (REVERTED)
- **Timestamp**: 23:23:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.300386, loss: 0.164966, params: 6.121M, vram: 2690.0MB, speed: 7.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: patch_size_128 (REVERTED)
- **Timestamp**: 23:38:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999328, loss: 0.502955, params: 6.351M, vram: 7163.5MB, speed: 12.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: lr_1e-4 (REVERTED)
- **Timestamp**: 23:54:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999636, loss: 0.502268, params: 6.121M, vram: 2690.0MB, speed: 7.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: wd_0.01 (REVERTED)
- **Timestamp**: 00:09:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400792, loss: 0.158133, params: 6.121M, vram: 2690.0MB, speed: 7.95Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: heads_4 (REVERTED)
- **Timestamp**: 00:25:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999778, loss: 0.502315, params: 6.121M, vram: 1784.1MB, speed: 7.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_128 (REVERTED)
- **Timestamp**: 00:40:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350469, loss: 0.183717, params: 6.351M, vram: 7163.5MB, speed: 13.53Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: wd_0.0 (REVERTED)
- **Timestamp**: 00:55:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350032, loss: 0.122291, params: 6.121M, vram: 2690.0MB, speed: 8.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: base_feat_64 (REVERTED)
- **Timestamp**: 01:11:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999858, loss: 0.502644, params: 1.619M, vram: 2253.7MB, speed: 7.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: wd_0.1 (REVERTED)
- **Timestamp**: 01:26:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400834, loss: 0.223602, params: 6.121M, vram: 2690.0MB, speed: 7.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: batch_size_4 (REVERTED)
- **Timestamp**: 01:42:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999852, loss: 0.502864, params: 6.121M, vram: 2690.0MB, speed: 3.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: blocks_12 (REVERTED)
- **Timestamp**: 01:57:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.299998, loss: 0.274589, params: 4.005M, vram: 1688.3MB, speed: 9.84Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: num_layers_24 (REVERTED)
- **Timestamp**: 02:12:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999822, loss: 0.503129, params: 6.269M, vram: 3955.4MB, speed: 9.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: base_feat_64 (REVERTED)
- **Timestamp**: 02:28:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999742, loss: 0.504156, params: 1.619M, vram: 2253.7MB, speed: 7.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: blocks_16 (REVERTED)
- **Timestamp**: 02:43:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250485, loss: 0.120344, params: 5.063M, vram: 2189.3MB, speed: 8.88Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: heads_12 (REVERTED)
- **Timestamp**: 02:43:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.250485, loss: 0.120344, params: 5.063M, vram: 2189.3MB, speed: 8.88Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: dropout_0.0 (REVERTED)
- **Timestamp**: 02:59:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.999880, loss: 0.501857, params: 6.121M, vram: 1627.1MB, speed: 8.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: dropout_0.1 (REVERTED)
- **Timestamp**: 03:14:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999660, loss: 0.503622, params: 6.121M, vram: 2690.0MB, speed: 7.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: blocks_10 (REVERTED)
- **Timestamp**: 03:30:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350967, loss: 0.198928, params: 3.475M, vram: 1436.2MB, speed: 11.24Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: num_layers_12 (REVERTED)
- **Timestamp**: 03:45:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350735, loss: 0.270551, params: 6.047M, vram: 2019.5MB, speed: 6.65Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: lr_5e-5 (REVERTED)
- **Timestamp**: 04:00:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999867, loss: 0.502339, params: 6.121M, vram: 2690.0MB, speed: 8.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: dropout_0.0 (REVERTED)
- **Timestamp**: 04:16:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.400467, loss: 0.204431, params: 6.121M, vram: 1627.1MB, speed: 8.44Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: blocks_20 (REVERTED)
- **Timestamp**: 04:31:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200318, loss: 0.199711, params: 6.121M, vram: 2690.0MB, speed: 8.14Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: base_feat_128 (REVERTED)
- **Timestamp**: 04:46:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400581, loss: 0.146744, params: 6.121M, vram: 2690.0MB, speed: 8.19Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: batch_size_16 (REVERTED)
- **Timestamp**: 05:02:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300918, loss: 0.254222, params: 6.121M, vram: 2690.0MB, speed: 15.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: heads_12 (REVERTED)
- **Timestamp**: 05:02:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.300918, loss: 0.254222, params: 6.121M, vram: 2690.0MB, speed: 15.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: dropout_0.4 (REVERTED)
- **Timestamp**: 05:18:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.350051, loss: 0.188835, params: 6.121M, vram: 2690.0MB, speed: 8.01Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: patch_size_128 (REVERTED)
- **Timestamp**: 05:33:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999745, loss: 0.502050, params: 6.351M, vram: 7163.5MB, speed: 13.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: base_feat_64 (REVERTED)
- **Timestamp**: 05:48:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999789, loss: 0.501356, params: 1.619M, vram: 2253.7MB, speed: 7.89Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: blocks_10 (REVERTED)
- **Timestamp**: 06:04:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999767, loss: 0.503400, params: 3.475M, vram: 1436.2MB, speed: 10.47Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: wd_0.01 (REVERTED)
- **Timestamp**: 06:19:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999446, loss: 0.503267, params: 6.121M, vram: 2690.0MB, speed: 7.87Mvps
- **Result**: No improvement detected. Changes reverted.

