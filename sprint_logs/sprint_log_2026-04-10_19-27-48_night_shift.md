# Night Shift Sprint - 2026-04-10
- **Start Time**: 19:27:48
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: lr_5e-4 (REVERTED)
- **Timestamp**: 19:43:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999889, loss: 0.501735, params: 6.269M, vram: 3955.4MB, speed: 26.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: base_feat_128 (REVERTED)
- **Timestamp**: 19:58:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999549, loss: 0.503429, params: 6.269M, vram: 3955.4MB, speed: 21.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: batch_size_8 (REVERTED)
- **Timestamp**: 20:14:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.301522, loss: 0.201597, params: 6.269M, vram: 3955.4MB, speed: 13.48Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: base_feat_128 (REVERTED)
- **Timestamp**: 20:29:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999600, loss: 0.502423, params: 6.269M, vram: 3955.4MB, speed: 35.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: dropout_0.0 (REVERTED)
- **Timestamp**: 20:44:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.999724, loss: 0.501188, params: 6.269M, vram: 2381.2MB, speed: 39.85Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: blocks_12 (REVERTED)
- **Timestamp**: 21:00:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350771, loss: 0.174994, params: 4.152M, vram: 2477.0MB, speed: 52.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: lr_5e-5 (REVERTED)
- **Timestamp**: 21:15:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999500, loss: 0.502936, params: 6.269M, vram: 3955.4MB, speed: 26.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: blocks_12 (REVERTED)
- **Timestamp**: 21:30:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.849607, loss: 0.444856, params: 4.152M, vram: 2477.0MB, speed: 52.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: batch_size_4 (REVERTED)
- **Timestamp**: 21:45:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.201834, loss: 0.176158, params: 6.269M, vram: 3955.4MB, speed: 9.40Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: dropout_0.4 (REVERTED)
- **Timestamp**: 22:01:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.300438, loss: 0.149175, params: 6.269M, vram: 3955.4MB, speed: 38.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: base_feat_32 (REVERTED)
- **Timestamp**: 22:16:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999658, loss: 0.501676, params: 0.486M, vram: 3115.9MB, speed: 38.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: lr_5e-4 (REVERTED)
- **Timestamp**: 22:31:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999773, loss: 0.503041, params: 6.269M, vram: 3955.4MB, speed: 38.43Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: base_feat_64 (REVERTED)
- **Timestamp**: 22:47:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999849, loss: 0.502166, params: 1.693M, vram: 3362.9MB, speed: 37.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: heads_12 (REVERTED)
- **Timestamp**: 22:47:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.999849, loss: 0.502166, params: 1.693M, vram: 3362.9MB, speed: 37.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: wd_0.1 (REVERTED)
- **Timestamp**: 23:02:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300369, loss: 0.167875, params: 6.269M, vram: 3955.4MB, speed: 38.26Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: blocks_10 (REVERTED)
- **Timestamp**: 23:17:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350110, loss: 0.153816, params: 3.623M, vram: 2105.8MB, speed: 61.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: wd_0.1 (REVERTED)
- **Timestamp**: 23:33:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999639, loss: 0.502178, params: 6.269M, vram: 3955.4MB, speed: 38.82Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: blocks_16 (REVERTED)
- **Timestamp**: 23:48:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350757, loss: 0.204603, params: 5.210M, vram: 3213.5MB, speed: 45.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: num_layers_16 (REVERTED)
- **Timestamp**: 00:03:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150752, loss: 0.272778, params: 6.121M, vram: 2690.0MB, speed: 26.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: heads_8 (REVERTED)
- **Timestamp**: 00:18:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350418, loss: 0.143540, params: 6.269M, vram: 3955.4MB, speed: 38.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: num_layers_16 (REVERTED)
- **Timestamp**: 00:34:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350230, loss: 0.249113, params: 6.121M, vram: 2690.0MB, speed: 27.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: dropout_0.4 (REVERTED)
- **Timestamp**: 00:49:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.999500, loss: 0.503380, params: 6.269M, vram: 3955.4MB, speed: 38.01Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: wd_0.001 (REVERTED)
- **Timestamp**: 01:04:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300772, loss: 0.122036, params: 6.269M, vram: 3955.4MB, speed: 38.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: batch_size_16 (REVERTED)
- **Timestamp**: 01:20:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350246, loss: 0.059772, params: 6.269M, vram: 3955.4MB, speed: 38.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: num_layers_24 (REVERTED)
- **Timestamp**: 01:35:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999697, loss: 0.501165, params: 6.269M, vram: 3955.4MB, speed: 38.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: batch_size_16 (REVERTED)
- **Timestamp**: 01:50:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999702, loss: 0.503713, params: 6.269M, vram: 3955.4MB, speed: 38.19Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: wd_0.1 (REVERTED)
- **Timestamp**: 02:05:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300054, loss: 0.146357, params: 6.269M, vram: 3955.4MB, speed: 38.30Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: blocks_12 (REVERTED)
- **Timestamp**: 02:21:06
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450631, loss: 0.146989, params: 4.152M, vram: 2477.0MB, speed: 55.39Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: blocks_10 (REVERTED)
- **Timestamp**: 02:36:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.151278, loss: 0.284403, params: 3.623M, vram: 2105.8MB, speed: 62.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: batch_size_16 (REVERTED)
- **Timestamp**: 02:51:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.201083, loss: 0.250371, params: 6.269M, vram: 3955.4MB, speed: 37.95Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: patch_size_96 (REVERTED)
- **Timestamp**: 03:06:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150762, loss: 0.204244, params: 6.269M, vram: 3955.4MB, speed: 38.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: base_feat_32 (REVERTED)
- **Timestamp**: 03:22:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999696, loss: 0.502386, params: 0.486M, vram: 3115.9MB, speed: 38.14Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: base_feat_128 (REVERTED)
- **Timestamp**: 03:37:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300737, loss: 0.145486, params: 6.269M, vram: 3955.4MB, speed: 38.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: heads_8 (REVERTED)
- **Timestamp**: 03:52:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999357, loss: 0.502799, params: 6.269M, vram: 3955.4MB, speed: 37.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: batch_size_8 (REVERTED)
- **Timestamp**: 04:08:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999937, loss: 0.500906, params: 6.269M, vram: 3955.4MB, speed: 19.41Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 36: dropout_0.0 (REVERTED)
- **Timestamp**: 04:23:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.350627, loss: 0.246716, params: 6.269M, vram: 2381.2MB, speed: 40.74Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 37: heads_8 (REVERTED)
- **Timestamp**: 04:38:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.550033, loss: 0.153163, params: 6.269M, vram: 3955.4MB, speed: 38.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 38: lr_1e-4 (REVERTED)
- **Timestamp**: 04:53:53
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999090, loss: 0.504121, params: 6.269M, vram: 3955.4MB, speed: 38.32Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 39: lr_5e-5 (REVERTED)
- **Timestamp**: 05:09:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999677, loss: 0.502916, params: 6.269M, vram: 3955.4MB, speed: 38.27Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 40: dropout_0.1 (REVERTED)
- **Timestamp**: 05:24:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350317, loss: 0.164245, params: 6.269M, vram: 3955.4MB, speed: 38.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 41: dropout_0.4 (REVERTED)
- **Timestamp**: 05:39:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.449992, loss: 0.171467, params: 6.269M, vram: 3955.4MB, speed: 38.14Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 42: lr_5e-5 (REVERTED)
- **Timestamp**: 05:55:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999672, loss: 0.503674, params: 6.269M, vram: 3955.4MB, speed: 38.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 43: heads_8 (REVERTED)
- **Timestamp**: 06:10:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999797, loss: 0.502644, params: 6.269M, vram: 3955.4MB, speed: 38.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 44: patch_size_64 (REVERTED)
- **Timestamp**: 06:25:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999425, loss: 0.504732, params: 6.023M, vram: 1141.0MB, speed: 17.34Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 45: num_layers_16 (REVERTED)
- **Timestamp**: 06:40:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300221, loss: 0.216110, params: 6.121M, vram: 2690.0MB, speed: 26.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 46: wd_0.01 (REVERTED)
- **Timestamp**: 06:56:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400229, loss: 0.274793, params: 6.269M, vram: 3955.4MB, speed: 38.47Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 47: patch_size_64 (SUCCESS)
- **Timestamp**: 07:11:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.002509, loss: 0.241708, params: 6.023M, vram: 1141.0MB, speed: 17.28Mvps
- **Result**: Improvement detected. Changes committed.

