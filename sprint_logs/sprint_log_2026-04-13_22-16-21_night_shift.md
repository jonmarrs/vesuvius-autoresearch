# Night Shift Sprint - 2026-04-13
- **Start Time**: 22:16:21
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: heads_4 (REVERTED)
- **Timestamp**: 22:32:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998393, loss: 0.405400, params: N/AM, vram: N/AMB, speed: 9.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: wd_0.01 (REVERTED)
- **Timestamp**: 22:47:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998561, loss: 0.404655, params: N/AM, vram: N/AMB, speed: 10.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: batch_size_24 (REVERTED)
- **Timestamp**: 23:02:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 24, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998649, loss: 0.404917, params: N/AM, vram: N/AMB, speed: 12.02Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: patch_size_96 (REVERTED)
- **Timestamp**: 23:18:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998898, loss: 0.407143, params: N/AM, vram: N/AMB, speed: 10.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: base_feat_32 (REVERTED)
- **Timestamp**: 23:33:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 32, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998265, loss: 0.405008, params: N/AM, vram: N/AMB, speed: 14.06Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: dropout_0.0 (REVERTED)
- **Timestamp**: 23:49:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998170, loss: 0.406035, params: N/AM, vram: N/AMB, speed: 11.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: blocks_16 (REVERTED)
- **Timestamp**: 00:04:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: 6.53Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: heads_12 (REVERTED)
- **Timestamp**: 00:20:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 12, dropout: 0.0
- **Stats**: val_bpb: 0.998729, loss: 0.404690, params: N/AM, vram: N/AMB, speed: 8.45Mvps
- **Result**: No improvement detected. Changes reverted.
