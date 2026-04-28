# Day Shift Sprint - 2026-04-25
- **Start Time**: 11:47:15
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: loss_ink_dice_0.4 (CRASHED)
- **Timestamp**: 12:07:15
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 2: loss_ink_dice_0.2 (CRASHED)
- **Timestamp**: 12:27:17
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 3: loss_st_0.2 (CRASHED)
- **Timestamp**: 12:47:19
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.2, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 4: loss_fiber_bce_0.3 (CRASHED)
- **Timestamp**: 13:07:21
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 5: loss_st_0.0 (CRASHED)
- **Timestamp**: 13:27:23
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.0, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 6: loss_fiber_bce_0.1 (CRASHED)
- **Timestamp**: 13:47:30
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 7: loss_ink_dice_0.6 (CRASHED)
- **Timestamp**: 14:07:32
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 8: ridge_sigma_1.0 (CRASHED)
- **Timestamp**: 14:27:34
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 9: batch_size_8 (CRASHED)
- **Timestamp**: 14:47:36
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 11: loss_st_0.2 (CRASHED)
- **Timestamp**: 15:07:38
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 12: loss_ink_bce_0.6 (CRASHED)
- **Timestamp**: 15:27:40
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 13: ridge_sigma_3.0 (CRASHED)
- **Timestamp**: 15:47:42
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 3.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 14: num_heads_8 (CRASHED (OOM))
- **Timestamp**: 15:47:55
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 15: batch_size_24 (CRASHED)
- **Timestamp**: 16:07:57
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 24, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 16: num_heads_12 (CRASHED (OOM))
- **Timestamp**: 16:08:14
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 17: use_ridges_True (CRASHED)
- **Timestamp**: 16:08:23
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: True, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 18: num_layers_32 (CRASHED)
- **Timestamp**: 16:28:25
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 19: loss_ink_bce_0.2 (CRASHED)
- **Timestamp**: 16:48:27
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 21: lr_0.001 (CRASHED)
- **Timestamp**: 17:08:29
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 22: dropout_0.1 (CRASHED)
- **Timestamp**: 17:28:31
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 23: num_blocks_8 (CRASHED)
- **Timestamp**: 17:48:33
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 24: weight_decay_0.0 (CRASHED)
- **Timestamp**: 18:08:35
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.0, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 25: lr_0.0001 (CRASHED)
- **Timestamp**: 18:28:37
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 0.0001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 26: loss_ink_dice_0.4 (CRASHED)
- **Timestamp**: 18:48:42
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 27: num_blocks_12 (CRASHED)
- **Timestamp**: 19:08:44
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 48, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 12, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.


## Sprint Completed at 19:08:46
Transitioning to NIGHT SHIFT...
