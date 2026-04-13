# Day Shift Sprint - 2026-04-12
- **Start Time**: 07:58:42
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: patch_size_64 (REVERTED)
- **Timestamp**: 08:13:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200042, loss: 0.271595, params: 6.023M, vram: 1141.0MB, speed: 15.79Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: lr_1e-3 (REVERTED)
- **Timestamp**: 08:29:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999770, loss: 0.501846, params: 6.023M, vram: 1141.0MB, speed: 15.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: base_feat_64 (REVERTED)
- **Timestamp**: 08:44:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999926, loss: 0.502148, params: 1.570M, vram: 852.1MB, speed: 10.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: patch_size_64 (REVERTED)
- **Timestamp**: 08:59:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.103171, loss: 0.161797, params: 6.023M, vram: 1141.0MB, speed: 14.53Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: wd_0.001 (REVERTED)
- **Timestamp**: 09:15:09
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300139, loss: 0.180903, params: 6.023M, vram: 1141.0MB, speed: 15.34Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: base_feat_128 (REVERTED)
- **Timestamp**: 09:30:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450300, loss: 0.243243, params: 6.023M, vram: 1141.0MB, speed: 9.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: lr_1e-3 (REVERTED)
- **Timestamp**: 09:45:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999659, loss: 0.503500, params: 6.023M, vram: 1141.0MB, speed: 14.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: heads_12 (REVERTED)
- **Timestamp**: 09:45:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.999659, loss: 0.503500, params: 6.023M, vram: 1141.0MB, speed: 14.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: wd_0.0 (REVERTED)
- **Timestamp**: 10:01:15
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200008, loss: 0.083314, params: 6.023M, vram: 1141.0MB, speed: 16.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: batch_size_4 (REVERTED)
- **Timestamp**: 10:16:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999807, loss: 0.503901, params: 6.023M, vram: 1141.0MB, speed: 3.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: batch_size_8 (REVERTED)
- **Timestamp**: 10:31:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200486, loss: 0.229939, params: 6.023M, vram: 1141.0MB, speed: 8.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: lr_1e-4 (REVERTED)
- **Timestamp**: 10:47:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999625, loss: 0.503302, params: 6.023M, vram: 1141.0MB, speed: 15.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: num_layers_16 (REVERTED)
- **Timestamp**: 11:02:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.100059, loss: 0.191266, params: 5.957M, vram: 788.9MB, speed: 11.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: num_layers_12 (REVERTED)
- **Timestamp**: 11:17:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999828, loss: 0.502686, params: 5.925M, vram: 625.8MB, speed: 8.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: lr_1e-5 (REVERTED)
- **Timestamp**: 11:32:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999705, loss: 0.503213, params: 6.023M, vram: 1141.0MB, speed: 16.14Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: num_layers_12 (REVERTED)
- **Timestamp**: 11:48:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999782, loss: 0.503667, params: 5.925M, vram: 625.8MB, speed: 8.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: batch_size_16 (REVERTED)
- **Timestamp**: 12:03:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350981, loss: 0.238441, params: 6.023M, vram: 1141.0MB, speed: 15.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: blocks_12 (REVERTED)
- **Timestamp**: 12:18:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200204, loss: 0.113798, params: 3.906M, vram: 735.8MB, speed: 23.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: wd_0.1 (REVERTED)
- **Timestamp**: 12:33:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300289, loss: 0.123009, params: 6.023M, vram: 1141.0MB, speed: 16.27Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: patch_size_128 (REVERTED)
- **Timestamp**: 12:49:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999512, loss: 0.502275, params: 6.613M, vram: 10739.7MB, speed: 44.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: blocks_12 (REVERTED)
- **Timestamp**: 13:04:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999888, loss: 0.504052, params: 3.906M, vram: 735.8MB, speed: 23.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: num_layers_16 (REVERTED)
- **Timestamp**: 13:19:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450019, loss: 0.078925, params: 5.957M, vram: 788.9MB, speed: 11.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: patch_size_64 (REVERTED)
- **Timestamp**: 13:35:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.650398, loss: 0.194256, params: 6.023M, vram: 1141.0MB, speed: 16.13Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: base_feat_32 (REVERTED)
- **Timestamp**: 13:50:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999666, loss: 0.504421, params: 0.424M, vram: 703.1MB, speed: 15.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: base_feat_64 (REVERTED)
- **Timestamp**: 14:05:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999764, loss: 0.501885, params: 1.570M, vram: 852.4MB, speed: 16.62Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: heads_4 (REVERTED)
- **Timestamp**: 14:20:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.250024, loss: 0.078048, params: 6.023M, vram: 865.2MB, speed: 16.01Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: wd_0.1 (REVERTED)
- **Timestamp**: 14:36:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999926, loss: 0.501207, params: 6.023M, vram: 1141.0MB, speed: 16.08Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: lr_1e-4 (REVERTED)
- **Timestamp**: 14:51:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999615, loss: 0.501929, params: 6.023M, vram: 1141.0MB, speed: 15.65Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: batch_size_4 (REVERTED)
- **Timestamp**: 15:06:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300040, loss: 0.104202, params: 6.023M, vram: 1141.0MB, speed: 4.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: blocks_12 (REVERTED)
- **Timestamp**: 15:21:53
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200494, loss: 0.072918, params: 3.906M, vram: 735.8MB, speed: 23.46Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: base_feat_32 (REVERTED)
- **Timestamp**: 15:37:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999857, loss: 0.500970, params: 0.424M, vram: 703.1MB, speed: 16.39Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: patch_size_128 (REVERTED)
- **Timestamp**: 15:52:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400448, loss: 0.246128, params: 6.613M, vram: 10739.7MB, speed: 44.89Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: heads_4 (REVERTED)
- **Timestamp**: 16:07:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999625, loss: 0.504516, params: 6.023M, vram: 865.2MB, speed: 16.31Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: batch_size_8 (REVERTED)
- **Timestamp**: 16:23:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999492, loss: 0.503904, params: 6.023M, vram: 1141.0MB, speed: 7.88Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: patch_size_128 (REVERTED)
- **Timestamp**: 16:38:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999791, loss: 0.502924, params: 6.613M, vram: 10739.7MB, speed: 45.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 36: blocks_20 (REVERTED)
- **Timestamp**: 16:53:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200142, loss: 0.074171, params: 6.023M, vram: 1141.0MB, speed: 16.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 37: batch_size_4 (REVERTED)
- **Timestamp**: 17:08:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300025, loss: 0.096619, params: 6.023M, vram: 1141.0MB, speed: 3.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 38: num_layers_12 (REVERTED)
- **Timestamp**: 17:24:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350380, loss: 0.180131, params: 5.925M, vram: 625.8MB, speed: 4.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 39: wd_0.1 (REVERTED)
- **Timestamp**: 17:39:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300037, loss: 0.103655, params: 6.023M, vram: 1141.0MB, speed: 8.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 40: blocks_10 (REVERTED)
- **Timestamp**: 17:55:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300400, loss: 0.156357, params: 3.377M, vram: 635.9MB, speed: 16.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 41: blocks_16 (REVERTED)
- **Timestamp**: 18:10:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200490, loss: 0.094781, params: 4.965M, vram: 939.7MB, speed: 14.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 42: base_feat_32 (REVERTED)
- **Timestamp**: 18:25:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999496, loss: 0.502764, params: 0.424M, vram: 703.1MB, speed: 8.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 43: dropout_0.0 (REVERTED)
- **Timestamp**: 18:40:55
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.251014, loss: 0.171065, params: 6.023M, vram: 797.4MB, speed: 16.37Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 44: wd_0.0 (REVERTED)
- **Timestamp**: 18:56:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400600, loss: 0.159911, params: 6.023M, vram: 1141.0MB, speed: 15.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 45: blocks_12 (REVERTED)
- **Timestamp**: 19:11:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999886, loss: 0.503784, params: 3.906M, vram: 735.8MB, speed: 22.75Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 PM
