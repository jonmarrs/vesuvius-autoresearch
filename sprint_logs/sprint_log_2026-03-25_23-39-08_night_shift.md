# Night Shift Sprint - 2026-03-25
- **Start Time**: 23:39:08
- **Goal**: Monotonic val_bpb optimization via 5-min cycles.

## Cycle 1: batch_size_8 (REVERTED)
- **Timestamp**: 23:51:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 8, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501900, params: 0.328M, vram: 2412.7MB, speed: 14.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: batch_size_16 (REVERTED)
- **Timestamp**: 23:56:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 16, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502109, params: 0.328M, vram: 2412.7MB, speed: 30.42Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: num_layers_16 (REVERTED)
- **Timestamp**: 00:01:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501177, params: 0.328M, vram: 3355.8MB, speed: 3.50Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: batch_size_4 (REVERTED)
- **Timestamp**: 00:06:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 4, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.504324, params: 0.328M, vram: 2412.7MB, speed: 7.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: dropout_0.0 (REVERTED)
- **Timestamp**: 00:12:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 1.000000, loss: 0.504150, params: 0.328M, vram: 2390.2MB, speed: 3.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: patch_size_96 (REVERTED)
- **Timestamp**: 00:17:33
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 96, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503385, params: 0.328M, vram: 1397.5MB, speed: 3.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: base_feat_64 (REVERTED)
- **Timestamp**: 00:22:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 64, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501436, params: 1.278M, vram: 4500.9MB, speed: 2.17Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: wd_0.001 (REVERTED)
- **Timestamp**: 00:28:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502205, params: 0.328M, vram: 2412.7MB, speed: 3.83Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: num_layers_16 (REVERTED)
- **Timestamp**: 00:33:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502828, params: 0.328M, vram: 3355.8MB, speed: 3.58Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: base_feat_32 (REVERTED)
- **Timestamp**: 00:38:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501865, params: 0.328M, vram: 2412.7MB, speed: 3.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: wd_0.001 (REVERTED)
- **Timestamp**: 00:44:08
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.504000, params: 0.328M, vram: 2412.7MB, speed: 3.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: lr_5e-5 (REVERTED)
- **Timestamp**: 00:49:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503863, params: 0.328M, vram: 2412.7MB, speed: 3.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: heads_8 (REVERTED)
- **Timestamp**: 00:54:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501853, params: 0.328M, vram: 2412.7MB, speed: 3.82Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: base_feat_32 (REVERTED)
- **Timestamp**: 01:00:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503670, params: 0.328M, vram: 2412.7MB, speed: 3.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: batch_size_16 (REVERTED)
- **Timestamp**: 01:05:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 16, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503482, params: 0.328M, vram: 2412.7MB, speed: 31.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: patch_size_96 (REVERTED)
- **Timestamp**: 01:10:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 96, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502640, params: 0.328M, vram: 1397.5MB, speed: 3.46Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: wd_0.01 (REVERTED)
- **Timestamp**: 01:15:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.01, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503100, params: 0.328M, vram: 2412.7MB, speed: 3.71Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: dropout_0.2 (REVERTED)
- **Timestamp**: 01:21:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.000000, loss: 0.501129, params: 0.328M, vram: 2412.7MB, speed: 3.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: heads_8 (REVERTED)
- **Timestamp**: 01:26:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502761, params: 0.328M, vram: 2412.7MB, speed: 3.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: wd_0.0 (REVERTED)
- **Timestamp**: 01:31:53
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501967, params: 0.328M, vram: 2412.7MB, speed: 3.67Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: heads_8 (REVERTED)
- **Timestamp**: 01:37:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502791, params: 0.328M, vram: 2412.7MB, speed: 3.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: batch_size_8 (REVERTED)
- **Timestamp**: 01:42:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 8, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502633, params: 0.328M, vram: 2412.7MB, speed: 14.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: blocks_12 (REVERTED)
- **Timestamp**: 01:47:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 12, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501903, params: 0.390M, vram: 2773.4MB, speed: 3.34Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: wd_0.0 (REVERTED)
- **Timestamp**: 01:53:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502177, params: 0.328M, vram: 2412.7MB, speed: 4.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: heads_12 (REVERTED)
- **Timestamp**: 01:53:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 12, dropout: 0.4
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: blocks_10 (REVERTED)
- **Timestamp**: 01:58:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501776, params: 0.328M, vram: 2412.7MB, speed: 3.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: blocks_20 (REVERTED)
- **Timestamp**: 02:04:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 20, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503425, params: 0.636M, vram: 4216.2MB, speed: 2.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: lr_1e-4 (REVERTED)
- **Timestamp**: 02:09:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502160, params: 0.328M, vram: 2412.7MB, speed: 3.74Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: heads_4 (REVERTED)
- **Timestamp**: 02:14:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503322, params: 0.328M, vram: 2258.9MB, speed: 4.01Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: patch_size_96 (REVERTED)
- **Timestamp**: 02:19:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 96, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503421, params: 0.328M, vram: 1397.5MB, speed: 3.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: base_feat_128 (REVERTED)
- **Timestamp**: 02:25:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502411, params: 5.046M, vram: 8805.8MB, speed: 1.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: heads_8 (REVERTED)
- **Timestamp**: 02:30:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501689, params: 0.328M, vram: 2412.7MB, speed: 3.72Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: lr_5e-5 (REVERTED)
- **Timestamp**: 02:35:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501787, params: 0.328M, vram: 2412.7MB, speed: 3.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: base_feat_32 (REVERTED)
- **Timestamp**: 02:41:09
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503735, params: 0.328M, vram: 2412.7MB, speed: 3.80Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: heads_4 (REVERTED)
- **Timestamp**: 02:46:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501196, params: 0.328M, vram: 2258.9MB, speed: 4.06Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 36: base_feat_128 (REVERTED)
- **Timestamp**: 02:51:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.504084, params: 5.046M, vram: 8805.8MB, speed: 0.97Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 37: num_layers_12 (REVERTED)
- **Timestamp**: 02:57:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503482, params: 0.328M, vram: 2412.7MB, speed: 3.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 38: wd_0.001 (REVERTED)
- **Timestamp**: 03:02:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503969, params: 0.328M, vram: 2412.7MB, speed: 3.72Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 39: blocks_20 (REVERTED)
- **Timestamp**: 03:07:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 20, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502448, params: 0.636M, vram: 4216.2MB, speed: 2.24Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 40: heads_4 (REVERTED)
- **Timestamp**: 03:13:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503608, params: 0.328M, vram: 2258.9MB, speed: 4.07Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 41: lr_1e-5 (REVERTED)
- **Timestamp**: 03:18:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.504130, params: 0.328M, vram: 2412.7MB, speed: 3.74Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 42: heads_12 (REVERTED)
- **Timestamp**: 03:18:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 12, dropout: 0.4
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 43: lr_1e-4 (REVERTED)
- **Timestamp**: 03:23:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502923, params: 0.328M, vram: 2412.7MB, speed: 3.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 44: dropout_0.4 (REVERTED)
- **Timestamp**: 03:29:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503373, params: 0.328M, vram: 2412.7MB, speed: 3.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 45: patch_size_64 (REVERTED)
- **Timestamp**: 03:34:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502995, params: 0.328M, vram: 619.6MB, speed: 2.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 46: heads_8 (REVERTED)
- **Timestamp**: 03:39:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502705, params: 0.328M, vram: 2412.7MB, speed: 3.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 47: num_layers_16 (REVERTED)
- **Timestamp**: 03:45:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502167, params: 0.328M, vram: 3355.8MB, speed: 3.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 48: patch_size_96 (REVERTED)
- **Timestamp**: 03:50:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 96, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503905, params: 0.328M, vram: 1397.5MB, speed: 3.41Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 49: batch_size_4 (REVERTED)
- **Timestamp**: 03:55:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 4, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.504904, params: 0.328M, vram: 2412.7MB, speed: 7.47Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 50: base_feat_128 (REVERTED)
- **Timestamp**: 04:01:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502095, params: 5.046M, vram: 8805.8MB, speed: 0.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 51: heads_12 (REVERTED)
- **Timestamp**: 04:01:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 12, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.504081, params: 0.328M, vram: 2412.7MB, speed: 3.50Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 52: num_layers_16 (REVERTED)
- **Timestamp**: 04:06:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503077, params: 0.328M, vram: 2412.7MB, speed: 3.61Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 53: dropout_0.0 (REVERTED)
- **Timestamp**: 04:11:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 1.000000, loss: 0.502874, params: 0.328M, vram: 2412.7MB, speed: 3.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 54: patch_size_64 (REVERTED)
- **Timestamp**: 04:17:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503382, params: 0.328M, vram: 2412.7MB, speed: 34.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 55: heads_12 (REVERTED)
- **Timestamp**: 04:17:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 12, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503093, params: 0.328M, vram: 619.6MB, speed: 2.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 56: wd_0.0 (REVERTED)
- **Timestamp**: 04:22:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502391, params: 0.328M, vram: 2412.7MB, speed: 3.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 57: batch_size_8 (REVERTED)
- **Timestamp**: 04:28:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 8, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503182, params: 0.328M, vram: 2412.7MB, speed: 15.13Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 58: patch_size_128 (REVERTED)
- **Timestamp**: 04:33:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501264, params: 0.328M, vram: 2412.7MB, speed: 3.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 59: wd_0.1 (REVERTED)
- **Timestamp**: 04:38:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.1, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.501887, params: 0.328M, vram: 2412.7MB, speed: 3.61Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 60: dropout_0.0 (REVERTED)
- **Timestamp**: 04:44:02
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 1.000000, loss: 0.501830, params: 0.328M, vram: 2412.7MB, speed: 28.85Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 61: blocks_12 (REVERTED)
- **Timestamp**: 04:49:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 12, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502730, params: 0.328M, vram: 2412.7MB, speed: 14.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 62: lr_5e-5 (REVERTED)
- **Timestamp**: 04:54:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502777, params: 0.328M, vram: 619.6MB, speed: 2.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 63: wd_0.0 (REVERTED)
- **Timestamp**: 04:59:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503325, params: 0.328M, vram: 1397.5MB, speed: 3.50Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 64: patch_size_64 (REVERTED)
- **Timestamp**: 05:05:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502688, params: 0.328M, vram: 619.6MB, speed: 2.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 65: base_feat_64 (REVERTED)
- **Timestamp**: 05:10:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 64, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502108, params: 0.328M, vram: 2412.7MB, speed: 3.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 66: batch_size_4 (REVERTED)
- **Timestamp**: 05:15:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 4, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503417, params: 0.328M, vram: 2412.7MB, speed: 3.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 67: lr_5e-5 (REVERTED)
- **Timestamp**: 05:21:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503498, params: 0.328M, vram: 619.6MB, speed: 2.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 68: patch_size_128 (REVERTED)
- **Timestamp**: 05:26:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503266, params: 0.328M, vram: 2390.2MB, speed: 3.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 69: dropout_0.4 (REVERTED)
- **Timestamp**: 05:31:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502497, params: 0.328M, vram: 5464.0MB, speed: 3.48Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 70: blocks_20 (REVERTED)
- **Timestamp**: 05:37:01
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 20, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503259, params: 0.328M, vram: 2412.7MB, speed: 3.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 71: base_feat_64 (REVERTED)
- **Timestamp**: 05:42:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 64, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502674, params: 0.328M, vram: 2412.7MB, speed: 3.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 72: num_layers_24 (REVERTED)
- **Timestamp**: 05:47:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503883, params: 0.328M, vram: 2412.7MB, speed: 3.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 73: batch_size_4 (REVERTED)
- **Timestamp**: 05:52:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 4, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502010, params: 0.328M, vram: 2412.7MB, speed: 3.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 74: heads_8 (REVERTED)
- **Timestamp**: 05:58:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502968, params: 0.328M, vram: 2412.7MB, speed: 3.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 75: wd_0.1 (REVERTED)
- **Timestamp**: 06:03:32
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.1, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503161, params: 0.328M, vram: 5464.0MB, speed: 3.46Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 76: lr_1e-3 (REVERTED)
- **Timestamp**: 06:08:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502977, params: 0.328M, vram: 2412.7MB, speed: 3.86Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 77: patch_size_128 (REVERTED)
- **Timestamp**: 06:14:08
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503539, params: 0.328M, vram: 2412.7MB, speed: 3.65Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 78: wd_0.1 (REVERTED)
- **Timestamp**: 06:19:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.1, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502789, params: 0.328M, vram: 2412.7MB, speed: 3.61Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 79: wd_0.001 (REVERTED)
- **Timestamp**: 06:24:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502618, params: 0.328M, vram: 2412.7MB, speed: 3.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 80: lr_5e-5 (REVERTED)
- **Timestamp**: 06:30:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503244, params: 0.328M, vram: 2412.7MB, speed: 3.68Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 81: heads_4 (REVERTED)
- **Timestamp**: 06:35:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502212, params: 0.328M, vram: 2258.9MB, speed: 3.88Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 82: heads_4 (REVERTED)
- **Timestamp**: 06:40:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502747, params: 0.328M, vram: 2258.9MB, speed: 3.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 83: lr_1e-4 (REVERTED)
- **Timestamp**: 06:46:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502194, params: 0.328M, vram: 2412.7MB, speed: 3.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 84: heads_4 (REVERTED)
- **Timestamp**: 06:51:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502035, params: 0.328M, vram: 2258.9MB, speed: 3.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 85: lr_1e-4 (REVERTED)
- **Timestamp**: 06:56:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.502952, params: 0.328M, vram: 2412.7MB, speed: 3.47Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 86: batch_size_16 (REVERTED)
- **Timestamp**: 07:01:56
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 16, patch_size: 128, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 1.000000, loss: 0.503457, params: 0.328M, vram: 2412.7MB, speed: 28.75Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 AM
