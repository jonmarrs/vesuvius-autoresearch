# Night Shift Sprint - 2026-03-28
- **Start Time**: 23:20:23
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: lr_5e-5 (REVERTED)
- **Timestamp**: 23:36:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999624, loss: 0.501869, params: 3.475M, vram: 1436.2MB, speed: 13.53Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: patch_size_128 (REVERTED)
- **Timestamp**: 23:51:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400157, loss: 0.240209, params: 6.351M, vram: 7163.5MB, speed: 15.67Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: base_feat_64 (REVERTED)
- **Timestamp**: 00:07:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999809, loss: 0.501862, params: 1.619M, vram: 2253.7MB, speed: 10.89Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: lr_1e-3 (REVERTED)
- **Timestamp**: 00:23:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450177, loss: 0.177257, params: 6.121M, vram: 2690.0MB, speed: 10.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: lr_1e-3 (REVERTED)
- **Timestamp**: 00:38:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400267, loss: 0.129500, params: 6.121M, vram: 2690.0MB, speed: 10.59Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: lr_1e-5 (REVERTED)
- **Timestamp**: 00:54:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999662, loss: 0.504313, params: 6.121M, vram: 2690.0MB, speed: 11.14Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: lr_5e-5 (REVERTED)
- **Timestamp**: 01:09:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999697, loss: 0.504109, params: 6.121M, vram: 2690.0MB, speed: 10.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: lr_1e-3 (REVERTED)
- **Timestamp**: 01:25:16
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450060, loss: 0.177936, params: 6.121M, vram: 2690.0MB, speed: 11.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: num_layers_24 (REVERTED)
- **Timestamp**: 01:40:46
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250692, loss: 0.214464, params: 6.269M, vram: 3955.4MB, speed: 15.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: batch_size_16 (REVERTED)
- **Timestamp**: 01:56:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.549999, loss: 0.266082, params: 6.121M, vram: 2690.0MB, speed: 21.82Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: blocks_10 (REVERTED)
- **Timestamp**: 02:11:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999785, loss: 0.502607, params: 3.475M, vram: 1436.2MB, speed: 17.34Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: dropout_0.1 (REVERTED)
- **Timestamp**: 02:27:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999796, loss: 0.502875, params: 6.121M, vram: 2690.0MB, speed: 10.82Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: lr_1e-5 (REVERTED)
- **Timestamp**: 02:43:12
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-5, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999569, loss: 0.504306, params: 6.121M, vram: 2690.0MB, speed: 11.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: base_feat_128 (REVERTED)
- **Timestamp**: 02:58:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300011, loss: 0.177523, params: 6.121M, vram: 2690.0MB, speed: 10.81Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: num_layers_12 (REVERTED)
- **Timestamp**: 03:14:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999725, loss: 0.503240, params: 6.047M, vram: 2019.5MB, speed: 8.25Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: wd_0.001 (REVERTED)
- **Timestamp**: 03:30:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.001, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300160, loss: 0.176253, params: 6.121M, vram: 2690.0MB, speed: 10.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: blocks_12 (REVERTED)
- **Timestamp**: 03:45:40
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450356, loss: 0.269748, params: 4.005M, vram: 1688.3MB, speed: 15.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: num_layers_12 (REVERTED)
- **Timestamp**: 04:01:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200315, loss: 0.162181, params: 6.047M, vram: 2019.5MB, speed: 8.36Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: base_feat_32 (REVERTED)
- **Timestamp**: 04:16:51
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999629, loss: 0.502488, params: 6.121M, vram: 2690.0MB, speed: 11.07Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: heads_8 (REVERTED)
- **Timestamp**: 04:32:22
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.399998, loss: 0.106400, params: 6.121M, vram: 2690.0MB, speed: 21.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: lr_5e-4 (REVERTED)
- **Timestamp**: 04:48:11
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-4, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999749, loss: 0.503660, params: 6.121M, vram: 2690.0MB, speed: 10.17Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: base_feat_64 (REVERTED)
- **Timestamp**: 05:03:41
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450250, loss: 0.233232, params: 6.121M, vram: 1784.1MB, speed: 10.94Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: patch_size_64 (REVERTED)
- **Timestamp**: 05:19:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 64, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300382, loss: 0.110050, params: 1.619M, vram: 2253.7MB, speed: 10.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: num_layers_24 (REVERTED)
- **Timestamp**: 05:35:35
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.250354, loss: 0.163707, params: 6.269M, vram: 3955.4MB, speed: 14.30Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: dropout_0.1 (REVERTED)
- **Timestamp**: 05:51:30
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999512, loss: 0.503747, params: 6.121M, vram: 2690.0MB, speed: 5.50Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: lr_1e-4 (REVERTED)
- **Timestamp**: 06:07:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 16, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999806, loss: 0.501563, params: 5.063M, vram: 2189.3MB, speed: 13.01Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: heads_8 (REVERTED)
- **Timestamp**: 06:22:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.299907, loss: 0.199365, params: 4.005M, vram: 1688.3MB, speed: 15.99Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: patch_size_128 (REVERTED)
- **Timestamp**: 06:38:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 128, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999484, loss: 0.501922, params: 6.351M, vram: 7163.5MB, speed: 11.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: blocks_10 (REVERTED)
- **Timestamp**: 06:54:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999818, loss: 0.501986, params: 3.475M, vram: 1436.2MB, speed: 16.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: wd_0.0 (REVERTED)
- **Timestamp**: 07:10:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.0, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300412, loss: 0.139404, params: 6.121M, vram: 1627.1MB, speed: 11.59Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 AM
