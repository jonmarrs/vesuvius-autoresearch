# Night Shift Sprint - 2026-04-30
- **Start Time**: 21:54:59
- **Goal**: Monotonic val_bpb optimization via 60-min cycles (Config-Driven).

## Cycle 1: loss_st_0.0 (REVERTED)
- **Timestamp**: 22:55:19
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.0, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.8201430414203856, params: 1.308793M, vram: 6873.0654296875MB, speed: 6.397730466254546Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: num_heads_12 (REVERTED)
- **Timestamp**: 23:55:39
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.2763273717433133, params: 1.308793M, vram: 8718.8154296875MB, speed: 6.335313332257254Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: batch_size_16 (REVERTED)
- **Timestamp**: 00:56:08
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.29468079813246717, params: 1.308793M, vram: 13700.65625MB, speed: 8.807016704806907Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: lr_0.001 (REVERTED)
- **Timestamp**: 01:56:29
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 1.0343859663193224, params: 1.308793M, vram: 6872.0654296875MB, speed: 6.072115097722481Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: num_blocks_12 (REVERTED)
- **Timestamp**: 02:56:54
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 12, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.8999349584601298, params: 1.575801M, vram: 8272.3525390625MB, speed: 5.244051972208192Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 03:57:12
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 1.9389005896633276, params: 1.308793M, vram: 6870.1904296875MB, speed: 7.1186208507464395Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 04:12:28
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.6616242590267495, params: 1.308793M, vram: 6869.9404296875MB, speed: 7.231341976691324Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 05:12:50
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 1.0189232518568128, params: 1.308793M, vram: 6870.3154296875MB, speed: 7.083282367938627Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: lr_5e-05 (REVERTED)
- **Timestamp**: 06:13:12
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 5e-05, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.4678414121073919, params: 1.308793M, vram: 6871.4404296875MB, speed: 6.796151932046031Mvps
- **Result**: No improvement detected. Config reverted.
