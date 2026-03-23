# Day Shift Sprint - 2026-03-23
- **Start Time**: 09:56:10
- **Goal**: Monotonic val_bpb optimization via 5-min cycles.

## Cycle 1: patch_size_32 (REVERTED)
- **Timestamp**: 10:01:18
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 32, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.027387, loss: 0.887345, params: 0.267M, vram: 297.7MB, speed: 0.37Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: lr_5e-5 (REVERTED)
- **Timestamp**: 10:06:27
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 5e-5, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000782, loss: 0.031282, params: 0.267M, vram: 1128.2MB, speed: 1.52Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: base_feat_32 (REVERTED)
- **Timestamp**: 10:11:36
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000132, loss: 0.001363, params: 0.267M, vram: 1128.2MB, speed: 1.63Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: blocks_12 (REVERTED)
- **Timestamp**: 10:16:43
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 12, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000989, loss: 0.050483, params: 0.390M, vram: 1489.7MB, speed: 1.56Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: patch_size_48 (REVERTED)
- **Timestamp**: 10:21:50
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 48, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000725, loss: 0.006343, params: 0.267M, vram: 647.5MB, speed: 1.24Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: wd_0.0 (REVERTED)
- **Timestamp**: 10:26:57
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000388, loss: 0.010597, params: 0.267M, vram: 1128.2MB, speed: 1.70Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: heads_8 (REVERTED)
- **Timestamp**: 10:32:06
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.001560, loss: 0.021564, params: 0.267M, vram: 1128.2MB, speed: 1.28Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: num_layers_16 (REVERTED)
- **Timestamp**: 10:37:16
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000224, loss: 0.008480, params: 0.267M, vram: 1577.7MB, speed: 1.81Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_48 (REVERTED)
- **Timestamp**: 10:42:23
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 48, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.010378, loss: 0.106762, params: 0.267M, vram: 647.5MB, speed: 1.10Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: heads_8 (REVERTED)
- **Timestamp**: 10:47:30
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000490, loss: 0.006843, params: 0.267M, vram: 1128.2MB, speed: 1.78Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: patch_size_32 (REVERTED)
- **Timestamp**: 10:52:38
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 32, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.128159, loss: 1.537962, params: 0.267M, vram: 297.7MB, speed: 0.46Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: patch_size_32 (REVERTED)
- **Timestamp**: 10:57:44
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 32, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.008618, loss: 0.462464, params: 0.267M, vram: 297.7MB, speed: 0.51Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: lr_3e-4 (SUCCESS)
- **Timestamp**: 11:02:53
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000043, loss: 0.003072, params: 0.267M, vram: 1128.2MB, speed: 1.70Mvps
- **Result**: Improvement detected. Changes committed.

## Cycle 27: blocks_10 (SUCCESS)
- **Timestamp**: 12:14:41
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.0, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000027, loss: 0.002053, params: 0.328M, vram: 1309.0MB, speed: 1.18Mvps
- **Result**: Improvement detected. Changes committed.

