# Night Shift Sprint - 2026-03-31
- **Start Time**: 22:36:49
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: num_layers_16 (REVERTED)
- **Timestamp**: 22:52:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300227, loss: 0.164907, params: 6.121M, vram: 2690.0MB, speed: 12.84Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: batch_size_4 (REVERTED)
- **Timestamp**: 23:07:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.399998, loss: 0.178065, params: 6.121M, vram: 2690.0MB, speed: 6.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: batch_size_8 (REVERTED)
- **Timestamp**: 23:23:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400177, loss: 0.184767, params: 6.121M, vram: 2690.0MB, speed: 12.93Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: batch_size_8 (REVERTED)
- **Timestamp**: 23:38:42
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450428, loss: 0.154128, params: 6.121M, vram: 2690.0MB, speed: 12.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: blocks_20 (REVERTED)
- **Timestamp**: 23:54:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350482, loss: 0.208832, params: 6.121M, vram: 2690.0MB, speed: 13.15Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: batch_size_16 (REVERTED)
- **Timestamp**: 00:09:28
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999591, loss: 0.502901, params: 6.121M, vram: 2690.0MB, speed: 25.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: base_feat_32 (REVERTED)
- **Timestamp**: 00:24:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999841, loss: 0.501450, params: 0.449M, vram: 2085.6MB, speed: 13.11Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: wd_0.1 (REVERTED)
- **Timestamp**: 00:40:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999883, loss: 0.503818, params: 6.121M, vram: 2690.0MB, speed: 13.11Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_128 (REVERTED)
- **Timestamp**: 00:55:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999693, loss: 0.502744, params: 6.351M, vram: 7163.5MB, speed: 21.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: dropout_0.1 (REVERTED)
- **Timestamp**: 01:11:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350543, loss: 0.152372, params: 6.121M, vram: 2690.0MB, speed: 13.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: base_feat_64 (REVERTED)
- **Timestamp**: 01:26:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999515, loss: 0.502396, params: 1.619M, vram: 2253.7MB, speed: 12.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: lr_5e-4 (REVERTED)
- **Timestamp**: 01:41:50
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999646, loss: 0.502680, params: 6.121M, vram: 2690.0MB, speed: 13.09Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: wd_0.001 (REVERTED)
- **Timestamp**: 01:57:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999719, loss: 0.501362, params: 6.121M, vram: 2690.0MB, speed: 13.16Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: patch_size_96 (REVERTED)
- **Timestamp**: 02:12:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350010, loss: 0.185892, params: 6.121M, vram: 2690.0MB, speed: 12.75Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: wd_0.0 (REVERTED)
- **Timestamp**: 02:27:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500170, loss: 0.164253, params: 6.121M, vram: 2690.0MB, speed: 13.17Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: num_layers_12 (REVERTED)
- **Timestamp**: 02:43:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300488, loss: 0.140184, params: 6.047M, vram: 2019.5MB, speed: 9.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: patch_size_64 (REVERTED)
- **Timestamp**: 02:58:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.401859, loss: 0.238895, params: 5.957M, vram: 788.9MB, speed: 5.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: base_feat_64 (REVERTED)
- **Timestamp**: 03:14:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999746, loss: 0.502264, params: 1.619M, vram: 2253.7MB, speed: 12.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: patch_size_64 (REVERTED)
- **Timestamp**: 03:29:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.150458, loss: 0.135414, params: 5.957M, vram: 788.9MB, speed: 5.91Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: heads_4 (REVERTED)
- **Timestamp**: 03:44:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.450642, loss: 0.213747, params: 6.121M, vram: 1784.1MB, speed: 12.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: num_layers_12 (REVERTED)
- **Timestamp**: 04:00:09
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400406, loss: 0.229956, params: 6.047M, vram: 2019.5MB, speed: 9.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: patch_size_64 (REVERTED)
- **Timestamp**: 04:15:29
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400510, loss: 0.179382, params: 5.957M, vram: 788.9MB, speed: 5.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: wd_0.001 (REVERTED)
- **Timestamp**: 04:30:52
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999748, loss: 0.502040, params: 6.121M, vram: 2690.0MB, speed: 13.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: patch_size_128 (REVERTED)
- **Timestamp**: 04:46:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450517, loss: 0.224251, params: 6.351M, vram: 7163.5MB, speed: 21.51Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: wd_0.1 (REVERTED)
- **Timestamp**: 05:01:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.1, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400121, loss: 0.210000, params: 6.121M, vram: 2690.0MB, speed: 13.02Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: blocks_12 (REVERTED)
- **Timestamp**: 05:17:03
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200480, loss: 0.250728, params: 4.005M, vram: 1688.3MB, speed: 19.14Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: num_layers_16 (REVERTED)
- **Timestamp**: 05:32:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450179, loss: 0.203650, params: 6.121M, vram: 2690.0MB, speed: 12.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: num_layers_16 (REVERTED)
- **Timestamp**: 05:47:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999510, loss: 0.502558, params: 6.121M, vram: 2690.0MB, speed: 13.20Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: num_layers_16 (REVERTED)
- **Timestamp**: 06:03:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400632, loss: 0.113894, params: 6.121M, vram: 2690.0MB, speed: 13.08Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: patch_size_128 (REVERTED)
- **Timestamp**: 06:18:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500188, loss: 0.251454, params: 6.351M, vram: 7163.5MB, speed: 21.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: patch_size_128 (REVERTED)
- **Timestamp**: 06:33:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.204289, loss: 0.282378, params: 6.351M, vram: 7163.5MB, speed: 21.48Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: blocks_16 (REVERTED)
- **Timestamp**: 06:49:20
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400325, loss: 0.243357, params: 5.063M, vram: 2189.3MB, speed: 15.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: dropout_0.2 (REVERTED)
- **Timestamp**: 07:04:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.999446, loss: 0.502943, params: 6.121M, vram: 2690.0MB, speed: 12.98Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 AM
