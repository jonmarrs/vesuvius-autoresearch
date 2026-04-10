# Day Shift Sprint - 2026-04-08
- **Start Time**: 11:45:58
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: heads_4 (REVERTED)
- **Timestamp**: 12:01:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999663, loss: 0.502777, params: 6.121M, vram: 1784.1MB, speed: 5.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: batch_size_4 (REVERTED)
- **Timestamp**: 12:17:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200740, loss: 0.288071, params: 6.121M, vram: 2690.0MB, speed: 3.65Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: num_layers_12 (REVERTED)
- **Timestamp**: 12:32:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200612, loss: 0.127776, params: 6.047M, vram: 2019.5MB, speed: 4.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: lr_5e-4 (REVERTED)
- **Timestamp**: 12:48:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999808, loss: 0.501581, params: 6.121M, vram: 2690.0MB, speed: 4.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: patch_size_128 (REVERTED)
- **Timestamp**: 13:04:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200504, loss: 0.206817, params: 6.351M, vram: 7163.5MB, speed: 7.37Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: lr_1e-3 (REVERTED)
- **Timestamp**: 13:19:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.401225, loss: 0.199520, params: 6.121M, vram: 2690.0MB, speed: 7.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: dropout_0.2 (REVERTED)
- **Timestamp**: 13:35:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.551963, loss: 0.207613, params: 6.121M, vram: 2690.0MB, speed: 4.67Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: dropout_0.2 (REVERTED)
- **Timestamp**: 13:50:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.999657, loss: 0.504856, params: 6.121M, vram: 2690.0MB, speed: 6.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_128 (REVERTED)
- **Timestamp**: 14:06:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500020, loss: 0.188547, params: 6.351M, vram: 7163.5MB, speed: 10.06Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: heads_4 (REVERTED)
- **Timestamp**: 14:21:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999621, loss: 0.502969, params: 6.121M, vram: 1784.1MB, speed: 13.30Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: patch_size_128 (REVERTED)
- **Timestamp**: 14:37:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.451052, loss: 0.323715, params: 6.351M, vram: 7163.5MB, speed: 21.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: num_layers_24 (REVERTED)
- **Timestamp**: 14:52:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999746, loss: 0.502236, params: 6.269M, vram: 3955.4MB, speed: 19.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: patch_size_128 (REVERTED)
- **Timestamp**: 15:07:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350057, loss: 0.136136, params: 6.351M, vram: 7163.5MB, speed: 18.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: wd_0.1 (REVERTED)
- **Timestamp**: 15:23:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250221, loss: 0.138522, params: 6.121M, vram: 2690.0MB, speed: 9.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: num_layers_24 (REVERTED)
- **Timestamp**: 15:38:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999919, loss: 0.502367, params: 6.269M, vram: 3955.4MB, speed: 13.50Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: blocks_12 (REVERTED)
- **Timestamp**: 15:54:06
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400472, loss: 0.230618, params: 4.005M, vram: 1688.3MB, speed: 17.87Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: heads_4 (REVERTED)
- **Timestamp**: 16:09:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.250213, loss: 0.188726, params: 6.121M, vram: 1784.1MB, speed: 10.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: patch_size_96 (REVERTED)
- **Timestamp**: 16:24:55
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999642, loss: 0.502187, params: 6.121M, vram: 2690.0MB, speed: 8.65Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: batch_size_8 (REVERTED)
- **Timestamp**: 16:40:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400367, loss: 0.119184, params: 6.121M, vram: 2690.0MB, speed: 6.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: batch_size_8 (REVERTED)
- **Timestamp**: 16:55:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.100694, loss: 0.109282, params: 6.121M, vram: 2690.0MB, speed: 13.38Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: num_layers_16 (REVERTED)
- **Timestamp**: 17:10:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500034, loss: 0.209968, params: 6.121M, vram: 2690.0MB, speed: 13.41Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: lr_1e-4 (REVERTED)
- **Timestamp**: 17:26:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999583, loss: 0.503993, params: 6.121M, vram: 2690.0MB, speed: 13.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: blocks_20 (REVERTED)
- **Timestamp**: 17:41:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250007, loss: 0.133139, params: 6.121M, vram: 2690.0MB, speed: 13.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: wd_0.0 (REVERTED)
- **Timestamp**: 17:56:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999512, loss: 0.503091, params: 6.121M, vram: 2690.0MB, speed: 13.91Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: heads_12 (REVERTED)
- **Timestamp**: 17:57:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.999512, loss: 0.503091, params: 6.121M, vram: 2690.0MB, speed: 13.91Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: dropout_0.2 (REVERTED)
- **Timestamp**: 18:12:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.600100, loss: 0.157922, params: 6.121M, vram: 2690.0MB, speed: 13.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: patch_size_64 (REVERTED)
- **Timestamp**: 18:27:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.100073, loss: 0.161926, params: 5.957M, vram: 788.9MB, speed: 6.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: batch_size_16 (REVERTED)
- **Timestamp**: 18:42:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500103, loss: 0.104230, params: 6.121M, vram: 2690.0MB, speed: 27.26Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: wd_0.1 (REVERTED)
- **Timestamp**: 18:58:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.301105, loss: 0.242228, params: 6.121M, vram: 2690.0MB, speed: 13.78Mvps
- **Result**: No improvement detected. Changes reverted.

