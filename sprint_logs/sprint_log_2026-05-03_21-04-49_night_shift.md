# Night Shift Sprint - 2026-05-03
- **Start Time**: 21:04:49
- **Goal**: Monotonic val_bpb optimization via 60-min cycles (Config-Driven).

## Cycle 1: aug_mode_albumentations (SUCCESS)
- **Timestamp**: 22:05:47
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.41435245752334593, loss: 0.8882382079817224, params: 10.221186M, vram: 6058.26904296875MB, speed: 0.9075338747816343Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 2: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 23:07:05
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4173927639424801, loss: 0.6721632720364176, params: 10.221186M, vram: 6057.26904296875MB, speed: 0.8733219634062868Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: batch_size_8 (REVERTED)
- **Timestamp**: 00:07:36
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.42865423325449226, loss: 0.7872430634831772, params: 10.221186M, vram: 3240.0322265625MB, speed: 0.9998995350128812Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: use_ridges_True (REVERTED)
- **Timestamp**: 01:08:39
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: True, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.41627325922250746, loss: 0.8313809060671727, params: 10.222914M, vram: 6077.85400390625MB, speed: 1.0381311514197562Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: num_heads_4 (CRASHED)
- **Timestamp**: 01:59:26
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 6: loss_ink_dice_0.2 (SUCCESS)
- **Timestamp**: 03:00:25
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4141129274666309, loss: 0.7159587231329908, params: 10.221186M, vram: 6054.08154296875MB, speed: 1.0397798041068669Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 7: base_feat_32 (CRASHED)
- **Timestamp**: 03:50:30
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 32, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 8: loss_st_0.2 (REVERTED)
- **Timestamp**: 04:51:20
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.2, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.41450986355543135, loss: 0.692895148131397, params: 10.221186M, vram: 6057.26904296875MB, speed: 1.0519965920286525Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 05:52:11
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.1, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.4144029147922993, loss: 0.6658331209380073, params: 10.221186M, vram: 6057.20654296875MB, speed: 1.0488583042532025Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: use_ridges_True (REVERTED)
- **Timestamp**: 06:53:14
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: True, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.41520066529512406, loss: 0.6525870307803459, params: 10.222914M, vram: 6077.72900390625MB, speed: 1.0384584588144714Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: architecture_timesformer (CRASHED)
- **Timestamp**: 06:53:24
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: timesformer, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 15: weight_decay_0.1 (REVERTED)
- **Timestamp**: 07:54:23
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.1, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1
- **Stats**: val_bpb: 0.41697939559817315, loss: 0.5973924274456057, params: 10.221186M, vram: 6056.95654296875MB, speed: 0.9897915696673246Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:54:30
Transitioning to NIGHT SHIFT...
