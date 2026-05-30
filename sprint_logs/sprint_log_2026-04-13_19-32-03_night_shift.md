# Night Shift Sprint - 2026-04-13
- **Start Time**: 19:32:03
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: patch_size_64 (REVERTED)
- **Timestamp**: 19:47:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998669, loss: 0.405563, params: N/AM, vram: N/AMB, speed: 11.88Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: base_feat_64 (REVERTED)
- **Timestamp**: 20:02:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998359, loss: 0.405030, params: N/AM, vram: N/AMB, speed: 12.21Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: num_layers_24 (REVERTED)
- **Timestamp**: 20:18:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998095, loss: 0.405069, params: N/AM, vram: N/AMB, speed: 12.41Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: lr_5e-4 (REVERTED)
- **Timestamp**: 20:33:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998458, loss: 0.405654, params: N/AM, vram: N/AMB, speed: 12.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: blocks_16 (SUCCESS)
- **Timestamp**: 20:48:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: 11.16Mvps
- **Result**: Improvement detected. Changes committed.

## Cycle 6: blocks_10 (REVERTED)
- **Timestamp**: 21:04:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.998158, loss: 0.405633, params: N/AM, vram: N/AMB, speed: 13.13Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: heads_8 (REVERTED)
- **Timestamp**: 21:19:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.998635, loss: 0.404122, params: N/AM, vram: N/AMB, speed: 9.71Mvps
- **Result**: No improvement detected. Changes reverted.
