# Day Shift Sprint - 2026-03-28
- **Start Time**: 11:04:43
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: base_feat_64 (REVERTED)
- **Timestamp**: 11:20:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999284, loss: 0.504990, params: 1.619M, vram: 2253.7MB, speed: 7.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: num_layers_12 (REVERTED)
- **Timestamp**: 11:35:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999705, loss: 0.501692, params: 6.047M, vram: 2019.5MB, speed: 8.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: dropout_0.2 (REVERTED)
- **Timestamp**: 11:51:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.999550, loss: 0.502689, params: 6.121M, vram: 2690.0MB, speed: 11.62Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: batch_size_16 (REVERTED)
- **Timestamp**: 12:06:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150291, loss: 0.226346, params: 6.121M, vram: 2690.0MB, speed: 22.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: blocks_12 (REVERTED)
- **Timestamp**: 12:22:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999079, loss: 0.505619, params: 4.005M, vram: 1688.3MB, speed: 16.72Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: dropout_0.0 (REVERTED)
- **Timestamp**: 12:37:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.999615, loss: 0.501683, params: 6.121M, vram: 1627.1MB, speed: 12.39Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: heads_4 (REVERTED)
- **Timestamp**: 12:53:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.400038, loss: 0.173960, params: 6.121M, vram: 1784.1MB, speed: 11.88Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: base_feat_128 (REVERTED)
- **Timestamp**: 13:08:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.501636, loss: 0.183531, params: 6.121M, vram: 2690.0MB, speed: 11.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: dropout_0.1 (REVERTED)
- **Timestamp**: 13:24:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400898, loss: 0.188475, params: 6.121M, vram: 2690.0MB, speed: 11.58Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: dropout_0.4 (REVERTED)
- **Timestamp**: 13:39:53
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.999794, loss: 0.504118, params: 6.121M, vram: 2690.0MB, speed: 11.62Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: lr_1e-3 (REVERTED)
- **Timestamp**: 13:55:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150336, loss: 0.171196, params: 6.121M, vram: 2690.0MB, speed: 11.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: batch_size_4 (REVERTED)
- **Timestamp**: 14:10:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999521, loss: 0.503770, params: 6.121M, vram: 2690.0MB, speed: 5.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: num_layers_24 (REVERTED)
- **Timestamp**: 14:26:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999602, loss: 0.503453, params: 6.269M, vram: 3955.4MB, speed: 15.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: heads_12 (REVERTED)
- **Timestamp**: 14:27:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: heads_8 (REVERTED)
- **Timestamp**: 14:42:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.401110, loss: 0.152002, params: 6.121M, vram: 2690.0MB, speed: 11.79Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: batch_size_8 (REVERTED)
- **Timestamp**: 14:58:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999770, loss: 0.501685, params: 6.121M, vram: 2690.0MB, speed: 11.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: blocks_20 (REVERTED)
- **Timestamp**: 15:13:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999280, loss: 0.504084, params: 6.121M, vram: 2690.0MB, speed: 11.33Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: wd_0.01 (REVERTED)
- **Timestamp**: 15:29:08
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.201093, loss: 0.189140, params: 6.121M, vram: 2690.0MB, speed: 11.41Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: batch_size_16 (REVERTED)
- **Timestamp**: 15:44:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.299999, loss: 0.084677, params: 6.121M, vram: 2690.0MB, speed: 23.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: patch_size_64 (REVERTED)
- **Timestamp**: 16:00:08
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.206062, loss: 0.180386, params: 5.957M, vram: 788.9MB, speed: 5.24Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: wd_0.001 (REVERTED)
- **Timestamp**: 16:15:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500020, loss: 0.138031, params: 6.121M, vram: 2690.0MB, speed: 11.37Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: num_layers_12 (REVERTED)
- **Timestamp**: 16:31:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999379, loss: 0.504171, params: 6.047M, vram: 2019.5MB, speed: 8.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: batch_size_8 (REVERTED)
- **Timestamp**: 16:46:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300807, loss: 0.261744, params: 6.121M, vram: 2690.0MB, speed: 11.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: lr_5e-5 (REVERTED)
- **Timestamp**: 17:02:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999822, loss: 0.502559, params: 6.121M, vram: 2690.0MB, speed: 11.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: lr_1e-4 (REVERTED)
- **Timestamp**: 17:17:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999619, loss: 0.503045, params: 6.121M, vram: 2690.0MB, speed: 11.74Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: wd_0.001 (REVERTED)
- **Timestamp**: 17:33:15
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200174, loss: 0.103703, params: 6.121M, vram: 2690.0MB, speed: 11.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: dropout_0.0 (REVERTED)
- **Timestamp**: 17:48:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.400651, loss: 0.164645, params: 6.121M, vram: 1627.1MB, speed: 11.47Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: batch_size_8 (REVERTED)
- **Timestamp**: 18:04:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250925, loss: 0.149450, params: 6.121M, vram: 2690.0MB, speed: 10.82Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: num_layers_12 (REVERTED)
- **Timestamp**: 18:19:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999527, loss: 0.503745, params: 6.047M, vram: 2019.5MB, speed: 8.82Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: wd_0.0 (REVERTED)
- **Timestamp**: 18:35:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300217, loss: 0.088074, params: 6.121M, vram: 2690.0MB, speed: 11.83Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: wd_0.001 (REVERTED)
- **Timestamp**: 18:50:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300537, loss: 0.129334, params: 6.121M, vram: 2690.0MB, speed: 10.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: dropout_0.0 (REVERTED)
- **Timestamp**: 19:06:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.999211, loss: 0.504633, params: 6.121M, vram: 1627.1MB, speed: 11.26Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 PM
