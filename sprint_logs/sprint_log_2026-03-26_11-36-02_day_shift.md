# Day Shift Sprint - 2026-03-26
- **Start Time**: 11:36:02
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: lr_1e-3 (REVERTED)
- **Timestamp**: 11:51:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 8, batch_size: 2, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999795, loss: 0.501847, params: 0.245M, vram: 887.2MB, speed: 3.41Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: patch_size_128 (REVERTED)
- **Timestamp**: 12:07:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.01, blocks: 8, batch_size: 2, patch_size: 128, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999635, loss: 0.504132, params: 0.932M, vram: 2769.0MB, speed: 4.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: wd_0.0 (REVERTED)
- **Timestamp**: 12:22:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999689, loss: 0.501489, params: 0.818M, vram: 965.5MB, speed: 5.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: patch_size_96 (REVERTED)
- **Timestamp**: 12:38:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.01, blocks: 8, batch_size: 2, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999926, loss: 0.501852, params: 0.818M, vram: 965.5MB, speed: 5.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: patch_size_96 (REVERTED)
- **Timestamp**: 12:53:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.01, blocks: 8, batch_size: 2, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999852, loss: 0.502747, params: 0.818M, vram: 965.5MB, speed: 5.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: wd_0.0 (REVERTED)
- **Timestamp**: 13:09:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999828, loss: 0.502235, params: 0.818M, vram: 965.5MB, speed: 5.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: num_layers_24 (SUCCESS)
- **Timestamp**: 13:24:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.01, blocks: 8, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999443, loss: 0.501751, params: 0.892M, vram: 1436.5MB, speed: 8.02Mvps
- **Result**: Improvement detected. Changes committed.

