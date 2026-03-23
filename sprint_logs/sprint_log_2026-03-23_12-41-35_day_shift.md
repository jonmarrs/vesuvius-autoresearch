# Day Shift Sprint - 2026-03-23
- **Start Time**: 12:41:35
- **Goal**: Monotonic val_bpb optimization via 5-min cycles.

## Cycle 1: dropout_0.3 (REVERTED)
- **Timestamp**: 12:46:40
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.3
- **Stats**: val_bpb: 0.042115, loss: 0.129301, params: 0.328M, vram: 1219.6MB, speed: 1.49Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 2: wd_0.05 (REVERTED)
- **Timestamp**: 12:51:47
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.05, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000763, loss: 0.006599, params: 0.328M, vram: 1309.0MB, speed: 1.64Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 3: lr_1e-4 (REVERTED)
- **Timestamp**: 12:56:55
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 1e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.001164, loss: 0.036358, params: 0.328M, vram: 1309.0MB, speed: 1.38Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 4: batch_size_2 (REVERTED)
- **Timestamp**: 13:02:04
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 5: batch_size_6 (REVERTED)
- **Timestamp**: 13:07:11
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 6, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000688, loss: 0.023947, params: 0.328M, vram: 3892.6MB, speed: 1.31Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 6: wd_0.001 (REVERTED)
- **Timestamp**: 13:12:19
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.001675, loss: 0.080318, params: 0.328M, vram: 1309.0MB, speed: 1.03Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 7: heads_8 (REVERTED)
- **Timestamp**: 13:17:28
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.009496, loss: 0.086545, params: 0.328M, vram: 1309.0MB, speed: 1.09Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 8: patch_size_32 (REVERTED)
- **Timestamp**: 13:22:36
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 32, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.018789, loss: 2.546309, params: 0.328M, vram: 343.4MB, speed: 0.32Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 9: patch_size_48 (REVERTED)
- **Timestamp**: 13:27:44
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 48, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.000830, loss: 0.009115, params: 0.328M, vram: 751.4MB, speed: 0.87Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 10: patch_size_48 (REVERTED)
- **Timestamp**: 13:32:50
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 48, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.005459, loss: 0.060473, params: 0.328M, vram: 751.4MB, speed: 0.87Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 11: heads_4 (REVERTED)
- **Timestamp**: 13:37:57
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 4, dropout: 0.4
- **Stats**: val_bpb: 0.000485, loss: 0.005888, params: 0.328M, vram: 1219.6MB, speed: 1.27Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 12: lr_3e-4 (REVERTED)
- **Timestamp**: 13:43:06
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.4
- **Stats**: val_bpb: 0.001017, loss: 0.006197, params: 0.328M, vram: 1309.0MB, speed: 1.21Mvps
- **Result**: No improvement detected. Changes reverted.

## Cycle 13: dropout_0.0 (REVERTED)
- **Timestamp**: 13:48:13
- **Data**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **Config**: lr: 3e-4, wd: 0.001, blocks: 10, batch_size: 2, patch_size: 64, num_layers: 12, base_feat: 32, heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.007395, loss: 0.078434, params: 0.328M, vram: 1244.0MB, speed: 1.11Mvps
- **Result**: No improvement detected. Changes reverted.

