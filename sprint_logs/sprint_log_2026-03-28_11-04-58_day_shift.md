# Day Shift Sprint - 2026-03-28
- **Start Time**: 11:04:58
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: dropout_0.4 (REVERTED)
- **Timestamp**: 11:20:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.999284, loss: 0.504990, params: 1.619M, vram: 2253.7MB, speed: 7.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: num_layers_16 (REVERTED)
- **Timestamp**: 11:36:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400539, loss: 0.222481, params: 6.121M, vram: 2690.0MB, speed: 11.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: num_layers_16 (REVERTED)
- **Timestamp**: 11:51:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.151074, loss: 0.218972, params: 6.121M, vram: 2690.0MB, speed: 11.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: base_feat_128 (REVERTED)
- **Timestamp**: 12:07:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999874, loss: 0.501679, params: 6.121M, vram: 2690.0MB, speed: 11.42Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: blocks_20 (REVERTED)
- **Timestamp**: 12:22:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999837, loss: 0.502098, params: 6.121M, vram: 2690.0MB, speed: 11.45Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: base_feat_32 (REVERTED)
- **Timestamp**: 12:38:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999778, loss: 0.502362, params: 0.449M, vram: 2085.6MB, speed: 11.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: patch_size_96 (REVERTED)
- **Timestamp**: 12:53:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300026, loss: 0.118434, params: 6.121M, vram: 2690.0MB, speed: 11.81Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: base_feat_32 (REVERTED)
- **Timestamp**: 13:09:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999581, loss: 0.503128, params: 0.449M, vram: 2085.6MB, speed: 12.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_128 (REVERTED)
- **Timestamp**: 13:25:09
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.501313, loss: 0.303602, params: 6.351M, vram: 7163.5MB, speed: 15.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: heads_12 (REVERTED)
- **Timestamp**: 13:25:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: num_layers_16 (REVERTED)
- **Timestamp**: 13:40:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350446, loss: 0.312931, params: 6.121M, vram: 2690.0MB, speed: 11.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: blocks_20 (REVERTED)
- **Timestamp**: 13:56:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350880, loss: 0.251828, params: 6.121M, vram: 2690.0MB, speed: 11.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: base_feat_64 (REVERTED)
- **Timestamp**: 14:12:08
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999840, loss: 0.503459, params: 1.619M, vram: 2253.7MB, speed: 11.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: wd_0.001 (REVERTED)
- **Timestamp**: 14:27:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999903, loss: 0.503107, params: 6.121M, vram: 2690.0MB, speed: 11.37Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: batch_size_8 (REVERTED)
- **Timestamp**: 14:43:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200002, loss: 0.092598, params: 6.121M, vram: 2690.0MB, speed: 11.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: lr_5e-5 (REVERTED)
- **Timestamp**: 14:58:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999525, loss: 0.502131, params: 6.121M, vram: 2690.0MB, speed: 11.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: wd_0.001 (REVERTED)
- **Timestamp**: 15:14:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150023, loss: 0.206188, params: 6.121M, vram: 2690.0MB, speed: 11.33Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: num_layers_24 (REVERTED)
- **Timestamp**: 15:30:06
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400265, loss: 0.135053, params: 6.269M, vram: 3955.4MB, speed: 16.35Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: blocks_20 (REVERTED)
- **Timestamp**: 15:45:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200974, loss: 0.213212, params: 6.121M, vram: 2690.0MB, speed: 11.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: dropout_0.4 (REVERTED)
- **Timestamp**: 16:01:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.150128, loss: 0.204496, params: 6.121M, vram: 2690.0MB, speed: 11.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: patch_size_128 (REVERTED)
- **Timestamp**: 16:16:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999161, loss: 0.502420, params: 6.351M, vram: 7163.5MB, speed: 15.07Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: batch_size_4 (REVERTED)
- **Timestamp**: 16:32:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999735, loss: 0.502987, params: 6.121M, vram: 2690.0MB, speed: 5.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: base_feat_128 (REVERTED)
- **Timestamp**: 16:48:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200344, loss: 0.112204, params: 6.121M, vram: 2690.0MB, speed: 11.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: lr_5e-5 (REVERTED)
- **Timestamp**: 17:03:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999660, loss: 0.502508, params: 6.121M, vram: 2690.0MB, speed: 11.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: patch_size_96 (REVERTED)
- **Timestamp**: 17:19:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300127, loss: 0.177720, params: 6.121M, vram: 2690.0MB, speed: 11.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: batch_size_16 (REVERTED)
- **Timestamp**: 17:34:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.251288, loss: 0.223685, params: 6.121M, vram: 2690.0MB, speed: 22.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: lr_1e-5 (REVERTED)
- **Timestamp**: 17:50:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999578, loss: 0.501362, params: 6.121M, vram: 2690.0MB, speed: 10.88Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: num_layers_16 (REVERTED)
- **Timestamp**: 18:05:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.402002, loss: 0.216668, params: 6.121M, vram: 2690.0MB, speed: 11.11Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: base_feat_128 (REVERTED)
- **Timestamp**: 18:21:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300117, loss: 0.252056, params: 6.121M, vram: 2690.0MB, speed: 12.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: batch_size_8 (REVERTED)
- **Timestamp**: 18:36:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350286, loss: 0.201240, params: 6.121M, vram: 2690.0MB, speed: 11.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: batch_size_16 (REVERTED)
- **Timestamp**: 18:52:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400455, loss: 0.170039, params: 6.121M, vram: 2690.0MB, speed: 21.07Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: blocks_16 (REVERTED)
- **Timestamp**: 19:08:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999336, loss: 0.502465, params: 5.063M, vram: 2189.3MB, speed: 13.16Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 PM
