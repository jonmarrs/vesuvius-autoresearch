# Day Shift Sprint - 2026-04-13
- **Start Time**: 07:57:54
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: base_feat_32 (REVERTED)
- **Timestamp**: 08:13:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999725, loss: 0.502666, params: 0.424M, vram: 703.1MB, speed: 5.87Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: wd_0.0 (REVERTED)
- **Timestamp**: 08:28:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999916, loss: 0.501433, params: 6.023M, vram: 1141.0MB, speed: 14.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: batch_size_16 (REVERTED)
- **Timestamp**: 08:43:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250092, loss: 0.131608, params: 6.023M, vram: 1141.0MB, speed: 15.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: wd_0.01 (REVERTED)
- **Timestamp**: 08:59:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400149, loss: 0.101428, params: 6.023M, vram: 1141.0MB, speed: 15.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: base_feat_32 (REVERTED)
- **Timestamp**: 09:14:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999652, loss: 0.501387, params: 0.424M, vram: 703.1MB, speed: 14.54Mvps
- **Result**: No improvement detected. Changes reverted.

