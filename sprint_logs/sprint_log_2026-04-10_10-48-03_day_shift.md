# Day Shift Sprint - 2026-04-10
- **Start Time**: 10:48:03
- **Goal**: Monotonic val_bpb optimization via 15-min cycles.

## Cycle 1: blocks_12 (REVERTED)
- **Timestamp**: 11:03:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 12, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.201393, loss: 0.266038, params: 4.152M, vram: 2477.0MB, speed: 54.83Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: heads_8 (REVERTED)
- **Timestamp**: 11:18:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400772, loss: 0.255188, params: 6.269M, vram: 3955.4MB, speed: 37.13Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: lr_5e-5 (REVERTED)
- **Timestamp**: 11:33:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 5e-5, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999749, loss: 0.501670, params: 6.269M, vram: 3955.4MB, speed: 37.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: base_feat_32 (REVERTED)
- **Timestamp**: 11:49:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 32, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999110, loss: 0.503809, params: 0.486M, vram: 3115.9MB, speed: 31.09Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: heads_12 (REVERTED)
- **Timestamp**: 11:49:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.999110, loss: 0.503809, params: 0.486M, vram: 3115.9MB, speed: 31.09Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: dropout_0.1 (REVERTED)
- **Timestamp**: 12:05:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.301810, loss: 0.284175, params: 6.269M, vram: 3955.4MB, speed: 23.90Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: blocks_16 (REVERTED)
- **Timestamp**: 12:20:23
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999678, loss: 0.503699, params: 5.210M, vram: 3213.5MB, speed: 42.69Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: dropout_0.2 (REVERTED)
- **Timestamp**: 12:35:45
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.400000, loss: 0.116232, params: 6.269M, vram: 3955.4MB, speed: 20.92Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: num_layers_12 (REVERTED)
- **Timestamp**: 12:51:18
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.501116, loss: 0.246639, params: 6.047M, vram: 2019.5MB, speed: 9.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: blocks_10 (REVERTED)
- **Timestamp**: 13:06:57
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 10, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.399998, loss: 0.195471, params: 3.623M, vram: 2105.8MB, speed: 39.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: patch_size_128 (REVERTED)
- **Timestamp**: 13:22:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500908, loss: 0.233909, params: 6.613M, vram: 10739.7MB, speed: 45.31Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: base_feat_64 (REVERTED)
- **Timestamp**: 13:37:36
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999651, loss: 0.502611, params: 1.693M, vram: 3362.9MB, speed: 24.53Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: patch_size_128 (REVERTED)
- **Timestamp**: 13:52:58
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450761, loss: 0.284132, params: 6.613M, vram: 10739.7MB, speed: 45.54Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 14: patch_size_96 (REVERTED)
- **Timestamp**: 14:08:19
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.350141, loss: 0.191344, params: 6.269M, vram: 3955.4MB, speed: 37.05Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 15: wd_0.01 (REVERTED)
- **Timestamp**: 14:23:47
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.500090, loss: 0.141370, params: 6.269M, vram: 3955.4MB, speed: 25.55Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 16: batch_size_8 (REVERTED)
- **Timestamp**: 14:39:05
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450208, loss: 0.288258, params: 6.269M, vram: 3955.4MB, speed: 18.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 17: dropout_0.2 (REVERTED)
- **Timestamp**: 14:54:24
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.999675, loss: 0.503923, params: 6.269M, vram: 3955.4MB, speed: 38.04Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 18: batch_size_4 (REVERTED)
- **Timestamp**: 15:09:44
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 4, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.300646, loss: 0.232456, params: 6.269M, vram: 3955.4MB, speed: 6.30Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 19: num_layers_16 (REVERTED)
- **Timestamp**: 15:25:07
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.200240, loss: 0.206069, params: 6.121M, vram: 2690.0MB, speed: 19.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 20: num_layers_12 (REVERTED)
- **Timestamp**: 15:40:31
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 12, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.353536, loss: 0.219936, params: 6.047M, vram: 2019.5MB, speed: 11.73Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 21: patch_size_128 (REVERTED)
- **Timestamp**: 15:55:59
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 128, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.949812, loss: 0.452831, params: 6.613M, vram: 10739.7MB, speed: 37.60Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 22: batch_size_16 (REVERTED)
- **Timestamp**: 16:11:25
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999619, loss: 0.501637, params: 6.269M, vram: 3955.4MB, speed: 17.57Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 23: lr_1e-4 (REVERTED)
- **Timestamp**: 16:26:54
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-4, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999608, loss: 0.504253, params: 6.269M, vram: 3955.4MB, speed: 31.95Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 24: dropout_0.0 (REVERTED)
- **Timestamp**: 16:42:15
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.250671, loss: 0.222994, params: 6.269M, vram: 2381.2MB, speed: 23.48Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 25: heads_12 (REVERTED)
- **Timestamp**: 16:42:39
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.250671, loss: 0.222994, params: 6.269M, vram: 2381.2MB, speed: 23.48Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 26: base_feat_128 (REVERTED)
- **Timestamp**: 16:58:10
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999775, loss: 0.502306, params: 6.269M, vram: 3955.4MB, speed: 24.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 27: batch_size_16 (REVERTED)
- **Timestamp**: 17:13:27
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999548, loss: 0.503470, params: 6.269M, vram: 3955.4MB, speed: 37.76Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 28: num_layers_16 (REVERTED)
- **Timestamp**: 17:28:43
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.550225, loss: 0.182205, params: 6.121M, vram: 2690.0MB, speed: 26.96Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 29: patch_size_96 (REVERTED)
- **Timestamp**: 17:44:00
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.400084, loss: 0.092967, params: 6.269M, vram: 3955.4MB, speed: 37.62Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 30: dropout_0.1 (REVERTED)
- **Timestamp**: 17:59:17
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450238, loss: 0.097922, params: 6.269M, vram: 3955.4MB, speed: 38.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 31: blocks_16 (REVERTED)
- **Timestamp**: 18:14:34
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 16, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999588, loss: 0.503538, params: 5.210M, vram: 3213.5MB, speed: 45.07Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 32: heads_12 (REVERTED)
- **Timestamp**: 18:14:48
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 128, heads: 12, dropout: 0.1
- **Stats**: val_bpb: 0.999588, loss: 0.503538, params: 5.210M, vram: 3213.5MB, speed: 45.07Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 33: base_feat_64 (REVERTED)
- **Timestamp**: 18:30:04
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 24, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.999691, loss: 0.502198, params: 1.693M, vram: 3362.9MB, speed: 37.98Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 34: batch_size_8 (REVERTED)
- **Timestamp**: 18:45:21
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 8, patch_size: 96, num_layers: 24, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.460490, loss: 0.200714, params: 6.269M, vram: 3955.4MB, speed: 18.91Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 35: num_layers_16 (REVERTED)
- **Timestamp**: 19:00:37
- **Data**: local_data/PHercParis2Fr47/surface_volume/
- **Config**: lr: 1e-3, wd: 0.01, blocks: 20, batch_size: 16, patch_size: 96, num_layers: 16, base_feat: 128, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.450049, loss: 0.171852, params: 6.121M, vram: 2690.0MB, speed: 26.85Mvps
- **Result**: No improvement detected. Changes reverted.


## Sprint Completed at 7:00 PM
