# Day Shift Sprint - 2026-04-27
- **Start Time**: 08:18:20
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: ridge_sigma_1.0 (REVERTED)
- **Timestamp**: 08:33:49
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.30902026500350327, params: 1.842809M, vram: 8988.38525390625MB, speed: 3.5659700637232605Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: architecture_i3d (CRASHED)
- **Timestamp**: 08:34:05
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: i3d, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 3: base_feat_128 (REVERTED)
- **Timestamp**: 08:49:25
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 128, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.24804812896778405, params: 5.545961M, vram: 14692.4375MB, speed: 3.2830604226824245Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: num_layers_16 (REVERTED)
- **Timestamp**: 09:04:43
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.00022517740726470947, loss: 0.7452920907716793, params: 1.842809M, vram: 4560.13525390625MB, speed: 1.9751481338155146Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: architecture_resenc_unet (CRASHED)
- **Timestamp**: 09:04:56
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 6: architecture_timesformer (REVERTED)
- **Timestamp**: 09:20:27
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.9851485637563404, params: 33.765685M, vram: 3948.6484375MB, speed: 4.691447834272168Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: num_layers_16 (REVERTED)
- **Timestamp**: 09:36:00
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.2833342332021817, params: 1.842809M, vram: 8989.57275390625MB, speed: 2.10984265184058Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: num_blocks_8 (REVERTED)
- **Timestamp**: 09:51:49
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0016454678773880004, loss: 0.5351181738864769, params: 1.308793M, vram: 6526.37353515625MB, speed: 1.8673610181551783Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: weight_decay_0.1 (REVERTED)
- **Timestamp**: 10:07:52
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.1, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.5832072888053225, params: 1.842809M, vram: 8985.26025390625MB, speed: 1.4687817909418859Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: gp_winner_baseline (CRASHED)
- **Timestamp**: 10:08:13
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume/'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 256, num_layers: 16, lr: 3e-05, weight_decay: 0.01, time_budget: 900, pinned: True, loss_ink_bce: 0.5, loss_ink_dice: 0.5, loss_fiber_bce: 0.0, loss_st: 0.0, label_smoothing: 0.25, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 11: num_blocks_12 (REVERTED)
- **Timestamp**: 10:24:11
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 12, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.001484416127204895, loss: 0.45279087435499255, params: 1.575801M, vram: 7758.66064453125MB, speed: 1.7671269338355433Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: patch_size_96 (REVERTED)
- **Timestamp**: 10:40:11
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 96, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.013869609832763672, loss: 0.5754872675679612, params: 1.842809M, vram: 15036.69775390625MB, speed: 2.5048120033206294Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: lr_1e-05 (CRASHED)
- **Timestamp**: 11:00:17
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 14: num_heads_12 (CRASHED)
- **Timestamp**: 11:20:20
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.
