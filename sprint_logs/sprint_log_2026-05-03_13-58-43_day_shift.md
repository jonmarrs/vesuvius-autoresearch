# Day Shift Sprint - 2026-05-03
- **Start Time**: 13:58:43
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: architecture_resenc_unet (SUCCESS)
- **Timestamp**: 14:15:06
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4348419015109539, loss: 0.7562502183037246, params: 10.221186M, vram: 4721.15966796875MB, speed: 0.7253481982417092Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 2: num_layers_16 (SUCCESS)
- **Timestamp**: 14:31:31
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.43392683655023573, loss: 0.7174322634453834, params: 10.221186M, vram: 3240.5947265625MB, speed: 0.7841669408490737Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 3: loss_fiber_bce_0.3 (SUCCESS)
- **Timestamp**: 14:47:16
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.43352827824652196, loss: 0.813268944583485, params: 10.221186M, vram: 3238.4072265625MB, speed: 0.6930384486313388Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 4: loss_ink_bce_0.6 (SUCCESS)
- **Timestamp**: 15:02:50
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.43209410443902013, loss: 0.843194244019951, params: 10.221186M, vram: 3239.0322265625MB, speed: 1.030749115899542Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 5: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 15:18:49
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4382350986450911, loss: 0.6834438465322095, params: 10.221186M, vram: 3240.9072265625MB, speed: 0.8855886311779573Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: loss_st_0.0 (REVERTED)
- **Timestamp**: 15:34:34
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.0, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.44850898131728173, loss: 0.8340051549523214, params: 10.221186M, vram: 3239.5947265625MB, speed: 0.8457863277124875Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: aug_mode_batchgeneratorsv2 (SUCCESS)
- **Timestamp**: 15:50:10
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4303992448747158, loss: 0.8827130746583005, params: 10.221186M, vram: 3239.0322265625MB, speed: 0.9890866078467287Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 8: lr_0.0005 (REVERTED)
- **Timestamp**: 16:05:44
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.0005, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.43132815018296244, loss: 0.7762837858231209, params: 10.221186M, vram: 3238.9072265625MB, speed: 1.0169534486203826Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: num_layers_24 (REVERTED)
- **Timestamp**: 16:21:19
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4336954380944371, loss: 0.9070779297578832, params: 10.221186M, vram: 4761.0322265625MB, speed: 1.1684841813672553Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 16:37:04
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.6, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: None, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4612743651121855, loss: 1.0860571557579284, params: 10.221186M, vram: 3239.5947265625MB, speed: 0.8095215005160725Mvps
- **Result**: No improvement detected. Config reverted.

