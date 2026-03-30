# Day Shift Sprint - 2026-03-28
- **Start Time**: 23:19:05
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: blocks_10 (REVERTED)
- **Timestamp**: 23:34:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150265, loss: 0.142095, params: 3.475M, vram: 1436.2MB, speed: 12.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: blocks_10 (REVERTED)
- **Timestamp**: 23:50:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400075, loss: 0.121374, params: 3.475M, vram: 1436.2MB, speed: 17.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: num_layers_16 (REVERTED)
- **Timestamp**: 00:05:53
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.251276, loss: 0.328989, params: 6.121M, vram: 2690.0MB, speed: 10.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: heads_12 (REVERTED)
- **Timestamp**: 00:06:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: batch_size_16 (REVERTED)
- **Timestamp**: 00:21:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999639, loss: 0.502526, params: 6.121M, vram: 2690.0MB, speed: 21.30Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: blocks_12 (REVERTED)
- **Timestamp**: 00:37:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999381, loss: 0.503220, params: 4.005M, vram: 1688.3MB, speed: 15.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: dropout_0.4 (REVERTED)
- **Timestamp**: 00:53:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.350231, loss: 0.132094, params: 6.121M, vram: 2690.0MB, speed: 10.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: dropout_0.1 (REVERTED)
- **Timestamp**: 01:08:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150834, loss: 0.226011, params: 6.121M, vram: 2690.0MB, speed: 10.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: lr_1e-3 (REVERTED)
- **Timestamp**: 01:24:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.349997, loss: 0.203753, params: 6.121M, vram: 2690.0MB, speed: 10.87Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: base_feat_128 (REVERTED)
- **Timestamp**: 01:39:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.351477, loss: 0.200683, params: 6.121M, vram: 2690.0MB, speed: 10.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: base_feat_128 (REVERTED)
- **Timestamp**: 01:55:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.301419, loss: 0.251381, params: 6.121M, vram: 2690.0MB, speed: 10.79Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: batch_size_4 (REVERTED)
- **Timestamp**: 02:10:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400561, loss: 0.160771, params: 6.121M, vram: 2690.0MB, speed: 5.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: blocks_12 (REVERTED)
- **Timestamp**: 02:26:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999740, loss: 0.502150, params: 4.005M, vram: 1688.3MB, speed: 15.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: wd_0.1 (REVERTED)
- **Timestamp**: 02:42:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200313, loss: 0.137372, params: 6.121M, vram: 2690.0MB, speed: 10.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: dropout_0.1 (REVERTED)
- **Timestamp**: 02:57:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.351055, loss: 0.237206, params: 6.121M, vram: 2690.0MB, speed: 10.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: batch_size_16 (REVERTED)
- **Timestamp**: 03:13:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.550092, loss: 0.205339, params: 6.121M, vram: 2690.0MB, speed: 21.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: batch_size_8 (REVERTED)
- **Timestamp**: 03:29:08
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999440, loss: 0.504500, params: 6.121M, vram: 2690.0MB, speed: 10.87Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: lr_5e-5 (REVERTED)
- **Timestamp**: 03:44:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999642, loss: 0.504356, params: 6.121M, vram: 2690.0MB, speed: 11.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: dropout_0.4 (REVERTED)
- **Timestamp**: 04:00:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.451247, loss: 0.205558, params: 6.121M, vram: 2690.0MB, speed: 10.79Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: heads_12 (REVERTED)
- **Timestamp**: 04:00:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: wd_0.0 (REVERTED)
- **Timestamp**: 04:16:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999629, loss: 0.502488, params: 6.121M, vram: 2690.0MB, speed: 11.07Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: batch_size_16 (REVERTED)
- **Timestamp**: 04:32:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.399998, loss: 0.106400, params: 6.121M, vram: 2690.0MB, speed: 21.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: base_feat_128 (REVERTED)
- **Timestamp**: 04:47:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999749, loss: 0.503660, params: 6.121M, vram: 2690.0MB, speed: 10.17Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: heads_4 (REVERTED)
- **Timestamp**: 05:03:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.450250, loss: 0.233232, params: 6.121M, vram: 1784.1MB, speed: 10.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: base_feat_64 (REVERTED)
- **Timestamp**: 05:19:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300382, loss: 0.110050, params: 1.619M, vram: 2253.7MB, speed: 10.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: base_feat_128 (REVERTED)
- **Timestamp**: 05:35:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250354, loss: 0.163707, params: 6.269M, vram: 3955.4MB, speed: 14.30Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: batch_size_4 (REVERTED)
- **Timestamp**: 05:51:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999512, loss: 0.503747, params: 6.121M, vram: 2690.0MB, speed: 5.50Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: blocks_16 (REVERTED)
- **Timestamp**: 06:07:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999806, loss: 0.501563, params: 5.063M, vram: 2189.3MB, speed: 13.01Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: blocks_12 (REVERTED)
- **Timestamp**: 06:22:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.299907, loss: 0.199365, params: 4.005M, vram: 1688.3MB, speed: 15.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: lr_1e-5 (REVERTED)
- **Timestamp**: 06:38:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999484, loss: 0.501922, params: 6.351M, vram: 7163.5MB, speed: 11.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: patch_size_96 (REVERTED)
- **Timestamp**: 06:54:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999818, loss: 0.501986, params: 3.475M, vram: 1436.2MB, speed: 16.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: dropout_0.0 (REVERTED)
- **Timestamp**: 07:10:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.300412, loss: 0.139404, params: 6.121M, vram: 1627.1MB, speed: 11.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: wd_0.01 (REVERTED)
- **Timestamp**: 07:26:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999815, loss: 0.504133, params: 6.121M, vram: 2690.0MB, speed: 11.58Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: patch_size_128 (REVERTED)
- **Timestamp**: 07:41:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.650809, loss: 0.270761, params: 6.351M, vram: 7163.5MB, speed: 20.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: blocks_16 (REVERTED)
- **Timestamp**: 07:57:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300235, loss: 0.192829, params: 5.063M, vram: 2189.3MB, speed: 14.58Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 36: blocks_20 (REVERTED)
- **Timestamp**: 08:12:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350950, loss: 0.218062, params: 6.121M, vram: 2690.0MB, speed: 11.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 37: heads_4 (REVERTED)
- **Timestamp**: 08:28:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999593, loss: 0.503743, params: 6.121M, vram: 1784.1MB, speed: 12.19Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 38: lr_1e-3 (REVERTED)
- **Timestamp**: 08:44:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.351987, loss: 0.232710, params: 6.121M, vram: 2690.0MB, speed: 11.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 39: num_layers_16 (REVERTED)
- **Timestamp**: 08:59:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.251237, loss: 0.248979, params: 6.121M, vram: 2690.0MB, speed: 12.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 40: num_layers_24 (REVERTED)
- **Timestamp**: 09:15:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400136, loss: 0.169816, params: 6.269M, vram: 3955.4MB, speed: 16.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 41: wd_0.0 (REVERTED)
- **Timestamp**: 09:31:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400847, loss: 0.198158, params: 6.121M, vram: 2690.0MB, speed: 11.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 42: blocks_10 (REVERTED)
- **Timestamp**: 09:46:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.351037, loss: 0.144795, params: 3.475M, vram: 1436.2MB, speed: 17.31Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 43: dropout_0.2 (REVERTED)
- **Timestamp**: 10:02:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.500096, loss: 0.070987, params: 6.121M, vram: 2690.0MB, speed: 6.02Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 44: patch_size_128 (REVERTED)
- **Timestamp**: 10:18:15
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.451411, loss: 0.247772, params: 6.351M, vram: 7163.5MB, speed: 19.67Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 45: blocks_12 (REVERTED)
- **Timestamp**: 10:33:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250254, loss: 0.087285, params: 4.005M, vram: 1688.3MB, speed: 13.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 46: lr_1e-3 (REVERTED)
- **Timestamp**: 10:49:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999779, loss: 0.501621, params: 6.121M, vram: 2690.0MB, speed: 9.48Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 47: num_layers_12 (REVERTED)
- **Timestamp**: 11:04:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999738, loss: 0.501870, params: 6.047M, vram: 2019.5MB, speed: 9.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 48: batch_size_4 (REVERTED)
- **Timestamp**: 11:20:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999871, loss: 0.502414, params: 6.121M, vram: 2690.0MB, speed: 5.89Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 49: dropout_0.0 (REVERTED)
- **Timestamp**: 11:36:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.350267, loss: 0.068022, params: 6.121M, vram: 1627.1MB, speed: 12.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 50: num_layers_16 (REVERTED)
- **Timestamp**: 11:51:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999633, loss: 0.503152, params: 6.121M, vram: 2690.0MB, speed: 12.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 51: batch_size_4 (REVERTED)
- **Timestamp**: 12:06:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999570, loss: 0.502295, params: 6.121M, vram: 2690.0MB, speed: 6.38Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 52: heads_8 (REVERTED)
- **Timestamp**: 12:22:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300287, loss: 0.105694, params: 6.121M, vram: 2690.0MB, speed: 12.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 53: patch_size_128 (REVERTED)
- **Timestamp**: 12:37:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400791, loss: 0.160122, params: 6.351M, vram: 7163.5MB, speed: 21.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 54: batch_size_4 (REVERTED)
- **Timestamp**: 12:53:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350072, loss: 0.254517, params: 6.121M, vram: 2690.0MB, speed: 6.40Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 55: heads_12 (REVERTED)
- **Timestamp**: 12:53:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.350072, loss: 0.254517, params: 6.121M, vram: 2690.0MB, speed: 6.40Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 56: blocks_20 (REVERTED)
- **Timestamp**: 13:09:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400096, loss: 0.069726, params: 6.121M, vram: 2690.0MB, speed: 12.95Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 57: batch_size_4 (REVERTED)
- **Timestamp**: 13:24:53
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400575, loss: 0.239945, params: 6.121M, vram: 2690.0MB, speed: 6.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 58: dropout_0.4 (REVERTED)
- **Timestamp**: 13:40:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.150018, loss: 0.145310, params: 6.121M, vram: 2690.0MB, speed: 13.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 59: heads_8 (REVERTED)
- **Timestamp**: 13:55:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450000, loss: 0.090549, params: 6.121M, vram: 2690.0MB, speed: 12.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 60: blocks_20 (REVERTED)
- **Timestamp**: 14:11:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999669, loss: 0.501962, params: 6.121M, vram: 2690.0MB, speed: 13.15Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 61: num_layers_24 (REVERTED)
- **Timestamp**: 14:27:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150365, loss: 0.192234, params: 6.269M, vram: 3955.4MB, speed: 18.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 62: blocks_12 (REVERTED)
- **Timestamp**: 14:42:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300184, loss: 0.166530, params: 4.005M, vram: 1688.3MB, speed: 18.74Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 63: wd_0.01 (REVERTED)
- **Timestamp**: 14:57:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350097, loss: 0.214304, params: 6.121M, vram: 2690.0MB, speed: 13.11Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 64: blocks_10 (REVERTED)
- **Timestamp**: 15:13:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200757, loss: 0.301020, params: 3.475M, vram: 1436.2MB, speed: 21.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 65: base_feat_64 (REVERTED)
- **Timestamp**: 15:28:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400236, loss: 0.126984, params: 1.619M, vram: 2253.7MB, speed: 12.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 66: lr_1e-3 (REVERTED)
- **Timestamp**: 15:44:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300580, loss: 0.107722, params: 6.121M, vram: 2690.0MB, speed: 12.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 67: lr_1e-4 (REVERTED)
- **Timestamp**: 15:59:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999750, loss: 0.502345, params: 6.121M, vram: 2690.0MB, speed: 12.84Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 68: batch_size_8 (REVERTED)
- **Timestamp**: 16:15:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999757, loss: 0.501557, params: 6.121M, vram: 2690.0MB, speed: 13.06Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 69: lr_5e-5 (REVERTED)
- **Timestamp**: 16:31:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999692, loss: 0.503193, params: 6.121M, vram: 2690.0MB, speed: 12.82Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 70: wd_0.0 (REVERTED)
- **Timestamp**: 16:46:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350780, loss: 0.124397, params: 6.121M, vram: 2690.0MB, speed: 12.42Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 71: blocks_16 (REVERTED)
- **Timestamp**: 17:02:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.302066, loss: 0.166617, params: 5.063M, vram: 2189.3MB, speed: 15.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 72: blocks_16 (REVERTED)
- **Timestamp**: 17:17:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999828, loss: 0.501790, params: 5.063M, vram: 2189.3MB, speed: 15.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 73: batch_size_16 (REVERTED)
- **Timestamp**: 17:33:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999437, loss: 0.503475, params: 6.121M, vram: 2690.0MB, speed: 26.01Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 74: wd_0.1 (REVERTED)
- **Timestamp**: 17:49:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999754, loss: 0.502033, params: 6.121M, vram: 2690.0MB, speed: 12.72Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 75: batch_size_4 (REVERTED)
- **Timestamp**: 18:04:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999623, loss: 0.501804, params: 6.121M, vram: 2690.0MB, speed: 6.53Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 76: base_feat_64 (REVERTED)
- **Timestamp**: 18:20:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999748, loss: 0.501949, params: 1.619M, vram: 2253.7MB, speed: 12.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 77: dropout_0.2 (REVERTED)
- **Timestamp**: 18:35:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.266090, loss: 0.343141, params: 6.121M, vram: 2690.0MB, speed: 13.16Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 78: lr_5e-4 (REVERTED)
- **Timestamp**: 18:51:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999166, loss: 0.505254, params: 6.121M, vram: 2690.0MB, speed: 13.06Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 79: lr_5e-5 (REVERTED)
- **Timestamp**: 19:06:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999649, loss: 0.502496, params: 6.121M, vram: 2690.0MB, speed: 13.14Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 PM
