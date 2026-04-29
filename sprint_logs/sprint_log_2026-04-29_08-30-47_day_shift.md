# Day Shift Sprint - 2026-04-29
- **Start Time**: 08:30:47
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: weight_decay_0.001 (REVERTED)
- **Timestamp**: 08:46:06
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.001, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.7816893577637857, params: 1.842809M, vram: 8985.76025390625MB, speed: 3.9110167655919525Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: batch_size_8 (REVERTED)
- **Timestamp**: 09:01:26
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.555484732897207, params: 1.842809M, vram: 8987.63525390625MB, speed: 4.011121789882377Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: architecture_i3d (CRASHED)
- **Timestamp**: 09:01:39
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: i3d, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 4: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 09:01:53
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 24, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 5: use_ridges_True (CRASHED)
- **Timestamp**: 09:02:01
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: True, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 6: architecture_resenc_unet (CRASHED)
- **Timestamp**: 09:02:17
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 7: architecture_resnet3d (CRASHED)
- **Timestamp**: 09:02:29
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: resnet3d, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 8: loss_st_0.0 (REVERTED)
- **Timestamp**: 09:17:47
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.0, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.6818100249082696, params: 1.842809M, vram: 8990.13525390625MB, speed: 3.9881980206538667Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: num_layers_16 (REVERTED)
- **Timestamp**: 09:33:04
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.00031111955642700197, loss: 0.5463055612713945, params: 1.842809M, vram: 4562.01025390625MB, speed: 2.09739665725304Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: gp_winner_baseline (CRASHED)
- **Timestamp**: 09:33:12
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume/'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 256, num_layers: 16, lr: 3e-05, weight_decay: 0.01, time_budget: 900, pinned: True, loss_ink_bce: 0.5, loss_ink_dice: 0.5, loss_fiber_bce: 0.0, loss_st: 0.0, label_smoothing: 0.25, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 11: architecture_timesformer (REVERTED)
- **Timestamp**: 09:48:41
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.3253913435692877, params: 33.765685M, vram: 3960.6875MB, speed: 5.133364421770493Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: dropout_0.1 (REVERTED)
- **Timestamp**: 10:04:10
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.1
- **Stats**: val_bpb: 0.0, loss: 0.34343123073946946, params: 1.842809M, vram: 9679.01025390625MB, speed: 3.747364048074599Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: aug_mode_albumentations (REVERTED)
- **Timestamp**: 10:19:41
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 9.766817092895509e-06, loss: 0.32282311870025376, params: 1.842809M, vram: 8986.69775390625MB, speed: 2.217433173623679Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: num_blocks_12 (REVERTED)
- **Timestamp**: 10:35:06
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 12, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0001158308982849121, loss: 0.5604945942938779, params: 1.575801M, vram: 7757.22314453125MB, speed: 3.9160952716987065Mvps
- **Result**: No improvement detected. Config reverted.

