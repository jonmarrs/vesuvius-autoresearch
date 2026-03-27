# Night Shift Sprint - 2026-03-26
- **Start Time**: 20:31:50
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: batch_size_8 (REVERTED)
- **Timestamp**: 20:47:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999623, loss: 0.504504, params: 1.693M, vram: 3362.9MB, speed: 18.45Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: wd_0.01 (REVERTED)
- **Timestamp**: 21:02:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999858, loss: 0.503826, params: 1.693M, vram: 3362.9MB, speed: 4.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: lr_1e-5 (REVERTED)
- **Timestamp**: 21:17:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.01, blocks: 20, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999402, loss: 0.502428, params: 1.693M, vram: 3362.9MB, speed: 2.79Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: wd_0.001 (REVERTED)
- **Timestamp**: 21:33:09
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999499, loss: 0.501971, params: 1.693M, vram: 3362.9MB, speed: 4.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: heads_4 (REVERTED)
- **Timestamp**: 21:48:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999575, loss: 0.503201, params: 1.693M, vram: 1984.2MB, speed: 4.33Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: dropout_0.2 (REVERTED)
- **Timestamp**: 22:03:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.999827, loss: 0.502542, params: 1.693M, vram: 3362.9MB, speed: 4.35Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: lr_1e-3 (REVERTED)
- **Timestamp**: 22:19:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999614, loss: 0.502408, params: 1.693M, vram: 3362.9MB, speed: 4.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: base_feat_128 (SUCCESS)
- **Timestamp**: 00:08:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 2, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350198, loss: 0.123922, params: 6.269M, vram: 3955.4MB, speed: 3.69Mvps
- **Result**: Improvement detected. Changes committed.

