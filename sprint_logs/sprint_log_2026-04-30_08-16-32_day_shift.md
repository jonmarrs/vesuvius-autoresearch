# Day Shift Sprint - 2026-04-30
- **Start Time**: 08:16:32
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: dropout_0.0 (REVERTED)
- **Timestamp**: 08:32:10
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.0, loss: 0.14015080628228674, params: 1.842809M, vram: 8988.0107421875MB, speed: 2.5817086227912305Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: aug_mode_batchgeneratorsv2 (REVERTED)
- **Timestamp**: 08:47:33
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.1570275257633895, params: 1.842809M, vram: 9677.0107421875MB, speed: 3.3312784878274972Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 09:02:51
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.5168605150821183, params: 1.842809M, vram: 9675.5732421875MB, speed: 3.9905021035302517Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: ridge_sigma_2.0 (REVERTED)
- **Timestamp**: 09:18:07
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.3196858767146649, params: 1.842809M, vram: 9677.4482421875MB, speed: 4.073036480830579Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: loss_st_0.2 (REVERTED)
- **Timestamp**: 09:33:24
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.2, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 2.74658203125e-06, loss: 0.5114080180492013, params: 1.842809M, vram: 9679.0732421875MB, speed: 4.055918237565506Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: num_heads_8 (REVERTED)
- **Timestamp**: 09:48:41
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.2671704922298693, params: 1.842809M, vram: 13373.5107421875MB, speed: 3.748818888105776Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: base_feat_64 (REVERTED)
- **Timestamp**: 10:03:58
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.8159549540004177, params: 1.842809M, vram: 9678.6982421875MB, speed: 4.0438806682040465Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 10:19:28
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.24012586880928044, params: 1.842809M, vram: 9675.5732421875MB, speed: 2.834348266306916Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: lr_0.0001 (REVERTED)
- **Timestamp**: 10:34:56
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0, loss: 0.14254646176784672, params: 1.842809M, vram: 9676.8232421875MB, speed: 3.2480418662830273Mvps
- **Result**: No improvement detected. Config reverted.

