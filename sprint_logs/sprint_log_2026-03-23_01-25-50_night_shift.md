# Night Shift Sprint - 2026-03-23
- **Start Time**: 01:25:50
- **Goal**: Monotonic val_bpb optimization via 5-min cycles.

## Cycle 1: blocks_10 (REVERTED)
- **Timestamp**: 01:30:55
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 10, batch_size: 4, patch_size: 64, num_layers: 12, base_feat: 64, heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.002402, loss: 0.154113, params: 1.278M, vram: 4814.5MB, speed: 1.21Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: batch_size_6 (SUCCESS)
- **Timestamp**: 01:36:04
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 6, patch_size: 64, num_layers: 16, base_feat: 64, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000434, loss: 0.007496, params: 1.032M, vram: 8388.5MB, speed: 1.47Mvps
- **Result**: Improvement detected. Changes committed.

## Cycle 5: base_feat_32 (SUCCESS)
- **Timestamp**: 01:51:24
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 6, patch_size: 64, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000389, loss: 0.006907, params: 0.267M, vram: 4696.5MB, speed: 2.17Mvps
- **Result**: Improvement detected. Changes committed.

## Cycle 10: batch_size_2 (SUCCESS)
- **Timestamp**: 02:17:00
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000153, loss: 0.004661, params: 0.267M, vram: 1577.7MB, speed: 2.28Mvps
- **Result**: Improvement detected. Changes committed.

## Cycle 28: lr_1e-4 (SUCCESS)
- **Timestamp**: 03:49:01
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.0, blocks: 8, batch_size: 2, patch_size: 64, num_layers: 16, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000088, loss: 0.004095, params: 0.267M, vram: 1577.7MB, speed: 2.27Mvps
- **Result**: Improvement detected. Changes committed.


## Sprint Completed at 7:00 AM
