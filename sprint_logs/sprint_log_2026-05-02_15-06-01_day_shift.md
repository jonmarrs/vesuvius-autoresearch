# Day Shift Sprint - 2026-05-02
- **Start Time**: 15:06:01
- **Goal**: Monotonic val_bpb optimization via 60-min cycles (Config-Driven).

## Cycle 3: base_feat_128 (REVERTED)
- **Timestamp**: 16:06:29
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 128, num_blocks: 8, num_heads: 4, dropout: 0.2, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 1.0, loss: 0.5178714692897166, params: 3.429353M, vram: 11768.15283203125MB, speed: 4.197339498153035Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 17:06:56
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 1.0, loss: 0.7541861449616541, params: 1.308793M, vram: 6865.5341796875MB, speed: 4.640231713804693Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 18:07:18
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 1.0, loss: 0.6279905722350734, params: 1.308793M, vram: 6866.4091796875MB, speed: 4.74652845679608Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: architecture_i3d (CRASHED)
- **Timestamp**: 18:07:33
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: i3d, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 7: weight_decay_0.0 (REVERTED)
- **Timestamp**: 19:07:53
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 1.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 0.0005, weight_decay: 0.0, time_budget: 3600, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: gated_unet, base_feat: 64, num_blocks: 8, num_heads: 4, dropout: 0.2, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 1.0, loss: 1.0861488211528765, params: 1.308793M, vram: 6866.2841796875MB, speed: 6.526754405462051Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 19:07:55
Transitioning to DAY SHIFT...
