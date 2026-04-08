# Night Shift Sprint - 2026-04-07
- **Start Time**: 14:46:27
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: num_layers_24 (REVERTED)
- **Timestamp**: 15:02:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350000, loss: 0.354229, params: 6.269M, vram: 3955.4MB, speed: 10.62Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: dropout_0.1 (REVERTED)
- **Timestamp**: 15:17:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450122, loss: 0.139985, params: 6.121M, vram: 2690.0MB, speed: 13.39Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: blocks_16 (REVERTED)
- **Timestamp**: 15:33:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999604, loss: 0.502632, params: 5.063M, vram: 2189.3MB, speed: 16.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: wd_0.01 (REVERTED)
- **Timestamp**: 15:48:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.401856, loss: 0.256348, params: 6.121M, vram: 2690.0MB, speed: 14.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: blocks_20 (REVERTED)
- **Timestamp**: 16:03:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500623, loss: 0.201893, params: 6.121M, vram: 2690.0MB, speed: 14.34Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: wd_0.0 (REVERTED)
- **Timestamp**: 16:18:55
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999414, loss: 0.502197, params: 6.121M, vram: 2690.0MB, speed: 14.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: heads_4 (REVERTED)
- **Timestamp**: 16:34:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.201238, loss: 0.104881, params: 6.121M, vram: 1784.1MB, speed: 14.27Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: blocks_12 (REVERTED)
- **Timestamp**: 16:49:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.600077, loss: 0.205091, params: 4.005M, vram: 1688.3MB, speed: 21.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: heads_4 (REVERTED)
- **Timestamp**: 17:04:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.404119, loss: 0.231411, params: 6.121M, vram: 1784.1MB, speed: 14.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: patch_size_96 (REVERTED)
- **Timestamp**: 17:20:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.550081, loss: 0.128743, params: 6.121M, vram: 2690.0MB, speed: 14.15Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: blocks_10 (REVERTED)
- **Timestamp**: 17:35:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450513, loss: 0.134596, params: 3.475M, vram: 1436.2MB, speed: 23.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: wd_0.01 (REVERTED)
- **Timestamp**: 17:50:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400196, loss: 0.089573, params: 6.121M, vram: 2690.0MB, speed: 14.39Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: base_feat_32 (REVERTED)
- **Timestamp**: 18:05:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999649, loss: 0.501619, params: 0.449M, vram: 2085.6MB, speed: 14.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: dropout_0.2 (REVERTED)
- **Timestamp**: 18:21:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.150758, loss: 0.158207, params: 6.121M, vram: 2690.0MB, speed: 14.09Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: wd_0.1 (REVERTED)
- **Timestamp**: 18:36:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999726, loss: 0.500861, params: 6.121M, vram: 2690.0MB, speed: 14.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: patch_size_96 (REVERTED)
- **Timestamp**: 18:51:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999679, loss: 0.503617, params: 6.121M, vram: 2690.0MB, speed: 14.31Mvps
- **Result**: No improvement detected. Changes reverted.

