# Night Shift Sprint - 2026-04-27
- **Start Time**: 23:04:58
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: use_ridges_False (REVERTED)
- **Timestamp**: 23:20:23
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.2721220151597345, params: 1.842809M, vram: 8986.51025390625MB, speed: 2.891361194618193Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: use_ridges_True (CRASHED)
- **Timestamp**: 23:20:31
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: True, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 3: num_blocks_10 (REVERTED)
- **Timestamp**: 23:35:51
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 10, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 1.3580322265625e-05, loss: 0.6658177867577328, params: 1.442297M, vram: 7142.86083984375MB, speed: 3.631539925816639Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 23:36:07
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 24, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 5: weight_decay_0.0 (REVERTED)
- **Timestamp**: 23:51:28
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.0, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.34664518561227287, params: 1.842809M, vram: 8989.51025390625MB, speed: 3.512578994179618Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: batch_size_16 (REVERTED)
- **Timestamp**: 00:06:57
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.3679060658413781, params: 1.842809M, vram: 17921.53857421875MB, speed: 4.5309338470959695Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: num_heads_12 (REVERTED)
- **Timestamp**: 00:22:16
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.6644253729967221, params: 1.842809M, vram: 8988.01025390625MB, speed: 3.6339068502072402Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: dropout_0.2 (REVERTED)
- **Timestamp**: 00:37:35
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.5175677347372101, params: 1.842809M, vram: 9675.26025390625MB, speed: 3.58069170093888Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: num_heads_8 (REVERTED)
- **Timestamp**: 00:52:53
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.5979730907453413, params: 1.842809M, vram: 8989.19775390625MB, speed: 3.6366792454849426Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: gp_winner_baseline (CRASHED)
- **Timestamp**: 00:53:01
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume/'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 256, num_layers: 16, lr: 3e-05, weight_decay: 0.01, time_budget: 900, pinned: True, loss_ink_bce: 0.5, loss_ink_dice: 0.5, loss_fiber_bce: 0.0, loss_st: 0.0, label_smoothing: 0.25, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 11: ridge_sigma_3.0 (REVERTED)
- **Timestamp**: 01:08:24
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 3.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.38168209861453295, params: 1.842809M, vram: 8988.51025390625MB, speed: 3.6500348945155006Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: num_blocks_20 (REVERTED)
- **Timestamp**: 01:23:42
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 20, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 3.35693359375e-06, loss: 0.3514327647124452, params: 2.109817M, vram: 10217.48486328125MB, speed: 3.283083852761595Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: aug_mode_batchgeneratorsv2 (REVERTED)
- **Timestamp**: 01:39:01
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.34008077308776746, params: 1.842809M, vram: 8986.76025390625MB, speed: 3.6545847934335276Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: aug_mode_albumentations (REVERTED)
- **Timestamp**: 01:54:20
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.00010391771793365479, loss: 0.34367613019487214, params: 1.842809M, vram: 8987.13525390625MB, speed: 4.578388478356611Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: batch_size_8 (REVERTED)
- **Timestamp**: 02:09:38
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.30608900908379394, params: 1.842809M, vram: 8988.38525390625MB, speed: 3.70679972670518Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: lr_0.0005 (REVERTED)
- **Timestamp**: 02:25:01
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.622745877945887, params: 1.842809M, vram: 8988.01025390625MB, speed: 3.687004582205675Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: use_ridges_True (REVERTED)
- **Timestamp**: 02:40:19
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.7891810447912242, params: 1.842809M, vram: 8989.32275390625MB, speed: 3.7685060707593965Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: num_layers_16 (REVERTED)
- **Timestamp**: 02:55:37
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.29469671259152125, params: 1.842809M, vram: 8985.76025390625MB, speed: 3.7105479210143084Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: base_feat_32 (REVERTED)
- **Timestamp**: 03:10:54
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 32, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.22656518936157227, loss: 0.6985092843016808, params: 0.836865M, vram: 6209.11328125MB, speed: 3.812691280712491Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: gp_winner_baseline (CRASHED)
- **Timestamp**: 03:11:02
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume/'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 256, num_layers: 16, lr: 3e-05, weight_decay: 0.01, time_budget: 900, pinned: True, loss_ink_bce: 0.5, loss_ink_dice: 0.5, loss_fiber_bce: 0.0, loss_st: 0.0, label_smoothing: 0.25, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 21: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 03:26:24
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.6783602519226097, params: 1.842809M, vram: 8988.63525390625MB, speed: 3.714427003891628Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: architecture_resnet3d (CRASHED)
- **Timestamp**: 03:26:37
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: resnet3d, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 23: num_blocks_12 (REVERTED)
- **Timestamp**: 03:41:55
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.6871490401096964, params: 1.842809M, vram: 8988.51025390625MB, speed: 3.7215301838625603Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 03:57:13
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.4557140245532817, params: 1.842809M, vram: 8986.51025390625MB, speed: 3.7799223508410473Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: aug_mode_albumentations (REVERTED)
- **Timestamp**: 04:12:31
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.39791652062989064, params: 1.842809M, vram: 8985.38525390625MB, speed: 3.7867501095569813Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 26: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 04:27:53
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.7156428371100261, params: 1.842809M, vram: 8989.51025390625MB, speed: 3.764659382788226Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: num_layers_24 (REVERTED)
- **Timestamp**: 04:43:12
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 24, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0001709723472595215, loss: 0.7225917270468074, params: 1.842809M, vram: 6788.07275390625MB, speed: 2.962426312621605Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: lr_5e-05 (REVERTED)
- **Timestamp**: 04:58:29
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 5e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.9362111980782161, params: 1.842809M, vram: 8992.01025390625MB, speed: 3.76892687018067Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 05:13:47
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.3976008541978608, params: 1.842809M, vram: 8987.44775390625MB, speed: 3.7895998000757785Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: gp_winner_baseline (CRASHED)
- **Timestamp**: 05:13:54
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume/'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 256, num_layers: 16, lr: 3e-05, weight_decay: 0.01, time_budget: 900, pinned: True, loss_ink_bce: 0.5, loss_ink_dice: 0.5, loss_fiber_bce: 0.0, loss_st: 0.0, label_smoothing: 0.25, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 31: aug_mode_albumentations (REVERTED)
- **Timestamp**: 05:29:16
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.37333828658162815, params: 1.842809M, vram: 8988.38525390625MB, speed: 3.8349327848138657Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 32: batch_size_24 (REVERTED)
- **Timestamp**: 05:44:34
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.4130182818632144, params: 1.842809M, vram: 8990.07275390625MB, speed: 3.848205322806131Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 33: num_layers_24 (REVERTED)
- **Timestamp**: 05:59:52
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.674560739142792, params: 1.842809M, vram: 8985.76025390625MB, speed: 3.8089605763300627Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 34: use_ridges_False (REVERTED)
- **Timestamp**: 06:15:10
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.6141577471337477, params: 1.842809M, vram: 8986.88525390625MB, speed: 3.822448520363485Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 35: loss_st_0.1 (REVERTED)
- **Timestamp**: 06:30:27
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.31815847861910584, params: 1.842809M, vram: 8986.51025390625MB, speed: 3.8412134091366514Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 36: lr_1e-05 (REVERTED)
- **Timestamp**: 06:45:49
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.324752001278121, params: 1.842809M, vram: 8989.38525390625MB, speed: 3.8411593046275723Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 37: lr_0.0001 (REVERTED)
- **Timestamp**: 07:01:07
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.3068948406948562, params: 1.842809M, vram: 8986.88525390625MB, speed: 3.846220212781496Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:01:09
Transitioning to DAY SHIFT...
