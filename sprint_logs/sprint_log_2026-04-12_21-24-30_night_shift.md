# Night Shift Sprint - 2026-04-12
- **Start Time**: 21:24:30
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: patch_size_64 (REVERTED)
- **Timestamp**: 21:39:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400547, loss: 0.216355, params: 6.023M, vram: 1141.0MB, speed: 13.71Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: blocks_12 (REVERTED)
- **Timestamp**: 21:55:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300603, loss: 0.227361, params: 3.906M, vram: 735.8MB, speed: 23.44Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: blocks_20 (REVERTED)
- **Timestamp**: 22:10:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300110, loss: 0.144642, params: 6.023M, vram: 1141.0MB, speed: 16.06Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: lr_1e-4 (REVERTED)
- **Timestamp**: 22:25:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999403, loss: 0.503635, params: 6.023M, vram: 1141.0MB, speed: 15.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: wd_0.01 (REVERTED)
- **Timestamp**: 22:40:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350000, loss: 0.233949, params: 6.023M, vram: 1141.0MB, speed: 16.16Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: batch_size_4 (REVERTED)
- **Timestamp**: 22:56:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350279, loss: 0.204705, params: 6.023M, vram: 1141.0MB, speed: 3.91Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: base_feat_128 (REVERTED)
- **Timestamp**: 23:11:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200525, loss: 0.058566, params: 6.023M, vram: 1141.0MB, speed: 14.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: wd_0.1 (REVERTED)
- **Timestamp**: 23:26:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.301748, loss: 0.281785, params: 6.023M, vram: 1141.0MB, speed: 14.27Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_128 (REVERTED)
- **Timestamp**: 23:42:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.449996, loss: 0.129548, params: 6.613M, vram: 10739.7MB, speed: 45.15Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: dropout_0.4 (REVERTED)
- **Timestamp**: 23:57:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.400203, loss: 0.151521, params: 6.023M, vram: 1141.0MB, speed: 15.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: wd_0.0 (REVERTED)
- **Timestamp**: 00:12:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350190, loss: 0.155606, params: 6.023M, vram: 1141.0MB, speed: 15.45Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: base_feat_64 (REVERTED)
- **Timestamp**: 00:27:55
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999903, loss: 0.500944, params: 1.570M, vram: 852.4MB, speed: 15.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: dropout_0.2 (REVERTED)
- **Timestamp**: 00:43:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.150043, loss: 0.138217, params: 6.023M, vram: 1141.0MB, speed: 16.13Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: heads_12 (REVERTED)
- **Timestamp**: 00:43:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.150043, loss: 0.138217, params: 6.023M, vram: 1141.0MB, speed: 16.13Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: dropout_0.1 (REVERTED)
- **Timestamp**: 00:58:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250399, loss: 0.184870, params: 6.023M, vram: 1141.0MB, speed: 15.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: lr_1e-3 (REVERTED)
- **Timestamp**: 01:13:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300390, loss: 0.153074, params: 6.023M, vram: 1141.0MB, speed: 15.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: dropout_0.2 (REVERTED)
- **Timestamp**: 01:29:14
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.999562, loss: 0.503318, params: 6.023M, vram: 1141.0MB, speed: 15.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: base_feat_32 (REVERTED)
- **Timestamp**: 01:44:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999760, loss: 0.502934, params: 0.424M, vram: 703.1MB, speed: 16.12Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: batch_size_16 (REVERTED)
- **Timestamp**: 01:59:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.203015, loss: 0.249973, params: 6.023M, vram: 1141.0MB, speed: 16.00Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: num_layers_24 (REVERTED)
- **Timestamp**: 02:15:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999513, loss: 0.503928, params: 6.023M, vram: 1141.0MB, speed: 15.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: base_feat_128 (REVERTED)
- **Timestamp**: 02:30:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150782, loss: 0.090997, params: 6.023M, vram: 1141.0MB, speed: 15.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: lr_1e-4 (REVERTED)
- **Timestamp**: 02:45:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999811, loss: 0.501633, params: 6.023M, vram: 1141.0MB, speed: 15.77Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: base_feat_64 (REVERTED)
- **Timestamp**: 03:00:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999636, loss: 0.503088, params: 1.570M, vram: 852.1MB, speed: 16.27Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: num_layers_16 (REVERTED)
- **Timestamp**: 03:16:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999546, loss: 0.501556, params: 5.957M, vram: 788.9MB, speed: 11.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: blocks_12 (REVERTED)
- **Timestamp**: 03:31:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.100437, loss: 0.162481, params: 3.906M, vram: 735.8MB, speed: 23.23Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: blocks_20 (REVERTED)
- **Timestamp**: 03:46:38
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200133, loss: 0.159504, params: 6.023M, vram: 1141.0MB, speed: 15.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: num_layers_16 (REVERTED)
- **Timestamp**: 04:01:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250721, loss: 0.233396, params: 5.957M, vram: 788.9MB, speed: 11.21Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: dropout_0.2 (REVERTED)
- **Timestamp**: 04:17:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.201269, loss: 0.151179, params: 6.023M, vram: 1141.0MB, speed: 15.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: wd_0.01 (REVERTED)
- **Timestamp**: 04:32:26
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.251460, loss: 0.191663, params: 6.023M, vram: 1141.0MB, speed: 15.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: dropout_0.2 (REVERTED)
- **Timestamp**: 04:47:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.450702, loss: 0.175955, params: 6.023M, vram: 1141.0MB, speed: 15.71Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: wd_0.0 (REVERTED)
- **Timestamp**: 05:02:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150266, loss: 0.272431, params: 6.023M, vram: 1141.0MB, speed: 16.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: batch_size_4 (REVERTED)
- **Timestamp**: 05:18:13
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.052057, loss: 0.246793, params: 6.023M, vram: 1141.0MB, speed: 3.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: num_layers_12 (REVERTED)
- **Timestamp**: 05:33:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300139, loss: 0.091461, params: 5.925M, vram: 625.8MB, speed: 8.66Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: heads_8 (REVERTED)
- **Timestamp**: 05:48:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.301319, loss: 0.159951, params: 6.023M, vram: 1141.0MB, speed: 15.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: patch_size_64 (REVERTED)
- **Timestamp**: 06:04:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350316, loss: 0.104004, params: 6.023M, vram: 1141.0MB, speed: 15.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 36: patch_size_96 (REVERTED)
- **Timestamp**: 06:19:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999807, loss: 0.502459, params: 6.269M, vram: 3955.4MB, speed: 35.18Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 37: base_feat_64 (REVERTED)
- **Timestamp**: 06:34:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999809, loss: 0.501123, params: 1.570M, vram: 852.4MB, speed: 16.02Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 38: num_layers_16 (REVERTED)
- **Timestamp**: 06:49:49
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350069, loss: 0.098854, params: 5.957M, vram: 788.9MB, speed: 11.29Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 39: heads_4 (REVERTED)
- **Timestamp**: 07:05:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 64, num_layers: 24, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.200179, loss: 0.119338, params: 6.023M, vram: 865.2MB, speed: 15.98Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 AM
