# Night Shift Sprint - 2026-04-04
- **Start Time**: 22:23:30
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: heads_12 (REVERTED)
- **Timestamp**: 22:24:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.999446, loss: 0.502943, params: 6.121M, vram: 2690.0MB, speed: 12.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: num_layers_16 (REVERTED)
- **Timestamp**: 22:39:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.950158, loss: 0.444530, params: 6.121M, vram: 2690.0MB, speed: 7.36Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: heads_4 (REVERTED)
- **Timestamp**: 22:55:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.301667, loss: 0.175393, params: 6.121M, vram: 1784.1MB, speed: 11.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: patch_size_96 (REVERTED)
- **Timestamp**: 23:10:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999614, loss: 0.501530, params: 6.121M, vram: 2690.0MB, speed: 11.89Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: batch_size_4 (REVERTED)
- **Timestamp**: 23:26:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999334, loss: 0.501945, params: 6.121M, vram: 2690.0MB, speed: 5.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: batch_size_16 (REVERTED)
- **Timestamp**: 23:41:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400450, loss: 0.238349, params: 6.121M, vram: 2690.0MB, speed: 23.41Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: lr_1e-4 (REVERTED)
- **Timestamp**: 23:56:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999674, loss: 0.502639, params: 6.121M, vram: 2690.0MB, speed: 11.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: patch_size_128 (REVERTED)
- **Timestamp**: 00:12:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350474, loss: 0.254583, params: 6.351M, vram: 7163.5MB, speed: 18.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_128 (REVERTED)
- **Timestamp**: 00:27:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999707, loss: 0.502291, params: 6.351M, vram: 7163.5MB, speed: 18.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: batch_size_8 (REVERTED)
- **Timestamp**: 00:42:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150647, loss: 0.249651, params: 6.121M, vram: 2690.0MB, speed: 11.43Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: patch_size_64 (REVERTED)
- **Timestamp**: 00:58:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200006, loss: 0.241860, params: 5.957M, vram: 788.9MB, speed: 5.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: dropout_0.4 (REVERTED)
- **Timestamp**: 01:13:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.999423, loss: 0.504963, params: 6.121M, vram: 2690.0MB, speed: 11.47Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: num_layers_12 (REVERTED)
- **Timestamp**: 01:29:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999910, loss: 0.502196, params: 6.047M, vram: 2019.5MB, speed: 9.02Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: patch_size_64 (REVERTED)
- **Timestamp**: 01:44:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300120, loss: 0.220737, params: 5.957M, vram: 788.9MB, speed: 5.35Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: dropout_0.2 (REVERTED)
- **Timestamp**: 01:59:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.250215, loss: 0.244828, params: 6.121M, vram: 2690.0MB, speed: 11.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: base_feat_32 (REVERTED)
- **Timestamp**: 02:15:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999691, loss: 0.502700, params: 0.449M, vram: 2085.6MB, speed: 11.61Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: blocks_10 (REVERTED)
- **Timestamp**: 02:30:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450313, loss: 0.271562, params: 3.475M, vram: 1436.2MB, speed: 18.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: num_layers_24 (REVERTED)
- **Timestamp**: 02:45:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350033, loss: 0.093831, params: 6.269M, vram: 3955.4MB, speed: 16.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: lr_1e-3 (REVERTED)
- **Timestamp**: 03:01:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250164, loss: 0.171217, params: 6.121M, vram: 2690.0MB, speed: 11.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: heads_8 (REVERTED)
- **Timestamp**: 03:16:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999556, loss: 0.504946, params: 6.121M, vram: 2690.0MB, speed: 11.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: lr_5e-5 (REVERTED)
- **Timestamp**: 03:32:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999690, loss: 0.502401, params: 6.121M, vram: 2690.0MB, speed: 11.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: heads_8 (REVERTED)
- **Timestamp**: 03:47:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300098, loss: 0.106859, params: 6.121M, vram: 2690.0MB, speed: 11.79Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: lr_1e-4 (REVERTED)
- **Timestamp**: 04:02:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999312, loss: 0.504648, params: 6.121M, vram: 2690.0MB, speed: 11.62Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: batch_size_16 (REVERTED)
- **Timestamp**: 04:18:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250000, loss: 0.306285, params: 6.121M, vram: 2690.0MB, speed: 23.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: blocks_12 (REVERTED)
- **Timestamp**: 04:33:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999740, loss: 0.504247, params: 4.005M, vram: 1688.3MB, speed: 16.43Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: dropout_0.0 (REVERTED)
- **Timestamp**: 04:48:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.400243, loss: 0.210631, params: 6.121M, vram: 1627.1MB, speed: 12.09Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: patch_size_64 (REVERTED)
- **Timestamp**: 05:04:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350003, loss: 0.176475, params: 5.957M, vram: 788.9MB, speed: 5.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: wd_0.01 (REVERTED)
- **Timestamp**: 05:19:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400225, loss: 0.125995, params: 6.121M, vram: 2690.0MB, speed: 11.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: lr_5e-4 (REVERTED)
- **Timestamp**: 05:35:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999922, loss: 0.502653, params: 6.121M, vram: 2690.0MB, speed: 11.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: heads_8 (REVERTED)
- **Timestamp**: 05:50:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300476, loss: 0.204555, params: 6.121M, vram: 2690.0MB, speed: 11.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: wd_0.0 (REVERTED)
- **Timestamp**: 06:05:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400920, loss: 0.197525, params: 6.121M, vram: 2690.0MB, speed: 11.38Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: wd_0.1 (REVERTED)
- **Timestamp**: 06:21:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250524, loss: 0.141909, params: 6.121M, vram: 2690.0MB, speed: 11.45Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: lr_5e-5 (REVERTED)
- **Timestamp**: 06:36:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999629, loss: 0.501281, params: 6.121M, vram: 2690.0MB, speed: 11.31Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: heads_4 (REVERTED)
- **Timestamp**: 06:51:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999688, loss: 0.502056, params: 6.121M, vram: 1784.1MB, speed: 11.36Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: dropout_0.1 (SUCCESS)
- **Timestamp**: 07:07:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.050932, loss: 0.192857, params: 6.121M, vram: 2690.0MB, speed: 11.24Mvps
- **Result**: Improvement detected. Changes committed.

