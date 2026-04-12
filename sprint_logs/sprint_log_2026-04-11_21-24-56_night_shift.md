# Night Shift Sprint - 2026-04-11
- **Start Time**: 21:24:56
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: blocks_16 (REVERTED)
- **Timestamp**: 21:40:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999811, loss: 0.501945, params: 5.210M, vram: 3213.5MB, speed: 18.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: patch_size_96 (REVERTED)
- **Timestamp**: 21:56:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250000, loss: 0.224218, params: 6.269M, vram: 3955.4MB, speed: 15.51Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: patch_size_128 (REVERTED)
- **Timestamp**: 22:11:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.501244, loss: 0.221146, params: 6.613M, vram: 10739.7MB, speed: 32.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: blocks_10 (REVERTED)
- **Timestamp**: 22:27:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200489, loss: 0.178109, params: 3.377M, vram: 635.9MB, speed: 10.95Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: blocks_10 (REVERTED)
- **Timestamp**: 22:42:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999646, loss: 0.503376, params: 3.377M, vram: 635.9MB, speed: 11.67Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: lr_5e-4 (REVERTED)
- **Timestamp**: 22:58:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999674, loss: 0.501793, params: 6.023M, vram: 1141.0MB, speed: 15.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: patch_size_64 (REVERTED)
- **Timestamp**: 23:13:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.151897, loss: 0.268397, params: 6.023M, vram: 1141.0MB, speed: 16.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: lr_5e-5 (REVERTED)
- **Timestamp**: 23:29:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999557, loss: 0.501436, params: 6.023M, vram: 1141.0MB, speed: 16.38Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_64 (REVERTED)
- **Timestamp**: 23:44:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150013, loss: 0.099291, params: 6.023M, vram: 1141.0MB, speed: 16.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: heads_12 (REVERTED)
- **Timestamp**: 23:44:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.150013, loss: 0.099291, params: 6.023M, vram: 1141.0MB, speed: 16.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: heads_4 (REVERTED)
- **Timestamp**: 23:59:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.999773, loss: 0.501869, params: 6.023M, vram: 865.2MB, speed: 16.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: num_layers_16 (REVERTED)
- **Timestamp**: 00:15:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999588, loss: 0.501574, params: 5.957M, vram: 788.9MB, speed: 11.15Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: heads_12 (REVERTED)
- **Timestamp**: 00:15:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.999588, loss: 0.501574, params: 5.957M, vram: 788.9MB, speed: 11.15Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: wd_0.1 (REVERTED)
- **Timestamp**: 00:30:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350356, loss: 0.197488, params: 6.023M, vram: 1141.0MB, speed: 16.47Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: patch_size_96 (REVERTED)
- **Timestamp**: 00:46:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300737, loss: 0.208650, params: 6.269M, vram: 3955.4MB, speed: 34.95Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: dropout_0.2 (REVERTED)
- **Timestamp**: 01:01:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.999678, loss: 0.502107, params: 6.023M, vram: 1141.0MB, speed: 16.08Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: blocks_20 (REVERTED)
- **Timestamp**: 01:16:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300046, loss: 0.220497, params: 6.023M, vram: 1141.0MB, speed: 15.83Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: blocks_20 (REVERTED)
- **Timestamp**: 01:31:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450155, loss: 0.160244, params: 6.023M, vram: 1141.0MB, speed: 16.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: num_layers_24 (REVERTED)
- **Timestamp**: 01:47:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999781, loss: 0.502415, params: 6.023M, vram: 1141.0MB, speed: 15.95Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: batch_size_4 (REVERTED)
- **Timestamp**: 02:02:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400185, loss: 0.351562, params: 6.023M, vram: 1141.0MB, speed: 4.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: dropout_0.2 (REVERTED)
- **Timestamp**: 02:17:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.350059, loss: 0.148431, params: 6.023M, vram: 1141.0MB, speed: 15.83Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: num_layers_12 (REVERTED)
- **Timestamp**: 02:33:08
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999640, loss: 0.504155, params: 5.925M, vram: 625.8MB, speed: 8.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: lr_5e-5 (REVERTED)
- **Timestamp**: 02:48:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999693, loss: 0.502931, params: 6.023M, vram: 1141.0MB, speed: 15.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: wd_0.1 (REVERTED)
- **Timestamp**: 03:03:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999556, loss: 0.502973, params: 6.023M, vram: 1141.0MB, speed: 16.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: heads_8 (REVERTED)
- **Timestamp**: 03:18:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.301102, loss: 0.226250, params: 6.023M, vram: 1141.0MB, speed: 16.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: heads_8 (REVERTED)
- **Timestamp**: 03:34:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999386, loss: 0.504259, params: 6.023M, vram: 1141.0MB, speed: 16.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: base_feat_64 (REVERTED)
- **Timestamp**: 03:49:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999712, loss: 0.504205, params: 1.570M, vram: 852.1MB, speed: 16.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: dropout_0.0 (REVERTED)
- **Timestamp**: 04:04:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.899562, loss: 0.451930, params: 6.023M, vram: 797.4MB, speed: 17.11Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: patch_size_96 (REVERTED)
- **Timestamp**: 04:20:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400549, loss: 0.202340, params: 6.269M, vram: 3955.4MB, speed: 35.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: batch_size_16 (REVERTED)
- **Timestamp**: 04:35:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250549, loss: 0.190980, params: 6.023M, vram: 1141.0MB, speed: 16.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: blocks_10 (REVERTED)
- **Timestamp**: 04:50:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250012, loss: 0.098131, params: 3.377M, vram: 635.9MB, speed: 26.14Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: blocks_16 (REVERTED)
- **Timestamp**: 05:05:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350203, loss: 0.193556, params: 4.965M, vram: 939.7MB, speed: 19.45Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: blocks_12 (REVERTED)
- **Timestamp**: 05:21:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250184, loss: 0.053342, params: 3.906M, vram: 735.8MB, speed: 23.45Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: batch_size_4 (REVERTED)
- **Timestamp**: 05:36:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200251, loss: 0.159223, params: 6.023M, vram: 1141.0MB, speed: 4.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: blocks_12 (REVERTED)
- **Timestamp**: 05:51:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350255, loss: 0.107450, params: 3.906M, vram: 735.8MB, speed: 23.08Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 36: num_layers_24 (REVERTED)
- **Timestamp**: 06:07:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.550312, loss: 0.158629, params: 6.023M, vram: 1141.0MB, speed: 16.15Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 37: heads_4 (REVERTED)
- **Timestamp**: 06:22:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.401773, loss: 0.234959, params: 6.023M, vram: 865.2MB, speed: 15.85Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 38: heads_4 (REVERTED)
- **Timestamp**: 06:37:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.200322, loss: 0.069771, params: 6.023M, vram: 865.2MB, speed: 16.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 39: wd_0.01 (REVERTED)
- **Timestamp**: 06:52:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300053, loss: 0.239247, params: 6.023M, vram: 1141.0MB, speed: 15.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 40: dropout_0.1 (REVERTED)
- **Timestamp**: 07:08:06
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300752, loss: 0.146459, params: 6.023M, vram: 1141.0MB, speed: 16.18Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 AM
